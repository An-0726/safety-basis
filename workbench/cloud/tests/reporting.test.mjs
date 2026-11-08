import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { PDFDocument, PDFName } from 'pdf-lib';
import { unzipSync, unzlibSync, strFromU8 } from 'fflate';
import { renderReport, REPORT_LIMITS } from '../reporting.mjs';

const snapshot = JSON.parse(await readFile(new URL('./fixtures/report-snapshot.json', import.meta.url), 'utf8'));
const fontBytes = await readFile(new URL('../assets/report-font.ttf', import.meta.url));
const jpeg = await readFile(new URL('./fixtures/synthetic-demo.jpg', import.meta.url));
const png = await readFile(new URL('./fixtures/synthetic-demo.png', import.meta.url));
const options = { fontBytes, getPhoto: async () => ({ bytes: jpeg, contentType: 'image/jpeg' }) };
const copy = () => structuredClone(snapshot);
const base = await renderReport(snapshot, options);
const xmlOf = result => strFromU8(unzipSync(result.docx)['word/document.xml']);
const unescapeXml = value => value.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, '&');
const visible = value => unescapeXml(value.replace(/<[^>]*>/g, '')).replace(/\s+/g, '');
const hasPoppler = spawnSync('pdftotext', ['-v'], { encoding: 'utf8' }).status === 0;

test('real binaries preserve six landscape columns, full law, facts, review and snapshot input', async () => {
  assert.ok(base.docx instanceof Uint8Array && base.pdf instanceof Uint8Array);
  assert.equal(String.fromCharCode(...base.pdf.subarray(0, 5)), '%PDF-');
  const xml = xmlOf(base);
  assert.equal((xml.match(/<w:gridCol\b/g) || []).length, 6);
  const page = xml.match(/<w:pgSz\b[^>]*>/)?.[0];
  assert.match(page, /w:w="16838"/); assert.match(page, /w:h="11906"/); assert.match(page, /w:orient="landscape"/);
  assert.match(xml, /<w:tblHeader\b/);
  assert.doesNotMatch(xml, /<w:trHeight\b/);
  assert.match(xml, /<w:top\b[^>]*w:sz="12"/);
  assert.match(xml, /<w:insideH\b[^>]*w:sz="4"/);
  for (const value of [snapshot.findings[0].observation, ...snapshot.findings[0].bases.flatMap(b => [b.text, b.applicability, b.hazard_conditions, b.source_url, b.link_id, b.as_of]), ...snapshot.findings[0].facts.map(f => f.label), snapshot.findings[0].reviews[0].comment]) assert.ok(visible(xml).includes(value.replace(/\s+/g, '')), `missing content: ${value.slice(0, 24)}`);
  const zip = unzipSync(base.docx);
  assert.ok(Object.keys(zip).some(name => name.startsWith('word/media/') && name.endsWith('.jpg')));
  const media = Object.entries(zip).filter(([name]) => name.startsWith('word/media/')).map(([, value]) => value);
  assert.ok(media.some(value => Buffer.from(value).equals(jpeg)), 'Word must contain the original photo bytes, never a placeholder');
  assert.match(strFromU8(zip['word/header1.xml']), /草稿 待核/);
  assert.match(strFromU8(zip['word/footer1.xml']), /PAGE/);
  const pdf = await PDFDocument.load(base.pdf);
  assert.equal(pdf.getPageCount(), 3);
  assert.ok(pdf.getPages().every(page => page.getWidth() > page.getHeight()));
  assert.match(base.template_version, /^inspection-cloud-v1-[a-f0-9]{10}$/);
  assert.match(base.pdf_engine, /^pdf-lib/);
  const reread = JSON.parse(await readFile(new URL('./fixtures/report-snapshot.json', import.meta.url), 'utf8'));
  assert.deepEqual(snapshot, reread);
});

