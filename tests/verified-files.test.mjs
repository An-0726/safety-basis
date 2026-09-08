import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {VerifiedFiles} from '../js/verified-files.js';

test('release hashes accept exact bytes and reject a different deployment', async () => {
  const original = globalThis.fetch;
  const body = JSON.stringify({text: '安全生产'});
  const sha = createHash('sha256').update(body).digest('hex');
  let swapped = false;
  globalThis.fetch = async url => new Response(url.endsWith('site-manifest.json')
    ? JSON.stringify({schemaVersion:'safety-site-bundle-v1', fileHashes:{'data/text.json':sha}})
    : swapped ? JSON.stringify({text:'another version'}) : body);
  try {
    const files = await new VerifiedFiles().init({required:true});
    assert.deepEqual(await files.read('data/text.json'), {text:'安全生产'});
    swapped = true;
    await assert.rejects(files.read('data/text.json'), /数据已更新/);
    await assert.rejects(files.read('data/private.json'), /清单/);
  } finally { globalThis.fetch = original; }
});

test('only a missing optional manifest permits legacy mode', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response('', {status:404});
    assert.equal((await new VerifiedFiles().init()).manifest, null);
    await assert.rejects(new VerifiedFiles().init({required:true}), /读取失败/);
    globalThis.fetch = async () => new Response('', {status:500});
    await assert.rejects(new VerifiedFiles().init(), /读取失败/);
  } finally { globalThis.fetch = original; }
});
