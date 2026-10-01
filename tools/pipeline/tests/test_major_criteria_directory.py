"""Synthetic metadata-directory tests; no production reviews are generated."""
import copy
import os
import subprocess
import json
from datetime import date
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'v4'))
import major_criteria_directory as directory
import major_criteria_references as references
from canonical import content_hash
from release_gate_core import evaluate_release_gate
import release_snapshot
import validate_all
from validate_publication_integrity import metadata_date_equal
import test_major_criteria_references as reference_fixtures


class DirectoryTests(unittest.TestCase):
    def setUp(self):
        self.f=reference_fixtures.ReferenceTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.root,self.pub=self.f.root,self.f.pub
        (self.root/references.NAMESPACE/'records/REF_TEST.json').unlink()
        self.f.f.law['documentKind']='部门规范性文件'
        self.f.f.version['publicationDate']='2020-01-01'
        for kind,entity in [('laws',self.f.f.law),('law-versions',self.f.f.version)]:self.entity(kind,entity)
        self.record={'schemaVersion':1,'id':'DIR_TEST','lawVersionId':'LV_TEST',
          'officialLink':self.f.record['officialLink'],'officialTextLink':self.f.record['officialTextLink'],
          'directoryGroup':{'id':'test_group','label':'合成目录主题','role':'primary'},
          'requiredCompanionIds':[],'supplementsReferenceId':None,'legalNature':'部门规范性文件',
          'criterionKind':'synthetic_metadata_only','scopeHint':'合成主体范围提示','scopeCaveat':'不能代替判定原文',
          'referenceStatus':'current','statusAsOf':'2026-10-01','effectiveDateNote':''}
        # The official page and text may be distinct; both require tracked evidence.
        self.f.f.put('evidence/E_PAGE.json',{'id':'E_PAGE','url':self.record['officialLink'],
          'tier':'authoritative-public','snapshotSha256':'b'*64})
        for kind,ident in [('laws','LF_TEST'),('law-versions','LV_TEST')]:
            path=f'reviews/{kind}/{ident}.json';value=directory.read(self.root/path);value['evidenceRefs'].append('E_PAGE');self.f.f.put(path,value)
        self.save_record();self.approve()

    def entity(self,kind,value):
        self.f.f.entity(kind,value)
        path=f"reviews/{kind}/{value['id']}.json"
        self.f.f.put(path,{**directory.read(self.root/path),'checkedAt':'2026-10-01T08:00:00+00:00'})

    def save_record(self,record=None):
        row=record or self.record;self.f.f.put(f"{directory.NAMESPACE}/records/{row['id']}.json",row)

    def approve(self,record=None):
        row=record or self.record
        review={'schemaVersion':1,'referenceId':row['id'],'decision':'verified','checkedAt':'2026-10-01T09:00:00+00:00',
          'reviewScope':directory.REVIEW_SCOPE,'fullQuotePublicationReady':False,'reviewer':'Synthetic test only',
          'reason':'Synthetic metadata admission; never a real source approval',**directory.review_bindings(row,self.root,self.pub)}
        self.f.f.put(f"{directory.NAMESPACE}/reviews/{row['id']}.json",review)
        return review

    def project(self,at=date(2026,10,1)):
        return directory.public_projection(self.root,self.pub,as_of=at)

    def entries(self):return self.project()['public']['entries']

    def nullable(self):
        self.f.f.version['effectiveDate']=None
        path='law-versions/LV_TEST.json';self.f.f.put(path,self.f.f.version)
        path='reviews/law-versions/LV_TEST.json';rv=directory.read(self.root/path);rv['reviewedContentHash']=content_hash(self.f.f.version);self.f.f.put(path,rv)
        self.f.doc.update(effectiveDate=None,status='现行使用中');self.f.source_row.update(effectiveDate=None,status='现行使用中');self.f.save_publication()
        self.record.update(referenceStatus='current_in_use',effectiveDateNote='原件未单列实施日，不以发文日替代')
        self.save_record();self.approve()

    def companion(self):
        # Same synthetic official evidence describes two separate example documents.
        law={**self.f.f.law,'id':'LF_COMP','canonicalName':'Synthetic companion'}
        version={**self.f.f.version,'id':'LV_COMP','lawId':'LF_COMP'}
        for kind,entity in [('laws',law),('law-versions',version)]:
            self.entity(kind,entity)
            path=f"reviews/{kind}/{entity['id']}.json";value=directory.read(self.root/path);value['evidenceRefs'].append('E_PAGE');self.f.f.put(path,value)
        doc={**self.f.doc,'lawId':'LF_COMP','versionId':'LV_COMP','title':'Synthetic companion'}
        row={**self.f.source_row,'id':'LV_COMP','name':'Synthetic companion'}
        for rel,value in [('law-index.json',row),('fulltext/catalog.json',doc),('fulltext/search-index.json',{k:doc[k] for k in references.SEARCH_FIELDS})]:
            obj=directory.read(self.pub/rel);(obj if isinstance(obj,list) else obj['documents']).append(value);self.f.f.put('publication/'+rel,obj)
        self.record['requiredCompanionIds']=['DIR_COMP']
        other={**copy.deepcopy(self.record),'id':'DIR_COMP','lawVersionId':'LV_COMP','requiredCompanionIds':[],
          'supplementsReferenceId':'DIR_TEST','directoryGroup':{**self.record['directoryGroup'],'role':'supplement'}}
        self.save_record();self.save_record(other);self.approve();self.approve(other)
        return other

    def test_metadata_visible_without_creating_clauses_hazards_links(self):
        for rel in ['hazards/H_TEST.json','clauses/C_TEST.json','links/K_TEST.json']:(self.root/rel).unlink()
        before=release_snapshot.source_hashes(self.root);public=self.project()['public'];e=public['entries'][0]
        self.assertEqual((public['directoryGroupCount'],public['documentCount']),(1,1))
        self.assertEqual((e['reviewedClauseCount'],e['directHazardCount'],e['searchTopicCount']),(0,0,0))
        self.assertEqual(e['publicationReady'],{'metadata':True,'fullText':False})
        self.assertFalse(e['standaloneDeterminationAllowed']);self.assertFalse(public['allIndustryCoverage'])
        self.assertFalse(set(e)&{'quote','clauses','searchTopics','hazardIds','reviewer','dependencyFingerprint'})
        self.assertEqual(before,release_snapshot.source_hashes(self.root))

    def test_explicit_unknown_date_never_becomes_current_normative_basis(self):
        self.nullable();self.assertIsNone(self.entries()[0]['effectiveDate'])
        self.assertEqual(self.entries()[0]['statusLabel'],'现行使用中')
        gate=evaluate_release_gate(self.root,date(2026,10,1))
        self.assertFalse(gate.law_versions['LV_TEST']['supports_current'])
        self.assertFalse(gate.eligible_hazards);self.assertFalse(gate.eligible_links)
        self.assertEqual(self.f.f.version['effectiveDate'],None)

    def test_null_without_explanation_or_current_in_use_is_not_admitted(self):
        self.nullable()
        for key,value in [('effectiveDateNote',''),('referenceStatus','current')]:
            original=copy.deepcopy(self.record);self.record[key]=value;self.save_record();self.approve()
            self.assertEqual(self.entries(),[]);self.record=original

    def test_fabricated_current_in_use_or_new_record_needs_exact_signed_binding(self):
        self.record['referenceStatus']='current_in_use';self.save_record()
        self.assertEqual(self.entries(),[])
        p=self.root/directory.NAMESPACE/'reviews/DIR_TEST.json';p.unlink();self.assertEqual(self.entries(),[])

    def test_old_future_invalid_and_misbound_reviews_are_excluded(self):
        path=f'{directory.NAMESPACE}/reviews/DIR_TEST.json';original=directory.read(self.root/path)
        for key,value in [('checkedAt','2026-10-02'),('checkedAt','2026-10-01T09:00:00'),('decision','rejected'),
          ('reviewedContentHash','0'*64),('dependencyFingerprint','0'*64),('referenceId','OTHER'),
          ('reviewScope',references.REVIEW_SCOPE),('fullQuotePublicationReady',True)]:
            self.f.f.put(path,{**original,key:value});self.assertEqual(self.entries(),[],key)
        self.f.f.put(path,original);self.assertEqual(self.project(date(2026,9,30))['public']['entries'],[])

    def test_original_metadata_review_or_evidence_must_exist(self):
        (self.root/'reviews/laws/LF_TEST.json').unlink();self.assertEqual(self.entries(),[])

    def test_missing_or_untracked_official_page_evidence_is_rejected(self):
        (self.root/'evidence/E_PAGE.json').unlink();self.approve();self.assertEqual(self.entries(),[])

    def test_expired_proposed_future_and_malformed_versions_are_never_admitted(self):
        path='law-versions/LV_TEST.json';original=directory.read(self.root/path)
        for change in [{'endDate':'2026-10-01'},{'endDate':False},{'lifecycle':'proposed'},{'validityStatus':'upcoming'},
                       {'effectiveDate':'2027-01-01'},{'effectiveDate':''},{'effectiveDate':'bad'},{'publicationDate':None}]:
            self.f.f.put(path,{**original,**change});rvpath='reviews/law-versions/LV_TEST.json';rv=directory.read(self.root/rvpath)
            rv['reviewedContentHash']=content_hash({**original,**change});self.f.f.put(rvpath,rv);self.approve();self.assertEqual(self.entries(),[],change)

    def test_companion_graph_is_explicit_and_counts_one_group_two_documents(self):
        self.companion();public=self.project()['public'];self.assertEqual((public['directoryGroupCount'],public['documentCount']),(1,2))
        self.assertEqual(public['directoryGroups'][0]['documentIds'],['DIR_COMP','DIR_TEST'])

    def test_missing_future_or_stale_companion_review_holds_the_whole_group(self):
        other=self.companion();path=f"{directory.NAMESPACE}/reviews/{other['id']}.json";original=directory.read(self.root/path)
        for change in [{'checkedAt':'2026-10-02'},{'decision':'proposed'},{'reviewedContentHash':'0'*64},None]:
            if change is None:(self.root/path).unlink()
            else:self.f.f.put(path,{**original,**change})
            public=self.project()['public'];self.assertEqual((public['directoryGroupCount'],public['documentCount']),(0,0))

    def test_companion_record_or_metadata_change_invalidates_primary_binding(self):
        other=self.companion();other['scopeHint']='Changed synthetic scope';self.save_record(other);self.approve(other)
        self.assertEqual(self.entries(),[])

    def test_missing_companion_or_group_mismatch_is_a_structural_failure(self):
        other=self.companion();other['directoryGroup']['label']='Different group';self.save_record(other)
        with self.assertRaisesRegex(ValueError,'DIRECTORY_GROUP_IDENTITY'):self.project()
        (self.root/directory.NAMESPACE/'records/DIR_COMP.json').unlink()
        with self.assertRaisesRegex(ValueError,'DIRECTORY_COMPANION_GRAPH'):self.project()

    def test_no_source_status_override_without_exact_directory_approval(self):
        self.nullable();catalog=directory.read(self.pub/'fulltext/catalog.json');catalog['asOf']='2026-10-01';self.f.f.put('publication/fulltext/catalog.json',catalog)
        self.assertEqual(directory.approved_status_overrides(self.root,self.pub),{'LV_TEST':'现行使用中'})
        self.record['scopeHint']='New unreviewed scope';self.save_record()
        self.assertEqual(directory.approved_status_overrides(self.root,self.pub),{})

    def test_legacy_publication_metadata_cannot_smuggle_full_text(self):
        for key,value in [('quote','Private text'),('textMode','full_text'),('textPath','texts/private.json'),('fullTextReviewed',True)]:
            original=copy.deepcopy(self.f.doc);self.f.doc[key]=value;self.f.save_publication()
            with self.assertRaises(ValueError):self.project()
            self.f.doc=original

    def test_record_does_not_accept_conditions_quotes_or_implied_coverage(self):
        for key in ['quote','conditions','searchTopics','reviewedClauseCount','wholeStandardComplete','allIndustryCoverage']:
            with self.assertRaisesRegex(ValueError,'DIRECTORY_RECORD_FIELDS'):directory.validate_record({**self.record,key:True})
        with self.assertRaises(ValueError):directory.validate_record({**self.record,'scopeHint':'/workspace/private/source.pdf'})

    def test_unknown_and_empty_source_dates_do_not_accept_booleans(self):
        self.assertTrue(metadata_date_equal(None,None));self.assertTrue(metadata_date_equal(None,''))
        for value in [False,True,0,1,[],{}]:self.assertFalse(metadata_date_equal(value,value))

    def test_snapshot_and_blocking_checks_include_directory(self):
        self.assertIn(directory.NAMESPACE,release_snapshot.FORMAL_NAMESPACES)
        self.assertIn('check_major_criteria_directory',validate_all.BLOCKING)
        before=release_snapshot.snapshot_digest(release_snapshot.source_hashes(self.root));p=self.root/directory.NAMESPACE/'records/DIR_TEST.json';p.write_text(p.read_text()+'\n')
        self.assertNotEqual(before,release_snapshot.snapshot_digest(release_snapshot.source_hashes(self.root)))

    def test_public_bytes_are_deterministic_across_hash_seeds(self):
        code = "import sys,json;from datetime import date;sys.path.insert(0,sys.argv[1]);from major_criteria_directory import public_projection;print(json.dumps(public_projection(sys.argv[2],sys.argv[3],as_of=date(2026,10,1))['public'],ensure_ascii=False))"
        args=[sys.executable,'-c',code,str(Path(__file__).resolve().parents[2]/'v4'),str(self.root),str(self.pub)]
        first=subprocess.check_output(args,env={**os.environ,'PYTHONHASHSEED':'1'})
        second=subprocess.check_output(args,env={**os.environ,'PYTHONHASHSEED':'7'})
        self.assertEqual(first,second)

    def test_no_implicit_today_or_string_dates(self):
        with self.assertRaises(TypeError):directory.public_projection(self.root,self.pub)
        with self.assertRaises(TypeError):directory.public_projection(self.root,self.pub,as_of='2026-10-01')


