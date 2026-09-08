from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/pipeline'))
import exchange
import identity
import admission


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.db=self.root/'master.sqlite3'
        snapshot=self.root/'evidence.txt'
        snapshot.write_text('official standard identity',encoding='utf-8')
        with closing(sqlite3.connect(self.db)) as conn:
            conn.executescript((ROOT/'source/schemas/master.sql').read_text(encoding='utf-8'))
            conn.execute('INSERT INTO evidence VALUES(?,?,?,?,?,?,?)',('E_ONE','https://example.gov.cn/standard','2026-01-01T00:00:00+00:00','evidence.txt',exchange.sha256_bytes(snapshot.read_bytes()),'','identity'))
            for law,version,year in [('L_OLD','V_OLD','2017'),('L_KEEP','V_KEEP','2026')]:
                conn.execute('INSERT INTO laws(id,canonical_name,identity_key,legacy_payload) VALUES(?,?,?,?)',(law,'同一标准 '+year,law,'{}'))
                conn.execute('INSERT INTO law_versions(id,law_id,version_key,official_name,effective_date,legacy_payload) VALUES(?,?,?,?,?,?)',(version,law,year,'同一标准',year+'-01-01','{}'))
            conn.execute("INSERT INTO clauses(id,law_version_id,article_path,quote,legacy_payload) VALUES('C_KEEP','V_OLD','1','原条文','{}')")
            conn.commit()

    def tearDown(self):
        self.temp.cleanup()

    def proposal(self):
        file=self.root/'proposal.json'
        identity.propose(self.db,'L_OLD','L_KEEP','E_ONE','官方版本关系证明同一标准系列，保留两个版本。',file)
        return file

    def test_merge_preserves_versions_and_clause_ids_and_blocks_duplicate_apply(self):
        file=self.proposal()
        result=identity.apply(self.db,file,'tester')
        self.assertEqual(result['preservedVersionIds'],['V_OLD'])
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT law_id,revision,review_status FROM law_versions WHERE id='V_OLD'").fetchone(),('L_KEEP',2,'待核验'))
            self.assertEqual(conn.execute("SELECT law_version_id,quote FROM clauses WHERE id='C_KEEP'").fetchone(),('V_OLD','原条文'))
            self.assertEqual(conn.execute("SELECT identity_status FROM laws WHERE id='L_OLD'").fetchone()[0],'merged')
            self.assertEqual(conn.execute('SELECT count(*) FROM law_identity_actions').fetchone()[0],1)
        self.assertEqual(identity.apply(self.db,file,'tester')['status'],'already_applied')

    def test_conflicting_versions_and_resealed_tampering_are_rejected(self):
        file=self.proposal()
        data=json.loads(file.read_text(encoding='utf-8'))
        data['versions'][0]['quote']='invented'
        data=admission.seal({k:v for k,v in data.items() if k not in ('proposalId','proposalHash')})
        file.write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'母库已变化|被修改'):
            identity.apply(self.db,file,'tester')
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("UPDATE law_versions SET effective_date='2017-01-01' WHERE id='V_KEEP'")
            conn.commit()
        with self.assertRaisesRegex(ValueError,'冲突'):
            identity.propose(self.db,'L_OLD','L_KEEP','E_ONE','reviewed',self.root/'conflict.json')


if __name__=='__main__':
    unittest.main()
