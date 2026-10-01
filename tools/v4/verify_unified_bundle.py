# -*- coding: utf-8 -*-
"""统一正式发布包严格校验器。

公开包只允许包含当前日期链式 Gate 通过的正式隐患、其实际引用条款和对应的
knowledge 法规版本。独立受控重大判定目录可另含已核且当前有效、无H/K关联的条款。
候选仍可存在于 knowledge，但不得进入正式包。
``source/publication`` 的全文/题录资料可包含未被当前隐患引用的版本；它们属于
“法规全文/资料库”，不因此成为正式法规卡。
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from presentation import (  # noqa: E402
    SCENE_TAG_OPTIONS,
    display_level,
    project_hazard,
    raw_law_level,
    searchable,
)
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402
from field_profiles import public_projection  # noqa: E402
from basis_refs import basis_sort_key, project_basis_reference  # noqa: E402
from major_criteria import (public_projection as major_criteria_projection,
                            CATALOG_FILE, TOPIC_FILE)  # noqa: E402
from major_criteria_references import (public_projection as reference_projection,
                                       project_publication, REFERENCE_FILE)  # noqa: E402
from major_criteria_directory import (public_projection as directory_projection,
                                     project_publication as project_directory_publication, DIRECTORY_FILE)  # noqa: E402
from release_snapshot import stable_knowledge_snapshot  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
PUBLICATION = os.path.join(ROOT, "source", "publication")
SELECTION = os.path.join(ROOT, "source", "releases", "site-selection.json")

SITE_ASSETS = ("index.html", "library.html", "style.css", "library.css", "stage3.css", "app.js",
               "sw.js", "icon.svg", "manifest.webmanifest", "js/store.js", "js/search.js",
               "js/search-vocabulary.js",
               "js/library.js", "js/fulltext-search.js", "js/verified-files.js",
               "major-criteria.html", "major-criteria.css",
               "js/major-criteria.js", "js/major-criteria-model.js",
               "js/major-criteria-reference-model.js", "js/major-criteria-directory-model.js")
COVER_EXCLUDE = {"checksums.json", "release.json", "site-manifest.json", "data/manifest.json"}
FIELD_PROFILE_FILE = 'data/field-profiles.json'
PRIVATE_PROFILE_KEYS = {'inventory', 'hazardsWithoutProfiles', 'excludedProfiles',
                        'orphanReviewIds', 'reviewedProfileHash', 'dependencyFingerprint',
                        'semanticChecks', 'basisScopeReasons', 'internalNotes',
                        'sourceRefs', 'fieldReview', 'reviewer', 'reviewedContentHash',
                        'contextHashes', 'evidenceRefs', 'reviewedOn', 'profileRevision',
                        'profileCount', 'publishedCount', 'orphanReviewCount'}


class Failures(list):
    def check(self, cond, message):
        if not cond:
            self.append(message)
        return cond


def rd(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def check_hazard_conditions(bad, hazard_id, row, source):
    """Validate the public conditions projection against its source field."""
    source_value = source.get("conditions")
    expected = "" if source_value is None else source_value
    if not isinstance(source_value, (str, type(None))):
        bad.check(
            False,
            "源隐患 conditions 必须是字符串、null 或缺失：" + hazard_id,
        )
        return
    bad.check(
        isinstance(row.get("conditions"), str),
        "公开隐患 conditions 必须是字符串：" + hazard_id,
    )
    bad.check(
        row.get("conditions") == expected,
        "隐患 conditions 与源字段不一致：" + hazard_id,
    )


def check_hazard_presentation(bad, hazard_id, row, search_row, source):
    """Recompute public hazard display projection instead of trusting the bundle."""
    expected = project_hazard(source, hazard_id=hazard_id)
    for field in ("displayCategory", "sceneTags"):
        bad.check(row.get(field) == expected[field],
                  "隐患展示投影被改动：%s/%s" % (hazard_id, field))
        bad.check(search_row.get(field) == expected[field],
                  "搜索索引展示投影被改动：%s/%s" % (hazard_id, field))
    for field in ("noteSegments", "businessNote", "maintenanceNote"):
        bad.check(row.get(field) == expected[field],
                  "隐患备注投影被改动：%s/%s" % (hazard_id, field))
    bad.check(search_row.get("businessNote") == expected["businessNote"],
              "搜索索引业务备注投影被改动：" + hazard_id)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def all_files(root):
    out = {}
    for base, _dirs, files in os.walk(root):
        for name in files:
            p = os.path.join(base, name)
            out[os.path.relpath(p, root).replace(os.sep, "/")] = p
    return out


def expected_release_hash(bundle):
    payload = {rel: sha256_file(p) for rel, p in all_files(bundle).items()
               if rel not in COVER_EXCLUDE}
    return hashlib.sha256(
        json.dumps(sorted(payload.items()), ensure_ascii=False,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def private_profile_keys(value):
    """Find structural private fields, including attempts to hide them elsewhere."""
    found = set()
    if isinstance(value, dict):
        found.update(set(value) & PRIVATE_PROFILE_KEYS)
        for child in value.values():
            found.update(private_profile_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(private_profile_keys(child))
    return found


def check_field_profiles(bad, payload, expected, manifest, release, hazards, clauses, law_ids):
    """Require the exact governed projection and resolvable existing public joins."""
    bad.check(json.dumps(payload, ensure_ascii=False, sort_keys=True) ==
              json.dumps(expected, ensure_ascii=False, sort_keys=True),
              'field profiles 与当前日期已审核的精确公开投影不一致')
    bad.check(manifest.get('files', {}).get('fieldProfiles') == FIELD_PROFILE_FILE,
              'manifest fieldProfiles 文件引用不一致')
    count = len(expected['records'])
    for owner, value in [('manifest', manifest), ('release', release)]:
        bad.check(type(value.get('counts', {}).get('fieldProfiles')) is int and
                  value['counts']['fieldProfiles'] == count,
                  owner + ' fieldProfiles 数量不一致')
    # Walk the trusted expected structure so a malformed public record reports
    # rejection above instead of crashing the verifier or widening its joins.
    for profile in expected['records']:
        ident, hid = profile['id'], profile['hazardId']
        hazard = hazards.get(hid)
        if not bad.check(hazard is not None, 'field profile 隐患引用断链：' + ident):
            continue
        source = profile['sourceHazard']
        bad.check(source['id'] == hid and hazard.get('title') == source['title'] and
                  hazard.get('conditions') == (source['conditions'] or ''),
                  'field profile 源隐患标题/conditions 不一致：' + ident)
        selected = {basis['linkId'] for basis in profile['bases']}
        bad.check(selected == set(profile['basisLinkIds']) and
                  len(selected) == len(profile['bases']),
                  'field profile selected links 不一致：' + ident)
        for basis in profile['bases']:
            clause = clauses.get(basis['clauseId'])
            bad.check(clause is not None and clause.get('lawId') == basis['lawVersionId'] and
                      basis['lawVersionId'] in law_ids,
                      'field profile 法规条款引用断链：' + ident + '/' + basis['linkId'])
            bad.check(any(ref.get('clauseId') == basis['clauseId'] and
                          ref.get('role') == basis['role'] and ref.get('linkId') == basis['linkId'] and
                          ref.get('applicability') == basis['applicability'] and
                          ref.get('jurisdictionCode') == basis['jurisdictionCode']
                          for ref in hazard.get('basisRefs', [])),
                      'field profile 依据不在源隐患公开依据中：' + ident + '/' + basis['linkId'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default=None)
    ap.add_argument("--selection", default=SELECTION)
    args = ap.parse_args()
    with stable_knowledge_snapshot(KNOW) as (snapshot, source_hash):
        return verify(args, str(snapshot), source_hash)


def verify(args, KNOW, source_hash):
    bad = Failures()

    sel = rd(args.selection)
    bad.check(set(sel) == {"schemaVersion", "bundle", "releaseHash"}
              and sel["schemaVersion"] == "safety-site-selection-v1",
              "site-selection 格式无效")
    bundle = os.path.abspath(args.bundle or os.path.join(ROOT, "source", "releases", sel["bundle"]))
    releases_root = os.path.join(ROOT, "source", "releases")
    bad.check(os.path.dirname(bundle) == releases_root, "发布包必须位于 source/releases 下")
    if not bad.check(os.path.isdir(bundle), "发布包不存在：" + bundle):
        print(json.dumps({"ok": False, "errors": list(bad)}, ensure_ascii=False, indent=2))
        return 1

    files = all_files(bundle)
    checksums = rd(os.path.join(bundle, "checksums.json"))
    bad.check(set(checksums) == {rel for rel in files if rel != "checksums.json"},
              "checksums.json 与文件集合不一致")
    for rel, expected in checksums.items():
        if rel in files:
            bad.check(sha256_file(files[rel]) == expected, "哈希不匹配：" + rel)

    bad.check(not any(rel.startswith("data/_internal") for rel in files),
              "发布包含 _internal 索引")
    for rel, path in files.items():
        if rel.endswith('.json'):
            private_keys = private_profile_keys(rd(path))
            bad.check(not private_keys, '公开包包含私有 field profile 字段：' + rel +
                      ' ' + ', '.join(sorted(private_keys)))

    release = rd(os.path.join(bundle, "release.json"))
    bad.check(release.get("formatVersion") == "safety-unified-release-v1",
              "release.json 格式无效")
    actual_hash = expected_release_hash(bundle)
    bad.check(release.get("releaseHash") == actual_hash, "releaseHash 复算不一致")
    bad.check(release.get("releaseHash") == sel.get("releaseHash"),
              "site-selection releaseHash 不匹配")
    bad.check((release.get("knowledge") or {}).get("gate", {}).get("publicProposalHazards") == 0,
              "正式发布包不得公开 proposed 候选")

    manifest = rd(os.path.join(bundle, "data", "manifest.json"))
    site_manifest = rd(os.path.join(bundle, "site-manifest.json"))
    public_files = {'searchIndex': 'data/search-index.json', 'lawIndex': 'data/law-index.json',
                    'taxonomy': 'data/taxonomy.json', 'fieldProfiles': FIELD_PROFILE_FILE,
                    'majorCriteriaCatalog': CATALOG_FILE, 'majorCriteriaTopic': TOPIC_FILE,
                    'majorCriteriaReferences': REFERENCE_FILE, 'majorCriteriaDirectory': DIRECTORY_FILE}
    bad.check(manifest.get('files') == public_files, 'manifest files 必须恰好为公开消费入口')
    allowed = ({'checksums.json', 'release.json', 'site-manifest.json', 'data/manifest.json'} |
               set(SITE_ASSETS) | set(public_files.values()) |
               {'data/fulltext/' + rel for rel in all_files(os.path.join(PUBLICATION, 'fulltext'))})
    safe_shard_paths = True
    for kind, prefix in [('hazardShards', 'hazards/h'), ('clauseShards', 'clauses/c')]:
        for shard in manifest.get(kind, []):
            url = shard.get('url', '')
            if bad.check(isinstance(url, str) and re.fullmatch('data/' + prefix + r'\d{4}\.json', url),
                         '非法分片文件引用：' + str(url)):
                allowed.add(url)
            else:
                safe_shard_paths = False
    stray = sorted(set(files) - allowed)
    bad.check(not stray, '发布包含白名单之外文件：' + ', '.join(stray[:10]))
    bad.check(set(files) == allowed, '公开包与预期公开文件集合不一致')
    if not safe_shard_paths:
        print(json.dumps({'ok': False, 'errors': list(bad)}, ensure_ascii=False, indent=2))
        return 1
    bad.check(manifest.get("schemaVersion") == 2 and manifest.get("v4SchemaVersion") == 3,
              "manifest 格式标记无效")
    bad.check(manifest.get("releaseHash") == actual_hash, "manifest releaseHash 不一致")
    bad.check(site_manifest.get("releaseHash") == actual_hash, "site-manifest releaseHash 不一致")

    try:
        as_of = date.fromisoformat(str(release.get("asOf")))
    except ValueError:
        as_of = None
        bad.append("release.asOf 不是有效日期")
    if as_of is None:
        print(json.dumps({'ok': False, 'errors': list(bad)}, ensure_ascii=False, indent=2))
        return 1
    bad.check(manifest.get('generatedAt') == release.get('asOf') == site_manifest.get('asOf'),
              '公开清单日期不一致')
    bad.check(release.get('knowledge', {}).get('gate', {}).get('asOf') == as_of.isoformat(),
              'Gate 日期与 release.asOf 不一致')
    bad.check(release.get('knowledge', {}).get('snapshotSha256') == source_hash,
              'knowledge 快照与当前稳定源不一致')

    # ---- 分片与索引 ----
    hazards, clauses = {}, {}
    clause_shard_by_id = {}
    for key, target in (("hazardShards", hazards), ("clauseShards", clauses)):
        for shard in manifest[key]:
            payload = rd(os.path.join(bundle, shard["url"]))
            for row in payload["records"]:
                if not bad.check(row["id"] not in target, "分片记录重复：" + row["id"]):
                    continue
                target[row["id"]] = row
                if key == "clauseShards":
                    clause_shard_by_id[row["id"]] = shard["id"]

    for row in hazards.values():
        bad.check(row.get("status") == "已核验", "正式包出现非已核验隐患：" + row["id"])
        bad.check(row.get("publishable") is True, "正式隐患 publishable 必须为 true：" + row["id"])
        bad.check((row.get("lifecycle") or "active") == "active",
                  "正式包出现非 active 隐患：" + row["id"])

    for row in clauses.values():
        bad.check(row.get("status") == "现行有效",
                  "正式条款必须来自当前已生效版本：" + row["id"] + " " + str(row.get("status")))

    si = rd(os.path.join(bundle, "data", "search-index.json"))
    law_index = rd(os.path.join(bundle, "data", "law-index.json"))
    taxonomy = rd(os.path.join(bundle, "data", "taxonomy.json"))
    si_by_id = {row["id"]: row for row in si}
    law_ids = {e["id"] for e in law_index}
    si_ids = {r["id"] for r in si}
    bad.check(si_ids == set(hazards), "search-index 与隐患分片集合不一致")
    bad.check(len(law_ids) == len(law_index), "法规目录存在重复 id")
    bad.check(taxonomy.get("hazardStatuses") == ["已核验"],
              "正式 taxonomy 不得包含候选状态")
    bad.check(taxonomy.get("sceneTagOptions") == list(SCENE_TAG_OPTIONS),
              "taxonomy sceneTagOptions 与受控场景字典不一致")
    bad.check(set(taxonomy.get("displayCategories", [])) ==
              {row.get("displayCategory") for row in si},
              "taxonomy displayCategories 与搜索索引不一致")
    bad.check(set(taxonomy.get("displayLevels", [])) ==
              {row.get("displayLevel") for row in law_index},
              "taxonomy displayLevels 与法规索引不一致")

    for row in clauses.values():
        bad.check(row["lawId"] in law_ids, "条款法规引用断链：" + row["id"])
    for row in hazards.values():
        for ref in row["basisRefs"]:
            ok = bad.check(ref["clauseId"] in clauses,
                           "隐患依据断链：" + row["id"] + "/" + ref["clauseId"])
            if ok:
                shard_url = next(s["url"] for s in manifest["clauseShards"]
                                 if s["id"] == ref["clauseShard"])
                shard_ids = {r["id"] for r in rd(os.path.join(bundle, shard_url))["records"]}
                bad.check(ref["clauseId"] in shard_ids,
                          "basisRefs clauseShard 错误：" + row["id"])
    for entry in law_index:
        bad.check(bool(entry.get("clauseRefs")), "正式法规不得是零条款目录项：" + entry["id"])
        bad.check(entry.get("clauseCount") == len(entry.get("clauseRefs", [])),
                  "法规 clauseCount 不一致：" + entry["id"])
        for ref in entry.get("clauseRefs", []):
            ok = bad.check(ref["clauseId"] in clauses,
                           "法规条款引用断链：" + entry["id"] + "/" + ref["clauseId"])
            if ok:
                bad.check(set(ref.get("hazardIds", [])) <= si_ids,
                          "法规引用的隐患不存在：" + entry["id"])

    counts = manifest["counts"]
    bad.check(counts["hazards"] == len(hazards) and counts["clauses"] == len(clauses)
              and counts["laws"] == len(law_index) and counts["lawVersions"] == len(law_index),
              "manifest counts 与正式数据不一致")

    # ---- 与实时 Gate / knowledge 一致性 ----
    gate = evaluate_release_gate(KNOW, as_of)
    know_hazards = load_dir(KNOW, "hazards")
    know_links = load_dir(KNOW, "links")
    know_clauses = load_dir(KNOW, "clauses")
    know_lvs = load_dir(KNOW, "law-versions")
    know_laws = load_dir(KNOW, "laws")
    publication_index = rd(os.path.join(PUBLICATION, "law-index.json"))
    publication_by_id = {entry["id"]: entry for entry in publication_index}

    expected_profiles = public_projection(KNOW, as_of=as_of)['public']
    if bad.check(FIELD_PROFILE_FILE in files, '缺少 governed field profiles 公开文件'):
        check_field_profiles(bad, rd(files[FIELD_PROFILE_FILE]), expected_profiles,
                             manifest, release, hazards, clauses, law_ids)
    expected_directory = directory_projection(KNOW, PUBLICATION, as_of=as_of)
    if bad.check(DIRECTORY_FILE in files, '缺少官方文件题录目录'):
        bad.check(rd(files[DIRECTORY_FILE]) == expected_directory['public'], '官方文件题录目录精确投影不一致')
    expected_references = reference_projection(KNOW, PUBLICATION, as_of=as_of)
    if bad.check(REFERENCE_FILE in files, '缺少重大判定官方查阅入口文件'):
        bad.check(rd(files[REFERENCE_FILE]) == expected_references['public'],
                  '官方查阅入口精确投影不一致；不得添加正文或判定结论')
    expected_major = major_criteria_projection(KNOW, as_of=as_of)
    for key, path in [('catalog', CATALOG_FILE), ('topic', TOPIC_FILE)]:
        if bad.check(path in files, '缺少重大判定公开文件：' + path):
            bad.check(rd(files[path]) == expected_major[key], '重大判定精确公开投影不一致：' + key)
    major_standards = expected_major['catalog']['standards']
    for key, value in {
            'majorCriteriaStandards': len(major_standards),
            'majorCriteriaClauses': sum(len(s['clauses']) for s in major_standards),
            'majorCriteriaHazards': len(expected_major['topic']['hazardIds']),
            'majorCriteriaAssociations': len(expected_major['topic']['associations']),
            'majorCriteriaDirectoryGroups': expected_directory['public']['directoryGroupCount'],
            'majorCriteriaDirectoryDocuments': expected_directory['public']['documentCount'],
            'majorCriteriaReferenceStandards': len(expected_references['public']['referenceEntries']),
            'majorCriteriaSearchTopics': sum(e['searchTopicCount'] for e in expected_references['public']['referenceEntries'])}.items():
        bad.check(counts.get(key) == value, '重大判定计数不一致：' + key)
    for association in expected_major['topic']['associations']:
        bad.check(association['hazardId'] in hazards and association['clauseId'] in clauses and
                  association['lawVersionId'] in law_ids, '重大判定关联公开链断裂：' + association['linkId'])
    bad.check(release.get('counts') == counts, 'release/manifest counts 不一致')

    bad.check(set(hazards) == gate.eligible_hazards,
              "正式隐患集合 != 当前 Gate eligibleHazards（%d vs %d）" %
              (len(hazards), len(gate.eligible_hazards)))

    verified_by_hazard = {}
    verified_links_by_hazard = {}
    shipped_link_count = 0
    for kid in gate.eligible_links:
        link = know_links[kid]
        hid, cid = link.get("hazardId"), link.get("clauseId")
        if hid in gate.eligible_hazards and cid in know_clauses:
            verified_by_hazard.setdefault(hid, set()).add((cid, link.get("role", "direct")))
            verified_links_by_hazard.setdefault(hid, []).append(link)
            shipped_link_count += 1

    for hid, row in hazards.items():
        src = know_hazards[hid]
        check_hazard_conditions(bad, hid, row, src)
        check_hazard_presentation(bad, hid, row, si_by_id.get(hid, {}), src)
        expected_display_levels = set()
        law_names, standard_numbers = set(), set()
        for cid, _role in verified_by_hazard.get(hid, set()):
            clause_source = know_clauses[cid]
            vid = clause_source.get("lawVersionId")
            lv = know_lvs.get(vid) or {}
            law = know_laws.get(lv.get("lawId")) or {}
            source = publication_by_id.get(vid) or {}
            name = law.get("canonicalName") or law.get("officialName") or lv.get("officialName")
            if name:
                law_names.add(name)
            if lv.get("documentNumber"):
                standard_numbers.add(lv["documentNumber"])
            raw_level = raw_law_level(law, lv, source)
            expected_display_levels.add(display_level(raw_level, vid))
        bad.check(si_by_id.get(hid, {}).get("displayLevels") ==
                  sorted(expected_display_levels),
                  "搜索索引 displayLevels 展示投影被改动：" + hid)
        source_projection = project_hazard(src, hazard_id=hid)
        expected_search_text = searchable([
            src.get("title", ""), " ".join(src.get("aliases") or []),
            " ".join(src.get("keywords") or []), src.get("description", ""),
            src.get("conditions") or "", source_projection["businessNote"],
            " ".join(sorted(law_names)), " ".join(sorted(standard_numbers)),
            src.get("category", ""), source_projection["displayCategory"],
            " ".join(source_projection["sceneTags"]),
            " ".join(sorted(expected_display_levels)),
        ])
        bad.check(si_by_id.get(hid, {}).get("searchText") == expected_search_text,
                  "搜索索引 searchText 与业务备注投影不一致：" + hid)
        for field in ("title", "description", "measures", "note", "category", "mode", "lifecycle"):
            bad.check(row.get(field) == src.get(field),
                      "隐患字段被改动：%s/%s" % (hid, field))
        for field in ("places", "aliases", "keywords"):
            bad.check((row.get(field) or []) == (src.get(field) or []),
                      "隐患标签被改动：%s/%s" % (hid, field))
        expected_basis_refs = [project_basis_reference(link, clause_shard_by_id.get(link['clauseId'], 'missing'))
                               for link in sorted(verified_links_by_hazard.get(hid, []), key=basis_sort_key)]
        bad.check(row.get('basisRefs') == expected_basis_refs,
                  '隐患逐K依据身份或适用范围与精确源投影不一致：' + hid)
        shipped = {(r["clauseId"], r["role"]) for r in row["basisRefs"]}
        bad.check(shipped == verified_by_hazard.get(hid, set()),
                  "隐患依据集合与 Gate 关联不一致：" + hid)

    expected_law_ids = set()
    for cid, row in clauses.items():
        src = know_clauses[cid]
        vid = src.get("lawVersionId")
        expected_law_ids.add(vid)
        bad.check(vid in know_lvs, "正式条款引用不存在的 knowledge 法规版本：" + cid)
        bad.check(row["lawId"] == vid, "条款法规键被改动：" + cid)
        bad.check(row["quote"] == src.get("quote", ""), "条款原文被改动：" + cid)
        bad.check(row["article"] == (src.get("articlePath") or src.get("clauseNumber") or ""),
                  "条款条号被改动：" + cid)

    bad.check(law_ids == expected_law_ids,
              "正式法规索引必须恰好等于正式条款实际引用的 knowledge 法规版本")
    for entry in law_index:
        lv = know_lvs.get(entry["id"])
        if not bad.check(lv is not None, "正式法规不是 knowledge 法规版本：" + entry["id"]):
            continue
        law = know_laws.get(lv.get("lawId")) or {}
        source = publication_by_id.get(entry["id"]) or {}
        expected_raw_level = raw_law_level(law, lv, source)
        bad.check(entry.get("level") == expected_raw_level,
                  "法规原始 level 被改动：" + entry["id"])
        bad.check(entry.get("displayLevel") == display_level(expected_raw_level, entry["id"]),
                  "法规 displayLevel 展示投影被改动：" + entry["id"])
        bad.check(lv.get("validityStatus") == "active",
                  "正式法规版本不是 active：" + entry["id"])
        eff = lv.get("effectiveDate") or ""
        bad.check(bool(eff) and (not as_of or eff <= as_of.isoformat()),
                  "正式法规版本尚未实施：" + entry["id"])

    bad.check(counts.get("links") == shipped_link_count,
              "manifest links 与正式 Gate 关联数量不一致")

    # ---- 全文/题录资料边界 ----
    catalog = rd(os.path.join(bundle, "data", "fulltext", "catalog.json"))
    publication_catalog = rd(os.path.join(PUBLICATION, "fulltext", "catalog.json"))
    bad.check(catalog == project_directory_publication(project_publication(publication_catalog, expected_references), expected_directory),
              "公开全文/题录资料必须与受控日期投影一致")
    search_source = rd(os.path.join(PUBLICATION, "fulltext", "search-index.json"))
    bad.check(rd(os.path.join(bundle, "data/fulltext/search-index.json")) ==
              project_directory_publication(project_publication(search_source, expected_references), expected_directory),
              "全文检索题录必须与受控日期投影一致")
    docs = catalog["documents"]
    full_text = {d["versionId"] for d in docs if d["textMode"] == "full_text"}
    d47236 = [d for d in docs if d.get("versionId") == "LV_STD_GBT47236_2026"]
    if bad.check(len(d47236) == 1, "GB/T 47236-2026 题录缺失"):
        d = d47236[0]
        bad.check(d["textMode"] == "link_only", "GB/T 47236-2026 必须是 link_only 题录")
        bad.check("openstd.samr.gov.cn" in d.get("officialUrl", ""),
                  "GB/T 47236-2026 官方入口异常")
        bad.check(d.get("effectiveDate") == "2026-09-01",
                  "GB/T 47236-2026 实施日期应为 2026-09-01")

    bad.check(site_manifest.get("fullTextCount") == len(full_text),
              "site-manifest fullTextCount 不一致")
    bad.check(site_manifest.get("officialLinkCount") ==
              sum(1 for d in docs if d["textMode"] == "link_only"),
              "site-manifest officialLinkCount 不一致")
    data_actual = {rel: sha256_file(p) for rel, p in files.items()
                   if rel.startswith("data/") and rel.endswith(".json")}
    bad.check(site_manifest.get("fileHashes") == data_actual,
              "site-manifest fileHashes 与实际不一致")

    summary = {
        "ok": not bad,
        "bundle": os.path.basename(bundle),
        "releaseHash": actual_hash,
        "counts": {
            "hazards": len(hazards),
            "laws": len(law_index),
            "clauses": len(clauses),
            "links": counts["links"],
            "fieldProfiles": len(expected_profiles['records']),
        },
        "gate": {
            "asOf": gate.as_of,
            "eligibleHazards": len(gate.eligible_hazards),
            "eligibleLinks": len(gate.eligible_links),
        },
        "fullText": {
            "fullTextCount": len(full_text),
            "officialLinkCount": site_manifest.get("officialLinkCount"),
        },
        "errors": list(bad),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
