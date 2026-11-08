"""Editable Word + PDF from immutable inspection snapshots, no AI-authored law."""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

from .storage import dumps

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / 'templates'
STATUS = {'draft': '草稿', 'needs_facts': '待补事实/证据', 'pending_review': '待审核',
          'confirmed': '已确认', 'rejected': '已驳回'}


def load_config(private_root):
    config = json.loads((TEMPLATE_DIR / 'report-config.json').read_text(encoding='utf-8'))
    override = private_root / 'templates/report-config.json'
    if override.is_file():
        config.update(json.loads(override.read_text(encoding='utf-8')))
    if not 8 <= float(config['body_pt']) <= 18 or not 0.8 <= float(config['margin_cm']) <= 4:
        raise ValueError('模板字号或页边距超出可用范围')
    return config


def set_font(run, name, size=None, bold=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)


def table_borders(table):
    props = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        element = OxmlElement('w:' + edge)
        element.set(qn('w:val'), 'single')
        element.set(qn('w:sz'), '12' if edge in ('top', 'left', 'bottom', 'right') else '4')
        element.set(qn('w:color'), '666666')
        borders.append(element)
    props.append(borders)
    margins = OxmlElement('w:tblCellMar')
    for edge in ('top', 'left', 'bottom', 'right'):
        element = OxmlElement('w:' + edge)
        element.set(qn('w:w'), '90')
        element.set(qn('w:type'), 'dxa')
        margins.append(element)
    props.append(margins)


def set_repeat_header(row):
    trpr = row._tr.get_or_add_trPr()
    trpr.append(OxmlElement('w:tblHeader'))


def add_body(doc, text, config, bold=False, size=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.15
    set_font(p.add_run(text), config['font'], size or config['body_pt'], bold)
    return p


def heading(doc, text, config, level=1):
    p = add_body(doc, text, config, bold=True, size=14 if level == 1 else 11)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.keep_with_next = True
    return p


def citation(basis):
    number = basis['document_number']
    name = basis['law_name']
    if number and name.endswith(' ' + number):
        name = name[:-(len(number) + 1)]
    return f'《{name}》' + (f'（{number}）' if number else '') + basis['article']


def all_bases(snapshot):
    result, positions = [], {}
    for finding in snapshot['findings']:
        for basis in finding['bases']:
            key = (basis['link_id'], basis['text'], basis['applicability'], basis['as_of'])
            if key not in positions:
                positions[key] = len(result) + 1
                result.append(basis)
    return result, positions


def basis_numbers(finding, positions):
    return list(dict.fromkeys(positions[(b['link_id'], b['text'], b['applicability'], b['as_of'])] for b in finding['bases']))


def fill_template(doc, fields):
    paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)
    for section in doc.sections:
        paragraphs.extend(section.header.paragraphs)
        paragraphs.extend(section.footer.paragraphs)
    for paragraph in paragraphs:
        old = paragraph.text
        text = old
        for key, value in fields.items():
            text = text.replace('{{' + key + '}}', str(value))
        if text != old:
            # Preserve paragraph styling and the first run's style.
            if paragraph.runs:
                paragraph.runs[0].text = text
                for run in paragraph.runs[1:]:
                    run.text = ''
            else:
                paragraph.add_run(text)


