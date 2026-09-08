import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
async function sandbox(fn) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'safety-gate-'));
  try {
    await fs.cp(path.join(root, 'content'), path.join(dir, 'content'), {recursive:true});
    await fs.mkdir(path.join(dir, 'tools'));
    await fs.copyFile(path.join(root, 'tools/build-data.mjs'), path.join(dir, 'tools/build-data.mjs'));
    await fn(dir);
  } finally {
    // Only remove this test's verified mkdtemp directory beneath the OS temp root.
    assert.equal(path.dirname(dir), os.tmpdir());
    assert.ok(path.basename(dir).startsWith('safety-gate-'));
    await fs.rm(dir, {recursive:true, force:true});
  }
}
const read = async (dir, file) => JSON.parse(await fs.readFile(path.join(dir,file), 'utf8'));
const write = (dir, file, value) => fs.writeFile(path.join(dir,file), JSON.stringify(value));
const build = dir => execFileSync(process.execPath, [path.join(dir,'tools/build-data.mjs')], {stdio:'pipe'});
async function publicIds(dir) {
  build(dir);
  return (await read(dir,'data/search-index.json')).map(x=>x.id);
}

test('all source batches reconcile and no pending hazard reaches the release', async () => sandbox(async dir => {
  const ids = await publicIds(dir);
  const batchNames = (await fs.readdir(path.join(dir,'content/batches'))).filter(x=>x.endsWith('.json'));
  const batches = await Promise.all(batchNames.map(n=>read(dir,`content/batches/${n}`)));
  const totals = {};
  for (const key of ['hazards','laws','clauses','links']) {
    const rows = [...await read(dir,`content/${key}.json`), ...batches.flatMap(b=>b[key]||[])];
    totals[key] = rows.length;
    if (key === 'hazards') {
      const unpublished = rows.filter(h=>h.status !== '已核验').map(h=>h.id);
      assert.ok(unpublished.every(id=>!ids.includes(id)));
    }
  }
  const manifest = await read(dir,'data/manifest.json');
  assert.deepEqual(manifest.sourceCounts,totals);
  assert.equal(manifest.health.stagedHazards,totals.hazards-ids.length);
  const index = await read(dir,'data/law-index.json');
  assert.ok(index.every(l=>l.status !== '待核验' && l.status !== '已废止'));
  for (const shard of manifest.clauseShards) {
    assert.ok((await read(dir,shard.url)).records.every(c=>c.status === '已核验'));
  }
}));

test('pending hazard is removed from public search and reverse references', async () => sandbox(async dir => {
  const rows = await read(dir,'content/hazards.json');
  const id = rows[0].id;
  rows[0].status = '待核验';
  await write(dir,'content/hazards.json',rows);
  assert.ok(!(await publicIds(dir)).includes(id));
  const laws = await read(dir,'data/law-index.json');
  assert.ok(laws.every(l=>l.clauseRefs.every(c=>!c.hazardIds.includes(id))));
}));

test('pending clause or expired law blocks every dependent hazard', async () => {
  for (const entity of ['clauses','laws']) await sandbox(async dir => {
    const rows = await read(dir,`content/${entity}.json`);
    const allClauses = await read(dir,'content/clauses.json');
    const links = await read(dir,'content/links.json');
    const id = rows[0].id;
    const clauseIds = entity === 'clauses' ? [id] : allClauses.filter(c=>c.lawId===id).map(c=>c.id);
    const blocked = links.filter(x=>clauseIds.includes(x.clauseId)).map(x=>x.hazardId);
    assert.ok(blocked.length>0);
    rows[0].status = entity === 'clauses' ? '待核验' : '已废止';
    await write(dir,`content/${entity}.json`,rows);
    const publicRecords = await publicIds(dir);
    assert.ok(blocked.every(id=>!publicRecords.includes(id)));
  });
});

test('orphan reference fails the build', async () => sandbox(async dir => {
  const links = await read(dir,'content/links.json');
  links[0].clauseId = 'C_DOES_NOT_EXIST';
  await write(dir,'content/links.json',links);
  assert.throws(()=>build(dir), /条款不存在/);
}));

test('catalog version IDs survive builds and reverse references', async () => sandbox(async dir => {
  const laws = await read(dir, 'content/laws.json');
  const clauses = await read(dir, 'content/clauses.json');
  const old = laws[0].id;
  const id = 'LV_NPC_2933e1a00644487bbd43d0960cb01931';
  laws[0].id = id;
  for (const law of laws) for (const key of ['replaces', 'replacedBy']) {
    law[key] = law[key].map(ref => ref === old ? id : ref);
  }
  for (const clause of clauses) if (clause.lawId === old) clause.lawId = id;
  const names = await fs.readdir(path.join(dir, 'content/batches'));
  for (const name of names.filter(name => name.endsWith('.json'))) {
    const file = `content/batches/${name}`;
    const batch = await read(dir, file);
    for (const clause of batch.clauses || []) if (clause.lawId === old) clause.lawId = id;
    for (const law of batch.laws || []) for (const key of ['replaces', 'replacedBy']) {
      law[key] = (law[key] || []).map(ref => ref === old ? id : ref);
    }
    await write(dir, file, batch);
  }
  await write(dir, 'content/laws.json', laws);
  await write(dir, 'content/clauses.json', clauses);
  build(dir);
  assert.ok((await read(dir, 'data/law-index.json')).some(law => law.id === id));
  laws[0].id = '../invalid';
  await write(dir, 'content/laws.json', laws);
  assert.throws(() => build(dir), /ID 无效/);
}));