class DirectoryReleaseTests(unittest.TestCase):
    from test_field_profile_release import FieldProfileReleaseTests as _Harness
    build=_Harness.build;read=_Harness.read;reseal=_Harness.reseal;verify=_Harness.verify

    def setUp(self):
        self.d=DirectoryTests();self.d.setUp();self.addCleanup(self.d.doCleanups)
        self.fixture=self.d.f.f;self.root=self.d.root;self.publication=self.d.pub
        self.fixture.hazard.update(note='',mode='direct',conditions='Synthetic exact source condition')
        self.fixture.entity('hazards',self.fixture.hazard);self.fixture.entity('links',self.fixture.link)
        self.fixture.approve_synthetic();self.fixture.put('manifest.json',{'synthetic':True})
        self.out=self.root/'source/releases/test';self.selection=self.root/'selection.json'
        self.add_required_library_entry()

    def add_required_library_entry(self):
        doc={'versionId':'LV_STD_GBT47236_2026','textMode':'link_only','officialUrl':'https://openstd.samr.gov.cn/','effectiveDate':'2026-09-01'}
        for rel,extra in [('law-index.json',{'id':'LV_STD_GBT47236_2026'}),('fulltext/catalog.json',doc),('fulltext/search-index.json',doc)]:
            payload=directory.read(self.publication/rel);(payload if isinstance(payload,list) else payload['documents']).append(extra)
            self.fixture.put('publication/'+rel,payload)

    def test_directory_bundle_manifest_hash_and_exact_dated_library(self):
        self.build('2026-10-01');manifest=self.read('data/manifest.json')
        self.assertEqual(manifest['files']['majorCriteriaDirectory'],directory.DIRECTORY_FILE)
        self.assertEqual(manifest['counts']['majorCriteriaDirectoryGroups'],1)
        self.assertEqual(manifest['counts']['majorCriteriaDirectoryDocuments'],1)
        self.assertIn(directory.DIRECTORY_FILE,self.read('site-manifest.json')['fileHashes'])
        rc,report=self.verify();self.assertEqual(rc,0,report)
        before={p:(self.out/p).read_bytes() for p in ['data/hazards/h0000.json','data/clauses/c0000.json','data/law-index.json','data/search-index.json']}
        self.build('2026-09-30');self.assertEqual(self.read(directory.DIRECTORY_FILE)['entries'],[])
        for name in ['catalog.json','search-index.json']:
            self.assertNotIn('LV_TEST',[d['versionId'] for d in self.read('data/fulltext/'+name)['documents']])
        for path,content in before.items():self.assertEqual((self.out/path).read_bytes(),content,path)
        rc,report=self.verify();self.assertEqual(rc,0,report)

    def test_resealed_fake_current_criteria_quote_or_counts_are_rejected(self):
        self.build('2026-10-01');base=self.read(directory.DIRECTORY_FILE)
        for key,value in [('quote','Full private condition'),('effectiveDate','1900-01-01'),('fullTextReviewed',True),
                          ('standaloneDeterminationAllowed',True),('reviewedClauseCount',53)]:
            data=copy.deepcopy(base);data['entries'][0][key]=value;(self.out/directory.DIRECTORY_FILE).write_text(json.dumps(data));self.reseal()
            rc,report=self.verify();self.assertEqual(rc,1,report)
            self.assertTrue(any('官方文件题录目录精确投影' in e for e in report['errors']),report)
            self.assertFalse(any('哈希' in e or 'Hash' in e for e in report['errors']),report)

    def test_unknown_date_entry_has_no_formal_hazard_or_clause(self):
        self.d.nullable();self.add_required_library_entry();self.build('2026-10-01')
        counts=self.read('data/manifest.json')['counts'];self.assertEqual(counts['majorCriteriaDirectoryDocuments'],1)
        self.assertEqual((counts['hazards'],counts['clauses'],counts['links']),(0,0,0))
        self.assertIsNone(self.read(directory.DIRECTORY_FILE)['entries'][0]['effectiveDate'])
        rc,report=self.verify();self.assertEqual(rc,0,report)


if __name__=='__main__':unittest.main()