def write_word(snapshot, private_root, out, config):
    base_template = private_root / 'templates/inspection.docx'
    custom = base_template.is_file()
    doc = Document(base_template) if custom else Document()
    project = snapshot['project']
    title = config['title'] + ('（草稿·待核）' if snapshot['mode'] == 'draft' else '')
    fields = {**project, 'company': project['company'], 'project': project['name'], 'title': title,
              'report_id': snapshot['id'], 'created_at': snapshot['created_at'],
              'report_mode': '草稿·待核' if snapshot['mode'] == 'draft' else '已审核记录'}
    if not custom:
        section = doc.sections[0]
        width, height = (21.0, 29.7) if config['page_size'] == 'A4' else (21.59, 27.94)
        if config['orientation'] == 'landscape':
            width, height = height, width
            section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = Cm(width), Cm(height)
        section.left_margin = section.right_margin = Cm(config['margin_cm'])
        section.top_margin = section.bottom_margin = Cm(config['margin_cm'])
        section.header_distance = section.footer_distance = Cm(0.7)
        style = doc.styles['Normal']
        style.font.name = config['font']
        style.font.size = Pt(config['body_pt'])
        style.element.rPr.rFonts.set(qn('w:eastAsia'), config['font'])
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.line_spacing = 1.15
        p = add_body(doc, title, config, bold=True, size=19)
        p.alignment = 1
        add_body(doc, f'受检单位：{project["company"]}    检查项目：{project["name"]}', config)
        add_body(doc, f'检查日期：{project["inspection_date"]}    检查人：{project["inspectors"]}    检查用途：{project["purpose"]}', config)
        add_body(doc, f'导出记录 {len(snapshot["findings"])} 条；未纳入本报告 {snapshot["excluded_count"]} 条。', config)
        if snapshot['mode'] == 'draft':
            add_body(doc, '草稿用于核查与审核；其中待核、待审核和驳回记录均不得作为已确认隐患结论。', config, bold=True)
    else:
        fill_template(doc, fields)
        # Make report status explicit even when a user-supplied template omits the placeholder.
        add_body(doc, f'报告状态：{fields["report_mode"]}；记录 {len(snapshot["findings"])} 条。', config, bold=True)
    bases, positions = all_bases(snapshot)
    table = doc.add_table(rows=1, cols=6)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    section = doc.sections[0]
    available = (section.page_width - section.left_margin - section.right_margin) / 360000
    ratios = config['columns_cm']
    widths = [available * value / sum(ratios) for value in ratios]
    for column, width in zip(table.columns, widths):
        column.width = Cm(width)
    headers = ['序号', '位置 / 设备', '隐患', '隐患照片', '整改建议', '依据 / 状态']
    for index, cell in enumerate(table.rows[0].cells):
        cell.width = Cm(widths[index])
        cell.text = headers[index]
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), 'E7EDF2')
        cell._tc.get_or_add_tcPr().append(shading)
    set_repeat_header(table.rows[0])
    for index, finding in enumerate(snapshot['findings'], 1):
        row = table.add_row()
        for ci, cell in enumerate(row.cells):
            cell.width = Cm(widths[ci])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        row.cells[0].text = str(index)
        row.cells[1].text = '\n'.join(filter(None, [finding['location'], finding['equipment']]))
        row.cells[2].text = finding['description'] or '待填写专业描述'
        if finding['finding_kind'] == 'document_review':
            row.cells[2].add_paragraph('核查类型：资料核查')
        photo_cell = row.cells[3]
        photos = finding['photos']
        photo_cell.text = '' if photos else '无照片'
        for photo_index, photo in enumerate(photos[:2]):
            image_path = private_root / photo['path']
            p = photo_cell.paragraphs[0] if photo_index == 0 else photo_cell.add_paragraph()
            p.alignment = 1
            if image_path.is_file():
                p.add_run().add_picture(str(image_path), width=Cm(max(1, widths[3] - 0.4)))
                photo_cell.add_paragraph(photo['caption'] or f'照片 {photo_index + 1}')
            else:
                raise FileNotFoundError('快照引用的照片缺失：' + photo['id'])
        if len(photos) > 2:
            photo_cell.add_paragraph(f'其余 {len(photos)-2} 张见照片附件。')
        row.cells[4].text = finding['rectification'] or '待核定整改方向'
        if finding['due_date'] or finding['assignee']:
            row.cells[4].add_paragraph(f'责任人：{finding["assignee"] or "待定"}\n期限：{finding["due_date"] or "待定"}')
        refs = basis_numbers(finding, positions)
        refs_text = '\n'.join(f'[{n}] {citation(bases[n-1])}' for n in refs) or '法源待核'
        row.cells[5].text = f'{refs_text}\n状态：{STATUS[finding["status"]]}'
        reviews = [r for r in finding['reviews'] if r['decision'] in ('confirm', 'reject')]
        if reviews:
            r = reviews[-1]
            row.cells[5].add_paragraph(f'审核人：{r["reviewer"]}\n意见：{r["comment"]}')
    table_borders(table)
    for ri, row in enumerate(table.rows):
        for ci, cell in enumerate(row.cells):
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.line_spacing = 1.1
                if ri == 0 or ci == 0:
                    p.alignment = 1
                for run in p.runs:
                    set_font(run, config['font'], config['body_pt'], bold=ri == 0)
    if custom:
        marker = next((p for p in doc.paragraphs if '{{findings_table}}' in p.text), None)
        if marker is not None:
            marker._p.addnext(table._tbl)
            marker._p.getparent().remove(marker._p)
    doc.add_page_break()
    heading(doc, '附件一  法规依据与适用条件', config)
    add_body(doc, '以下为选定引用的完整条文快照。引用序号对应检查记录，适用条件和逐项现场核实记录分别保留。', config)
    for index, basis in enumerate(bases, 1):
        heading(doc, f'[{index}] {citation(basis)}', config, level=2)
        add_body(doc, basis['text'], config)
        add_body(doc, '本次关联的适用条件：' + basis['applicability'], config)
        add_body(doc, '隐患适用范围：' + basis['hazard_conditions'], config)
        add_body(doc, '官方来源：' + (basis['source_url'] or '见知识库已核证据链'), config, size=9)
        add_body(doc, f'H：{basis["hazard_id"]}；K：{basis["link_id"]}；C：{basis["clause_id"]}；LV：{basis["law_version_id"]}', config, size=9)
        add_body(doc, f'施行日期：{basis.get("effective_date", "待核")}；依据快照日期：{basis["as_of"]}；知识包版本：{basis["data_version"]}；查询时间：{basis["queried_at"]}', config, size=9)
    if config.get('append_facts', True):
        doc.add_page_break()
        heading(doc, '附件二  现场事实与审核记录', config)
        for index, finding in enumerate(snapshot['findings'], 1):
            heading(doc, f'记录 {index} · {finding["location"]} · {STATUS[finding["status"]]}', config, level=2)
            add_body(doc, '现场原话：' + finding['observation'], config)
            for fact in finding['facts']:
                state = {'confirmed': '已确认', 'denied': '已否定', 'unknown': '待核'}[fact['status']]
                add_body(doc, f'[{state}] {fact["label"]}\n核实记录：{fact["note"] or "待补充"}', config)
            if finding.get('notes'):
                add_body(doc, '备注：' + finding['notes'], config)
            for review in finding['reviews']:
                add_body(doc, f'{review["created_at"]} · {review["reviewer"]} · {review["decision"]} · {review["comment"]}', config, size=9)
    extras = [(i, photo) for i, f in enumerate(snapshot['findings'], 1) for photo in f['photos'][2:]]
    if extras:
        heading(doc, '附件三  补充照片', config)
        for index, photo in extras:
            add_body(doc, f'记录 {index} · {photo["caption"] or photo["filename"]}', config)
            doc.add_picture(str(private_root / photo['path']), width=Cm(min(14, available)))
    for section in doc.sections:
        p = section.footer.add_paragraph() if custom else section.footer.paragraphs[0]
        p.alignment = 2
        set_font(p.add_run('记录编号 ' + snapshot['id'][-12:] + '  第 '), config['font'], 8)
        field = OxmlElement('w:fldSimple')
        field.set(qn('w:instr'), 'PAGE')
        p._p.append(field)
        set_font(p.add_run(' 页'), config['font'], 8)
    doc.core_properties.author = ''
    doc.core_properties.last_modified_by = ''
    doc.core_properties.title = title
    doc.core_properties.subject = project['name']
    target = out / 'inspection.docx'
    doc.save(target)
    return target


