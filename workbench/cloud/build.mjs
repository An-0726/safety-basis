import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {parseArgs} from 'node:util';
import {build} from 'esbuild';

const cloud = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(cloud, '../..');
const {values} = parseArgs({options: {
  bundle: {type: 'string'}, output: {type: 'string'}, hosting: {type: 'string'},
}});
const bundle = path.resolve(values.bundle || process.env.WORKBENCH_BUNDLE || path.join(repo, 'source/releases/current'));
const out = path.resolve(values.output || path.join(cloud, 'dist'));
const hostingPath = path.resolve(values.hosting || path.join(repo, '.openai/hosting.json'));
const manifest = JSON.parse(await fs.readFile(path.join(bundle, 'site-manifest.json'), 'utf8'));
if (manifest.schemaVersion !== 'safety-site-bundle-v1') throw new Error('A verified site bundle is required');
const hosting = JSON.parse(await fs.readFile(hostingPath, 'utf8'));
if (!hosting.project_id || hosting.d1 !== 'DB' || hosting.r2 !== 'BUCKET' || hosting.static) throw new Error('The private Worker requires project_id, DB and BUCKET bindings');
if (out === repo || out === cloud || out === bundle || repo.startsWith(out + path.sep)) throw new Error('Unsafe build output path');
const assetRoot = path.join(out, 'client');
await fs.rm(out, {recursive: true, force: true});
await fs.mkdir(path.join(out, 'server'), {recursive: true});
await fs.mkdir(path.join(assetRoot, 'knowledge'), {recursive: true});
for (const [name, expected] of Object.entries(manifest.fileHashes || {})) {
  if (!/^data\/[A-Za-z0-9_./-]+\.json$/.test(name) || name.includes('..')) throw new Error('Unsafe knowledge asset path');
  const bytes = await fs.readFile(path.join(bundle, name));
  if (createHash('sha256').update(bytes).digest('hex') !== expected) throw new Error(`Knowledge hash mismatch: ${name}`);
  const target = path.join(assetRoot, 'knowledge', name);
  await fs.mkdir(path.dirname(target), {recursive: true});
  await fs.writeFile(target, bytes);
}
await fs.copyFile(path.join(bundle, 'site-manifest.json'), path.join(assetRoot, 'knowledge/site-manifest.json'));
for (const name of ['index.html', 'app.js', 'styles.css']) await fs.copyFile(path.join(repo, 'workbench/frontend', name), path.join(assetRoot, name));
await fs.mkdir(path.join(assetRoot, 'assets'), {recursive: true});
for (const name of ['report-font.ttf', 'OFL.txt']) await fs.copyFile(path.join(cloud, 'assets', name), path.join(assetRoot, 'assets', name));
await fs.copyFile(path.join(repo, 'workbench/templates/report-config.json'), path.join(assetRoot, 'assets/report-config.json'));
await build({entryPoints: [path.join(cloud, 'worker.mjs')], outfile: path.join(out, 'server/index.js'), bundle: true,
  format: 'esm', platform: 'browser', target: 'es2022', minify: true, legalComments: 'linked',
  external: ['node:*'], conditions: ['browser', 'import', 'default']});
await fs.writeFile(path.join(out, 'server/wrangler.json'), JSON.stringify({
  name: 'safety-basis-inspection', main: './index.js', compatibility_date: '2026-11-08', compatibility_flags: ['nodejs_compat'],
  assets: {directory: '../client', binding: 'ASSETS', run_worker_first: true},
  d1_databases: [{binding: 'DB', database_name: 'safety-basis-workbench', database_id: '00000000-0000-4000-8000-000000000000'}],
  r2_buckets: [{binding: 'BUCKET', bucket_name: 'safety-basis-workbench-files'}],
}, null, 2) + '\n');
await fs.mkdir(path.join(out, '.openai'), {recursive: true});
await fs.writeFile(path.join(out, '.openai/hosting.json'), JSON.stringify(hosting, null, 2) + '\n');
await fs.cp(path.join(cloud, 'migrations'), path.join(out, '.openai/drizzle'), {recursive: true});
const data = JSON.parse(await fs.readFile(path.join(bundle, 'data/manifest.json'), 'utf8'));
console.log(JSON.stringify({output: out, data_version: data.dataVersion, release_hash: data.releaseHash,
  knowledge_files: Object.keys(manifest.fileHashes).length, private_data_in_build: false}));
