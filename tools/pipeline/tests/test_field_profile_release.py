"""Governed profiles join the release without changing the legacy public inventory."""
import contextlib
import copy
from datetime import date
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v4'))
import build_unified_release as builder
import check_field_profiles as validator
import release_snapshot
import validate_all
import verify_unified_bundle as verifier
import test_field_profiles as fixtures


class FieldProfileReleaseTests(unittest.TestCase):
    fixture_type = fixtures.FieldProfileTests

    def setUp(self):
        self.fixture = self.fixture_type()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.fixture.law['documentKind'] = '法律'
        self.fixture.entity('laws', self.fixture.law)
        self.fixture.hazard.update(note='', mode='direct', conditions='Exact restricted source conditions')
        self.fixture.entity('hazards', self.fixture.hazard)
        self.fixture.entity('links', self.fixture.link)
        self.fixture.approve_synthetic()
        self.fixture.put('manifest.json', {'synthetic': True})
        self.publication = self.root / 'publication'
        self.fixture.put('publication/law-index.json', [{'id': 'LV_STD_GBT47236_2026'}])
        self.fixture.put('publication/fulltext/catalog.json', {'documents': [{
            'versionId': 'LV_STD_GBT47236_2026', 'textMode': 'link_only',
            'officialUrl': 'https://openstd.samr.gov.cn/', 'effectiveDate': '2026-09-01'}]})
        self.fixture.put('publication/fulltext/search-index.json', {'documents': [{
            'versionId': 'LV_STD_GBT47236_2026', 'textMode': 'link_only',
            'officialUrl': 'https://openstd.samr.gov.cn/', 'effectiveDate': '2026-09-01'}]})
        self.out = self.root / 'source/releases/test'
        self.selection = self.root / 'selection.json'

    def build(self, at='2026-09-30'):
        with patch.object(builder, 'KNOW', str(self.root)), \
                patch.object(builder, 'PUBLICATION', str(self.publication)), \
                patch.object(sys, 'argv', ['build', '--out', str(self.out), '--as-of', at,
                                         '--data-version', 'synthetic', '--overwrite']), \
                contextlib.redirect_stdout(io.StringIO()):
            builder.main()
        release = self.read('release.json')
        self.selection.write_text(json.dumps({'schemaVersion': 'safety-site-selection-v1',
                                              'bundle': 'test', 'releaseHash': release['releaseHash']}))
        return release

    def read(self, rel):
        return json.loads((self.out / rel).read_text(encoding='utf-8'))

    def reseal(self):
        """An attacker can recompute hashes; semantics/privacy must still reject."""
        def write(rel, value):
            (self.out / rel).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        release_hash = verifier.expected_release_hash(self.out)
        for rel in ('release.json', 'data/manifest.json', 'site-manifest.json'):
            value = self.read(rel)
            value['releaseHash'] = release_hash
            write(rel, value)
        site = self.read('site-manifest.json')
        site['fileHashes'] = {rel: verifier.sha256_file(path)
                              for rel, path in verifier.all_files(self.out).items()
                              if rel.startswith('data/')}
        write('site-manifest.json', site)
        write('checksums.json', {rel: verifier.sha256_file(path)
                                 for rel, path in verifier.all_files(self.out).items()
                                 if rel != 'checksums.json'})
        self.selection.write_text(json.dumps({'schemaVersion': 'safety-site-selection-v1',
                                              'bundle': 'test', 'releaseHash': release_hash}))

    def verify(self):
        output = io.StringIO()
        with patch.object(verifier, 'KNOW', str(self.root)), \
                patch.object(verifier, 'PUBLICATION', str(self.publication)), \
                patch.object(verifier, 'ROOT', str(self.root)), \
                patch.object(sys, 'argv', ['verify', '--bundle', str(self.out),
                                         '--selection', str(self.selection)]), \
                contextlib.redirect_stdout(output):
            rc = verifier.main()
        return rc, json.loads(output.getvalue())

    def test_aggregate_registers_schema_ref_check_as_blocking(self):
        self.assertIn(('check_field_profiles', 'check_field_profiles.py'), validate_all.STEPS)
        self.assertIn('check_field_profiles', validate_all.BLOCKING)

    def test_builder_requires_explicit_gate_date(self):
        with patch.object(sys, 'argv', ['build', '--out', str(self.out)]), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            builder.main()
        self.assertEqual(exc.exception.code, 2)
        self.assertFalse(self.out.exists())

    def test_schema_refs_fail_but_missing_and_unreviewed_coverage_do_not(self):
        f = self.fixture
        (self.root / 'field-profiles/v1/reviews/RV_FPR_TEST.json').unlink()
        f.put('hazards/H_UNCLASSIFIED.json', {**f.hazard, 'id': 'H_UNCLASSIFIED'})
        self.assertEqual(validator.validate_namespace(self.root)['errors'], [])
        f.profile['hazardId'] = 'H_MISSING'
        f.save_profile()
        errors = validator.validate_namespace(self.root)['errors']
        self.assertTrue(any('PROFILE_HAZARD_REF_MISSING' in error for error in errors))
        self.assertTrue(any('PROFILE_LINK_HAZARD_MISMATCH' in error for error in errors))
        f.profile['revision'] = False
        f.save_profile()
        self.assertIn('FPR_TEST:PROFILE_REVISION', validator.validate_namespace(self.root)['errors'])

    def test_dangling_selected_chain_is_structural_but_unapproved_is_not(self):
        (self.root / 'reviews/links/K_TEST.json').unlink()
        self.assertEqual(validator.validate_namespace(self.root)['errors'], [])
        (self.root / 'clauses/C_TEST.json').unlink()
        self.assertIn('FPR_TEST:PROFILE_DEPENDENCY_REF_MISSING:clauses/C_TEST',
                      validator.validate_namespace(self.root)['errors'])

    def test_complete_bundle_counts_hash_reference_and_consumer_joins(self):
        release = self.build()
        manifest = self.read('data/manifest.json')
        self.assertEqual(release['counts']['fieldProfiles'], 1)
        self.assertEqual(manifest['files']['fieldProfiles'], 'data/field-profiles.json')
        self.assertIn('data/field-profiles.json', self.read('site-manifest.json')['fileHashes'])
        self.assertEqual(self.read('data/field-profiles.json'), self.fixture.project()['public'])
        rc, report = self.verify()
        self.assertEqual(rc, 0, report)
        self.assertEqual(report['counts']['fieldProfiles'], 1)

    def test_formal_ui_module_is_shipped_and_checksum_covered(self):
        self.build()
        asset = 'js/field-profiles.js'
        self.assertIn(asset, builder.SITE_ASSETS)
        self.assertIn(asset, verifier.SITE_ASSETS)
        self.assertEqual((self.out / asset).read_bytes(), (Path(builder.WEB) / asset).read_bytes())
        self.assertIn(asset, self.read('checksums.json'))

    def test_missing_ui_module_cannot_pass_after_resealing(self):
        self.build()
        (self.out / 'js/field-profiles.js').unlink()
        self.reseal()
        rc, report = self.verify()
        self.assertNotEqual(rc, 0)
        self.assertTrue(any('公开文件集合不一致' in error for error in report['errors']))

    def test_profile_kind_is_structural_and_builder_emits_only_authored_kind(self):
        f = self.fixture
        self.assertEqual(validator.validate_namespace(self.root)['errors'], [])
        self.build()
        row = self.read('data/field-profiles.json')['records'][0]
        self.assertEqual('profileKind' in row, 'profileKind' in f.profile)
        if 'profileKind' in f.profile:
            self.assertEqual(row['profileKind'], f.profile['profileKind'])
        self.assertEqual(row['findingTemplate'], f.profile['findingTemplate'])
        self.assertIs(row['observedViolation'], False)
        for kind in ('unknown', None, {}, []):
            f.profile['profileKind'] = kind
            f.save_profile()
            self.assertIn('FPR_TEST:PROFILE_KIND', validator.validate_namespace(self.root)['errors'])

    def test_resealed_kind_and_template_tampering_fail_full_verifier(self):
        self.build()
        expected = self.read('data/field-profiles.json')
        missing = object()
        for key, value in (
                ('profileKind', missing),
                ('profileKind', 'conditional_template'),
                ('profileKind', 'routing_only'),
                ('profileKind', None),
                ('profileKind', {}),
                ('profileKind', []),
                ('findingTemplate', None),
                ('findingTemplate', {}),
                ('findingTemplate', {'text': 'At {{location}}',
                                     'slots': [{'key': 'location', 'label': 'Location'}]})):
            with self.subTest(key=key, value=value):
                payload = copy.deepcopy(expected)
                row = payload['records'][0]
                if value is missing:
                    row.pop(key, None)
                else:
                    row[key] = value
                if payload == expected:
                    continue
                (self.out / 'data/field-profiles.json').write_text(json.dumps(payload), encoding='utf-8')
                self.reseal()
                rc, report = self.verify()
                self.assertEqual(rc, 1, report)
                self.assertTrue(any('精确公开投影' in error for error in report['errors']), report)
                self.assertFalse(any('哈希' in error or 'Hash' in error for error in report['errors']), report)

    def test_empty_unreviewed_and_undetermined_profiles_preserve_hazards_search(self):
        self.build()
        original = {rel: (self.out / rel).read_bytes() for rel in
                    ('data/search-index.json', 'data/hazards/h0000.json', 'data/clauses/c0000.json')}
        f = self.fixture
        (self.root / 'field-profiles/v1/reviews/RV_FPR_TEST.json').unlink()
        for stage in ('unreviewed', 'undetermined', 'absent'):
            if stage == 'undetermined':
                f.profile.update(inspectionClass='undetermined', defaultFieldEntry='undetermined',
                                 contentDisposition='undetermined', findingTemplate=None)
                f.save_profile()
                f.approve_synthetic()
            elif stage == 'absent':
                (self.root / 'field-profiles/v1/records/FPR_TEST.json').unlink()
            release = self.build()
            self.assertEqual(release['counts']['hazards'], 1)
            self.assertEqual(release['counts']['fieldProfiles'], 0)
            self.assertEqual(self.read('data/field-profiles.json')['records'], [])
            for rel, expected in original.items():
                self.assertEqual((self.out / rel).read_bytes(), expected, stage)
            rc, report = self.verify()
            self.assertEqual(rc, 0, report)

    def test_dated_gate_changes_profiles_without_source_edit(self):
        self.assertEqual(self.build()['counts']['fieldProfiles'], 1)
        self.assertEqual(self.build('2026-10-01')['counts']['fieldProfiles'], 0)
        self.assertEqual(self.read('data/field-profiles.json')['asOf'], '2026-10-01')
        rc, report = self.verify()
        self.assertEqual(rc, 0, report)

    def test_exact_projection_rejects_field_link_condition_route_and_private_tampering(self):
        self.build()
        expected = self.fixture.project()['public']
        hazard = self.read('data/hazards/h0000.json')['records'][0]
        clause = self.read('data/clauses/c0000.json')['records'][0]
        for route in ('condition', 'link', 'basis_scope', 'route', 'private', 'bool_type', 'omitted'):
            value = copy.deepcopy(expected)
            row = value['records'][0]
            if route == 'condition':
                row['sourceHazard']['conditions'] = 'Widened'
            elif route == 'link':
                row['bases'][0]['linkId'] = 'K_WRONG'
            elif route == 'basis_scope':
                row['bases'][0]['applicability'] = 'Everywhere'
            elif route == 'route':
                row['defaultFieldEntry'] = 'include'
            elif route == 'private':
                row['reviewer'] = 'private reviewer'
            elif route == 'bool_type':
                row['observedViolation'] = 0
            else:
                value['records'] = []
            bad = verifier.Failures()
            verifier.check_field_profiles(bad, value, expected, self.read('data/manifest.json'),
                                          self.read('release.json'), {'H_TEST': hazard},
                                          {'C_TEST': clause}, {'LV_TEST'})
            self.assertTrue(any('精确公开投影' in error for error in bad), route)

    def test_private_inventory_extra_files_and_pilot_never_ship(self):
        self.fixture.put('field-profiles-pilot/records/FP_P01.json', {'private': 'ignored'})
        self.fixture.profile['internalNotes'] = {'company': 'PRIVATE_SENTINEL', 'file': '/home/private/evidence'}
        self.fixture.save_profile()
        self.fixture.approve_synthetic()
        self.build()
        for path in self.out.rglob('*.json'):
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('PRIVATE_SENTINEL', text)
            self.assertNotIn('FP_P01', text)
            self.assertEqual(verifier.private_profile_keys(json.loads(text)), set())
        extra = self.out / 'data/private-review.json'
        extra.write_text(json.dumps({'hazardsWithoutProfiles': ['H_PRIVATE']}))
        self.reseal()
        rc, report = self.verify()
        self.assertEqual(rc, 1)
        self.assertTrue(any('白名单' in error for error in report['errors']))
        self.assertTrue(any('私有 field profile' in error for error in report['errors']))
        self.assertFalse(any('哈希' in error or 'Hash' in error for error in report['errors']))

    def test_resealed_tampering_still_fails_full_verifier(self):
        self.build()
        profile = self.read('data/field-profiles.json')
        profile['records'][0]['bases'][0]['applicability'] = 'Invented unrestricted scope'
        (self.out / 'data/field-profiles.json').write_text(json.dumps(profile))
        self.reseal()
        rc, report = self.verify()
        self.assertEqual(rc, 1)
        self.assertTrue(any('精确公开投影' in error for error in report['errors']))
        self.assertFalse(any('哈希' in error or 'Hash' in error for error in report['errors']))

    def test_verifier_rejects_stale_snapshot_and_mismatched_dates(self):
        self.build()
        self.fixture.put('evidence/E_NEW.json', {'id': 'E_NEW'})
        rc, report = self.verify()
        self.assertEqual(rc, 1)
        self.assertTrue(any('快照' in error for error in report['errors']))
        self.build()
        site = self.read('site-manifest.json')
        site['asOf'] = '2026-09-29'
        (self.out / 'site-manifest.json').write_text(json.dumps(site))
        self.reseal()
        rc, report = self.verify()
        self.assertEqual(rc, 1)
        self.assertTrue(any('清单日期' in error for error in report['errors']))

    def test_snapshot_isolated_and_pilot_changes_do_not_change_formal_digest(self):
        before = release_snapshot.source_hashes(self.root)
        self.fixture.put('field-profiles-pilot/records/FP_TEST.json', {'invalid': True})
        self.assertEqual(release_snapshot.source_hashes(self.root), before)
        with release_snapshot.stable_knowledge_snapshot(self.root) as (snapshot, digest):
            original = (snapshot / 'hazards/H_TEST.json').read_bytes()
            self.fixture.put('hazards/H_TEST.json', {'id': 'H_CHANGED'})
            self.assertEqual((snapshot / 'hazards/H_TEST.json').read_bytes(), original)
            self.assertEqual(digest, release_snapshot.snapshot_digest(before))
            self.assertFalse((snapshot / 'field-profiles-pilot').exists())
        self.assertFalse(snapshot.exists())

    def test_capture_mutation_aborts_instead_of_mixing_gate_and_profiles(self):
        original = release_snapshot.shutil.copyfile
        def changing_copy(source, target):
            result = original(source, target)
            if Path(source).name == 'manifest.json':
                Path(source).write_text('{"changed":true}')
            return result
        with patch.object(release_snapshot.shutil, 'copyfile', changing_copy):
            with self.assertRaisesRegex(ValueError, 'changed during release snapshot'):
                with release_snapshot.stable_knowledge_snapshot(self.root):
                    self.fail('unstable source was accepted')


class ExplicitConditionalFieldProfileReleaseTests(FieldProfileReleaseTests):
    fixture_type = fixtures.ExplicitConditionalFieldProfileTests


class RoutingOnlyFieldProfileReleaseTests(FieldProfileReleaseTests):
    fixture_type = fixtures.RoutingOnlyFieldProfileTests

    def test_routing_only_template_rejected_by_structural_validator(self):
        self.fixture.profile['findingTemplate'] = {
            'text': 'At {{location}}', 'slots': [{'key': 'location', 'label': 'Location'}]}
        self.fixture.save_profile()
        self.assertIn('FPR_TEST:PROFILE_ROUTING_ONLY_TEMPLATE',
                      validator.validate_namespace(self.root)['errors'])


if __name__ == '__main__':
    unittest.main()