def fallback_pdf(snapshot, private_root, target, config):
    """Explicit, complete PDF alternative when a Word converter is unavailable."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as PDFImage, PageBreak
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    body = ParagraphStyle('body', fontName='STSong-Light', fontSize=10.5, leading=16, spaceAfter=6, wordWrap='CJK')
    title_style = ParagraphStyle('title', parent=body, fontSize=18, leading=24, alignment=TA_CENTER, spaceAfter=14)
    sub = ParagraphStyle('sub', parent=body, fontSize=13, leading=19, spaceBefore=12)
    story = []
    def paragraph(text, style=body):
        story.append(Paragraph(escape(str(text)).replace('\n', '<br/>'), style))
    title = config['title'] + ('（草稿·待核）' if snapshot['mode'] == 'draft' else '')
    paragraph(title, title_style)
    p = snapshot['project']
    paragraph(f'受检单位：{p["company"]}；项目：{p["name"]}；检查日期：{p["inspection_date"]}；检查人：{p["inspectors"]}')
    paragraph('PDF采用直接排版引擎，内容与Word共用同一快照，分页可能不同。')
    bases, positions = all_bases(snapshot)
    for index, finding in enumerate(snapshot['findings'], 1):
        paragraph(f'{index}. {finding["location"]} · {STATUS[finding["status"]]}', sub)
        paragraph('隐患：' + (finding['description'] or '待核'))
        paragraph('隐患照片：')
        for photo in finding['photos']:
            path = private_root / photo['path']
            with Image.open(path) as im:
                width = min(12 * cm, im.width)
                height = min(8 * cm, width * im.height / im.width)
                width = height * im.width / im.height
            story.append(PDFImage(str(path), width=width, height=height))
            paragraph(photo['caption'] or photo['filename'])
        paragraph('整改建议：' + finding['rectification'])
        paragraph('依据：' + '、'.join(f'[{n}] {citation(bases[n-1])}' for n in basis_numbers(finding, positions)))
        paragraph('现场原话：' + finding['observation'])
        for fact in finding['facts']:
            paragraph(f'[{ {"confirmed":"已确认","unknown":"待核","denied":"已否定"}[fact["status"]] }] {fact["label"]}：{fact["note"] or "待补充"}')
        for review in finding['reviews']:
            paragraph(f'审核记录：{review["created_at"]} · {review["reviewer"]} · {review["decision"]} · {review["comment"]}')
    story.append(PageBreak())
    paragraph('附件  法规依据与适用条件', sub)
    for index, basis in enumerate(bases, 1):
        paragraph(f'[{index}] {citation(basis)}', sub)
        paragraph(basis['text'])
        paragraph('关联适用条件：' + basis['applicability'])
        paragraph('隐患适用范围：' + basis['hazard_conditions'])
        paragraph('官方来源：' + basis['source_url'])
        paragraph(f'{basis["hazard_id"]} / {basis["link_id"]} / {basis["clause_id"]} / {basis["law_version_id"]}')
        paragraph(f'施行日期：{basis.get("effective_date", "待核")}；快照日期：{basis["as_of"]}；知识包：{basis["data_version"]}；查询时间：{basis["queried_at"]}')
    def footer(canvas, doc):
        canvas.setFont('STSong-Light', 8)
        canvas.drawRightString(doc.pagesize[0]-1.5*cm, .8*cm, f'{snapshot["id"][-12:]} / {doc.page}')
    document = SimpleDocTemplate(str(target), pagesize=landscape(A4),
                                 leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def generate_reports(snapshot, private_root, out):
    config = load_config(private_root)
    template = private_root / 'templates/inspection.docx'
    version = config['version'] + '-' + hashlib.sha256(dumps(config).encode()).hexdigest()[:10]
    if template.is_file():
        version += '-' + hashlib.sha256(template.read_bytes()).hexdigest()[:12]
    docx = write_word(snapshot, private_root, out, config)
    pdf = out / 'inspection.pdf'
    converter = os.environ.get('WORKBENCH_SOFFICE') or shutil.which('soffice') or shutil.which('libreoffice')
    engine = 'reportlab (independent layout)'
    converter_error = None
    if converter and os.environ.get('WORKBENCH_PDF_ENGINE') != 'reportlab':
        try:
            with tempfile.TemporaryDirectory(prefix='inspection-office-') as profile:
                process = subprocess.run([
                    converter, '-env:UserInstallation=' + Path(profile).as_uri(),
                    '--headless', '--convert-to', 'pdf', '--outdir', str(out), str(docx),
                ], capture_output=True, text=True, timeout=55)
            if process.returncode == 0 and pdf.exists() and pdf.stat().st_size > 0:
                engine = 'LibreOffice (Word conversion)'
            else:
                converter_error = 'Word converter returned no PDF'
        except (OSError, subprocess.TimeoutExpired):
            converter_error = 'Word converter unavailable or timed out'
    if engine.startswith('reportlab'):
        fallback_pdf(snapshot, private_root, pdf, config)
    return {'docx': docx, 'pdf': pdf, 'pdf_engine': engine, 'template_version': version,
            'converter_notice': converter_error}


def create_template(path):
    doc = Document()
    config = json.loads((TEMPLATE_DIR / 'report-config.json').read_text(encoding='utf-8'))
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = Cm(29.7), Cm(21)
    section.left_margin = section.right_margin = Cm(config['margin_cm'])
    section.top_margin = section.bottom_margin = Cm(config['margin_cm'])
    add_body(doc, '{{title}}', config, bold=True, size=19)
    add_body(doc, '受检单位：{{company}}    检查项目：{{project}}', config)
    add_body(doc, '检查日期：{{inspection_date}}    检查人：{{inspectors}}', config)
    add_body(doc, '报告状态：{{report_mode}}', config)
    doc.add_paragraph('{{findings_table}}')
    doc.core_properties.author = ''
    doc.core_properties.last_modified_by = ''
    doc.save(path)