test('PDF embeds a valid TrueType subset, not a non-portable system-font reference', async () => {
  const pdf = await PDFDocument.load(base.pdf);
  const fonts = pdf.getPage(0).node.Resources().lookup(PDFName.of('Font'));
  const type0 = fonts.lookup(fonts.keys()[0]);
  const descendants = type0.lookup(PDFName.of('DescendantFonts'));
  const descriptor = descendants.lookup(0).lookup(PDFName.of('FontDescriptor'));
  assert.ok(descriptor.has(PDFName.of('FontFile2')));
  assert.ok(!descriptor.has(PDFName.of('FontFile3')));
  assert.ok(type0.has(PDFName.of('ToUnicode')));
});

test('every embedded glyph has intact contours and coordinate bytes after subsetting', async () => {
  // A PDF can extract the right text while broken loca offsets make glyphs blank.
  // This regression catches that defect, which file signatures/page counts miss.
  const pdf = await PDFDocument.load(base.pdf);
  const fonts = pdf.getPage(0).node.Resources().lookup(PDFName.of('Font'));
  const descriptor = fonts.lookup(fonts.keys()[0]).lookup(PDFName.of('DescendantFonts')).lookup(0).lookup(PDFName.of('FontDescriptor'));
  const stream = descriptor.lookup(PDFName.of('FontFile2'));
  const bytes = unzlibSync(stream.getContents());
  const data = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const tables = new Map();
  for (let n = 0; n < data.getUint16(4); n++) {
    const at = 12 + n * 16, tag = String.fromCharCode(...bytes.subarray(at, at + 4));
    tables.set(tag, data.getUint32(at + 8));
  }
  const glyphs = data.getUint16(tables.get('maxp') + 4);
  const long = data.getInt16(tables.get('head') + 50) === 1;
  const offset = gid => tables.get('glyf') + (long ? data.getUint32(tables.get('loca') + gid * 4) : data.getUint16(tables.get('loca') + gid * 2) * 2);
  let outlines = 0;
  for (let gid = 0; gid < glyphs; gid++) {
    const start = offset(gid), end = offset(gid + 1);
    if (start === end) continue;
    const contours = data.getInt16(start);
    assert.ok(contours >= 0, 'the generated report font uses simple quadratic outlines');
    if (!contours) continue;
    outlines++;
    const points = data.getUint16(start + 10 + (contours - 1) * 2) + 1;
    let pos = start + 10 + contours * 2;
    pos += 2 + data.getUint16(pos);
    let coordinates = 0, seen = 0;
    while (seen < points) {
      assert.ok(pos < end, `glyph ${gid}: flags were truncated`);
      const flag = data.getUint8(pos++);
      const repeat = (flag & 8) ? data.getUint8(pos++) + 1 : 1;
      seen += repeat;
      coordinates += repeat * ((flag & 2) ? 1 : (flag & 16) ? 0 : 2);
      coordinates += repeat * ((flag & 4) ? 1 : (flag & 32) ? 0 : 2);
    }
    assert.equal(seen, points, `glyph ${gid}: invalid repeat flags`);
    assert.ok(pos + coordinates <= end, `glyph ${gid}: coordinate bytes were truncated`);
  }
  assert.ok(outlines > 200, 'the report must carry the actual Chinese outlines');
});

