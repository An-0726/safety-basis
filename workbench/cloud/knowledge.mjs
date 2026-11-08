// The hosted workbench uses the same verified public store and query engine.
// No enterprise query, photo, or finding is sent to an external search service.
import {DataStore} from '../../web/js/store.js';
import {searchHazardsDetailed} from '../../web/js/search.js';

const stores = new WeakMap();

export function createKnowledge(assets, {origin = 'https://workbench-assets.invalid'} = {}) {
  if (!assets?.fetch) throw new Error('工作台知识包资源尚未绑定');
  let ready = stores.get(assets);
  if (!ready) {
    const fetcher = async input => {
      const url = new URL(String(input));
      if (url.origin !== origin || !url.pathname.startsWith('/knowledge/')) throw new Error('知识包路径无效');
      return assets.fetch(new Request(url));
    };
    ready = new DataStore(`${origin}/knowledge`, {fetcher}).init().then(store => {
      if (!store.verifiedFiles.manifest) throw new Error('工作台必须使用带校验清单的正式知识包');
      return store;
    });
    stores.set(assets, ready);
    ready.catch(() => stores.delete(assets));
  }
  return {
    async call(op, request = {}) {
      const store = await ready;
      const meta = {
        as_of: store.manifest.generatedAt, data_version: store.manifest.dataVersion,
        release_hash: store.manifest.releaseHash, counts: store.manifest.counts,
        profile_notice: store.fieldProfileNotice,
      };
      if (op === 'meta') return meta;
      if (op === 'search') {
        const result = searchHazardsDetailed(store.searchIndex, String(request.q || ''), request.filters || {});
        return {
          items: result.rows.slice(0, Math.min(Math.max(Number(request.limit) || 30, 1), 100)).map(row => ({
            id: row.id, title: row.title, category: row.displayCategory, scopes: row.scopes,
            mode: row.mode, inspectionClasses: row.inspectionClasses, profileSummary: row.profileSummary,
          })),
          total: result.rows.length, match_kind: result.matchKind, assessment: result.assessment,
          guidance: {notice: result.queryNotice, suggestions: result.suggestions || []}, meta,
        };
      }
      if (op === 'detail') {
        const row = store.searchIndex.find(item => item.id === request.hazard_id);
        if (!row) throw new Error('该条目不在当前正式发布包中');
        return {...await store.getHazardDetail(row), profiles: store.getFieldProfiles(row.id), meta};
      }
      throw new Error('未知知识查询操作');
    },
  };
}
