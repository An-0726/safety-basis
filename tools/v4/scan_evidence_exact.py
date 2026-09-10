# -*- coding: utf-8 -*-
"""精确扫描 review evidence 错配：clause 所属法规 vs evidence URL 归属映射。

只对 EXPECT 中已经配置了官方来源域名的法规执行“精确错配”判定；
未配置映射的法规记为 UNMAPPED，不得误报为 MISMATCHED。
真实 MISMATCHED > 0 时退出码为 1，供 V4 Gate/CI 作为 Evidence 阻断信号。
"""
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")


def main():
    laws = {}
    for f in glob.glob(os.path.join(KNOW, "laws", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        laws[d["id"]] = d
    lvs = {}
    for f in glob.glob(os.path.join(KNOW, "law-versions", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        lvs[d["id"]] = d
    clauses = {}
    for f in glob.glob(os.path.join(KNOW, "clauses", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        clauses[d["id"]] = d
    links = {}
    for f in glob.glob(os.path.join(KNOW, "links", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        links[d["id"]] = d
    evidence = {}
    for f in glob.glob(os.path.join(KNOW, "evidence", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        evidence[d["id"]] = d

    # 法规/标准 -> 期望的 evidence 官方来源域名（精确 host / 子域名判定）。
    # 这是一个逐步扩展的 allowlist，不是“未列入即错误”的 denylist。
    EXPECT = [
        ("中华人民共和国消防法", ("flk.npc.gov.cn", "www.npc.gov.cn", "www.gov.cn")),
        ("中华人民共和国安全生产法", ("flk.npc.gov.cn", "www.mem.gov.cn", "www.gov.cn", "npc.gov.cn")),
        ("危险废物贮存污染控制标准", ("mee.gov.cn",)),
        ("中华人民共和国特种设备安全法", ("samr.gov.cn", "flk.npc.gov.cn", "www.gov.cn")),
        ("易制毒化学品管理条例", ("mofcom.gov.cn", "www.gov.cn", "flk.npc.gov.cn", "npc.gov.cn")),
    ]

    def host_of(url):
        return url.split("//")[-1].split("/")[0].split(":")[0].lower().strip(".")

    def expected_domains(law_name):
        for name, doms in EXPECT:
            if name in law_name:
                return doms
        return None

    def host_allowed(host, domains):
        return any(host == d or host.endswith("." + d) for d in domains)

    mism = []
    unmapped = []
    checked = 0
    evidence_ref_count = 0
    for kid, r in sorted(links.items()):
        rf = os.path.join(KNOW, "reviews", "links", kid + ".json")
        if not os.path.exists(rf):
            continue
        with io.open(rf, encoding="utf-8") as fh:
            rev = json.load(fh)
        cid = r.get("clauseId")
        c = clauses.get(cid) or {}
        lv = lvs.get(c.get("lawVersionId")) or {}
        law_name = lv.get("officialName", "")
        doms = expected_domains(law_name) if law_name else None
        for e in (rev.get("evidenceRefs") or []):
            ev = evidence.get(e) or {}
            url = str(ev.get("url", ""))
            if not law_name or not url:
                continue
            evidence_ref_count += 1
            if doms is None:
                unmapped.append((kid, cid, law_name, e, url))
                continue
            checked += 1
            host = host_of(url)
            if not host_allowed(host, doms):
                mism.append((kid, cid, law_name[:40], e[:16], url[:80], str(ev.get("locator"))[:20]))

    print("Evidence refs inspected:", evidence_ref_count)
    print("Mapped refs checked:", checked)
    print("UNMAPPED refs (not adjudicated by domain allowlist):", len(unmapped))
    print("MISMATCHED reviews:", len(mism))
    for m in sorted(mism):
        print(" -", m[0], "| clause", m[1], "| law:", m[2], "| ev:", m[3], "| loc:", m[5], "| url:", m[4])

    return 1 if mism else 0


if __name__ == "__main__":
    raise SystemExit(main())
