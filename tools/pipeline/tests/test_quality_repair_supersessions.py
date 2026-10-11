"""Current exact bindings and immutable historical values for quality repairs."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from field_profiles import ProfileContext
from quality_repair_supersessions import load_supersessions, continued_hash

CATALOG = 'knowledge/major-criteria/v1/catalog.json'


def at_pointer(data, pointer):
    for key in pointer.lstrip('/').split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        data = data[int(key)] if isinstance(data, list) else data[key]
    return data


class QualityRepairSupersessionsTests(unittest.TestCase):
    def test_exact_current_hazard_lifecycle_and_historical_values(self):
        items = load_supersessions(ROOT)
        self.assertTrue(items)
        context = ProfileContext(ROOT / 'knowledge')
        catalog = json.loads((ROOT / CATALOG).read_text(encoding='utf-8'))
        for hid, item in items.items():
            with self.subTest(hazard=hid):
                hazard = context.entities['hazards'][hid]
                self.assertEqual(item['newLifecycle'], hazard['lifecycle'])
                if item['action'] == 'delist':
                    self.assertIsNone(item['newHazardHash'])
                    self.assertEqual(hazard['lifecycle'], 'proposed')
                else:
                    self.assertEqual(item['newHazardHash'], content_hash(hazard))
                self.assertEqual(context.reviews['hazards'][hid]['reviewedContentHash'], content_hash(hazard))
                for row in item['supersedes']:
                    filename = row['file']
                    self.assertEqual(row['pointer'].split('/')[-1], row['field'])
                    if filename == CATALOG:
                        # The catalog is a live file, so its previous value is recorded for the
                        # reader only; CI uses a shallow clone and cannot read the old revision.
                        self.assertRegex(row['oldValue'], r'^[a-f0-9]{64}$')
                        self.assertNotEqual(row['oldValue'], row['newValue'])
                        selected = at_pointer(catalog, row['pointer'].rsplit('/', 1)[0])
                        self.assertEqual(selected['hazardId'], hid)
                        fingerprint = context.fingerprint({'hazardId': hid, 'basisLinkIds': [selected['linkId']]})
                        self.assertEqual(row['newValue'], fingerprint)
                        self.assertEqual(at_pointer(catalog, row['pointer']), fingerprint)
                        continue
                    else:
                        self.assertTrue(filename.startswith('docs/'))
                        raw = (ROOT / filename).read_text(encoding='utf-8')
                        old = [json.loads(line) for line in raw.splitlines()] if filename.endswith('.jsonl') else json.loads(raw)
                        parent = at_pointer(old, row['pointer'].rsplit('/', 1)[0])
                        self.assertEqual(parent.get('targetId', parent.get('canonicalHazardId')), hid)
                    self.assertEqual(at_pointer(old, row['pointer']), row['oldValue'])

    def test_unlisted_id_or_unregistered_hash_keeps_exact_old_expectation(self):
        items = load_supersessions(ROOT)
        for hid, item in items.items():
            for row in item['supersedes']:
                if row['field'] not in ('targetHash', 'canonicalTargetContentHash'):
                    continue
                self.assertEqual(continued_hash(items, hid, row['oldValue'], row['field'], row['file']), item['newHazardHash'])
                self.assertEqual(continued_hash(items, 'H_NOT_LISTED', row['oldValue'], row['field'], row['file']), row['oldValue'])
                self.assertEqual(continued_hash(items, hid, '0' * 64, row['field'], row['file']), '0' * 64)
                self.assertEqual(continued_hash(items, hid, row['oldValue'], row['field'], 'docs/UNREGISTERED.json'), row['oldValue'])

    def test_changed_current_definition_cannot_satisfy_exact_continuation(self):
        items = load_supersessions(ROOT)
        for hid, item in items.items():
            if item['newHazardHash'] is None:
                continue
            hazard = json.loads((ROOT / f'knowledge/hazards/{hid}.json').read_text(encoding='utf-8'))
            changed = copy.deepcopy(hazard)
            changed['description'] += ' changed'
            self.assertNotEqual(content_hash(changed), item['newHazardHash'])


if __name__ == '__main__':
    unittest.main()
