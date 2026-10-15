import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

test('缓存升级清理接管期间旧页面重新打开的命名空间，保留其他应用缓存',async()=>{
  const source=fs.readFileSync(new URL('../web/sw.js',import.meta.url),'utf8');
  const current=source.match(/const SHELL = '([^']+)'/)[1];
  const stale='safety-basis-shell-previous';
  const keys=new Set([current,stale,'another-app-cache']);
  const listeners=new Map();let claims=0,pending;
  vm.runInNewContext(source,{
    self:{addEventListener:(name,handler)=>listeners.set(name,handler),clients:{claim:async()=>{
      claims++;
      // A still-controlled page queues an old-worker cache open during takeover.
      await Promise.resolve();keys.add(stale);
    }}},
    caches:{keys:async()=>[...keys],delete:async key=>keys.delete(key)},
  });
  listeners.get('activate')({waitUntil:promise=>{pending=promise;}});
  await pending;
  assert.equal(claims,1);
  assert.deepEqual([...keys].sort(),[current,'another-app-cache'].sort());
});
