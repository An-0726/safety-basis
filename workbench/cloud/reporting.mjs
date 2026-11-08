/**
 * Worker-compatible Word/PDF renderer for the existing immutable report snapshot.
 * No filesystem, network request, DOM, model, or secondary legal database is used.
 * The caller authorizes and retrieves private photos through getPhoto(photo).
 */
import {
  AlignmentType, BorderStyle, Document, Footer, Header, HeadingLevel, ImageRun, LineRuleType,
  Packer, PageNumber, PageOrientation, Paragraph, Table, TableCell, TableLayoutType,
  TableRow, TextRun, VerticalAlign, WidthType,
} from 'docx';
import { PDFDocument, rgb } from 'pdf-lib';
import fontkit from '@pdf-lib/fontkit';
import { unzipSync, zipSync } from 'fflate';

export const DEFAULT_REPORT_CONFIG = Object.freeze({
  version: 'inspection-cloud-v1', title: '安全检查记录', font: '宋体',
  page_size: 'A4', orientation: 'landscape', margin_cm: 1.5, body_pt: 10.5,
  columns_cm: Object.freeze([1.2, 2.8, 6, 4.2, 5.8, 6.7]), append_facts: true,
});
export const REPORT_LIMITS = Object.freeze({
  findings: 150, textCharacters: 300000, photoBytes: 6 * 1024 * 1024,
  totalPhotoBytes: 6 * 1024 * 1024, pngPixels: 4000000, totalPngPixels: 4000000,
  jpegPixels: 60000000, fontBytes: 24 * 1024 * 1024, pages: 500,
});
const STATUS = Object.freeze({ draft: '草稿', needs_facts: '待补事实/证据', pending_review: '待审核', confirmed: '已确认', rejected: '已驳回' });
const FACT_STATUS = Object.freeze({ confirmed: '已确认', denied: '已否定', unknown: '待核' });
const DECISION = Object.freeze({ submit: '提交审核', confirm: '审核确认', reject: '驳回', reopen: '重新核查' });
const HEADERS = ['序号', '位置 / 设备', '隐患', '隐患照片', '整改建议', '依据 / 状态'];
const CM = 72 / 2.54;
const PAGE = { width: 29.7 * CM, height: 21 * CM };
const BLACK = rgb(0, 0, 0);
const BORDER = rgb(0.82, 0.84, 0.86);
const HEADER_FILL = rgb(0.91, 0.94, 0.96);

