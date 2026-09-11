# -*- coding: utf-8 -*-
"""扫描件 OCR 适配器：把无文字层的 PDF 转成可检索文本。

项目全文库（tools/pipeline/fulltext.py）对纯文本按行切段，因此本工具输出
UTF-8 文本文件，可直接写进 safety-fulltext-manifest-v1 清单后导入。

依赖：PyMuPDF（渲染）+ 外部 tesseract 引擎（默认 chi_sim 中文简体）。

用法：
    python tools/v4/ocr_pdf.py --src scan.pdf --out text.txt
    python tools/v4/ocr_pdf.py --src scan.pdf --out text.txt --pages 1-20 --dpi 400

说明：
- 每页之间以空行分隔，便于按页定位；不会插入页码标记以免污染检索。
- OCR 结果必然带有误字（法规文本尤其影响数字与条款号），因此 OCR 文本只用于
  检索定位与线索；要写进 clause.quote 的条文仍须与第二来源或原件核对。
"""
import argparse
import os
import subprocess
import sys
import tempfile

import fitz  # PyMuPDF


def find_tesseract():
    for cand in (os.environ.get("TESSERACT_CMD"),
                 r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                 "/usr/bin/tesseract", "/usr/local/bin/tesseract"):
        if cand and os.path.exists(cand):
            return cand
    from shutil import which
    return which("tesseract")


def parse_pages(spec, total):
    if not spec:
        return 0, total
    if "-" in spec:
        a, b = spec.split("-", 1)
        lo = max(1, int(a)) if a else 1
        hi = min(total, int(b)) if b else total
    else:
        lo = hi = int(spec)
    return lo - 1, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", help="页码范围，如 1-20；默认全部")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--lang", default="chi_sim")
    ap.add_argument("--psm", default="6", help="tesseract 页面分割模式，默认 6（单一文本块）")
    args = ap.parse_args()

    exe = find_tesseract()
    if not exe:
        print("未找到 tesseract，可设环境变量 TESSERACT_CMD 指向可执行文件", file=sys.stderr)
        return 2
    if not os.path.isfile(args.src):
        print("原件不存在: %s" % args.src, file=sys.stderr)
        return 2

    doc = fitz.open(args.src)
    lo, hi = parse_pages(args.pages, len(doc))
    print("OCR: %s 第 %d-%d 页 / 共 %d 页, dpi=%d, lang=%s" % (args.src, lo + 1, hi, len(doc), args.dpi, args.lang))

    chunks = []
    tmpdir = tempfile.mkdtemp(prefix="ocrpdf_")
    for idx in range(lo, hi):
        page = doc[idx]
        pix = page.get_pixmap(dpi=args.dpi)
        png = os.path.join(tmpdir, "p%05d.png" % idx)
        pix.save(png)
        base = os.path.join(tmpdir, "p%05d" % idx)
        subprocess.run([exe, png, base, "-l", args.lang, "--psm", args.psm],
                       capture_output=True)
        txt_path = base + ".txt"
        page_text = ""
        if os.path.exists(txt_path):
            page_text = open(txt_path, encoding="utf-8", errors="replace").read()
        norm = "\n".join(line.strip() for line in page_text.splitlines() if line.strip())
        chunks.append(norm)
        if (idx - lo + 1) % 10 == 0 or idx == hi - 1:
            print("  已处理 %d/%d 页" % (idx - lo + 1, hi - lo))
        os.remove(png)
        if os.path.exists(txt_path):
            os.remove(txt_path)

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n\n".join(chunks) + "\n")
    nonempty = sum(1 for c in chunks if c)
    print("完成：%s（%d/%d 页有文本，%.1f KB）" % (args.out, nonempty, len(chunks), os.path.getsize(args.out) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
