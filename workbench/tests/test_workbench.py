"""Business-flow and privacy regressions, using the real governed public bundle."""
import io
import json
import os
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from docx import Document
from pypdf import PdfReader

from workbench.backend.app import ROOT, create_app
from workbench.backend.backup import restore_backup
from workbench.backend.demo import demo_photo
from workbench.backend.knowledge import Knowledge, KnowledgeError


class WorkbenchFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = ROOT / 'source/releases/current'
        if not (cls.bundle / 'site-manifest.json').is_file():
            raise RuntimeError('先运行 python -m workbench prepare，再运行工作台测试')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / 'private'
        self.app = create_app(self.data, self.bundle)
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def checked(self, response, expected=200):
        self.assertEqual(response.status_code, expected, response.text[:1500])
        return response.json()

    def demo(self):
        return self.checked(self.client.post('/api/demo'), 201)

    def confirm(self, finding):
        fid = finding['id']
        finding = self.checked(self.client.put(f'/api/findings/{fid}/facts', json={'revision': finding['revision'], 'facts': [
            {'key': f['key'], 'status': 'confirmed', 'note': '测试中的合成核实记录，不是真实现场'} for f in finding['facts']
        ]}))
        finding = self.checked(self.client.post(f'/api/findings/{fid}/review', json={'decision': 'submit', 'revision': finding['revision']}))
        self.assertEqual(finding['status'], 'pending_review')
        return self.checked(self.client.post(f'/api/findings/{fid}/review', json={
            'decision': 'confirm', 'reviewer': '测试审核人', 'comment': '合成业务流程核验',
            'revision': finding['revision'],
        }))

    def test_complete_flow_export_snapshot_edit_and_restore(self):
        data = self.demo()
        project, finding = data['project'], data['finding']
        fid = finding['id']
        self.assertTrue(finding['photos'])
        self.assertTrue(finding['bases'])
        self.assertTrue(all(f['status'] == 'unknown' for f in finding['facts']))
        denied = self.client.post(f'/api/findings/{fid}/review', json={
            'decision': 'confirm', 'reviewer': '检查人', 'comment': '缺事实不能通过',
            'revision': finding['revision'],
        })
        self.assertEqual(denied.status_code, 409)
        pending = self.checked(self.client.post(f'/api/findings/{fid}/review', json={'decision': 'submit', 'revision': finding['revision']}))
        self.assertEqual(pending['status'], 'needs_facts')
        self.assertTrue(pending['blockers'])
        finding = self.confirm(pending)
        self.assertEqual(finding['status'], 'confirmed')
        report = self.checked(self.client.post(f'/api/projects/{project["id"]}/reports', json={'mode': 'confirmed'}), 201)
        docx = self.client.get(report['docx_url'])
        pdf = self.client.get(report['pdf_url'])
        self.assertEqual(docx.status_code, 200)
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF-'))
        reader = PdfReader(io.BytesIO(pdf.content))
        self.assertGreaterEqual(len(reader.pages), 2)
        document = Document(io.BytesIO(docx.content))
        headers = [c.text for c in document.tables[0].rows[0].cells]
        self.assertEqual(headers[headers.index('隐患') + 1], '隐患照片')
        self.assertGreaterEqual(len(document.inline_shapes), 1)
        text = '\n'.join(p.text for p in document.paragraphs)
        for basis in finding['bases']:
            self.assertIn(basis['text'], text)
            self.assertIn(basis['link_id'], text)
            self.assertIn(basis['as_of'], text)
        before_snapshot = self.client.get(report['snapshot_url']).content
        edited = self.checked(self.client.patch(f'/api/findings/{fid}', json={
            'description': '重新核查后的描述待重新审核', 'revision': finding['revision'],
        }))
        self.assertEqual(edited['status'], 'draft')
        self.assertTrue(all(f['status'] == 'unknown' for f in edited['facts']))
        self.assertEqual(before_snapshot, self.client.get(report['snapshot_url']).content)
        self.assertEqual(self.client.get(report['docx_url']).content, docx.content)
        self.assertEqual(self.client.post(f'/api/projects/{project["id"]}/reports', json={'mode': 'confirmed'}).status_code, 409)
        backup = self.client.get('/api/backup')
        self.assertEqual(backup.status_code, 200)
        backup_file = Path(self.temp.name) / 'backup.zip'
        backup_file.write_bytes(backup.content)
        recovered = restore_backup(backup_file, Path(self.temp.name) / 'restored')
        with TestClient(create_app(recovered, self.bundle)) as other:
            restored = other.get(f'/api/findings/{fid}').json()
            self.assertEqual(restored['description'], edited['description'])
            self.assertEqual(other.get(report['pdf_url']).content, pdf.content)
            self.assertEqual(other.get(restored['photos'][0]['url']).status_code, 200)

    def test_client_cannot_forge_status_law_or_facts(self):
        data = self.demo()
        fid = data['finding']['id']
        self.assertEqual(self.client.patch(f'/api/findings/{fid}', json={'status': 'confirmed'}).status_code, 422)
        self.assertEqual(self.client.patch(f'/api/findings/{fid}', json={'bases': [{'text': '伪造法条'}]}).status_code, 422)
        self.assertEqual(self.client.post(f'/api/findings/{fid}/bases', json={'hazard_id': 'H001', 'link_ids': ['K_FAKE']}).status_code, 422)
        self.assertEqual(self.client.put(f'/api/findings/{fid}/facts', json={'revision': data['finding']['revision'], 'facts': [{'key': 'invented', 'status': 'confirmed'}]}).status_code, 422)
        confirmed_without_evidence = [{'key': f['key'], 'status': 'confirmed'} for f in data['finding']['facts']]
        f = self.checked(self.client.put(f'/api/findings/{fid}/facts', json={'revision': data['finding']['revision'], 'facts': confirmed_without_evidence}))
        self.assertTrue(f['blockers'])

    def test_search_preserves_uncertainty_and_exact_title(self):
        exact = self.checked(self.client.get('/api/knowledge/search', params={'q': '灭火器失压'}))
        self.assertEqual(exact['items'][0]['id'], 'H001')
        unknown = self.checked(self.client.get('/api/knowledge/search', params={'q': '气瓶没有防震圈'}))
        self.assertEqual(unknown['items'], [])
        self.assertTrue(unknown['guidance']['notice'])
        self.assertEqual(exact['meta']['as_of'], self.app.state.knowledge.call('meta')['as_of'])

    def test_profile_selection_does_not_combine_alternative_scenarios(self):
        data = self.demo()
        fid = data['finding']['id']
        detail = self.checked(self.client.get('/api/knowledge/hazards/H003'))
        profiles = detail['profiles']
        chosen = next(p for p in profiles if p['id'] == 'FPR_EXTINGUISHER_ACCESS_BLOCKED')
        result = self.checked(self.client.post(f'/api/findings/{fid}/bases', json={
            'hazard_id': 'H003', 'profile_id': chosen['id'],
        }))
        self.assertTrue(any(chosen['id'] in f['key'] for f in result['facts']))
        self.assertFalse(any('FPR_EXTINGUISHER_BRACKET_OBSTRUCTION' in f['key'] for f in result['facts']))
        self.assertTrue(all(f['status'] == 'unknown' for f in result['facts']))
        self.assertTrue(any(f['kind'] == '误判边界' and f['expected'] == 'confirmed' for f in result['facts']))

    def test_photo_validation_copy_conflict_and_delete(self):
        data = self.demo()
        fid = data['finding']['id']
        self.assertEqual(self.client.post(f'/api/findings/{fid}/photos', files={'file': ('fake.jpg', b'<script>bad</script>', 'image/jpeg')}).status_code, 422)
        self.assertEqual(self.client.patch(f'/api/findings/{fid}', json={'revision': 0, 'description': 'stale'}).status_code, 409)
        copied = self.checked(self.client.post(f'/api/findings/{fid}/copy'), 201)
        self.assertEqual(copied['status'], 'draft')
        self.assertEqual(copied['observation'], '')
        self.assertEqual(copied['photos'], [])
        self.assertTrue(copied['bases'])
        self.assertTrue(all(f['status'] == 'unknown' for f in copied['facts']))
        self.checked(self.client.delete(f'/api/findings/{copied["id"]}'))
        self.assertEqual(self.client.get(f'/api/findings/{copied["id"]}').status_code, 404)

    def test_private_files_and_cross_origin_are_not_served(self):
        data = self.demo()
        self.assertIn(self.client.get('/workbench.sqlite3').status_code, (404, 405))
        self.assertIn(self.client.get('/private/workbench.sqlite3').status_code, (404, 405))
        self.assertEqual(self.client.post('/api/demo', headers={'Origin': 'https://other.invalid'}).status_code, 403)
        self.assertEqual(self.client.get('/api/projects', headers={'Host': 'public.invalid'}).status_code, 403)
        response = self.client.get('/api/projects')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')

    def test_document_duty_cannot_be_confirmed_as_onsite_finding(self):
        data = self.demo()
        fid = data['finding']['id']
        result = self.checked(self.client.post(f'/api/findings/{fid}/bases', json={'hazard_id': 'H_JSXF_58_1'}))
        self.assertTrue(any('资料核查' in reason for reason in result['blockers']))
        self.checked(self.client.patch(f'/api/findings/{fid}', json={'finding_kind': 'document_review'}))
        result = self.checked(self.client.get(f'/api/findings/{fid}'))
        self.assertFalse(any('请将记录类型' in reason for reason in result['blockers']))

    def test_project_context_changes_invalidate_prior_confirmation(self):
        data = self.demo()
        finding = self.confirm(data['finding'])
        pid, fid = data['project']['id'], finding['id']
        report = self.checked(self.client.post(f'/api/projects/{pid}/reports', json={'mode': 'confirmed'}), 201)
        snapshot = self.client.get(report['snapshot_url']).content
        self.checked(self.client.patch(f'/api/projects/{pid}', json={'company': '另一家示例企业', 'inspection_date': '2026-11-07'}))
        edited = self.checked(self.client.get(f'/api/findings/{fid}'))
        self.assertEqual(edited['status'], 'draft')
        self.assertGreater(edited['revision'], finding['revision'])
        self.assertTrue(all(f['status'] == 'unknown' for f in edited['facts']))
        self.assertEqual(self.client.post(f'/api/projects/{pid}/reports', json={'mode': 'confirmed'}).status_code, 409)
        self.assertEqual(snapshot, self.client.get(report['snapshot_url']).content)

    def test_stale_facts_and_review_cannot_confirm_a_different_revision(self):
        data = self.demo()
        old = data['finding']
        fid = old['id']
        current = self.checked(self.client.patch(f'/api/findings/{fid}', json={'observation': '另一次观察，尚待核实', 'revision': old['revision']}))
        stale_facts = [{**f, 'status': 'confirmed', 'note': '旧页面的旧证据'} for f in old['facts']]
        self.assertEqual(self.client.put(f'/api/findings/{fid}/facts', json={'revision': old['revision'], 'facts': stale_facts}).status_code, 409)
        self.assertEqual(self.client.put(f'/api/findings/{fid}/facts', json={'facts': stale_facts}).status_code, 409)
        result = self.checked(self.client.get(f'/api/findings/{fid}'))
        self.assertTrue(all(f['status'] == 'unknown' for f in result['facts']))
        result = self.confirm(result)
        self.assertEqual(self.client.post(f'/api/findings/{fid}/review', json={
            'decision': 'confirm', 'revision': current['revision'], 'reviewer': '旧审核页', 'comment': '旧意见',
        }).status_code, 409)

    def test_law_not_yet_effective_at_inspection_date_is_blocked(self):
        project = self.checked(self.client.post('/api/projects', json={
            'company': '历史示例', 'name': '历史检查', 'inspection_date': '2020-01-01',
        }), 201)
        finding = self.checked(self.client.post(f'/api/projects/{project["id"]}/findings', json={
            'observation': '合成观察', 'description': '合成描述', 'rectification': '合成整改',
        }), 201)
        fid = finding['id']
        finding = self.checked(self.client.post(f'/api/findings/{fid}/bases', json={'hazard_id': 'H001'}))
        self.assertTrue(all(b['effective_date'] > '2020-01-01' for b in finding['bases']))
        finding = self.checked(self.client.put(f'/api/findings/{fid}/facts', json={
            'revision': finding['revision'], 'facts': [{**f, 'status': 'confirmed', 'note': '合成核实'} for f in finding['facts']],
        }))
        submitted = self.checked(self.client.post(f'/api/findings/{fid}/review', json={'revision': finding['revision'], 'decision': 'submit'}))
        self.assertEqual(submitted['status'], 'needs_facts')
        self.assertTrue(any('晚于本次检查日期' in b for b in submitted['blockers']))
        self.assertEqual(self.client.post(f'/api/findings/{fid}/review', json={
            'revision': submitted['revision'], 'decision': 'confirm', 'reviewer': '示例', 'comment': '不应放行',
        }).status_code, 409)

    def test_changed_current_basis_blocks_new_export_but_not_history(self):
        import copy
        data = self.demo()
        finding = self.confirm(data['finding'])
        pid = data['project']['id']
        report = self.checked(self.client.post(f'/api/projects/{pid}/reports', json={'mode': 'confirmed'}), 201)
        original_pdf = self.client.get(report['pdf_url']).content
        call = self.app.state.knowledge.call
        def changed(op, **kwargs):
            value = call(op, **kwargs)
            if op == 'detail':
                value = copy.deepcopy(value)
                value['bases'][0]['ref']['applicability'] = '变更后的适用条件（测试替身）'
            return value
        with patch.object(self.app.state.knowledge, 'call', side_effect=changed):
            self.assertEqual(self.client.post(f'/api/projects/{pid}/reports', json={'mode': 'confirmed'}).status_code, 409)
            self.assertEqual(self.client.get(report['pdf_url']).content, original_pdf)

    def test_supporting_only_basis_does_not_qualify_a_finding(self):
        from workbench.backend.storage import blockers
        value = {'observation': '观察', 'description': '描述', 'rectification': '整改',
                 'bases': [{'hazard_id': 'H_TEST', 'role': 'supporting'}], 'facts': []}
        self.assertTrue(any('辅助依据' in reason for reason in blockers(value)))

    def test_conditional_branch_can_be_unselected_without_asserting_false_facts(self):
        from workbench.backend.storage import blockers
        from workbench.backend.facts import FACT_LABELS
        profiles = json.loads((self.bundle / 'data/field-profiles.json').read_text())['records']
        keys = {key for p in profiles for key in p['applicability']['perUseFacts']}
        self.assertFalse(keys - FACT_LABELS.keys(), '新的场景事实需要提供可读中文标签')
        value = {'observation': '观察', 'description': '描述', 'rectification': '整改',
                 'bases': [{'hazard_id': 'H_TEST', 'role': 'direct'}], 'facts': [
                     {'key': 'branch', 'label': '如选用分支B，核实该事实', 'expected': 'confirmed',
                      'allows_denied': True, 'status': 'denied', 'note': '本次仅采用A分支，B不适用'},
                 ]}
        self.assertFalse(blockers(value))
        value['facts'][0]['allows_denied'] = False
        self.assertTrue(blockers(value))

    def test_private_word_template_keeps_full_basis_appendix(self):
        from workbench.backend.reporting import create_template
        path = self.data / 'templates/inspection.docx'
        create_template(path)
        data = self.demo()
        with patch.dict(os.environ, {'WORKBENCH_PDF_ENGINE': 'reportlab'}):
            report = self.checked(self.client.post(f'/api/projects/{data["project"]["id"]}/reports', json={'mode': 'draft'}), 201)
        word = Document(io.BytesIO(self.client.get(report['docx_url']).content))
        text = '\n'.join(p.text for p in word.paragraphs)
        self.assertIn(data['project']['company'], text)
        self.assertNotIn('{{findings_table}}', text)
        self.assertIn(data['finding']['bases'][0]['text'], text)
        self.assertEqual(word.tables[0].cell(0, 3).text, '隐患照片')

    def test_pdf_fallback_and_draft_labels(self):
        data = self.demo()
        with patch.dict(os.environ, {'WORKBENCH_PDF_ENGINE': 'reportlab'}):
            report = self.checked(self.client.post(f'/api/projects/{data["project"]["id"]}/reports', json={'mode': 'draft'}), 201)
        self.assertTrue(report['pdf_engine'].startswith('reportlab'))
        word = Document(io.BytesIO(self.client.get(report['docx_url']).content))
        self.assertIn('草稿', word.paragraphs[0].text)
        pdf = self.client.get(report['pdf_url'])
        self.assertGreater(len(PdfReader(io.BytesIO(pdf.content)).pages), 1)

    def test_backup_refuses_traversal_and_existing_data(self):
        bad = Path(self.temp.name) / 'bad.zip'
        with zipfile.ZipFile(bad, 'w') as archive:
            archive.writestr('backup.json', '{"schema_version":1}')
            archive.writestr('workbench.sqlite3', '')
            archive.writestr('../escape', 'bad')
        with self.assertRaises(ValueError):
            restore_backup(bad, Path(self.temp.name) / 'restored')
        with self.assertRaises(ValueError):
            restore_backup(bad, self.data)

    def test_corrupt_knowledge_bundle_is_rejected(self):
        bad = Path(self.temp.name) / 'bad-bundle'
        bad.mkdir()
        (bad / 'site-manifest.json').write_text('{"schemaVersion":"invalid"}')
        bridge = Knowledge(bad)
        try:
            with self.assertRaises(KnowledgeError):
                bridge.call('meta')
        finally:
            bridge.close()


if __name__ == '__main__':
    unittest.main()