test('rendered PDF has readable full content and no font parser errors', { skip: !hasPoppler }, async () => {
  const dir = await mkdtemp(join(tmpdir(), 'report-render-'));
  try {
    const path = join(dir, 'report.pdf'); await writeFile(path, base.pdf);
    const extracted = execFileSync('pdftotext', ['-enc', 'UTF-8', '-layout', path, '-'], { encoding: 'utf8' });
    const normalized = extracted.replace(/\s+/g, '');
    for (const value of [snapshot.findings[0].bases[0].text, snapshot.findings[0].bases[0].applicability, snapshot.findings[0].observation, snapshot.findings[0].reviews[0].comment]) assert.ok(normalized.includes(value.replace(/\s+/g, '')));
    const result = spawnSync('pdftoppm', ['-f', '1', '-l', '1', '-scale-to', '800', '-png', path, join(dir, 'page')], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stderr.trim(), '', 'renderer must not report broken embedded fonts');
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('long table cells paginate, repeated headers and last facts remain present', async () => {
  const s = copy(), record = s.findings[0];
  record.description = Array.from({ length: 72 }, (_, i) => `长记录分页核查第 ${i + 1} 项：记录所见事实及核实范围，不预先认定隐患。`).join('\n') + '\n长记录最后一行完整保留';
  record.notes += '\n字体覆盖核验：鿰鿿 ᵃᵇ ⁰⁵⁶⁷⁸⁹ ₀₁₂。';
  record.rectification += '\n整改建议末尾完整保留';
  const result = await renderReport(s, options);
  const pdf = await PDFDocument.load(result.pdf);
  assert.ok(pdf.getPageCount() > 3 && pdf.getPageCount() < 30);
  assert.ok(visible(xmlOf(result)).includes('长记录最后一行完整保留'));
  if (hasPoppler) {
    const dir = await mkdtemp(join(tmpdir(), 'report-long-'));
    try {
      const path = join(dir, 'report.pdf'); await writeFile(path, result.pdf);
      const output = execFileSync('pdftotext', ['-enc', 'UTF-8', '-layout', path, '-'], { encoding: 'utf8' });
      const normalized = output.replace(/\s+/g, '');
      for (const needle of ['长记录最后一行完整保留', '整改建议末尾完整保留', '现场事实与审核记录', '鿰鿿ᵃᵇ⁰⁵⁶⁷⁸⁹₀₁₂']) assert.ok(normalized.includes(needle));
      assert.ok((output.match(/隐患照片/g) || []).length > 1);
    } finally { await rm(dir, { recursive: true, force: true }); }
  }
});

test('JPEG and PNG photos are retained, including the third-photo attachment', async () => {
  const s = copy();
  const photo = s.findings[0].photos[0];
  s.findings[0].photos.push({ ...photo, id: 'PHOTO_PNG', caption: '合成示例 PNG 照片' }, { ...photo, id: 'PHOTO_EXTRA', caption: '补充照片不得遗漏' });
  const seen = [];
  const result = await renderReport(s, { fontBytes, getPhoto: async photo => { seen.push(photo.id); return { bytes: photo.id === 'PHOTO_PNG' ? png : jpeg, contentType: photo.id === 'PHOTO_PNG' ? 'image/png' : 'image/jpeg' }; } });
  assert.equal(seen.length, 3);
  assert.ok(visible(xmlOf(result)).includes('补充照片不得遗漏'));
  assert.ok(visible(xmlOf(result)).includes('附件三补充照片'));
  assert.ok(Object.keys(unzipSync(result.docx)).some(name => name.endsWith('.png')));
  const pdf = await PDFDocument.load(result.pdf);
  assert.ok(pdf.getPageCount() >= 4);
});

test('confirmed mode rejects unreviewed records and keeps actual review information', async () => {
  const s = copy(); s.mode = 'confirmed';
  await assert.rejects(renderReport(s, options), { code: 'REPORT_UNREVIEWED' });
  const record = s.findings[0]; record.status = 'confirmed'; record.blockers = [];
  record.facts.forEach(f => { f.status = 'confirmed'; f.note = '合成流程测试核实记录'; });
  record.reviews.push({ created_at: s.created_at, reviewer: '合成测试审核员', decision: 'confirm', comment: '仅用于测试审核流程' });
  const result = await renderReport(s, options);
  assert.ok(visible(xmlOf(result)).includes('合成测试审核员'));
  assert.ok(!visible(xmlOf(result)).includes('草稿用于核查与审核'));
  assert.match(strFromU8(unzipSync(result.docx)['word/header1.xml']), /已审核记录/);
});

test('missing, changed or invalid photo bytes fail explicitly instead of omitting evidence', async () => {
  await assert.rejects(renderReport(copy(), { fontBytes, getPhoto: async () => null }), { code: 'REPORT_PHOTO_MISSING' });
  await assert.rejects(renderReport(copy(), { fontBytes, getPhoto: async () => new Uint8Array([1, 2, 3]) }), { code: 'REPORT_PHOTO_FORMAT' });
  const s = copy(); s.findings[0].photos[0].sha256 = '0'.repeat(64);
  await assert.rejects(renderReport(s, options), { code: 'REPORT_PHOTO_CHANGED' });
});

test('PNG dimensions are checked before decompression', async () => {
  const tooLarge = new Uint8Array(png);
  const view = new DataView(tooLarge.buffer); view.setUint32(16, 100000); view.setUint32(20, 100000);
  await assert.rejects(renderReport(copy(), { fontBytes, getPhoto: async () => tooLarge }), { code: 'REPORT_SIZE_LIMIT' });
  const s = copy(); s.findings[0].photos.push({ ...s.findings[0].photos[0], id: 'PNG_SECOND' });
  view.setUint32(16, 2000); view.setUint32(20, 2000);
  await assert.rejects(renderReport(s, { fontBytes, getPhoto: async () => tooLarge }), { code: 'REPORT_SIZE_LIMIT' });
});

test('eight MiB photo sets are rejected before layout to preserve Worker memory headroom', async () => {
  const s = copy();
  s.findings[0].photos = Array.from({ length: 4 }, (_, i) => ({ id: `budget-${i}`, caption: '合成压力测试' }));
  let loaded = 0;
  await assert.rejects(renderReport(s, { fontBytes, getPhoto: () => {
    loaded++;
    const bytes = new Uint8Array(2 * 1024 * 1024); bytes.set(jpeg); return bytes;
  } }), error => error.code === 'REPORT_SIZE_LIMIT' && /整份 6 MiB/.test(error.message));
  assert.equal(loaded, 4);
  assert.equal(REPORT_LIMITS.totalPhotoBytes, 6 * 1024 * 1024);
});

test('unsupported Unicode, missing original clause and invalid font never produce a silent partial report', async () => {
  const s = copy(); s.findings[0].notes = '未覆盖字形测试 🦄';
  await assert.rejects(renderReport(s, options), { code: 'REPORT_FONT_GLYPH' });
  s.findings[0].notes = ''; s.findings[0].bases[0].text = '';
  await assert.rejects(renderReport(s, options), { code: 'REPORT_MISSING_BASIS_TEXT' });
  await assert.rejects(renderReport(copy(), { fontBytes: new Uint8Array([79, 84, 84, 79]) }), { code: 'REPORT_FONT' });
});

test('replaceable JSON configuration is identified and cannot suppress audit facts', async () => {
  const s = copy(); s.findings[0].photos = [];
  const result = await renderReport(s, { fontBytes, config: { title: '专项检查记录', version: 'company-template-v2', body_pt: 10, columns_cm: [1.2, 3, 6, 4.2, 5.6, 6.7] } });
  assert.match(result.template_version, /^company-template-v2-[a-f0-9]{10}$/);
  assert.ok(visible(xmlOf(result)).includes('专项检查记录'));
  await assert.rejects(renderReport(s, { fontBytes, config: { append_facts: false } }), { code: 'REPORT_CONFIG' });
  await assert.rejects(renderReport(s, { fontBytes, config: { columns_cm: [1, 2] } }), { code: 'REPORT_CONFIG' });
  await assert.rejects(renderReport({ ...s, findings: Array(REPORT_LIMITS.findings + 1).fill(s.findings[0]) }, { fontBytes }), { code: 'REPORT_SIZE_LIMIT' });
});
