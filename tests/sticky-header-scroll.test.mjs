import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';

const source=fs.readFileSync(new URL('../web/app.js',import.meta.url),'utf8')
  .replace(/^import[^\n]*\n/gm,'').replace(/^export /gm,'')
  .replace("if(typeof document!=='undefined') boot();",'');

function load({height=104,narrow=true,observer=true}={}){
  const properties=new Map(),events=new Map(),calls=[];
  const header={getBoundingClientRect:()=>({height})};
  const title={scrollIntoView:options=>calls.push({target:'title',options,offset:properties.get('--sticky-header-height')})};
  const list={focus:options=>calls.push({target:'focus',options}),scrollIntoView:options=>calls.push({target:'list',options,offset:properties.get('--sticky-header-height')})};
  let resizeObserver;
  const context={document:{querySelector:selector=>({'header':header,'#detail h2':title,'#list':list}[selector]||null),documentElement:{style:{setProperty:(key,value)=>properties.set(key,value)}}},
    addEventListener:(type,callback)=>events.set(type,callback),matchMedia:()=>({matches:narrow})};
  context.window=context;
  if(observer)context.ResizeObserver=class{constructor(callback){this.callback=callback;resizeObserver=this;}observe(node){this.node=node;}};
  vm.createContext(context);
  new vm.Script(source+'\nglobalThis.api={state,bindStickyHeaderHeight,bindDetailUtilities,backToResults};').runInContext(context);
  return {api:context.api,properties,events,calls,header,setHeight:value=>height=value,getObserver:()=>resizeObserver};
}

test('sticky offset measures actual header height at boot and after row/font changes',()=>{
  const app=load();app.api.bindStickyHeaderHeight();
  assert.equal(app.properties.get('--sticky-header-height'),'104px');
  assert.equal(app.getObserver().node,app.header);
  for(const height of [72,86,104,148,167.5]){
    app.setHeight(height);app.getObserver().callback();
    assert.equal(app.properties.get('--sticky-header-height'),`${height}px`);
  }
});

test('resize fallback works without ResizeObserver',()=>{
  const app=load({observer:false});app.api.bindStickyHeaderHeight();
  app.setHeight(148);app.events.get('resize')();
  assert.equal(app.properties.get('--sticky-header-height'),'148px');
});

test('narrow selection measures synchronously before scrolling, including repeated selection',()=>{
  const app=load();app.api.bindStickyHeaderHeight();
  for(const height of [104,148]){
    app.setHeight(height);app.api.state.pendingDetailScroll=true;app.api.bindDetailUtilities('H004');
    const call=app.calls.at(-1);
    assert.equal(call.target,'title');assert.equal(call.options.block,'start');
    assert.equal(call.offset,`${height}px`);assert.equal(call.options.behavior,undefined);
    assert.equal(app.api.state.pendingDetailScroll,false);
  }
  app.api.bindDetailUtilities('H004');assert.equal(app.calls.length,2);
});

test('desktop selection and ordinary rerender retain existing non-scrolling behavior',()=>{
  const app=load({narrow:false,height:86});app.api.bindStickyHeaderHeight();
  app.api.state.pendingDetailScroll=true;app.api.bindDetailUtilities('H004');
  assert.equal(app.calls.length,0);assert.equal(app.api.state.pendingDetailScroll,false);
});

test('Return results keeps focus and measures current header before scrolling',()=>{
  const app=load();app.setHeight(148);app.api.backToResults();
  assert.equal(app.calls[0].target,'focus');assert.equal(app.calls[0].options.preventScroll,true);
  assert.equal(app.calls[1].target,'list');assert.equal(app.calls[1].offset,'148px');
  assert.equal(app.calls[1].options.block,'start');
});

test('narrow scroll margin covers heading, native detail hash and results without desktop redesign',()=>{
  const css=fs.readFileSync(new URL('../web/stage3.css',import.meta.url),'utf8');
  assert.match(css,/@media\(max-width:780px\)\{[^]*?\.detail h2,#detail,#list\{scroll-margin-top:calc\(var\(--sticky-header-height,0px\) \+ 12px\)\}/);
  assert.doesNotMatch(css,/scroll-margin-top:90px|scroll-behavior:smooth/);
});