export class ReportError extends Error {
  constructor(code, message) { super(message); this.name = 'ReportError'; this.code = code; }
}
function fail(code, message) { throw new ReportError(code, message); }
function text(value = '') {
  if (value === null || value === undefined) return '';
  if (typeof value !== 'string' && typeof value !== 'number') fail('REPORT_INVALID_SNAPSHOT', '报告文字字段格式无效');
  const result = String(value).replace(/\r\n?/g, '\n');
  if (/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/u.test(result)) fail('REPORT_INVALID_TEXT', '报告包含不可显示的控制字符，请修正对应文字');
  return result;
}
function list(value) { return Array.isArray(value) ? value : []; }
function labelled(label, value, fallback = '未填写') { return `${label}：${text(value) || fallback}`; }
function citation(basis) {
  const number = text(basis.document_number);
  let name = text(basis.law_name) || '法规名称待核';
  if (number && name.endsWith(` ${number}`)) name = name.slice(0, -(number.length + 1));
  return `《${name}》${number ? `（${number}）` : ''}${text(basis.article)}`;
}
function normalizeConfig(override) {
  if (override !== undefined && (!override || typeof override !== 'object' || Array.isArray(override))) fail('REPORT_CONFIG', '报告模板配置必须为 JSON 对象');
  const allowed = new Set(Object.keys(DEFAULT_REPORT_CONFIG));
  for (const key of Object.keys(override || {})) if (!allowed.has(key)) fail('REPORT_CONFIG', `不支持的报告模板配置项：${key}`);
  const config = { ...DEFAULT_REPORT_CONFIG, ...override };
  config.body_pt = Number(config.body_pt); config.margin_cm = Number(config.margin_cm);
  config.title = text(config.title); config.font = text(config.font); config.version = text(config.version);
  if (!config.title || config.title.length > 100 || !config.font || !/^[A-Za-z0-9._-]{1,80}$/.test(config.version)) fail('REPORT_CONFIG', '报告标题、字体或模板版本无效');
  if (config.page_size !== 'A4' || config.orientation !== 'landscape') fail('REPORT_CONFIG', '云端检查记录使用 A4 横向版式');
  if (!(config.body_pt >= 8 && config.body_pt <= 14) || !(config.margin_cm >= 0.8 && config.margin_cm <= 2.5)) fail('REPORT_CONFIG', '字号应为 8 至 14 磅，页边距应为 0.8 至 2.5 厘米');
  if (!Array.isArray(config.columns_cm) || config.columns_cm.length !== 6 || config.columns_cm.some(v => !Number.isFinite(v) || v <= 0)) fail('REPORT_CONFIG', '检查记录必须配置六列有效列宽');
  config.columns_cm = [...config.columns_cm];
  const sum = config.columns_cm.reduce((a, b) => a + b, 0);
  if (config.columns_cm.some(v => v / sum < 0.035)) fail('REPORT_CONFIG', '列宽过窄，可能影响完整显示');
  if (config.append_facts !== true) fail('REPORT_CONFIG', '云端报告必须保留完整事实与审核附件');
  return config;
}
function basisKey(basis) {
  // Never merge distinct historical texts, conditions, profiles or source versions.
  return JSON.stringify(['link_id', 'text', 'applicability', 'hazard_conditions', 'as_of', 'data_version', 'effective_date', 'source_url', 'release_hash', 'source_fingerprint'].map(k => text(basis[k])).concat(JSON.stringify(basis.profile || null)));
}
function makeModel(snapshot, config) {
  if (!snapshot || snapshot.schema_version !== 1 || !snapshot.project || !Array.isArray(snapshot.findings) || !['draft', 'confirmed'].includes(snapshot.mode) || !text(snapshot.id)) fail('REPORT_INVALID_SNAPSHOT', '报告快照结构或状态无效');
  if (!snapshot.findings.length || snapshot.findings.length > REPORT_LIMITS.findings) fail('REPORT_SIZE_LIMIT', `单份报告须包含 1 至 ${REPORT_LIMITS.findings} 条记录，请按项目分批导出`);
  const model = { snapshot, config, bases: [], rows: [], sections: [], strings: [] };
  const remember = value => { const result = text(value); model.strings.push(result); return result; };
  model.status = snapshot.mode === 'draft' ? '草稿 待核' : '已审核记录';
  model.title = remember(config.title + (snapshot.mode === 'draft' ? '（草稿·待核）' : ''));
  const project = snapshot.project;
  model.intro = [
    `受检单位：${text(project.company)}    检查项目：${text(project.name)}`,
    `检查日期：${text(project.inspection_date)}    检查人：${text(project.inspectors)}    检查用途：${text(project.purpose)}`,
    `导出记录 ${snapshot.findings.length} 条；未纳入本报告 ${Number(snapshot.excluded_count) || 0} 条。`,
  ];
  if (snapshot.mode === 'draft') model.intro.push('草稿用于核查与审核；待核、待审核和驳回记录均不得作为已确认隐患结论。');
  model.intro = model.intro.map(remember);
  const positions = new Map();
  const references = finding => list(finding.bases).map(basis => {
    const key = basisKey(basis);
    if (!positions.has(key)) { positions.set(key, model.bases.length + 1); model.bases.push(basis); }
    return positions.get(key);
  });
  snapshot.findings.forEach((finding, index) => {
    if (!Object.hasOwn(STATUS, finding.status)) fail('REPORT_INVALID_SNAPSHOT', '记录包含未知审核状态');
    if (snapshot.mode === 'confirmed' && (finding.status !== 'confirmed' || list(finding.blockers).length)) fail('REPORT_UNREVIEWED', '正式报告不能包含未确认或仍有待核事项的记录');
    const refs = [...new Set(references(finding))];
    const reviews = list(finding.reviews).filter(r => ['confirm', 'reject'].includes(r.decision));
    const latest = reviews.at(-1);
    const cells = [
      String(index + 1),
      [text(finding.location), text(finding.equipment)].filter(Boolean).join('\n') || '位置待填写',
      (text(finding.description) || '待填写专业描述') + (finding.finding_kind === 'document_review' ? '\n核查类型：资料核查' : ''),
      '',
      (text(finding.rectification) || '待核定整改方向') + ((finding.due_date || finding.assignee) ? `\n责任人：${text(finding.assignee) || '待定'}\n期限：${text(finding.due_date) || '待定'}` : ''),
      (refs.map(n => `[${n}] ${citation(model.bases[n - 1])}`).join('\n') || '法源待核') + `\n状态：${STATUS[finding.status]}` + (latest ? `\n审核人：${text(latest.reviewer)}\n意见：${text(latest.comment)}` : ''),
    ].map(remember);
    const photos = list(finding.photos).map((photo, pi) => {
      if (!text(photo.id)) fail('REPORT_INVALID_SNAPSHOT', '照片缺少稳定标识');
      const caption = remember(text(photo.caption) || text(photo.filename) || `照片 ${pi + 1}`);
      return { photo, caption, key: text(photo.id), findingNumber: index + 1 };
    });
    model.rows.push({ cells, photos });
  });
  const bases = { heading: '附件一 法规依据与适用条件', items: [] };
  bases.items.push({ text: '以下为选定引用的完整条文快照。引用序号对应检查记录，适用条件和逐项现场核实记录分别保留。' });
  if (!model.bases.length) bases.items.push({ text: '本报告尚未选定法规依据，相关记录仍需核实法源。' });
  model.bases.forEach((basis, index) => {
    const body = text(basis.text);
    if (!body) fail('REPORT_MISSING_BASIS_TEXT', '引用条款缺少完整原文，请重新选入已核实依据');
    bases.items.push(
      { text: `[${index + 1}] ${citation(basis)}`, heading: true },
      { text: body },
      { text: labelled('本次关联的适用条件', basis.applicability, '待核') },
      { text: labelled('隐患适用范围', basis.hazard_conditions, '待核') },
      { text: `地域与范围：${text(basis.scope) || '待核'}；引用作用：${text(basis.role) || '未标注'}` },
      { text: labelled('官方来源', basis.source_url, '见知识库已核证据链'), small: true },
      { text: `H：${text(basis.hazard_id)}；K：${text(basis.link_id)}；C：${text(basis.clause_id)}；LV：${text(basis.law_version_id)}`, small: true },
      { text: `施行日期：${text(basis.effective_date) || '待核'}；依据快照日期：${text(basis.as_of)}；知识包版本：${text(basis.data_version)}；查询时间：${text(basis.queried_at)}`, small: true },
    );
    if (basis.release_hash) bases.items.push({ text: labelled('知识包校验值', basis.release_hash), small: true });
    const profile = basis.profile;
    if (profile) {
      bases.items.push({ text: `所选场景：${text(profile.title || profile.name || profile.id)}（${text(profile.id)}）` });
      for (const [key, label] of [['requires', '场景前提'], ['excludes', '误判边界'], ['perUseFacts', '本次事实键']]) {
        for (const value of list(profile.applicability?.[key])) bases.items.push({ text: `${label}：${text(value)}` });
      }
    }
  });
  model.sections.push(bases);
  const facts = { heading: '附件二 现场事实与审核记录', items: [] };
  snapshot.findings.forEach((finding, index) => {
    facts.items.push({ text: `记录 ${index + 1} · ${text(finding.location)} · ${STATUS[finding.status]}`, heading: true });
    facts.items.push({ text: labelled('现场原话', finding.observation, '待填写') });
    facts.items.push({ text: `核查类型：${finding.finding_kind === 'document_review' ? '资料核查' : '现场隐患核查'}；记录版本：${text(finding.revision) || '未标注'}` });
    for (const fact of list(finding.facts)) {
      if (!Object.hasOwn(FACT_STATUS, fact.status)) fail('REPORT_INVALID_SNAPSHOT', '事实项包含未知确认状态');
      facts.items.push({ text: `[${FACT_STATUS[fact.status]}] ${text(fact.label)}\n核实记录：${text(fact.note) || '待补充'}` });
    }
    if (!list(finding.facts).length) facts.items.push({ text: '尚无逐项事实确认记录。' });
    if (finding.notes) facts.items.push({ text: labelled('备注', finding.notes) });
    for (const blocker of list(finding.blockers)) facts.items.push({ text: labelled('待核事项', blocker) });
    for (const review of list(finding.reviews)) facts.items.push({ text: `${text(review.created_at)} · ${text(review.reviewer) || '未填写审核人'} · ${DECISION[review.decision] || text(review.decision)} · ${text(review.comment) || '无补充意见'}`, small: true });
    if (!list(finding.reviews).length) facts.items.push({ text: '尚无专业审核记录。' });
  });
  model.sections.push(facts);
  const extras = model.rows.flatMap(row => row.photos.slice(2));
  if (extras.length) model.sections.push({ heading: '附件三 补充照片', items: extras.flatMap(photo => [{ text: `记录 ${photo.findingNumber} · ${photo.caption}`, heading: true }, { image: photo }]) });
  for (const section of model.sections) {
    remember(section.heading);
    for (const item of section.items) if (item.text !== undefined) item.text = remember(item.text);
  }
  remember(`记录编号 ${text(snapshot.id)}  ${text(snapshot.created_at)}`);
  remember(model.status); HEADERS.forEach(remember);
  // Generated labels may occur only with pictures or page continuation.
  remember('草稿 待核 未经审核不得作为确认结论 已审核记录 第 页 共 无照片 其余 张见照片附件 续');
  if (model.strings.reduce((n, s) => n + s.length, 0) > REPORT_LIMITS.textCharacters) fail('REPORT_SIZE_LIMIT', '报告文字过多，请按检查区域或记录分批导出');
  return model;
}

