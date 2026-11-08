'use strict';
import {VerifiedFiles, DataLoadError, loadResource, resolveDataVersion} from './verified-files.js';
import {profileEnvelope, validateProfileJoin, profileSummary} from './field-profiles.js';
import {validateNormativeClause} from './normative-content.js';

const joinUrl = (base, path) => `${base.replace(/\/$/,'')}/${path.replace(/^\//,'')}`;

export function publicSourceUrl(...values) {
  return values.find(value=>{
    if(typeof value!=='string' || !/^https?:\/\//.test(value)) return false;
    try { const url=new URL(value);return ['http:','https:'].includes(url.protocol)&&!url.username&&!url.password; } catch { return false; }
  })||'';
}

const currentHazards = rows => rows.filter(x => x.status === '已核验' && x.publishable !== false);
const currentLaws = rows => rows.filter(x => Number(x.clauseCount || 0) > 0);

export class DataStore {
  constructor(base='.', {fetcher = (...args) => fetch(...args), timeoutMs=12000, retries=1} = {}) {
    this.base=base;
    this.fetcher=fetcher;
    this.loadOptions={fetcher,timeoutMs,retries,onRetry:info=>this.progress('retry',`正在重试读取${info.resource}（第 ${info.attempt}/${info.totalAttempts} 次）`,info)};
    this.verifiedFiles=new VerifiedFiles(base,this.loadOptions);
    this.manifest=null;
    this.searchIndex=[];
    this.lawIndex=[];
    this.taxonomy=null;
    this.hazardShardUrls=new Map();
    this.clauseShardUrls=new Map();
    this.hazardCache=new Map();
    this.clauseCache=new Map();
    this.hazardPending=new Map();
    this.clausePending=new Map();
    this.lawMap=new Map();
    this.fieldProfiles=new Map();
    this.fieldProfileNotice='';
    this.fieldProfileStatus='idle';
    this.fieldProfileError=null;
    this.fieldProfilesReady=Promise.resolve(this);
    this.baseSearchText=new Map();
    this.generation=0;
    this.controller=null;
    this.onProgress=null;
    this.loadingState={phase:'idle',message:''};
    this.profilePromise=null;
  }

  progress(phase,message,detail={}) {
    const info={...detail,phase,message};
    this.loadingState=info;
    // Progress rendering is an observer; a UI error must not alter validated data.
    try { this.onProgress?.(info); } catch {}
  }

  assertGeneration(generation) {
    if(generation!==this.generation) throw new DataLoadError('CANCELLED','本次加载已取消，请以新的加载结果为准。');
  }

  async fetchJson(path, {fresh=false}={}) {
    if(this.verifiedFiles.manifest) return this.verifiedFiles.read(path);
    const version=this.manifest?.dataVersion;
    const suffix=version && !fresh ? `${path.includes('?')?'&':'?'}v=${encodeURIComponent(version)}` : '';
    return loadResource(joinUrl(this.base,path)+suffix,{
      ...this.loadOptions,signal:this.controller?.signal,resource:path,
    });
  }

  async init({deferFieldProfiles=false,onProgress,expectedVersion='',requiredManifest=false}={}) {
    const version=resolveDataVersion(expectedVersion);
    this.controller?.abort();
    this.controller=new AbortController();
    const generation=++this.generation;
    this.onProgress=onProgress||null;
    this.manifest=null;
    this.searchIndex=[];
    this.lawIndex=[];
    this.taxonomy=null;
    this.hazardShardUrls.clear();
    this.clauseShardUrls.clear();
    this.clearMemoryCache();
    this.hazardPending.clear();
    this.clausePending.clear();
    this.lawMap.clear();
    this.fieldProfiles.clear();
    this.baseSearchText.clear();
    this.fieldProfileNotice='';
    this.fieldProfileStatus='idle';
    this.fieldProfileError=null;
    this.fieldProfilesReady=Promise.resolve(this);
    this.profilePromise=null;
    this.verifiedFiles=new VerifiedFiles(this.base,this.loadOptions);
    this.progress('manifest','正在读取并校验当前发布版本');
    try {
      await this.verifiedFiles.init({required:requiredManifest,expectedVersion:version,signal:this.controller.signal});
      this.assertGeneration(generation);
      const manifest=await this.fetchJson('data/manifest.json',{fresh:true});
      this.assertGeneration(generation);
      this.manifest=manifest;
      if(this.manifest?.schemaVersion!==2 || !Array.isArray(this.manifest.hazardShards) ||
         !Array.isArray(this.manifest.clauseShards) || !this.manifest.files) {
        throw new DataLoadError('FORMAT','数据库目录格式无效，请重新加载最新数据。');
      }
      if((version && this.manifest.dataVersion!==version) ||
         (this.verifiedFiles.manifest?.dataVersion && this.verifiedFiles.manifest.dataVersion!==this.manifest.dataVersion) ||
         (this.verifiedFiles.manifest?.releaseHash && this.verifiedFiles.manifest.releaseHash!==this.manifest.releaseHash)) {
        throw new DataLoadError('VERSION_MISMATCH','页面与数据库发布版本不一致，请重新加载最新页面。');
      }
      this.hazardShardUrls=new Map(this.manifest.hazardShards.map(x=>[x.id,x.url]));
      this.clauseShardUrls=new Map(this.manifest.clauseShards.map(x=>[x.id,x.url]));
      this.progress('index','正在加载隐患、法规和分类索引');
      const [searchIndex,lawIndex,taxonomy]=await Promise.all([
        this.fetchJson(this.manifest.files.searchIndex),
        this.fetchJson(this.manifest.files.lawIndex),
        this.fetchJson(this.manifest.files.taxonomy)
      ]);
      this.assertGeneration(generation);
      if(!Array.isArray(searchIndex)||!Array.isArray(lawIndex)||!taxonomy||typeof taxonomy!=='object'||Array.isArray(taxonomy)) {
        throw new DataLoadError('FORMAT','搜索索引格式无效，请重新加载最新数据。');
      }

      // 正式网站只投影“当前已核验”视图。候选和无正式条款的 publication 目录项
      // 仍保留在 knowledge/source 层供审核与来源追溯，但不再混入正式检索结果。
      this.searchIndex=currentHazards(searchIndex).map(row=>({
        ...row,
        displayCategory:row.displayCategory??row.category??'',
        sceneTags:Array.isArray(row.sceneTags)?row.sceneTags:[],
        displayLevels:Array.isArray(row.displayLevels)?row.displayLevels:(row.levels||[]),
      }));
      this.lawIndex=currentLaws(lawIndex).map(row=>({
        ...row,
        displayLevel:row.displayLevel??row.level??'',
      }));
      this.taxonomy={
        ...taxonomy,
        displayCategories:taxonomy.displayCategories||[...new Set(this.searchIndex.map(x=>x.displayCategory).filter(Boolean))].sort(),
        sceneTagOptions:taxonomy.sceneTagOptions||[],
        displayLevels:taxonomy.displayLevels||[...new Set(this.lawIndex.map(x=>x.displayLevel).filter(Boolean))].sort(),
        hazardStatuses:['已核验'],
        lawStatuses:[...new Set(this.lawIndex.map(x=>x.status).filter(Boolean))].sort()
      };
      const health=this.manifest.health||{};
      this.manifest={
        ...this.manifest,
        counts:{...this.manifest.counts,hazards:this.searchIndex.length,laws:this.lawIndex.length,lawVersions:this.lawIndex.length},
        health:{
          ...health,
          verifiedHazards:this.searchIndex.length,
          pendingHazards:0,
          activeLaws:this.lawIndex.filter(x=>x.status==='现行有效').length,
          pendingLaws:this.lawIndex.filter(x=>x.status && x.status!=='现行有效').length
        }
      };
      this.lawMap=new Map(this.lawIndex.map(x=>[x.id,x]));
      this.baseSearchText=new Map(this.searchIndex.map(row=>[row.id,row.searchText||'']));
      this.progress('core-ready','索引已就绪，可以开始搜索',{loaded:this.searchIndex.length});
      // Profiles enrich results only after their complete exact-reference joins
      // pass. They must not hold the main search index behind dozens of requests.
      this.fieldProfilesReady=this.loadFieldProfiles();
      if(!deferFieldProfiles) await this.fieldProfilesReady;
      return this;
    } catch(error) {
      if(generation===this.generation) {
        this.controller.abort();
        this.searchIndex=[];
        this.lawIndex=[];
        this.progress('error',error.message,{error});
      }
      throw error;
    }
  }

  loadFieldProfiles({onProgress}={}) {
    if(this.profilePromise) return this.profilePromise;
    if(onProgress) this.onProgress=onProgress;
    const promise=this.loadFieldProfilesChecked(this.generation).finally(()=>{
      if(this.profilePromise===promise) this.profilePromise=null;
    });
    this.profilePromise=promise;
    this.fieldProfilesReady=promise;
    return promise;
  }

  applyProfileIndex() {
    this.searchIndex=this.searchIndex.map(row=>{
      if(!this.baseSearchText.has(row.id)) this.baseSearchText.set(row.id,row.searchText||'');
      const profiles=this.fieldProfiles.get(row.id)||[];
      return {...row,fieldProfiles:profiles,inspectionClasses:[...new Set(profiles.map(p=>p.inspectionClass))],
        profileSummary:profileSummary(profiles),searchText:[this.baseSearchText.get(row.id),...profiles.map(p=>p.title)].join(' ').trim().toLowerCase()};
    });
  }

  async loadFieldProfilesChecked(generation) {
    this.fieldProfiles.clear();
    this.fieldProfileNotice='';
    this.fieldProfileError=null;
    this.applyProfileIndex();
    if(!this.manifest?.files?.fieldProfiles) {
      this.fieldProfileStatus='ready';
      this.progress('ready','搜索数据已就绪');
      return this;
    }
    this.fieldProfileStatus='loading';
    this.progress('profiles','搜索已可用，正在校验现场适用条件');
    try {
      // Never use the legacy unverified fetch fallback for governed profiles.
      const payload=await this.verifiedFiles.read(this.manifest.files.fieldProfiles);
      this.assertGeneration(generation);
      const records=profileEnvelope(payload,this.verifiedFiles.manifest,this.manifest);
      const indexById=new Map(this.searchIndex.map(row=>[row.id,row]));
      let loaded=0;
      const outcomes=await Promise.allSettled(records.map(async profile=>{
        const index=indexById.get(profile.hazardId);
        if(!index) throw new Error('核查场景对应条目不在当前发布包中');
        const detail=await this.getHazardDetail(index);
        this.assertGeneration(generation);
        if(!validateProfileJoin(profile,detail,payload.asOf)) throw new Error('核查场景与精确依据关联不一致');
        loaded++;
        this.progress('profiles',`搜索已可用，正在校验现场适用条件（${loaded}/${records.length}）`,{loaded,total:records.length});
        return profile;
      }));
      this.assertGeneration(generation);
      const failed=outcomes.find(result=>result.status==='rejected');
      if(failed) throw failed.reason;
      const checked=outcomes.map(result=>result.value);
      // Commit only after the entire advertised payload and every join pass.
      for(const profile of checked) {
        const rows=this.fieldProfiles.get(profile.hazardId)||[];
        rows.push(profile);this.fieldProfiles.set(profile.hazardId,rows);
      }
      this.fieldProfileStatus='ready';
    } catch(error) {
      if(generation!==this.generation) return this;
      this.fieldProfiles.clear();
      this.fieldProfileStatus='unavailable';
      this.fieldProfileError=error;
      this.fieldProfileNotice=`核查场景暂不可用：${error.message} 原条目仍可检索，可重试加载场景；使用前请核对适用条件。`;
    }
    this.applyProfileIndex();
    this.progress('ready',this.fieldProfileStatus==='ready'?'搜索和现场适用条件已就绪':this.fieldProfileNotice);
    return this;
  }

  getFieldProfiles(hazardId) { return this.fieldProfiles.get(hazardId)||[]; }

  async loadHazardShard(id) {
    if(this.hazardCache.has(id)) return this.hazardCache.get(id);
    if(this.hazardPending.has(id)) return this.hazardPending.get(id);
    const url=this.hazardShardUrls.get(id);
    if(!url) throw new Error(`找不到隐患分片：${id}`);
    const generation=this.generation;
    const promise=(async()=>{
      const payload=await this.fetchJson(url);
      this.assertGeneration(generation);
      if(!Array.isArray(payload?.records)) throw new DataLoadError('FORMAT','隐患分片格式无效，请重新加载最新数据。',{resource:url});
      const map=new Map(payload.records.map(x=>[x.id,x]));
      this.hazardCache.set(id,map);
      return map;
    })();
    this.hazardPending.set(id,promise);
    try { return await promise; }
    finally { if(this.hazardPending.get(id)===promise) this.hazardPending.delete(id); }
  }

  async loadClauseShard(id) {
    if(this.clauseCache.has(id)) return this.clauseCache.get(id);
    if(this.clausePending.has(id)) return this.clausePending.get(id);
    const url=this.clauseShardUrls.get(id);
    if(!url) throw new Error(`找不到法规条款分片：${id}`);
    const generation=this.generation;
    const promise=(async()=>{
      const payload=await this.fetchJson(url);
      this.assertGeneration(generation);
      if(!Array.isArray(payload?.records)) throw new DataLoadError('FORMAT','法规分片格式无效，请重新加载最新数据。',{resource:url});
      // Do not cache or display a rich body with an incomplete plain-text copy.
      for(const clause of payload.records) validateNormativeClause(clause);
      const map=new Map(payload.records.map(x=>[x.id,x]));
      this.clauseCache.set(id,map);
      return map;
    })();
    this.clausePending.set(id,promise);
    try { return await promise; }
    finally { if(this.clausePending.get(id)===promise) this.clausePending.delete(id); }
  }

  async getHazard(indexRecord) {
    const shard=await this.loadHazardShard(indexRecord.shard);
    const row=shard.get(indexRecord.id);
    if(!row) throw new Error(`隐患记录不存在：${indexRecord.id}`);
    return row;
  }

  async getClause(ref) {
    const shard=await this.loadClauseShard(ref.clauseShard || ref.shard);
    const row=shard.get(ref.clauseId || ref.id);
    if(!row) throw new Error(`法规条款不存在：${ref.clauseId || ref.id}`);
    return row;
  }

  getLaw(id) {
    const law=this.lawMap.get(id);
    if(!law) throw new Error(`法规记录不存在：${id}`);
    return law;
  }

  async getHazardDetail(indexRecord) {
    const generation=this.generation;
    const hazard=await this.getHazard(indexRecord);
    this.assertGeneration(generation);
    const bases=await Promise.all(hazard.basisRefs.map(async ref=>{
      const clause=await this.getClause(ref);
      this.assertGeneration(generation);
      const law=this.getLaw(clause.lawId);
      return {ref,clause,law,sourceUrl:publicSourceUrl(clause.sourceUrl,law.sourceUrl)};
    }));
    return {hazard,bases};
  }

  async getLawDetail(lawRecord) {
    const generation=this.generation;
    const clauses=await Promise.all(lawRecord.clauseRefs.map(async ref=>{
      const clause=await this.getClause(ref);
      this.assertGeneration(generation);
      return {ref,clause};
    }));
    return {law:lawRecord,clauses};
  }

  async exportPublicBundle() {
    const [hazardShards,clauseShards]=await Promise.all([
      Promise.all([...this.hazardShardUrls.keys()].map(id=>this.loadHazardShard(id))),
      Promise.all([...this.clauseShardUrls.keys()].map(id=>this.loadClauseShard(id)))
    ]);
    const currentIds=new Set(this.searchIndex.map(x=>x.id));
    return {purpose:'当前已核验公开数据快照',manifest:this.manifest,laws:this.lawIndex,
      hazards:hazardShards.flatMap(rows=>[...rows.values()]).filter(x=>currentIds.has(x.id)),
      clauses:clauseShards.flatMap(rows=>[...rows.values()])};
  }

  clearMemoryCache() {
    this.hazardCache.clear();
    this.clauseCache.clear();
  }
}
