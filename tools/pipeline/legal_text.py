"""Extract an immutable article directory once per official document snapshot.

This is a text adapter, not a claim that a law is current or a rule applies.
Article text is stored once; numbered subitems are offsets into the article.
"""
from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
import re
from zipfile import ZipFile
from xml.etree import ElementTree

import exchange
import review

NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NUM = "零〇一二三四五六七八九十百千万两"
ARTICLE = re.compile(r"^\s*(第[" + NUM + r"\d]+条(?:之[" + NUM + r"\d]+)?)(?=\s|　|[：:]|[^\d" + NUM + r"]|$)")
CHAPTER = re.compile(r"^\s*第[" + NUM + r"\d]+[编章节]\s*")
SUBITEM = re.compile(r"[（(]([" + NUM + r"\d]+)[）)]")


def paragraphs(blob):
    if blob.startswith(b"PK"):
        with ZipFile(BytesIO(blob)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise ValueError("ZIP evidence is not a DOCX")
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        return ["".join(node.text or "" for node in p.iter(NS + "t")).strip()
                for p in root.iter(NS + "p")]
    return review.snapshot_text(blob).splitlines()


def chinese_number(value):
    if value.isdigit():
        return int(value)
    digits = dict(zip("零〇一二三四五六七八九两", (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2)))
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    result = current = 0
    for char in value:
        if char in digits:
            current = digits[char]
        elif char in units:
            result += (current or 1) * units[char]
            current = 0
        else:
            raise ValueError("Unrecognized article number")
    return result + current


def directory(blob):
    rows = paragraphs(blob)
    articles, current, heading, preamble = [], None, "", []
    for ordinal, text in enumerate(rows):
        if not text:
            continue
        match = ARTICLE.match(text)
        if match:
            if current:
                articles.append(current)
            current = {"articlePath": match[1], "heading": heading,
                       "paragraphStart": ordinal, "paragraphEnd": ordinal, "paragraphs": [text]}
        elif CHAPTER.match(text):
            if current:
                articles.append(current)
                current = None
            heading = text
        elif current:
            current["paragraphs"].append(text)
            current["paragraphEnd"] = ordinal
        else:
            preamble.append(text)
    if current:
        articles.append(current)
    seen, issues, numbers = set(), [], []
    for article in articles:
        locator = article["articlePath"]
        if locator in seen:
            issues.append("Duplicate article locator: " + locator)
        seen.add(locator)
        if "之" not in locator:
            numbers.append(chinese_number(locator[1:-1]))
        text = "\n".join(article.pop("paragraphs"))
        article["quote"] = text
        article["textSha256"] = exchange.sha256_bytes(text.encode("utf-8"))
        # The same article is not copied into each child. A subitem's exact span
        # remains available for a reviewer to validate its level and boundaries.
        matches = list(SUBITEM.finditer(text))
        article["subitemCandidates"] = [
            {"label": m[0], "textStart": m.start(),
             "textEnd": matches[i + 1].start() if i + 1 < len(matches) else len(text)}
            for i, m in enumerate(matches)]
    if numbers and numbers != list(range(1, max(numbers) + 1)):
        issues.append("Article sequence is not complete and strictly increasing from 1")
    if not articles:
        issues.append("No Chinese statutory article headings found; retain original and use a standard/table adapter")
    return {"formatVersion": "safety-article-directory-v1",
            "snapshotSha256": exchange.sha256_bytes(blob), "paragraphCount": len(rows),
            "articleCount": len(articles), "extractionIssues": issues,
            "legalVerification": "待核验", "preamble": "\n".join(preamble), "articles": articles}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = directory(args.snapshot.read_bytes())
    review.write_json(args.output, data)
    print({k: data[k] for k in ("articleCount", "paragraphCount", "extractionIssues", "legalVerification")})


if __name__ == "__main__":
    main()
