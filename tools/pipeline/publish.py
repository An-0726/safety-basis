"""Prepare a strict public snapshot and deterministically compile website JSON.

Outputs are new, isolated directories. This command never overwrites content/,
the currently served data/, a master, or an existing release, and never deploys.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import subprocess
import tempfile

import exchange
from master import ROOT, connect_readonly
import review
import verification as v

FORMAT = "safety-release-v1"
SETTINGS_FIELDS = {"schemaVersion", "dataVersion", "generatedAt", "hazardShardSize", "clauseShardSize", "publicScope"}


def validate_release(release):
    fields = {"formatVersion", "asOf", "sourceStateHash", "sourceCounts", "graph", "proofs", "evidence", "settings", "releaseHash"}
    if not isinstance(release, dict) or set(release) != fields or release["formatVersion"] != FORMAT:
        raise ValueError("发布快照格式无效或含额外字段")
    if release["releaseHash"] != v.digest({k: val for k, val in release.items() if k != "releaseHash"}):
        raise ValueError("发布快照哈希不匹配")
    v.date(release["asOf"])
    if not isinstance(release["sourceStateHash"], str) or len(release["sourceStateHash"]) != 64:
        raise ValueError("母库状态指纹无效")
    settings = release["settings"]
    if not isinstance(settings, dict) or set(settings) != SETTINGS_FIELDS or settings["schemaVersion"] != 2 or settings["generatedAt"] != release["asOf"]:
        raise ValueError("发布 settings 无效")
    graph = release["graph"]
    v.validate_graph(graph)
    if (not isinstance(release["sourceCounts"], dict) or set(release["sourceCounts"]) != set(v.TABLES.values())
            or any(type(release["sourceCounts"][table]) is not int or release["sourceCounts"][table] < len(rows)
                   for table, rows in graph.items())):
        raise ValueError("母库汇总计数无效")
    proofs, evidence = {}, {}
    if not isinstance(release["proofs"], list) or not isinstance(release["evidence"], list):
        raise ValueError("公开核验摘要或证据不是数组")
    for row in release["proofs"]:
        if not isinstance(row, dict) or set(row) != v.PROOF_FIELDS:
            raise ValueError("公开核验摘要字段无效")
        if (type(row["entity_revision"]) is not int or row["entity_revision"] < 1
                or type(row["public_fields_reviewed"]) is not bool
                or any(not isinstance(row[field], str) for field in v.PROOF_FIELDS - {"entity_revision", "public_fields_reviewed"})):
            raise ValueError("公开核验摘要类型无效")
        key = (row["entity_type"], row["entity_id"])
        if key in proofs or row["check_type"] != v.CHECKS.get(row["entity_type"]):
            raise ValueError("核验摘要重复或核验类型错误")
        proofs[key] = row
    for row in release["evidence"]:
        if (not isinstance(row, dict) or set(row) != v.EVIDENCE_FIELDS or any(not isinstance(val, str) for val in row.values())
                or row["id"] in evidence):
            raise ValueError("公开证据字段无效或重复")
        evidence[row["id"]] = row
    wanted = {(kind, row["id"]) for kind, table in v.TABLES.items() for row in graph[table]}
    if set(proofs) != wanted or {r["evidence_id"] for r in proofs.values()} != set(evidence):
        raise ValueError("发布实体、核验摘要和证据集合不一致")
    if {r["clause_id"] for r in graph["links"]} != {r["id"] for r in graph["clauses"]}:
        raise ValueError("存在未引用条款或条款缺失")
    if {r["law_id"] for r in graph["law_versions"]} != {r["id"] for r in graph["laws"]}:
        raise ValueError("存在未引用法规身份")
    blocked = v.gate(graph, proofs, evidence, release["asOf"])
    errors = {key: reasons for group in blocked.values() for key, reasons in group.items() if reasons}
    if errors:
        raise ValueError("快照含未通过核验的内容: " + json.dumps(errors, ensure_ascii=False))
    return release


def prepare(db, as_of, *, baseline=None):
    v.date(as_of)
    with closing(connect_readonly(Path(db).resolve())) as conn:
        conn.execute("BEGIN")
        exchange.check_integrity(conn)
        source_hash = exchange.state_hash(conn)
        graph = v.graph_from_db(conn)
        proofs, evidence = v.load_proofs(conn), v.load_evidence(conn, db)
        blocked = v.gate(graph, proofs, evidence, as_of)
        hazard_ids = {ident for ident, reasons in blocked["hazards"].items() if not reasons}
        links = [r for r in graph["links"] if r["hazard_id"] in hazard_ids and r["status"] != "已失效"]
        clause_ids = {r["clause_id"] for r in links}
        versions = [r for r in graph["law_versions"] if not blocked["lawVersions"][r["id"]]]
        law_ids = {r["law_id"] for r in versions}
        selected = {"hazards": [r for r in graph["hazards"] if r["id"] in hazard_ids], "links": links,
                    "clauses": [r for r in graph["clauses"] if r["id"] in clause_ids], "law_versions": versions,
                    "laws": [r for r in graph["laws"] if r["id"] in law_ids]}
        selected_proofs = [proofs[(kind, r["id"])] for kind, table in v.TABLES.items() for r in selected[table]]
        used_evidence = {r["evidence_id"] for r in selected_proofs}
        release = {"formatVersion": FORMAT, "asOf": as_of, "sourceStateHash": source_hash,
                   "sourceCounts": {table: len(rows) for table, rows in graph.items()}, "graph": selected,
                   "proofs": selected_proofs, "evidence": [{f: evidence[ident][f] for f in v.EVIDENCE_FIELDS} for ident in sorted(used_evidence)],
                   "settings": {"schemaVersion": 2, "dataVersion": as_of.replace("-", ".") + "." + source_hash[:12],
                                "generatedAt": as_of, "hazardShardSize": 500, "clauseShardSize": 500,
                                "publicScope": "国家法规标准优先，江苏／南京补充"}}
        release["releaseHash"] = v.digest(release)
        validate_release(release)
    old = set()
    if baseline is not None:
        rows = json.loads(Path(baseline).read_text(encoding="utf-8"))
        if not isinstance(rows, list) or any(not isinstance(r, dict) or not isinstance(r.get("id"), str) for r in rows):
            raise ValueError("基线必须是 search-index.json 记录数组")
        old = {r["id"] for r in rows}
    report = {"asOf": as_of, "sourceStateHash": source_hash, "releaseHash": release["releaseHash"],
              "publishedCounts": {table: len(rows) for table, rows in selected.items()},
              "blockedHazards": {ident: reasons for ident, reasons in blocked["hazards"].items() if reasons},
              "blockedLawVersions": {ident: reasons for ident, reasons in blocked["lawVersions"].items() if reasons},
              "baselineCompared": baseline is not None, "addedHazardIds": sorted(hazard_ids - old),
              "removedHazardIds": sorted(old - hazard_ids), "emptyHazardRelease": not hazard_ids,
              "requiresPublicationReview": bool(old - hazard_ids) or not hazard_ids}
    return release, report


def runtime_input(release):
    graph = release["graph"]
    proofs = {(r["entity_type"], r["entity_id"]): r for r in release["proofs"]}
    laws = {r["id"]: r for r in graph["laws"]}
    def checked(kind, ident):
        return v.business_date(proofs[(kind, ident)]["checked_at"]).isoformat()
    return {
        "settings": release["settings"],
        "hazards": [{"id": h["id"], "title": h["title"], "description": h["description"], "measures": h["measures"],
                     "category": h["category"], "mode": h["mode"], "note": "适用条件：" + h["conditions"],
                     "aliases": h["aliases"], "places": h["places"], "keywords": h["keywords"], "status": "已核验",
                     "checked": checked("hazard", h["id"])} for h in graph["hazards"]],
        "laws": [{"id": r["id"], "name": r["official_name"], "aliases": laws[r["law_id"]]["aliases"],
                  "level": r["level"], "scope": r["scope"], "status": r["validity_status"], "checked": checked("law_version", r["id"]),
                  "effectiveDate": r["effective_date"], "sourceUrl": r["source_url"], "replaces": [], "replacedBy": []}
                 for r in graph["law_versions"]],
        "clauses": [{"id": r["id"], "lawId": r["law_version_id"], "article": r["article_path"], "quote": r["quote"],
                     "sourceUrl": r["source_url"], "status": "已核验", "checked": checked("clause", r["id"])} for r in graph["clauses"]],
        "links": [{"hazardId": r["hazard_id"], "clauseId": r["clause_id"], "role": r["role"], "priority": r["priority"]}
                  for r in graph["links"]],
    }


def check_runtime(root, release):
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("data/manifest.json")
    graph = release["graph"]
    if {r["id"] for r in read("data/search-index.json")} != {r["id"] for r in graph["hazards"]}:
        raise ValueError("搜索索引与发布快照隐患集合不一致")
    if {r["id"] for r in read("data/law-index.json")} != {r["id"] for r in graph["law_versions"]}:
        raise ValueError("法规索引与发布快照不一致")
    clauses, hazards = {}, {}
    for key, records in (("clauseShards", clauses), ("hazardShards", hazards)):
        for shard in manifest[key]:
            for row in read(shard["url"])["records"]:
                if row["id"] in records or row["status"] != "已核验":
                    raise ValueError("公开分片存在重复或待核验记录")
                records[row["id"]] = row
    if set(clauses) != {r["id"] for r in graph["clauses"]} or set(hazards) != {r["id"] for r in graph["hazards"]}:
        raise ValueError("分片实体集合不一致")
    for h in hazards.values():
        for ref in h["basisRefs"]:
            if ref["clauseId"] not in clauses:
                raise ValueError("公开引用断链")
    return manifest


def build(release, output, *, node="node"):
    validate_release(release)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("输出目录已存在，拒绝覆盖现有发布")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="safety-release-", dir=output.parent) as scratch:
        scratch = Path(scratch)
        content, bundle = scratch / "input", scratch / "bundle"
        content.mkdir()
        bundle.mkdir()
        for name, value in runtime_input(release).items():
            review.write_json(content / (name + ".json"), value)
        result = subprocess.run([str(node), str(ROOT / "tools/build-data.mjs"), "--input-dir", str(content),
                                 "--output-dir", str(bundle / "data")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            raise ValueError("网站构建失败: " + result.stderr[-4000:])
        manifest = check_runtime(bundle, release)
        manifest.update(releaseHash=release["releaseHash"], sourceRevision=release["sourceStateHash"], asOf=release["asOf"], buildToolVersion=FORMAT)
        counts = release["sourceCounts"]
        manifest["sourceCounts"] = {"hazards": counts["hazards"], "laws": counts["law_versions"], "clauses": counts["clauses"], "links": counts["links"]}
        manifest["health"].update(stagedHazards=counts["hazards"] - manifest["counts"]["hazards"],
                                  stagedLaws=counts["law_versions"] - manifest["counts"]["laws"])
        (bundle / "data/manifest.json").write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode('utf-8'))
        # Proof fields originate from sets; canonical serialization must not depend on PYTHONHASHSEED.
        (bundle / "release.json").write_bytes((json.dumps(release, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode('utf-8'))
        checksums = {path.relative_to(bundle).as_posix(): exchange.sha256_bytes(path.read_bytes())
                     for path in sorted(bundle.rglob("*.json"))}
        review.write_json(bundle / "checksums.json", checksums)
        if output.exists():
            raise ValueError("输出目录被其他操作创建，拒绝覆盖")
        os.rename(bundle, output)
    return {"ok": True, "output": str(output), "releaseHash": release["releaseHash"], "counts": manifest["counts"]}


def publish(db, as_of, output, *, node="node", baseline=None):
    release, report = prepare(db, as_of, baseline=baseline)
    # Keep the private report outside the public bundle.
    output = Path(output).resolve()
    report_file = output.with_name(output.name + ".review.json")
    exchange.check_output(report_file, ".json")
    result = build(release, output, node=node)
    review.write_json(report_file, report)
    return {**result, "reviewReport": str(report_file), "removedHazardCount": len(report["removedHazardIds"]),
            "requiresPublicationReview": report["requiresPublicationReview"], "deployed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("publish")
    generate.add_argument("--db", type=Path, default=ROOT / "source/master/safety.sqlite3")
    generate.add_argument("--as-of", required=True)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--baseline", type=Path, default=ROOT / "data/search-index.json")
    generate.add_argument("--node", default="node")
    rebuild = sub.add_parser("build")
    rebuild.add_argument("--release", type=Path, required=True)
    rebuild.add_argument("--output", type=Path, required=True)
    rebuild.add_argument("--node", default="node")
    args = parser.parse_args(argv)
    try:
        if args.command == "publish":
            result = publish(args.db, args.as_of, args.output, node=args.node, baseline=args.baseline)
        else:
            result = build(json.loads(args.release.read_text(encoding="utf-8")), args.output, node=args.node)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
