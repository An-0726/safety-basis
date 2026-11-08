import {handleApi} from './api.mjs';
import {createKnowledge} from './knowledge.mjs';
import {renderReport} from './reporting.mjs';

const SECURITY_HEADERS = {
  'Cache-Control': 'private, no-store',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  'Content-Security-Policy': "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
};

function secure(response) {
  const headers = new Headers(response.headers);
  for (const [key, value] of Object.entries(SECURITY_HEADERS)) headers.set(key, value);
  return new Response(response.body, {status: response.status, headers});
}

function identity(request) {
  const id = request.headers.get('oai-authenticated-user-id');
  let name = request.headers.get('oai-authenticated-user-full-name') || '';
  if (request.headers.get('oai-authenticated-user-full-name-encoding') === 'percent-encoded-utf-8') {
    try { name = decodeURIComponent(name); } catch { name = ''; }
  }
  if (id) return {id, source: 'chatgpt', displayName: name || request.headers.get('oai-authenticated-user-email') || '登录检查人员'};
  // This Worker is deployed exclusively through the owner-private Sites operation.
  // Sites dispatch authenticates service access before forwarding it, and does not
  // inject a visitor identity for that access. Keep the provenance explicit; never
  // represent automated service actions as the owner's professional sign-off.
  return {id: 'sites-owner-private-service', source: 'site-owner-service', displayName: '工作区服务操作'};
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get('origin');
    if ((origin && origin !== url.origin) || request.headers.get('sec-fetch-site') === 'cross-site' && !['GET', 'HEAD'].includes(request.method)) {
      return secure(Response.json({detail: '仅接受工作台本身发起的请求'}, {status: 403}));
    }
    try {
      if (url.pathname.startsWith('/api/')) {
        const knowledge = createKnowledge(env.ASSETS);
        const reporting = {
          async renderReport(snapshot, options) {
            const font = await env.ASSETS.fetch(new Request(new URL('/assets/report-font.ttf', request.url)));
            if (!font.ok) throw new Error('报告中文字体尚未部署');
            const configResponse = await env.ASSETS.fetch(new Request(new URL('/assets/report-config.json', request.url)));
            const config = configResponse.ok ? await configResponse.json() : undefined;
            return renderReport(snapshot, {...options, fontBytes: new Uint8Array(await font.arrayBuffer()), config});
          },
        };
        const response = await handleApi(request, env, {knowledge, reporting, identity: identity(request)});
        return secure(response || Response.json({detail: '接口不存在'}, {status: 404}));
      }
      if (!['GET', 'HEAD'].includes(request.method)) return secure(new Response('Method not allowed', {status: 405}));
      // Knowledge assets contain public law only; business files are never served
      // by this binding. R2 photo/report downloads always pass through the API.
      return secure(await env.ASSETS.fetch(request));
    } catch (error) {
      console.error('workbench_request_failed', {path: url.pathname, name: error?.name});
      return secure(Response.json({detail: '请求未能完成，请重试；若持续失败请检查工作区服务状态。'}, {status: 503}));
    }
  },
};
