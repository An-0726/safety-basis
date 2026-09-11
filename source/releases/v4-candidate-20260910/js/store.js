'use strict';
import {VerifiedFiles} from './verified-files.js';

const joinUrl = (base, path) => `${base.replace(/\/$/,'')}/${path.replace(/^\//,'')}`;

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
    this.searchIndex=searchIndex;
    this.lawIndex=lawIndex;
    this.taxonomy=taxonomy;
    this.lawMap=new Map(lawIndex.map(x=>[x.id,x]));
    return this;
  }

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
      bases.push({ref,clause,law,sourceUrl:clause.sourceUrl || law.sourceUrl});
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
    return {purpose:'公开发布数据快照',manifest:this.manifest,laws:this.lawIndex,
      hazards:hazardShards.flatMap(rows=>[...rows.values()]),
      clauses:clauseShards.flatMap(rows=>[...rows.values()])};
  }

  clearMemoryCache() {
    this.hazardCache.clear();
    this.clauseCache.clear();
  }
}
