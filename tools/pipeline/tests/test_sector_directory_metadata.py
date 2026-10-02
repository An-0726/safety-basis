"""Exact approved source batch boundary; metadata is not normative coverage."""
from commerce_cohort_fixture import pre_commerce_manifest
import hashlib,json,sys,unittest
from pathlib import Path
from datetime import date
from power_fixture import CLAUSES as POWER_CLAUSES, EVIDENCE as POWER_EVIDENCE, VERSION as POWER_VERSION
from coal_fixture import CLAUSES as COAL_CLAUSES, EVIDENCE as COAL_EVIDENCE, VERSION as COAL_VERSION
from construction_fixture import CLAUSES as CONSTRUCTION_CLAUSES, EVIDENCE as CONSTRUCTION_EVIDENCE
from city_gas_fixture import CLAUSES as GAS_CLAUSES, EVIDENCE as GAS_EVIDENCE
from sector_directory_fixture import LAWS,VERSIONS,EVIDENCE
ROOT=Path(__file__).resolve().parents[3];KNOW=ROOT/'knowledge';PUB=ROOT/'source/publication'
sys.path.insert(0,str(ROOT/'tools/v4'))
from major_criteria_directory import public_projection,load_records,review_bindings,NAMESPACE,REVIEW_SCOPE
from release_gate_core import evaluate_release_gate


def read(p):return json.loads(p.read_text(encoding='utf-8'))


class SectorDirectoryMetadataTests(unittest.TestCase):
    def test_79_exact_reviewed_metadata_sources_preserve_bytes(self):
        fixture=read(ROOT/'tests/private/sector-major-directory-source-v1.json')
        self.assertEqual(len(fixture['files']),79)
        for row in fixture['files']:
            with self.subTest(path=row['path']):self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])

    def test_inventory_delta_is_exactly_nine_identities_and_25_evidence(self):
        self.assertEqual((len(LAWS),len(VERSIONS),len(EVIDENCE)),(9,9,25))
        manifest = pre_commerce_manifest(read(KNOW/'manifest.json'));batch=next(b for b in manifest['batches'] if b['id']=='sector-major-directory-metadata-20261001')
        self.assertEqual({k:batch[k] for k in ['lawsAdded','lawVersionsAdded','evidenceAdded','identityMetadataReviewsAdded','versionMetadataReviewsAdded']},
                         {'lawsAdded':9,'lawVersionsAdded':9,'evidenceAdded':25,'identityMetadataReviewsAdded':9,'versionMetadataReviewsAdded':9})
        historical_counts = dict(manifest['counts'])
        historical_counts['clauses'] -= len(GAS_CLAUSES) + len(CONSTRUCTION_CLAUSES) + len(COAL_CLAUSES) + len(POWER_CLAUSES); historical_counts['evidence'] -= len(GAS_EVIDENCE) + len(CONSTRUCTION_EVIDENCE) + len(COAL_EVIDENCE) + len(POWER_EVIDENCE)
        self.assertEqual({k:historical_counts[k] for k in ['laws','lawVersions','evidence','clauses','hazards','links','successions']},
                         {'laws':119,'lawVersions':122,'evidence':1290,'clauses':3011,'hazards':2131,'links':1971,'successions':26})
        for row in (KNOW/'clauses').glob('*.json'):
            clause=read(row)
            if clause['id'] not in GAS_CLAUSES | CONSTRUCTION_CLAUSES | COAL_CLAUSES | POWER_CLAUSES:self.assertNotIn(clause.get('lawVersionId'),VERSIONS)

    def test_real_projection_separates_groups_documents_and_unknown_dates(self):
        records=load_records(KNOW);self.assertEqual(len(records),9)
        old=public_projection(KNOW,PUB,as_of=date(2026,9,30))['public']
        self.assertEqual((old['directoryGroupCount'],old['documentCount']),(0,0))
        now=public_projection(KNOW,PUB,as_of=date(2026,10,1))['public']
        self.assertEqual((now['directoryGroupCount'],now['documentCount']),(8,9))
        nulls={e['lawVersionId'] for e in now['entries'] if e['effectiveDate'] is None}
        self.assertEqual(nulls,{'LV_MIIT_CIVIL_EXPLOSIVES_MAJOR_2024','LV_NMSA_NONCOAL_MAJOR_SUPPLEMENT_2024','LV_SAWS_FIREWORKS_MAJOR_2017'})
        gate=evaluate_release_gate(KNOW,date(2026,10,1))
        for vid in nulls:self.assertFalse(gate.law_versions[vid]['supports_current'])
        for e in now['entries']:
            self.assertEqual((e['reviewedClauseCount'],e['directHazardCount'],e['searchTopicCount']),(0,0,0))
            self.assertFalse(e['standaloneDeterminationAllowed']);self.assertNotIn('quote',e)
        noncoal=[g for g in now['directoryGroups'] if g['primaryReferenceId']=='DIR_NMSA_NONCOAL_2022'][0]
        self.assertEqual(set(noncoal['documentIds']),{'DIR_NMSA_NONCOAL_2022','DIR_NMSA_NONCOAL_SUPPLEMENT_2024'})

    def test_reviews_are_actual_metadata_only_and_exact_not_auto_approvals(self):
        for record in load_records(KNOW).values():
            rv=read(KNOW/NAMESPACE/'reviews'/(record['id']+'.json'))
            self.assertEqual(rv['reviewScope'],REVIEW_SCOPE);self.assertFalse(rv['fullQuotePublicationReady'])
            self.assertEqual(rv['checkedAt'],'2026-10-01T09:39:09+00:00')
            for k,v in review_bindings(record,KNOW,PUB).items():self.assertEqual(rv[k],v)


if __name__=='__main__':unittest.main()
