"""Rebuild the redistributable report font; no private input is required.

Use fonttools >= 4.60 and the OFL Noto Sans CJK collection supplied by
fonts-noto-cjk. The font is an asset, never bundled into the Worker script.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen


def supplement(font, source, wanted):
    """Copy supported fallback outlines without changing any Unicode values."""
    fallback_cmap = source.getBestCmap()
    missing = sorted((wanted - set(font.getBestCmap())) & set(fallback_cmap))
    top = font['CFF '].cff.topDictIndex[0]
    private = top.FDArray[0].Private
    source_set = source.getGlyphSet()
    scale = font['head'].unitsPerEm / source['head'].unitsPerEm
    # TTFont and CFF may share the same list; mutate independent order/charset.
    order = list(font.getGlyphOrder())
    top.charset = list(top.charset)
    metrics = font['hmtx'].metrics
    used = {int(name[3:]) for name in order if name.startswith('cid')}
    next_cid = 1
    for code in missing:
        while next_cid in used:
            next_cid += 1
        name = f'cid{next_cid:05d}'
        used.add(next_cid)
        glyph_name = fallback_cmap[code]
        glyph = source_set[glyph_name]
        advance = round(glyph.width * scale)
        pen = T2CharStringPen(advance, source_set)
        glyph.draw(TransformPen(pen, (scale, 0, 0, scale, 0, 0)))
        charstring = pen.getCharString(private=private, globalSubrs=font['CFF '].cff.GlobalSubrs)
        top.CharStrings.charStrings[name] = len(top.CharStrings.charStringsIndex)
        top.CharStrings.charStringsIndex.append(charstring)
        top.charset.append(name)
        top.FDSelect.gidArray.append(0)
        order.append(name)
        metrics[name] = (advance, round(source['hmtx'].metrics[glyph_name][1] * scale))
        for table in font['cmap'].tables:
            if table.isUnicode() and (code <= 0xFFFF or table.format in (12, 13)):
                table.cmap[code] = name
    font.setGlyphOrder(order)
    font['maxp'].numGlyphs = len(order)
    return missing


def true_type(font):
    """Convert offline to quadratic outlines for reliable fontkit subsetting.

    @pdf-lib/fontkit 1.1.1 writes an invalid offSize in its CFF subset header.
    TrueType avoids that path and leaves the Worker/dependencies unpatched.
    """
    # Report text is horizontal; the added glyphs need no vertical metrics.
    for tag in ('vmtx', 'vhea', 'VORG'):
        if tag in font:
            del font[tag]
    builder = FontBuilder(font['head'].unitsPerEm, isTTF=True)
    order = font.getGlyphOrder()
    builder.setupGlyphOrder(order)
    glyph_set = font.getGlyphSet()
    outlines = {}
    for name in order:
        pen = TTGlyphPen(None)
        glyph_set[name].draw(Cu2QuPen(pen, max_err=0.75, reverse_direction=True))
        outlines[name] = pen.glyph()
    builder.setupGlyf(outlines)
    # fontkit selects short loca for small PDF subsets. Its selector assumes
    # even offsets; four-byte padding prevents truncation of odd glyf offsets.
    builder.font['glyf'].padding = 4
    builder.setupHorizontalMetrics(dict(font['hmtx'].metrics))
    builder.setupHorizontalHeader(ascent=font['hhea'].ascent, descent=font['hhea'].descent, lineGap=font['hhea'].lineGap)
    builder.setupCharacterMap(dict(font.getBestCmap()))
    builder.font['name'] = font['name']
    os2 = font['OS/2']
    builder.setupOS2(sTypoAscender=os2.sTypoAscender, sTypoDescender=os2.sTypoDescender,
                     sTypoLineGap=os2.sTypoLineGap, usWinAscent=os2.usWinAscent,
                     usWinDescent=os2.usWinDescent, usWeightClass=400, fsType=0)
    builder.setupPost(keepGlyphNames=False)
    builder.setupMaxp()
    builder.font['head'].created = font['head'].created
    builder.font['head'].modified = font['head'].modified
    builder.font.recalcTimestamp = False
    return builder.font


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'))
    parser.add_argument('--font-number', type=int, default=2, help='Noto Sans CJK SC in the Debian collection')
    parser.add_argument('--cjk-fallback', type=Path, default=Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'))
    parser.add_argument('--latin-fallback', type=Path, default=Path('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'))
    parser.add_argument('--license-file', type=Path, default=Path('/usr/share/doc/fonts-noto-cjk/copyright'))
    parser.add_argument('--knowledge', type=Path, default=Path('knowledge'))
    parser.add_argument('--output', type=Path, default=Path('workbench/cloud/assets'))
    args = parser.parse_args()
    font = TTFont(args.source, fontNumber=args.font_number, recalcTimestamp=False)
    original_name = font['name'].getDebugName(1)
    # Basic CJK, Extension A, compatibility characters, full-width punctuation,
    # Latin/Greek/Cyrillic, common symbols, and all actual governed source text.
    wanted = set(range(0x20, 0x3000))
    for start, end in ((0x3000, 0xA000), (0xF900, 0xFB00), (0xFE00, 0x10000)):
        wanted.update(range(start, end))
    knowledge_chars = set()
    source_files = []
    for path in sorted(args.knowledge.rglob('*.json')):
        raw = path.read_bytes()
        # Decode JSON so escaped characters are included, too.
        data = json.dumps(json.loads(raw), ensure_ascii=False)
        knowledge_chars.update(map(ord, data))
        source_files.append((path.relative_to(args.knowledge).as_posix(), hashlib.sha256(raw).hexdigest()))
    wanted.update(knowledge_chars)
    cmap = font.getBestCmap()
    available = set(cmap)
    options = subset.Options()
    options.layout_features = []
    options.hinting = False
    options.desubroutinize = True
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14, 16, 17]
    options.name_legacy = True
    options.name_languages = ['*']
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=wanted & available)
    subsetter.subset(font)
    # Serialize the subset before inserting fallback glyphs: fontTools retains
    # original CID reverse mappings in a freshly subset in-memory collection.
    intermediate = io.BytesIO()
    font.save(intermediate, reorderTables=True)
    intermediate.seek(0)
    font = TTFont(intermediate, recalcTimestamp=False)
    copyrights = [font['name'].getDebugName(0)]
    supplements = []
    required = knowledge_chars | set(range(0x4E00, 0xA000))
    for path, number in ((args.cjk_fallback, 2), (args.latin_fallback, -1)):
        fallback = TTFont(path, fontNumber=number)
        copied = supplement(font, fallback, required)
        if copied:
            copyrights.append(fallback['name'].getDebugName(0))
            supplements.append({'family': fallback['name'].getDebugName(1), 'codepoints': [f'U+{c:04X}' for c in copied]})
    available = set(font.getBestCmap())
    # Distinguish this modified/subset font from the upstream font family.
    for record in font['name'].names:
        replacements = {1: 'Safety Basis Sans', 2: 'Regular', 3: 'SafetyBasisSans-Regular-1',
                        4: 'Safety Basis Sans Regular', 6: 'SafetyBasisSans-Regular',
                        16: 'Safety Basis Sans', 17: 'Regular'}
        if record.nameID in replacements:
            record.string = replacements[record.nameID].encode(record.getEncoding())
    if 'CFF ' in font:
        font['CFF '].cff.fontNames = ['SafetyBasisSans-Regular']
        top = font['CFF '].cff.topDictIndex[0]
        top.FamilyName = 'Safety Basis Sans'
        top.FullName = 'Safety Basis Sans Regular'
    args.output.mkdir(parents=True, exist_ok=True)
    font = true_type(font)
    target = args.output / 'report-font.ttf'
    font.save(target, reorderTables=True)
    metadata = {
        'family': 'Safety Basis Sans', 'upstream_family': original_name,
        'upstream': 'https://github.com/notofonts/noto-cjk', 'license': 'SIL Open Font License 1.1',
        'font_file': target.name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        'bytes': target.stat().st_size, 'glyphs': len(font.getGlyphOrder()),
        'codepoints': len(font.getBestCmap()),
        'supplemented_outlines': supplements,
        'coverage': 'Source-supported Basic CJK, Extension A, CJK compatibility, punctuation, Latin, symbols and governed knowledge characters',
        'basic_cjk_missing': [f'U+{c:04X}' for c in range(0x4E00, 0xA000) if c not in available],
        'knowledge_missing': [f'U+{c:04X}' for c in sorted(knowledge_chars - available) if not chr(c).isspace()],
        'knowledge_files_sha256': hashlib.sha256(json.dumps(source_files, ensure_ascii=False).encode()).hexdigest(),
        'knowledge_file_count': len(source_files),
        'rebuild': 'python workbench/cloud/tools/build_report_font.py',
        'unsupported_policy': 'renderReport rejects missing glyphs before writing either output; no silent substitution',
    }
    (args.output / 'report-font.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    license_source = args.license_file.read_text()
    if 'License: SIL-1.1\n ' in license_source:
        license_source = license_source.split('License: SIL-1.1\n ', 1)[1].split('\nLicense:', 1)[0]
        license_source = '\n'.join('' if line.strip() == '.' else line.removeprefix(' ') for line in license_source.splitlines())
    if 'SIL OPEN FONT LICENSE Version 1.1' not in license_source:
        raise ValueError('Provide the complete SIL OFL 1.1 license')
    (args.output / 'OFL.txt').write_text('\n'.join(dict.fromkeys(filter(None, copyrights))) + '\n\n' + license_source.strip() + '\n')
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == '__main__':
    main()