function asBytes(value) {
  if (value instanceof Uint8Array) return value;
  if (value instanceof ArrayBuffer) return new Uint8Array(value);
  if (ArrayBuffer.isView(value)) return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
  return null;
}
function imageInfo(bytes) {
  if (bytes.length >= 24 && bytes[0] === 137 && bytes[1] === 80 && bytes[2] === 78 && bytes[3] === 71 && bytes[4] === 13 && bytes[5] === 10 && bytes[6] === 26 && bytes[7] === 10) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    if (String.fromCharCode(...bytes.subarray(12, 16)) !== 'IHDR') fail('REPORT_PHOTO_FORMAT', 'PNG 图片结构无效');
    return { type: 'png', width: view.getUint32(16), height: view.getUint32(20) };
  }
  if (bytes[0] === 255 && bytes[1] === 216) {
    let offset = 2;
    const sof = new Set([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf]);
    while (offset + 3 < bytes.length) {
      if (bytes[offset++] !== 255) break;
      while (bytes[offset] === 255) offset++;
      const marker = bytes[offset++];
      if (marker === 0xda || marker === 0xd9) break;
      if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) continue;
      const length = bytes[offset] * 256 + bytes[offset + 1];
      if (length < 2 || offset + length > bytes.length) break;
      if (sof.has(marker) && length >= 8) return { type: 'jpg', height: bytes[offset + 3] * 256 + bytes[offset + 4], width: bytes[offset + 5] * 256 + bytes[offset + 6] };
      offset += length;
    }
  }
  fail('REPORT_PHOTO_FORMAT', '报告照片须为有效的 JPEG 或 PNG 文件，请重新上传规范化照片');
}
async function loadPhotos(model, getPhoto) {
  const result = new Map(); let total = 0, pngPixels = 0;
  for (const row of model.rows) for (const entry of row.photos) {
    if (result.has(entry.key)) continue;
    if (typeof getPhoto !== 'function') fail('REPORT_PHOTO_MISSING', '报告引用了照片，但未提供授权的照片读取接口');
    let payload;
    try { payload = await getPhoto(entry.photo); } catch { fail('REPORT_PHOTO_MISSING', `无法读取快照照片 ${entry.key}，请核实存储后重试`); }
    if (payload && typeof payload.arrayBuffer === 'function') {
      if ('ok' in payload && !payload.ok) fail('REPORT_PHOTO_MISSING', `快照照片 ${entry.key} 不可用`);
      const size = Number(payload.headers?.get?.('content-length') || 0);
      if (size > REPORT_LIMITS.photoBytes) fail('REPORT_SIZE_LIMIT', '单张照片超过 6 MiB，请先压缩照片');
      payload = await payload.arrayBuffer();
    }
    const bytes = asBytes(payload?.bytes ?? payload);
    if (!bytes?.length) fail('REPORT_PHOTO_MISSING', `快照照片 ${entry.key} 缺失，已停止生成报告`);
    total += bytes.length;
    if (bytes.length > REPORT_LIMITS.photoBytes || total > REPORT_LIMITS.totalPhotoBytes) fail('REPORT_SIZE_LIMIT', '照片超过单张或整份 6 MiB 限制，请压缩照片或分批导出');
    const info = imageInfo(bytes);
    if (!info.width || !info.height || info.width * info.height > (info.type === 'png' ? REPORT_LIMITS.pngPixels : REPORT_LIMITS.jpegPixels)) fail('REPORT_SIZE_LIMIT', info.type === 'png' ? 'PNG 照片超过 400 万像素，请缩小或转为 JPEG 后导出' : '照片尺寸超过可用范围');
    if (info.type === 'png') pngPixels += info.width * info.height;
    if (pngPixels > REPORT_LIMITS.totalPngPixels) fail('REPORT_SIZE_LIMIT', '整份报告的 PNG 照片超过 400 万像素，请转为 JPEG 后导出');
    if (entry.photo.sha256) {
      const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
      const hash = [...digest].map(v => v.toString(16).padStart(2, '0')).join('');
      if (hash !== entry.photo.sha256.toLowerCase()) fail('REPORT_PHOTO_CHANGED', `快照照片 ${entry.key} 的内容校验不一致`);
    }
    result.set(entry.key, { bytes, ...info });
  }
  return result;
}
function fitted(image, maxWidth, maxHeight) {
  const scale = Math.min(maxWidth / image.width, maxHeight / image.height);
  return { width: image.width * scale, height: image.height * scale };
}
function columnWidths(config) {
  const available = PAGE.width - config.margin_cm * CM * 2;
  const sum = config.columns_cm.reduce((a, b) => a + b, 0);
  return config.columns_cm.map(v => available * v / sum);
}

