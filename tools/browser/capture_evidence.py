"""Unedited full-page evidence from a settled, physically top-scrolled page.

Never hide a header/toast, change styles, or rewrite image pixels. Failed-state
screenshots deliberately do not use this success-evidence normalizer.
"""
from pathlib import Path

SCROLL_POSITION = '() => ({x: window.scrollX, y: window.scrollY})'
SCROLL_TO = '(position) => window.scrollTo({left: position.x, top: position.y, behavior: "instant"})'
SCROLL_AT = '(position) => Math.abs(window.scrollX-position.x)<=0.5 && Math.abs(window.scrollY-position.y)<=0.5'
FONTS_READY = 'async () => { if (document.fonts) await document.fonts.ready; }'
TOAST_GONE = '''() => {
 const toast=document.querySelector('#toast'); if(!toast)return true;
 const style=getComputedStyle(toast);
 return !toast.classList.contains('show') &&
   (style.display==='none'||style.visibility==='hidden'||Number(style.opacity)===0);
}'''
SETTLED_LAYOUT = '''async ({selector,position}) => {
 if(document.fonts)await document.fonts.ready;
 let previous=null,stable=0; const deadline=performance.now()+5000;
 while(performance.now()<deadline){
  await new Promise(resolve=>requestAnimationFrame(resolve));
  const header=document.querySelector('header'),content=document.querySelector(selector);
  if(!header||!content)throw Error('Missing screenshot header or content');
  const rectangle=e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]};
  const current=JSON.stringify([scrollX,scrollY,innerWidth,innerHeight,
    document.documentElement.scrollWidth,document.documentElement.scrollHeight,
    rectangle(header),rectangle(content),document.fonts?.status??'unsupported']);
  stable=current===previous?stable+1:0;previous=current;
  if(stable>=3&&(!document.fonts||document.fonts.status==='loaded')&&
     Math.abs(scrollX-position.x)<=0.5&&Math.abs(scrollY-position.y)<=0.5)return;
 }
 throw Error('Screenshot scroll/layout did not settle');
}'''
CAPTURE_GEOMETRY = '''selector => {
 const header=document.querySelector('header'),content=document.querySelector(selector);
 const rect=e=>{const r=e.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height}};
 const h=header?rect(header):null,overlaps=[];let textRectCount=0;
 if(content&&h){
  const walker=document.createTreeWalker(content,NodeFilter.SHOW_TEXT);let node;
  while(node=walker.nextNode()){
   if(!node.textContent.trim())continue;
   const range=document.createRange();range.selectNodeContents(node);
   for(const r of range.getClientRects()){
    if(r.width<=0||r.height<=0)continue;textRectCount++;
    if(r.left<h.right&&r.right>h.left&&r.top<h.bottom&&r.bottom>h.top)
      overlaps.push(node.textContent.trim().slice(0,120));
   }
  }
 }
 const toast=document.querySelector('#toast'),style=toast?getComputedStyle(toast):null;
 return {scrollX,scrollY,header:h,content:content?rect(content):null,textRectCount,overlaps,
  fontStatus:document.fonts?.status??'unsupported',
  toastVisible:!!toast&&(toast.classList.contains('show')||
    (style.display!=='none'&&style.visibility!=='hidden'&&Number(style.opacity)>0)),
  documentWidth:document.documentElement.scrollWidth,documentHeight:document.documentElement.scrollHeight,
  activeElementId:document.activeElement?.id??''};
}'''


def validate_capture_geometry(value):
    if abs(value['scrollX']) > 0.5 or abs(value['scrollY']) > 0.5:
        raise AssertionError('Full-page evidence must be captured at the real document origin')
    header = value['header']
    if not header or abs(header['top']) > 0.5 or header['height'] <= 0:
        raise AssertionError('Screenshot header is not at the document top')
    if not value['content'] or value['textRectCount'] <= 0:
        raise AssertionError('Screenshot contains no measurable detail text')
    if value['overlaps']:
        raise AssertionError('Screenshot header overlaps detail text: ' + repr(value['overlaps']))
    if value['toastVisible']:
        raise AssertionError('Copy toast has not naturally disappeared before screenshot')
    if value['fontStatus'] not in ('loaded', 'unsupported'):
        raise AssertionError('Screenshot fonts are still loading')
    return value


def wait_capture_ready(page, *, content_selector='#detail', position=None):
    """Wait on actual presentation state without scrolling or changing the DOM."""
    position = page.evaluate(SCROLL_POSITION) if position is None else position
    page.evaluate(FONTS_READY)
    # opacity:0 still has display:block in this app: locator.hidden is not
    # appropriate, and mutating its class would fabricate evidence.
    page.wait_for_function(TOAST_GONE)
    page.evaluate(SETTLED_LAYOUT, {'selector': content_selector, 'position': position})
    return page.evaluate(SCROLL_POSITION)


def capture_full_page(page, path, *, content_selector='#detail'):
    """Capture genuine pixels, then restore the interaction's original scroll."""
    original = page.evaluate(SCROLL_POSITION)
    origin = {'x': 0, 'y': 0}
    try:
        page.evaluate(SCROLL_TO, origin)
        page.wait_for_function(SCROLL_AT, arg=origin)
        wait_capture_ready(page, content_selector=content_selector, position=origin)
        before = validate_capture_geometry(page.evaluate(CAPTURE_GEOMETRY, content_selector))
        page.screenshot(path=str(Path(path)), full_page=True)
        after = validate_capture_geometry(page.evaluate(CAPTURE_GEOMETRY, content_selector))
        for field in ('header', 'content', 'documentWidth', 'documentHeight', 'activeElementId'):
            if after[field] != before[field]:
                raise AssertionError('Screenshot capture changed settled geometry/state: ' + field)
    finally:
        page.evaluate(SCROLL_TO, original)
        page.wait_for_function(SCROLL_AT, arg=original)
    return {'originalScroll': original, 'captureState': before,
            'restoredScroll': page.evaluate(SCROLL_POSITION), 'fullPage': True,
            'realScrollNormalization': True, 'domOrStyleAltered': False}
