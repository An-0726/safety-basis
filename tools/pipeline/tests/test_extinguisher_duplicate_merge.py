"""Current exact duplicate merge; no loss of the three distinct obligations."""
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate, load_dir
F = json.loads((ROOT/'docs/EXTINGUISHER_DUPLICATE_MERGE_20261004.json').read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda kind, i: json.loads((ROOT/'knowledge'/kind/(i+'.json')).read_text())


class ExtinguisherDuplicateMergeTests(unittest.TestCase):
    def test_exact_eight_paths_and_unchanged_canonical_source_are_bound(self):
        self.assertEqual(len(F['records']), 8)
        for path, row in F['records'].items():
            self.assertEqual(sha((ROOT/path).read_bytes()), row['afterSha256'], path)
            self.assertEqual(sha(row['beforeFileText'].encode()), row['beforeSha256'], path)
        for path, digest in F['unchangedSourceBindings'].items():
            self.assertEqual(sha((ROOT/path).read_bytes()), digest, path)

    def test_original_duplicates_match_all_business_fields_and_every_basis_scope(self):
        old, target = F['sourceHazardId'], F['targetHazardId']
        before = json.loads(F['records'][f'knowledge/hazards/{old}.json']['beforeFileText'])
        canonical = read('hazards', target)
        for field in F['sameHazardFields']:
            self.assertEqual(before.get(field), canonical.get(field), field)
        self.assertEqual(len(F['linkMapping']), 3)
        for a, b in F['linkMapping'].items():
            x = json.loads(F['records'][f'knowledge/links/{a}.json']['beforeFileText'])
            y = read('links', b)
            for field in ('clauseId', 'applicability', 'role', 'jurisdictionCode', 'priority'):
                self.assertEqual(x.get(field), y.get(field), (a, field))

    def test_history_is_complete_and_current_reviews_bind_superseded_entities(self):
        for kind, ident in [('hazards', F['sourceHazardId']), *[('links', i) for i in F['linkMapping']]]:
            entity = read(kind, ident); review = read('reviews/'+kind, ident)
            self.assertEqual(entity['lifecycle'], 'superseded')
            target = F['targetHazardId'] if kind == 'hazards' else F['linkMapping'][ident]
            self.assertEqual(entity['mergedInto'], target)
            self.assertEqual(review['reviewedContentHash'], content_hash(entity))
            previous = F['records'][f'knowledge/reviews/{kind}/{ident}.json']
            self.assertEqual(review['previousReview'], json.loads(previous['beforeFileText']))
            self.assertEqual(review['previousReviewFileSha256'], previous['beforeSha256'])
            old_entity = F['records'][f'knowledge/{kind}/{ident}.json']
            self.assertEqual(review['previousEntity'], json.loads(old_entity['beforeFileText']))
            self.assertEqual(review['previousEntityFileSha256'], old_entity['beforeSha256'])
            if kind == 'links':
                self.assertEqual(review['decision'], 'rejected')
                self.assertEqual(review['contextHashes']['hazard'], content_hash(read('hazards', F['sourceHazardId'])))
                self.assertEqual(review['contextHashes']['clause'], content_hash(read('clauses', entity['clauseId'])))

    def test_current_gate_preserves_three_obligations_and_excludes_only_duplicate(self):
        gate = evaluate_release_gate(ROOT/'knowledge', date(2026, 10, 4))
        self.assertNotIn(F['sourceHazardId'], gate.eligible_hazards)
        self.assertIn(F['targetHazardId'], gate.eligible_hazards)
        self.assertTrue(set(F['linkMapping']).isdisjoint(gate.eligible_links))
        self.assertTrue(set(F['linkMapping'].values()) <= gate.eligible_links)
        self.assertEqual({read('links', k)['clauseId'] for k in F['linkMapping'].values()},
            {'C_GB50444_5_2_1', 'C_GB50444_5_2_2', 'C_GB50444_5_2_4'})
        active = [h['id'] for h in load_dir(ROOT/'knowledge', 'hazards').values()
            if h.get('lifecycle') == 'active' and h.get('title') == read('hazards', F['targetHazardId'])['title']]
        self.assertEqual(active, [F['targetHazardId']])


if __name__ == '__main__': unittest.main()