class PDFLayout {
  constructor(pdf, font, model) {
    this.pdf = pdf; this.font = font; this.model = model;
    this.margin = model.config.margin_cm * CM; this.width = PAGE.width - this.margin * 2;
    this.bottom = this.margin; this.widthCache = new Map(); this.images = new Map();
    this.newPage();
  }
  newPage() {
    if (this.pdf.getPageCount() >= REPORT_LIMITS.pages) fail('REPORT_SIZE_LIMIT', '报告超过 500 页，请分批导出');
    this.page = this.pdf.addPage([PAGE.width, PAGE.height]); this.y = PAGE.height - this.margin;
    const label = `${this.model.config.title}  ${this.model.status}`;
    this.drawLine(label, this.margin, PAGE.height - 13, 8);
  }
  charWidth(char) {
    if (!this.widthCache.has(char)) this.widthCache.set(char, this.font.widthOfTextAtSize(char, 1));
    return this.widthCache.get(char);
  }
  wrap(value, width, size) {
    const output = [];
    for (const paragraph of text(value).replace(/\t/g, '    ').split('\n')) {
      let line = '', used = 0;
      for (const char of paragraph) {
        const advance = this.charWidth(char) * size;
        if (line && used + advance > width + 0.001) { output.push(line); line = ''; used = 0; }
        line += char; used += advance;
      }
      output.push(line);
    }
    return output;
  }
  drawLine(value, x, top, size, alignWidth = 0) {
    if (!value) return;
    const width = this.font.widthOfTextAtSize(value, size);
    this.page.drawText(value, { x: x + (alignWidth ? Math.max(0, (alignWidth - width) / 2) : 0), y: top - size, size, font: this.font, color: BLACK });
  }
  paragraph(value, { size = this.model.config.body_pt, heading = false, center = false, after = 6 } = {}) {
    const lines = this.wrap(value, this.width, size), leading = size * 1.45;
    const before = heading ? 7 : 0;
    if (this.y - before - leading * Math.min(lines.length + (heading ? 2 : 0), 4) < this.bottom) this.newPage();
    this.y -= before;
    for (const line of lines) {
      if (this.y - leading < this.bottom) this.newPage();
      this.drawLine(line, this.margin, this.y, size, center ? this.width : 0); this.y -= leading;
    }
    this.y -= after;
  }
  async image(entry, photos, maxWidth = 14 * CM, maxHeight = 9 * CM) {
    const info = photos.get(entry.key), dims = fitted(info, Math.min(this.width, maxWidth), maxHeight);
    if (this.y - dims.height < this.bottom) this.newPage();
    const image = await this.embedded(entry.key, info);
    this.page.drawImage(image, { x: this.margin, y: this.y - dims.height, ...dims });
    this.y -= dims.height + 8;
  }
  async embedded(key, info) {
    if (!this.images.has(key)) {
      try { this.images.set(key, info.type === 'png' ? await this.pdf.embedPng(info.bytes) : await this.pdf.embedJpg(info.bytes)); }
      catch { fail('REPORT_PHOTO_FORMAT', `照片 ${key} 无法解码，已停止生成报告`); }
    }
    return this.images.get(key);
  }
  textUnits(value, width, size) { return this.wrap(value, width, size).map(line => ({ kind: 'text', text: line, size, height: size * 1.35 })); }
  async table(photos) {
    const widths = columnWidths(this.model.config), padding = 5, size = this.model.config.body_pt;
    const headers = HEADERS.map((v, i) => this.textUnits(v, widths[i] - padding * 2, size));
    const headHeight = Math.max(...headers.map(a => a.reduce((n, u) => n + u.height, 0))) + padding * 2;
    const fullSpace = PAGE.height - this.margin - this.bottom - headHeight;
    const sumHeight = units => units.reduce((total, item) => total + item.height, 0);
    const draw = async (cells, height, header = false) => {
      let x = this.margin;
      for (let ci = 0; ci < widths.length; ci++) {
        this.page.drawRectangle({ x, y: this.y - height, width: widths[ci], height, borderColor: BORDER, borderWidth: 0.5, ...(header ? { color: HEADER_FILL } : {}) });
        let top = this.y - padding;
        for (const unit of cells[ci]) {
          if (unit.kind === 'text') this.drawLine(unit.text, x + padding, top, unit.size, (header || ci === 0) ? widths[ci] - padding * 2 : 0);
          else {
            const img = await this.embedded(unit.entry.key, photos.get(unit.entry.key));
            this.page.drawImage(img, { x: x + (widths[ci] - unit.width) / 2, y: top - unit.imageHeight, width: unit.width, height: unit.imageHeight });
          }
          top -= unit.height;
        }
        x += widths[ci];
      }
      this.y -= height;
    };
    let segmentTop;
    const repeatHeader = async () => { segmentTop = this.y; await draw(headers, headHeight, true); };
    const outline = () => this.page.drawRectangle({ x: this.margin, y: this.y, width: widths.reduce((a, b) => a + b), height: segmentTop - this.y, borderColor: BORDER, borderWidth: 1.5 });
    const nextTablePage = async () => { outline(); this.newPage(); await repeatHeader(); };
    if (this.y - headHeight - 40 < this.bottom) this.newPage();
    await repeatHeader();
    for (const row of this.model.rows) {
      const cells = row.cells.map((v, ci) => ci === 3 ? [] : this.textUnits(v, widths[ci] - padding * 2, size));
      for (const photo of row.photos.slice(0, 2)) {
        const dims = fitted(photos.get(photo.key), widths[3] - padding * 2, 86);
        cells[3].push({ kind: 'image', entry: photo, width: dims.width, imageHeight: dims.height, height: dims.height + 4 }, ...this.textUnits(photo.caption, widths[3] - padding * 2, 9));
      }
      if (!row.photos.length) cells[3].push(...this.textUnits('无照片', widths[3] - padding * 2, size));
      if (row.photos.length > 2) cells[3].push(...this.textUnits(`其余 ${row.photos.length - 2} 张见照片附件。`, widths[3] - padding * 2, 9));
      const totalHeight = Math.max(...cells.map(sumHeight)) + padding * 2;
      if (totalHeight <= fullSpace && this.y - totalHeight < this.bottom) await nextTablePage();
      let continuation = false;
      while (cells.some(c => c.length)) {
        const available = this.y - this.bottom - padding * 2;
        if (available < Math.max(...cells.map(c => c[0]?.height || 0))) { await nextTablePage(); continue; }
        const fragment = cells.map(units => {
          const selected = []; let height = 0;
          while (units.length && height + units[0].height <= available + 0.001) { const unit = units.shift(); selected.push(unit); height += unit.height; }
          return selected;
        });
        if (continuation && !fragment[0].length) fragment[0] = this.textUnits(`${row.cells[0]}\n续`, widths[0] - padding * 2, size);
        const height = Math.max(...fragment.map(sumHeight), size * 1.35) + padding * 2;
        await draw(fragment, height);
        if (cells.some(c => c.length)) { await nextTablePage(); continuation = true; }
      }
    }
    outline(); this.y -= 8;
  }
  footers() {
    const pages = this.pdf.getPages();
    pages.forEach((page, index) => {
      this.page = page;
      this.drawLine(this.model.snapshot.mode === 'draft' ? '草稿 待核 未经审核不得作为确认结论' : '已审核记录', this.margin, 20, 8);
      const right = `记录编号 ${text(this.model.snapshot.id).slice(-12)}  第 ${index + 1} 页 / 共 ${pages.length} 页`;
      const width = this.font.widthOfTextAtSize(right, 8);
      this.drawLine(right, PAGE.width - this.margin - width, 20, 8);
    });
  }
}

