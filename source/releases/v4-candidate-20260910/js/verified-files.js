// A page keeps one manifest; a deployment changing underneath it fails closed.
export class VerifiedFiles {
  constructor(base = '.') { this.base = base.replace(/\/$/, ''); this.manifest = null; }

  async init({required = false} = {}) {
    const response = await fetch(`${this.base}/site-manifest.json`, {cache: 'no-store'});
    if (response.status === 404 && !required) return this;
    if (!response.ok) throw new Error('发布清单读取失败，请联网刷新');
    const value = await response.json();
    if (value.schemaVersion !== 'safety-site-bundle-v1' || !value.fileHashes ||
        Object.entries(value.fileHashes).some(([path, sha]) => !/^data\/[A-Za-z0-9_./-]+\.json$/.test(path) || path.includes('..') || !/^[a-f0-9]{64}$/.test(sha))) {
      throw new Error('发布清单格式无效');
    }
    this.manifest = value;
    return this;
  }

  async read(path) {
    const sha = this.manifest?.fileHashes[path];
    if (!sha) throw new Error('文件不在当前发布清单中');
    const response = await fetch(`${this.base}/${path}?sha=${sha}`, {cache: 'no-store'});
    if (!response.ok) throw new Error(`读取失败（${response.status}）`);
    const bytes = await response.arrayBuffer();
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), x => x.toString(16).padStart(2, '0')).join('');
    if (digest !== sha) throw new Error('网站数据已更新或文件不完整，请刷新后重试');
    return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
  }
}
