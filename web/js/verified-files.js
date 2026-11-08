// Every page pins one release. Timeouts cover the response body as well as
// headers, and retries never admit bytes from a different release.
const BUILT_DATA_VERSION = '__SAFETY_BASIS_DATA_VERSION__';
export const SCRIPT_DATA_VERSION = BUILT_DATA_VERSION.startsWith('__') ? '' : BUILT_DATA_VERSION;

export class DataLoadError extends Error {
  constructor(code, message, {resource = '', status = 0, retryable = false, cause} = {}) {
    super(message, cause ? {cause} : undefined);
    this.name = 'DataLoadError';
    this.code = code;
    this.resource = resource;
    this.status = status;
    this.retryable = retryable;
  }
}

const cancelled = () => new DataLoadError('CANCELLED', '本次加载已取消，请以新的加载结果为准。');
const versionValue = value => typeof value === 'string' && !value.startsWith('__') ? value : '';
export function resolveDataVersion(expectedVersion = '') {
  const expected = versionValue(expectedVersion);
  const page = typeof document === 'undefined' ? '' : versionValue(
    document.querySelector?.('meta[name="safety-basis-version"]')?.content);
  const versions = [expected, page, SCRIPT_DATA_VERSION].filter(Boolean);
  if (new Set(versions).size > 1) {
    throw new DataLoadError('VERSION_MISMATCH', '页面与脚本版本不一致，请重新加载最新页面。');
  }
  return expected || page || SCRIPT_DATA_VERSION;
}

// A Promise race is necessary: AbortController alone cannot bound a stalled
// body, a service worker, or a custom fetcher that does not honor its signal.
export async function loadResource(url, {
  fetcher = (...args) => fetch(...args), resource = '网站数据', format = 'json',
  timeoutMs = 12000, retries = 1, signal, cache = 'no-store', allowMissing = false, onRetry,
} = {}) {
  const deadline = Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 12000;
  const retryCount = Number.isInteger(retries) ? Math.max(0, Math.min(retries, 2)) : 1;
  for (let attempt = 0; attempt <= retryCount; attempt++) {
    if (signal?.aborted) throw cancelled();
    const controller = new AbortController();
    let timer, abortListener, timedOut = false;
    const timeoutError = () => new DataLoadError('TIMEOUT',
      `读取${resource}超时（${Math.ceil(deadline / 1000)} 秒），请检查网络后重试。`,
      {resource, retryable: true});
    const interruption = new Promise((_, reject) => {
      timer = setTimeout(() => { timedOut = true; controller.abort(); reject(timeoutError()); }, deadline);
      if (signal) {
        abortListener = () => { controller.abort(); reject(cancelled()); };
        signal.addEventListener('abort', abortListener, {once: true});
      }
    });
    const operation = (async () => {
      let response;
      try {
        response = await fetcher(url, {cache, signal: controller.signal});
      } catch (cause) {
        if (signal?.aborted) throw cancelled();
        if (timedOut) throw timeoutError();
        throw new DataLoadError('NETWORK', `网络连接中断，未能读取${resource}，请重试。`,
          {resource, retryable: true, cause});
      }
      if (response.status === 404 && allowMissing) return null;
      if (!response.ok) {
        throw new DataLoadError('HTTP', `${resource}读取失败（HTTP ${response.status}），请重试。`,
          {resource, status: response.status, retryable: [408, 429].includes(response.status) || response.status >= 500});
      }
      try {
        return format === 'bytes' ? await response.arrayBuffer() : await response.json();
      } catch (cause) {
        if (signal?.aborted) throw cancelled();
        if (timedOut) throw timeoutError();
        if (cause instanceof SyntaxError) {
          throw new DataLoadError('FORMAT', `${resource}格式无效，请重新加载最新数据。`, {resource, cause});
        }
        throw new DataLoadError('NETWORK', `${resource}传输中断或未完整接收，请重试。`,
          {resource, retryable: true, cause});
      }
    })();
    try {
      return await Promise.race([operation, interruption]);
    } catch (error) {
      if (attempt >= retryCount || !error.retryable || signal?.aborted) throw error;
      onRetry?.({resource, attempt: attempt + 2, totalAttempts: retryCount + 1, error});
    } finally {
      clearTimeout(timer);
      if (signal && abortListener) signal.removeEventListener('abort', abortListener);
    }
  }
}

export class VerifiedFiles {
  constructor(base = '.', {fetcher = (...args) => fetch(...args), timeoutMs = 12000, retries = 1, onRetry} = {}) {
    this.base = base.replace(/\/$/, '');
    this.manifest = null;
    this.fetcher = fetcher;
    this.options = {fetcher, timeoutMs, retries, onRetry};
    this.signal = null;
    this.pending = new Map();
  }

  async init({required = false, expectedVersion = '', signal} = {}) {
    const version = resolveDataVersion(expectedVersion);
    this.manifest = null;
    this.pending.clear();
    this.signal = signal;
    const value = await loadResource(`${this.base}/site-manifest.json`, {
      ...this.options, signal, resource: '发布清单', allowMissing: !required && !version,
    });
    if (value === null) return this;
    if (value?.schemaVersion !== 'safety-site-bundle-v1' || !value.fileHashes ||
        typeof value.fileHashes !== 'object' || Array.isArray(value.fileHashes) ||
        Object.entries(value.fileHashes).some(([path, sha]) => !/^data\/[A-Za-z0-9_./-]+\.json$/.test(path) || path.includes('..') || !/^[a-f0-9]{64}$/.test(sha))) {
      throw new DataLoadError('FORMAT', '发布清单格式无效，请重新加载最新页面。');
    }
    if (version && value.dataVersion !== version) {
      throw new DataLoadError('VERSION_MISMATCH', '页面与数据库发布版本不一致，请重新加载最新页面。');
    }
    this.manifest = value;
    return this;
  }

  async read(path) {
    const sha = this.manifest?.fileHashes[path];
    if (!sha) throw new DataLoadError('MANIFEST_MISSING_FILE', '文件不在当前发布清单中，请重新加载最新页面。', {resource: path});
    // Coalesce concurrent reads, but do not retain a second unbounded data cache.
    // Later reads must still detect deployment changes and truncated responses.
    if (this.pending.has(path)) return this.pending.get(path);
    const promise = this.readVerified(path, sha);
    this.pending.set(path, promise);
    try { return await promise; }
    finally { if (this.pending.get(path) === promise) this.pending.delete(path); }
  }

  async readVerified(path, sha) {
    const bytes = await loadResource(`${this.base}/${path}?sha=${sha}`, {
      ...this.options, signal: this.signal, resource: path, format: 'bytes',
    });
    if (!globalThis.crypto?.subtle) {
      throw new DataLoadError('INTEGRITY', '浏览器无法校验数据，请使用 HTTPS 正式网址或本机服务打开。');
    }
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), x => x.toString(16).padStart(2, '0')).join('');
    if (digest !== sha) {
      throw new DataLoadError('INTEGRITY', '网站数据已更新或文件不完整，请刷新后重试。', {resource: path});
    }
    try { return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes)); }
    catch (cause) { throw new DataLoadError('FORMAT', '网站数据格式无效，请重新加载最新数据。', {resource: path, cause}); }
  }
}