async function renderPDF(model, photos, fontBytes) {
  const pdf = await PDFDocument.create(); pdf.registerFontkit(fontkit);
  let font;
  try { font = await pdf.embedFont(fontBytes, { subset: true, features: { kern: false, liga: false } }); }
  catch { fail('REPORT_FONT', '中文字体无法读取，请配置有效的独立 OTF 或 TTF 字体文件'); }
  const supported = new Set(font.getCharacterSet());
  const missing = new Set();
  for (const value of model.strings) for (const char of value) if (!'\n\r\t'.includes(char) && !supported.has(char.codePointAt(0))) missing.add(char.codePointAt(0));
  if (missing.size) fail('REPORT_FONT_GLYPH', `PDF 字体缺少 ${missing.size} 个字符字形（${[...missing].slice(0, 12).map(c => `U+${c.toString(16).toUpperCase()}`).join('、')}）。请更换覆盖这些字符的字体或修正原记录；未生成缺字报告。`);
  pdf.setTitle(model.title); pdf.setSubject(text(model.snapshot.project.name)); pdf.setAuthor('');
  pdf.setCreator('Safety Basis Inspection Workbench'); pdf.setProducer('pdf-lib with embedded CJK font');
  const stamp = new Date(model.snapshot.created_at);
  if (Number.isFinite(stamp.getTime())) { pdf.setCreationDate(stamp); pdf.setModificationDate(stamp); }
  const layout = new PDFLayout(pdf, font, model);
  layout.paragraph(model.title, { size: 19, center: true, after: 10 });
  model.intro.forEach(value => layout.paragraph(value, { after: 5 }));
  await layout.table(photos);
  for (const section of model.sections) {
    layout.newPage(); layout.paragraph(section.heading, { size: 14, heading: true, after: 9 });
    for (const item of section.items) {
      if (item.image) await layout.image(item.image, photos);
      else layout.paragraph(item.text, { size: item.heading ? 12 : item.small ? 9 : model.config.body_pt, heading: !!item.heading });
    }
  }
  layout.footers();
  return pdf.save({ useObjectStreams: true, addDefaultPage: false });
}

