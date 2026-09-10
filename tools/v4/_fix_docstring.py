# -*- coding: utf-8 -*-
import io
p = 'tools/v4/apply_link_reviews.py'
src = io.open(p, encoding='utf-8').read()
lines = src.split('\n')
# replace broken docstring (lines 2..12, 0-based) with comments
head = lines[:2]
tail = lines[12:]
comment = [
    "# Apply professional link-applicability adjudications (batch 2..N).",
    "# For each link id in DECISIONS, rewrite knowledge/reviews/links/<id>.json with:",
    "# - decision / reviewer(Doubao-Agent) / checkedAt (2026-09-10T12:00:00+08:00)",
    "# - freshly computed reviewedContentHash + contextHashes",
    "# - structured reasonCodes + detailed reason",
    "# - keep original evidenceRefs and migratedFromV3Verification",
    "# DECISIONS is the single source of truth for this round; every pending link",
    "# without a reviewer MUST have an entry (script fails otherwise).",
]
new = '\n'.join(head + comment + tail)
io.open(p, 'w', encoding='utf-8', newline='\n').write(new)
print('patched')
