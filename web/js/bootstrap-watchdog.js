// Runs as a small classic script before the module graph. A missing/old module
// must leave a usable recovery path instead of an endless initialization label.
(() => {
  const get = id => document.getElementById(id);
  const showFailure = message => {
    const status = get('loadStatus');
    if (status) { status.hidden = false; status.classList.add('failed'); }
    if (get('loadTitle')) get('loadTitle').textContent = '页面未能完成启动';
    if (get('loadMessage')) get('loadMessage').textContent = message;
    if (get('loadActions')) get('loadActions').hidden = false;
    if (get('summary')) get('summary').textContent = '启动失败，可重新加载或清理旧缓存后重试。';
  };
  async function recover() {
    if (get('recoverCache')) get('recoverCache').disabled = true;
    try {
      if ('caches' in window) {
        const keys = await caches.keys();
        await Promise.all(keys.filter(key => key.startsWith('safety-basis-')).map(key => caches.delete(key)));
      }
      if ('serviceWorker' in navigator) {
        const scope = new URL('./', location.href).href;
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.filter(registration => registration.scope === scope).map(registration => registration.unregister()));
      }
      location.reload();
    } catch (error) {
      showFailure(`清理缓存未完成：${error?.message || error}。请先点击“重新加载”；也可在浏览器网站设置中清除此站点缓存。`);
      if (get('recoverCache')) get('recoverCache').disabled = false;
    }
  }
  let started = false;
  const timer = setTimeout(() => {
    if (!started) showFailure('检索脚本未能加载，可能是网络中断、脚本加载失败或旧页面缓存与新脚本不一致。请重新加载；反复出现时清理旧缓存再试。');
  }, 20000);
  window.__safetyBasisBoot = {
    start() { started = true; clearTimeout(timer); },
    recover,
  };
  if (get('retryLoad')) get('retryLoad').onclick = () => location.reload();
  if (get('recoverCache')) get('recoverCache').onclick = recover;
  window.addEventListener('error', event => {
    if (!started && event.target?.tagName === 'SCRIPT' && /(?:^|\/)app\.js(?:\?|$)/.test(event.target.src || '')) {
      clearTimeout(timer);
      showFailure('检索脚本加载失败。请检查网络后重新加载；若更新后持续出现，请清理旧缓存再试。');
    }
  }, true);
})();
