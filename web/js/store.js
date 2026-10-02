'use strict';
import {VerifiedFiles} from './verified-files.js';
import {profileEnvelope, validateProfileJoin, profileSummary} from './field-profiles.js';

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
  constructor(base='.') {
    this.base=base;
    this.verifiedFiles=new VerifiedFiles(base);
    this.manifest=null;
    this.searchIndex=[];
    this.lawIndex=[];
    this.taxonomy=null;
    this.hazardShardUrls=new Map();
    this.clauseShardUrls=new Map();
    this.hazardCache=new Map();
    this.clauseCache=new Map();
    this.lawMap=new Map();
    this.fieldProfiles=new Map();
    this.fieldProfileNotice='';
  }

  async fetchJson(path, {fresh=false}={}) {
    if(this.verifiedFiles.manifest) return this.verifiedFiles.read(path);
    const version=this.manifest?.dataVersion;
    const suffix=version && !fresh ? `${path.includes('?')?'&':'?'}v=${encodeURIComponent(version)}` : '';
    const res=await fetch(joinUrl(this.base,path)+suffix,{cache:fresh?'no-store':'default'});
    if(!res.ok) throw new Error(`读取失败：${path} (${res.status})`);
    return res.json();
  }

  async init() {
    await this.verifiedFiles.init();
    this.manifest=await this.fetchJson('data/manifest.json',{fresh:true});
    if(this.manifest.schemaVersion!==2) throw new Error(`不支持的数据版本：${this.manifest.schemaVersion}`);
    this.hazardShardUrls=new Map(this.manifest.hazardShards.map(x=>[x.id,x.url]));
    this.clauseShardUrls=new Map(this.manifest.clauseShards.map(x=>[x.id,x.url]));
    const [searchIndex,lawIndex,taxonomy]=await Promise.all([
      this.fetchJson(this.manifest.files.searchIndex),
      this.fetchJson(this.manifest.files.lawIndex),
      this.fetchJson(this.manifest.files.taxonomy)
    ]);

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
    await this.loadFieldProfiles();
    return this;
  }

  async loadFieldProfiles() {
    this.fieldProfiles.clear();
    if(!this.manifest.files.fieldProfiles) return;
    try {
      // Never use the legacy unverified fetch fallback for governed profiles.
      const payload=await this.verifiedFiles.read(this.manifest.files.fieldProfiles);
      const records=profileEnvelope(payload,this.verifiedFiles.manifest,this.manifest);
      const checked=[];
      for(const profile of records) {
        const index=this.searchIndex.find(row=>row.id===profile.hazardId);
        if(!index) throw new Error('核查场景对应条目不在当前发布包中');
        const detail=await this.getHazardDetail(index);
        if(!validateProfileJoin(profile,detail,payload.asOf)) throw new Error('核查场景与精确依据关联不一致');
        checked.push(profile);
      }
      // Commit only after the entire advertised payload and every join pass.
      for(const profile of checked) {
        const rows=this.fieldProfiles.get(profile.hazardId)||[];
        rows.push(profile);this.fieldProfiles.set(profile.hazardId,rows);
      }
    } catch {
      this.fieldProfiles.clear();
      this.fieldProfileNotice='核查场景暂不可用：发布包或精确依据校验未通过。原条目仍可查阅，请核对适用条件。';
    }
    this.searchIndex=this.searchIndex.map(row=>{
      const profiles=this.fieldProfiles.get(row.id)||[];
      return {...row,fieldProfiles:profiles,inspectionClasses:[...new Set(profiles.map(p=>p.inspectionClass))],
        profileSummary:profileSummary(profiles),searchText:[row.searchText,...profiles.map(p=>p.title)].join(' ').toLowerCase()};
    });
  }

  getFieldProfiles(hazardId) { return this.fieldProfiles.get(hazardId)||[]; }

  async loadHazardShard(id) {
    if(this.hazardCache.has(id)) return this.hazardCache.get(id);
    const url=this.hazardShardUrls.get(id);
    if(!url) throw new Error(`找不到隐患分片：${id}`);
    const payload=await this.fetchJson(url);
    const map=new Map(payload.records.map(x=>[x.id,x]));
    this.hazardCache.set(id,map);
    return map;
  }

  async loadClauseShard(id) {
    if(this.clauseCache.has(id)) return this.clauseCache.get(id);
    const url=this.clauseShardUrls.get(id);
    if(!url) throw new Error(`找不到法规条款分片：${id}`);
    const payload=await this.fetchJson(url);
    const map=new Map(payload.records.map(x=>[x.id,x]));
    this.clauseCache.set(id,map);
    return map;
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
    const hazard=await this.getHazard(indexRecord);
    const bases=[];
    for(const ref of hazard.basisRefs) {
      const clause=await this.getClause(ref);
      const law=this.getLaw(clause.lawId);
      bases.push({ref,clause,law,sourceUrl:publicSourceUrl(clause.sourceUrl,law.sourceUrl)});
    }
    return {hazard,bases};
  }

  async getLawDetail(lawRecord) {
    const clauses=[];
    for(const ref of lawRecord.clauseRefs) {
      const clause=await this.getClause(ref);
      clauses.push({ref,clause});
    }
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
