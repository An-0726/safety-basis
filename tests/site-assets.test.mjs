import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=relative=>readFileSync(path.join(root,relative),'utf8');
const assetsFrom=relative=>new Set([...read(relative).match(/SITE_ASSETS = \(([\s\S]*?)\)\n/)[1].matchAll(/"([^"]+)"/g)].map(m=>m[1]));
test('builder and strict verifier cover every transitive shipped JavaScript import',()=>{
  const builder=assetsFrom('tools/v4/build_unified_release.py'),verifier=assetsFrom('tools/v4/verify_unified_bundle.py');
  assert.deepEqual(builder,verifier);
  for(const asset of builder){
    if(!asset.endsWith('.js'))continue;
    for(const [,relative] of read('web/'+asset).matchAll(/import\s+[^;]*?from\s*['"]([^'"]+)['"]/g)){
      assert.ok(relative.startsWith('.'),'Only local runtime imports are expected');
      const target=path.posix.normalize(path.posix.join(path.posix.dirname(asset),relative));
      assert.ok(builder.has(target),`${asset} imports unshipped ${target}`);
    }
  }
});
test('every service worker precache path is a shipped asset',()=>{
  const assets=assetsFrom('tools/v4/build_unified_release.py');
  for(const [,relative] of read('web/sw.js').matchAll(/'\.\/([^']*)'/g))assert.ok(assets.has(relative||'index.html'),`Unshipped precache file ${relative}`);
});
