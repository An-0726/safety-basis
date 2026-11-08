// Internal QA only. Hosted production uses real D1/R2, never these memory adapters.
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {MemoryD1, MemoryR2} from './tests/memory-bindings.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dist = path.join(root, 'dist');
const {default: worker} = await import(path.join(dist, 'server/index.js'));
const DB = new MemoryD1();
for (const name of (await fs.readdir(path.join(root, 'workbench/cloud/migrations'))).filter(name => name.endsWith('.sql')).sort()) {
  await DB.exec(await fs.readFile(path.join(root, 'workbench/cloud/migrations', name), 'utf8'));
}
const types = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.otf': 'font/otf', '.ttf': 'font/ttf', '.txt': 'text/plain; charset=utf-8'};
const env = {DB, BUCKET: new MemoryR2(), ASSETS: {async fetch(request) {
  const url = new URL(request.url);
  const assetRoot = path.join(dist, 'client');
  const file = path.resolve(assetRoot, '.' + decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname));
  if (!file.startsWith(assetRoot + path.sep)) return new Response('Not found', {status: 404});
  try { return new Response(await fs.readFile(file), {headers: {'Content-Type': types[path.extname(file)] || 'application/octet-stream'}}); }
  catch { return new Response('Not found', {status: 404}); }
}}};
const server = http.createServer(async (req, res) => {
  try {
    const chunks = []; let size = 0;
    for await (const chunk of req) { size += chunk.length; if (size > 24 * 1024 * 1024) { res.writeHead(413).end(); return; } chunks.push(chunk); }
    const headers = new Headers();
    for (const [key, value] of Object.entries(req.headers)) if (value !== undefined) headers.set(key, Array.isArray(value) ? value.join(', ') : value);
    const body = ['GET', 'HEAD'].includes(req.method) ? undefined : Buffer.concat(chunks);
    const request = new Request(`http://${req.headers.host}${req.url}`, {method: req.method, headers, body});
    const response = await worker.fetch(request, env);
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch { res.writeHead(500, {'Content-Type': 'text/plain; charset=utf-8'}).end('预览服务请求未完成'); }
});
const portArg = process.argv.indexOf('--port');
const port = Number(portArg >= 0 ? process.argv[portArg + 1] : process.env.PORT || 5173);
server.listen(port, '0.0.0.0', () => console.log(`Local: http://localhost:${port}/ (合成样例验收；内存存储)`));