function wordParagraph(value, config, { size = config.body_pt, bold = false, center = false, heading, pageBreakBefore = false, after = 80 } = {}) {
  return new Paragraph({
    ...(heading ? { heading } : {}), pageBreakBefore,
    alignment: center ? AlignmentType.CENTER : AlignmentType.LEFT,
    keepNext: !!heading && heading !== HeadingLevel.TITLE,
    spacing: { after, line: Math.round(size * 20 * 1.35), lineRule: LineRuleType.AT_LEAST, before: heading && !pageBreakBefore ? 120 : 0 },
    children: text(value).split('\n').map((line, index) => new TextRun({
      text: line, ...(index ? { break: 1 } : {}), bold, size: size * 2, color: '000000',
      font: { ascii: config.font, hAnsi: config.font, eastAsia: config.font, cs: config.font },
    })),
  });
}
async function renderWord(model, photos) {
  const config = model.config, widths = columnWidths(config);
  // ImageRun's JS SHA1 implementation expands every input byte to a JS number.
  // Hash short immutable photo IDs while assembling OOXML, then insert the
  // original compressed JPEG/PNG bytes into those media parts with fflate.
  // This uses the public Packer API and never changes the actual photo bytes.
  const wordMedia = new Map();
  for (const [key, info] of photos) {
    const seed = new TextEncoder().encode(`safety-basis:${model.snapshot.id}:${key}`);
    const hash = new Uint8Array(await crypto.subtle.digest('SHA-1', seed));
    const filename = [...hash].map(v => v.toString(16).padStart(2, '0')).join('') + `.${info.type}`;
    wordMedia.set(key, { seed, path: `word/media/${filename}` });
  }
  const body = [wordParagraph(model.title, config, { size: 19, bold: true, center: true, heading: HeadingLevel.TITLE, after: 180 })];
  body.push(...model.intro.map(value => wordParagraph(value, config)));
  const border = { style: BorderStyle.SINGLE, size: 4, color: 'D9D9D9' };
  const outerBorder = { ...border, size: 12 };
  const cell = (children, ci, header = false) => new TableCell({
    width: { size: Math.round(widths[ci] * 20), type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 100, bottom: 100, left: 100, right: 100 },
    ...(header ? { shading: { fill: 'E7EDF2' } } : {}), children,
  });
  const imageParagraph = (entry, maxWidth, maxHeight) => {
    const info = photos.get(entry.key), dims = fitted(info, maxWidth, maxHeight);
    return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [new ImageRun({
      type: info.type, data: wordMedia.get(entry.key).seed, transformation: { width: dims.width * 96 / 72, height: dims.height * 96 / 72 },
      altText: { title: entry.caption, description: `检查记录 ${entry.findingNumber} 的照片`, name: entry.key },
    })] });
  };
  const rows = [new TableRow({ tableHeader: true, cantSplit: true, children: HEADERS.map((value, ci) => cell([wordParagraph(value, config, { bold: true, center: true, after: 20 })], ci, true)) })];
  for (const row of model.rows) {
    rows.push(new TableRow({ cantSplit: false, children: row.cells.map((value, ci) => {
      if (ci !== 3) return cell([wordParagraph(value, config, { center: ci === 0, after: 40 })], ci);
      const children = [];
      for (const photo of row.photos.slice(0, 2)) children.push(imageParagraph(photo, widths[3] - 10, 86), wordParagraph(photo.caption, config, { size: 9, center: true, after: 60 }));
      if (!row.photos.length) children.push(wordParagraph('无照片', config));
      if (row.photos.length > 2) children.push(wordParagraph(`其余 ${row.photos.length - 2} 张见照片附件。`, config, { size: 9 }));
      return cell(children, ci);
    }) }));
  }
  body.push(new Table({ rows, layout: TableLayoutType.FIXED, alignment: AlignmentType.CENTER,
    width: { size: Math.round(widths.reduce((a, b) => a + b) * 20), type: WidthType.DXA },
    columnWidths: widths.map(w => Math.round(w * 20)),
    borders: { top: outerBorder, bottom: outerBorder, left: outerBorder, right: outerBorder, insideHorizontal: border, insideVertical: border },
  }));
  for (const section of model.sections) {
    body.push(wordParagraph(section.heading, config, { size: 14, bold: true, heading: HeadingLevel.HEADING_1, pageBreakBefore: true, after: 160 }));
    for (const item of section.items) {
      if (item.image) body.push(imageParagraph(item.image, Math.min(14 * CM, PAGE.width - config.margin_cm * CM * 2), 9 * CM));
      else body.push(wordParagraph(item.text, config, { size: item.heading ? 12 : item.small ? 9 : config.body_pt, bold: !!item.heading, ...(item.heading ? { heading: HeadingLevel.HEADING_2 } : {}) }));
    }
  }
  const footerRuns = [
    new TextRun({ text: `${model.status}    记录编号 ${text(model.snapshot.id).slice(-12)}    第 `, size: 16, font: config.font, color: '000000' }),
    new TextRun({ children: [PageNumber.CURRENT], size: 16, font: config.font }),
    new TextRun({ text: ' 页 / 共 ', size: 16, font: config.font }),
    new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, font: config.font }),
    new TextRun({ text: ' 页', size: 16, font: config.font }),
  ];
  const document = new Document({
    creator: '', lastModifiedBy: '', title: model.title, subject: text(model.snapshot.project.name),
    description: `检查记录 ${text(model.snapshot.id)}；${model.status}`,
    styles: { default: { document: { run: { font: config.font, size: config.body_pt * 2, color: '000000', language: { value: 'zh-CN', eastAsia: 'zh-CN' } }, paragraph: { spacing: { after: 80 } } } } },
    sections: [{
      // docx swaps the supplied portrait dimensions for LANDSCAPE itself.
      properties: { page: { size: { width: Math.round(PAGE.height * 20), height: Math.round(PAGE.width * 20), orientation: PageOrientation.LANDSCAPE }, margin: { top: Math.round(config.margin_cm * CM * 20), bottom: Math.round(config.margin_cm * CM * 20), left: Math.round(config.margin_cm * CM * 20), right: Math.round(config.margin_cm * CM * 20), header: 250, footer: 250 } } },
      headers: { default: new Header({ children: [wordParagraph(`${config.title}  ${model.status}`, config, { size: 8, after: 0 })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: footerRuns })] }) },
      children: body,
    }],
  });
  const files = unzipSync(new Uint8Array(await Packer.toArrayBuffer(document)));
  for (const [key, info] of photos) {
    const path = wordMedia.get(key).path;
    if (!Object.hasOwn(files, path)) fail('REPORT_MEDIA_PACKAGE', 'Word 图片引用生成不一致，已停止导出');
    // JPEG and PNG are already compressed. STORE avoids pointless extra copies.
    files[path] = [info.bytes, { level: 0 }];
  }
  return zipSync(files, { level: 6 });
}

