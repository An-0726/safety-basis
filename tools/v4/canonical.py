#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical content hash for Safety Basis V4 entities.

Rules (GATE_V4.md §2.2):
- parse JSON, UTF-8
- object keys sorted recursively by Unicode code point
- aliases / places / keywords are set-like: sorted before hashing
- conditions and other narrative arrays keep original order
- output json.dumps(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
- hash = sha256(canonical_bytes).hexdigest() lowercase
"""
import hashlib
import json
import sys

SET_FIELDS = ("aliases", "places", "keywords")


def canonical_obj(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in SET_FIELDS and isinstance(v, list):
                out[k] = sorted(v)
            else:
                out[k] = canonical_obj(v)
        return out
    if isinstance(obj, list):
        return [canonical_obj(x) for x in obj]
    return obj


def canonical_json(obj) -> str:
    return json.dumps(
        canonical_obj(obj),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def content_hash(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    import os
    if len(sys.argv) < 2:
        print("usage: python canonical.py <entity.json>")
        sys.exit(1)
    p = sys.argv[1]
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    print(content_hash(data))
