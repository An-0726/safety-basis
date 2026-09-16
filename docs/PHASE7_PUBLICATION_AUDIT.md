# PHASE 7 Publication Source Hygiene — Final Audit

- Status: **DONE**
- As of: **2026-09-16**
- Knowledge authority: **103 laws / 106 law versions**

## Result

- `source/publication/law-index.json`: 216 → **106** canonical version rows.
- Fulltext catalog: 155 → **69** canonical rows; **11** approved official full texts and **58** metadata-only official links.
- Proposed-hazard leakage: **0**.
- Private-boundary marker leakage: **0**.
- Fulltext search gram shards rebuilt: **256**.

## Canonicalization

Publication identity is now a 1:1 projection of `knowledge/law-versions`; publication no longer creates independent law/version identities. Existing full text is retained only when its catalog row has explicit `official_legal_text` permission and `fullTextReviewed=true`; all other public entries are metadata-only official links.

- Stale law-index IDs removed: **144**.
- Fulltext rows with no governed knowledge identity removed from the public catalog: **86**.

## Boundaries

- `knowledge/` was not modified by the finalizer.
- No private SQLite/PDF/OCR/archive material is introduced into `source/publication/`.
- No stable knowledge IDs are renumbered.
- No release bundle, PR merge, Pages deployment, or public deployment is performed by PHASE 7.