/**
 * @param {object} snapshot Existing schema_version=1 report snapshot (not mutated).
 * @param {{getPhoto?:Function, fontBytes:Uint8Array|ArrayBuffer, config?:object}} options
 * @returns {Promise<{docx:Uint8Array,pdf:Uint8Array,pdf_engine:string,template_version:string}>}
 */
export async function renderReport(snapshot, { getPhoto, fontBytes, config: overrides } = {}) {
  const config = normalizeConfig(overrides), model = makeModel(snapshot, config);
  const font = asBytes(fontBytes);
  if (!font?.length || font.length > REPORT_LIMITS.fontBytes) fail('REPORT_FONT', '请配置有效的中文 TrueType 字体资源（不超过 24 MiB）');
  if (!(font[0] === 0 && font[1] === 1 && font[2] === 0 && font[3] === 0)) fail('REPORT_FONT', '云端 PDF 请使用随包的 report-font.ttf（TrueType 轮廓）；不支持 CFF 或字体集合');
  const photos = await loadPhotos(model, getPhoto);
  // Keep only one layout engine active at a time in the 128 MiB Worker.
  const docx = await renderWord(model, photos);
  const pdf = await renderPDF(model, photos, font);
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(config))));
  const suffix = [...digest].slice(0, 5).map(v => v.toString(16).padStart(2, '0')).join('');
  return { docx, pdf, pdf_engine: 'pdf-lib (embedded CJK, independent table layout)', template_version: `${config.version}-${suffix}` };
}
