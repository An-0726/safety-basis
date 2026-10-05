"""The one commerce metadata continuation cannot weaken historical admission."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
import commerce_source_continuation as C
from check_commerce_candidate_dispositions import validate_commerce_dispositions


def inputs(root):
    independent = json.loads((root / C.LEGACY_REPORT).read_text())
    entities = {kind: {} for kind in ('hazards', 'links', 'clauses', 'law-versions')}
    for relative in [*C.UNCHANGED, C.VERSION_PATH]:
        row = json.loads((root / relative).read_text())
        entities[Path(relative).parts[1]][row['id']] = row
    return independent, entities


def minimal_copy(root):
    for relative in [C.PROOF, C.LEGACY_REPORT, *C.UNCHANGED, C.VERSION_PATH, C.REVIEW_PATH]:
        target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


class CommerceSourceContinuationTests(unittest.TestCase):
    def test_exact_current_source_passes_and_only_one_in_memory_hash_changes(self):
        independent, entities = inputs(ROOT)
        original = copy.deepcopy(independent); source_before = {p: (ROOT / p).read_bytes() for p in [C.PROOF, C.LEGACY_REPORT, *C.UNCHANGED, C.VERSION_PATH, C.REVIEW_PATH]}
        continued, errors = C.approved_source_continuation(ROOT, independent, entities)
        self.assertEqual(errors, [])
        expected = copy.deepcopy(independent)
        next(i for i in expected['items'] if i['hazardId'] == C.HAZARD)['links'][0]['lawVersionHash'] = C.AFTER_VERSION_HASH
        self.assertEqual(continued, expected)
        self.assertEqual(independent, original)
        self.assertEqual({p: (ROOT / p).read_bytes() for p in source_before}, source_before)
        self.assertEqual(validate_commerce_dispositions(ROOT), [])

    def test_without_new_proof_historical_audit_remains_unmodified(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = {'items': []}
            got, errors = C.approved_source_continuation(Path(tmp), original, {})
            self.assertIs(got, original); self.assertEqual(errors, [])

    def test_removing_the_proof_cannot_bypass_the_current_overall_commerce_check(self):
        is_file = Path.is_file
        def without_proof(path):
            return False if path == ROOT / C.PROOF else is_file(path)
        with patch.object(Path, 'is_file', without_proof):
            errors = validate_commerce_dispositions(ROOT)
        self.assertTrue(any(C.HAZARD in e and 'independent review stale' in e and C.VERSION in e for e in errors))
        self.assertTrue((ROOT / C.PROOF).is_file())

    def test_source_url_or_scope_cannot_change_after_the_exact_continuation(self):
        for field in ('sourceUrl', 'scope'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); minimal_copy(root); independent, entities = inputs(root)
                version = json.loads((root / C.VERSION_PATH).read_text()); version[field] = 'unapproved'
                (root / C.VERSION_PATH).write_text(json.dumps(version))
                _, errors = C.approved_source_continuation(root, independent, entities)
                self.assertTrue(any('current version differs' in e for e in errors))

    def test_legacy_document_and_all_current_source_byte_drift_reject(self):
        for relative in [C.PROOF, C.LEGACY_REPORT, *C.UNCHANGED, C.VERSION_PATH, C.REVIEW_PATH]:
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); minimal_copy(root); independent, entities = inputs(root)
                with (root / relative).open('ab') as output: output.write(b' ')
                got, errors = C.approved_source_continuation(root, independent, entities)
                self.assertTrue(errors); self.assertIs(got, independent)

    def test_proof_targets_true_baseline_fields_and_no_new_facts_are_independently_validated(self):
        mutations = {
            'target_hazard': lambda p: p.update(targetHazardId='H_OTHER'),
            'target_version': lambda p: p.update(targetLawVersionId='LV_OTHER'),
            'predecessor': lambda p: p.update(baselineTree='0' * 40),
            'allowed_fields': lambda p: p['allowedChangedVersionFields'].append('effectiveDate'),
            'old_item': lambda p: p['legacyReport']['item'].update(siteFactEstablished=True),
            'old_bytes': lambda p: p['beforeVersion'].update(fileTextUtf8='{}'),
            'old_definition': lambda p: p['beforeVersion']['definition'].update(scope='invented'),
            'current_definition': lambda p: p['afterVersion']['definition'].update(scope='invented'),
            'wrong_hkc_set': lambda p: p['unchangedEntities'].pop(),
            'new_duties': lambda p: p.update(newDutiesApproved=True),
            'site_facts': lambda p: p.update(siteFactsConfirmed=True),
            'other_items': lambda p: p.update(otherItemsUnchanged=22),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); minimal_copy(root); independent, entities = inputs(root)
                proof = json.loads((root / C.PROOF).read_text()); mutate(proof)
                raw = (json.dumps(proof, ensure_ascii=False, indent=2) + '\n').encode(); (root / C.PROOF).write_bytes(raw)
                # Bypass only the outer proof-byte guard to exercise each deeper
                # semantic guard. Production never changes the pinned digest.
                with patch.object(C, 'PROOF_SHA256', hashlib.sha256(raw).hexdigest()):
                    got, errors = C.approved_source_continuation(root, independent, entities)
                self.assertTrue(errors); self.assertIs(got, independent)

    def test_unapproved_version_field_still_fails_even_if_outer_pins_are_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); minimal_copy(root); independent, entities = inputs(root)
            proof = json.loads((root / C.PROOF).read_text()); version = proof['afterVersion']['definition']
            version['effectiveDate'] = '1900-01-01'
            raw = (json.dumps(version, ensure_ascii=False, indent=2) + '\n').encode(); (root / C.VERSION_PATH).write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest(); canon = content_hash(version)
            proof['afterVersion'].update(fileSha256=digest, contentHash=canon)
            raw_proof = (json.dumps(proof, ensure_ascii=False, indent=2) + '\n').encode(); (root / C.PROOF).write_bytes(raw_proof)
            with patch.multiple(C, PROOF_SHA256=hashlib.sha256(raw_proof).hexdigest(), AFTER_VERSION_SHA256=digest, AFTER_VERSION_HASH=canon):
                _, errors = C.approved_source_continuation(root, independent, entities)
            self.assertTrue(any('two approved metadata fields' in e for e in errors))

    def test_caller_cannot_supply_stale_entities_or_modify_other_legacy_items(self):
        for mode in ('entity', 'target_hash', 'other_item', 'duplicate', 'missing'):
            independent, entities = inputs(ROOT)
            if mode == 'entity': entities['hazards'][C.HAZARD]['title'] = 'wrong'
            elif mode == 'target_hash': next(i for i in independent['items'] if i['hazardId'] == C.HAZARD)['links'][0]['lawVersionHash'] = C.AFTER_VERSION_HASH
            elif mode == 'other_item': next(i for i in independent['items'] if i['hazardId'] != C.HAZARD)['siteFactEstablished'] = True
            elif mode == 'duplicate': independent['items'].append(copy.deepcopy(independent['items'][0]))
            else: independent['items'].pop()
            with self.subTest(mode=mode):
                got, errors = C.approved_source_continuation(ROOT, independent, entities)
                self.assertTrue(errors); self.assertIs(got, independent)

    def test_old_commerce_merge_history_and_legacy_report_remain_exact_baseline_files(self):
        self.assertEqual(hashlib.sha256((ROOT / C.LEGACY_REPORT).read_bytes()).hexdigest(), C.LEGACY_REPORT_SHA256)
        # The preexisting carry-forward guard must remain in production code.
        source = (ROOT / 'tools/v4/commerce_merge_history.py').read_text()
        self.assertIn("'old independent review was modified'", source)
        self.assertIn("'both old independent reviews must remain intact'", source)


class CommerceSourceContinuationHistoricalTests(unittest.TestCase):
    def test_guarded_old_inverse_removes_new_proof_and_preserves_original_commerce_logic(self):
        from complete_remaining_cohort_fixture import pre_complete_repo_root
        prior = pre_complete_repo_root(ROOT)
        self.assertFalse((prior / C.PROOF).exists())
        self.assertEqual(hashlib.sha256((prior / C.LEGACY_REPORT).read_bytes()).hexdigest(), C.LEGACY_REPORT_SHA256)
        self.assertEqual(hashlib.sha256((prior / C.VERSION_PATH).read_bytes()).hexdigest(), C.BEFORE_VERSION_SHA256)
        independent, entities = inputs(prior)
        continued, errors = C.approved_source_continuation(prior, independent, entities)
        self.assertIs(continued, independent); self.assertEqual(errors, [])
        self.assertEqual(validate_commerce_dispositions(prior), [])


if __name__ == '__main__':
    unittest.main()
