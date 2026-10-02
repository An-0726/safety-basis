# Governed reusable field profiles, version 1

This is the backend governance and release contract, not automatic approval of
content. The formal search/detail consumer is specified in
[FIELD_PROFILE_UI_CONTRACT](FIELD_PROFILE_UI_CONTRACT.md). The existing 24-case private pilot namespace remains untouched
and isolated. No automatic or bulk pilot migration, automatic review signing, or
automatic frontend admission of unreviewed content is included.

## Storage and identity

- Records: `knowledge/field-profiles/v1/records/*.json`
- Independent semantic review sidecars: `knowledge/field-profiles/v1/reviews/*.json`
- Profile ID: stable `FPR_*`; `revision` is a positive integer. Keep the ID when
  revising a profile; increase revision for authored changes. Hash checks also
  invalidate content changes made without a revision bump.
- `hazardId` references the existing hazard identity. Do not copy, renumber,
  promote, or change that hazard's lifecycle. Several narrower profiles may
  reference one eligible hazard, provided each receives exact-scope review.
- The namespace is variable-sized, including zero records. Pilot `FP_*` records
  and pilot review decisions cannot serve as governed production profiles.

## Record schema

All fields below except `profileKind` are required. Top-level private authoring metadata is permitted,
review-bound, and excluded from the public projection. Nested public structures
are exact allowlists; unsupported keys in them are invalid.

| Field | Contract |
| --- | --- |
| `schemaVersion` | Integer `1` |
| `profileKind` | Optional: `conditional_template` or `routing_only`. Absence retains legacy conditional-template behavior; an explicit null, unknown value or wrong type is invalid |
| `id`, `revision`, `hazardId` | Identity as above |
| `title` | Nonempty reusable profile title |
| `inspectionClass` | `core_onsite_inspection`, `document_review`, `special_review`, `legal_obligation`, or `undetermined` |
| `defaultFieldEntry` | `include`, `conditional`, `exclude`, or `undetermined`; this is routing, never an observed finding |
| `contentDisposition` | `onsite_finding`, `document_check`, `special_check`, `legal_obligation`, `counterexample`, or `undetermined` |
| `applicability` | Exactly `requires`, `excludes`, `perUseFacts`: arrays of unique nonempty strings; requires and perUseFacts must be nonempty; an explicitly empty excludes list is permitted |
| `findingTemplate` | Required even when null. For `routing_only`, always null, including onsite routes. For explicit or implicit `conditional_template` on an onsite route: exactly `{text, slots}`, with `{{slotKey}}` placeholders and slots `{key, label}`; all placeholders must match declared unique keys. Otherwise null |
| `evidenceRequirements` | Nonempty array of unique nonempty evidence-instruction strings |
| `correctiveDirection` | Nonempty correction guidance, separate from the finding template |
| `basisLinkIds` | Nonempty unique array of exact existing link IDs |

`routing_only` expresses reviewed routing and scope without authoring a finding
template. It is not a finding, a shortcut to approval, or an automatic conversion
of a candidate. It retains every required routing, applicability, onsite fact,
evidence, corrective-direction, basis, semantic-review and dated-Gate rule below.
An onsite routing-only profile may use `include` or `conditional`, but that is
only an inspection-entry decision; `findingTemplate` stays explicitly null and
`observedViolation` stays false. No production records or reviews are created by
adding support for this kind.

There is no default-field injection or migration. The optional kind is read as a
behavioral default only; it is not added to source objects, review-hash inputs or
public objects when absent. Existing kind-less records, reviews and public
payloads remain byte-compatible. Authoring, changing or removing an explicit
kind changes the complete profile hash and requires a fresh independent review.

Onsite findings must use `core_onsite_inspection`. Document, special and legal
obligation dispositions must use their corresponding class and have
`defaultFieldEntry: exclude`. Counterexamples cannot have an onsite template or
an include/conditional default entry. Any `undetermined` route is inventoried
and excluded even when a review claims verification.

Onsite `perUseFacts` must include `applicableRequirementConfirmed`,
`siteTriggerConfirmed`, and `defectObserved`. Additional named conditions are
allowed. Their actual values, enterprise identity, documents, measurements and
observations do **not** belong in reusable template approval. This module neither
collects facts nor renders a completed onsite finding. In particular, design
omission alone must not be treated as proof of a violation or as a blanket reason
to discard an otherwise applicable requirement.

## Explicit semantic review

A review must contain:

- `schemaVersion: 1`, `entityId`, `profileRevision`
- `decision: verified`, nonempty `reviewer` and `reason`, `reviewedOn` as ISO date
  not later than the projection date
- `reviewedProfileHash` and `dependencyFingerprint`
- `semanticChecks`, exactly the keys `routing`, `applicability`,
  `findingTemplate`, `evidenceRequirements`, `correctiveDirection`,
  `scopeContainment`, each explicitly true
- `basisScopeReasons`: exactly the selected link IDs mapped to nonempty reasoning
  explaining why that particular legal requirement supports this profile within
  its subject, equipment/process, regional and triggering scope

The same semantic checks apply to both kinds. For `routing_only`, a true
`findingTemplate` check confirms that no template is supplied and the profile is
used only for its reviewed route/scope. It does not approve a finding or invent
per-use observations. Neither a null template nor a routing-only label waives
the independent review, exact selected-link scope reasons, dependency binding,
source-hazard eligibility or the explicit projection date.

An eligible hazard is necessary but **not sufficient**: an eligible link about
activated-carbon VOC treatment does not support a generic gas/dust electrical
profile; an E-class fire basis does not establish all fire classes. Reviewers must
verify the exact requirement and scope, not merely match titles or check hashes.
The module requires recorded reasoning but cannot decide its truth automatically.

`review_bindings(profile, knowledge)` calculates binding values for independent
review; it never creates a review, sets a decision or signs anything. Synthetic
test fixtures are the only approvals created by the test suite.

The content hash covers the complete profile, including private authoring
metadata. The dependency fingerprint binds the source hazard, its review, the
complete set of its link associations, all associated and selected links, their
clause/version/law chains and reviews, and referenced evidence objects. Missing
objects are represented explicitly. Link addition/removal, source content,
review, evidence, scope and status changes invalidate the review. Reviews are
resolved by entityId, not their filename. Duplicate entity IDs abort rather than
silently choosing one.

## Publication and integration API

Import `tools/v4/field_profiles.py` using the repository's existing v4 Python
module path convention:

```python
from datetime import date
from field_profiles import public_projection, review_bindings, validate_profile
result = public_projection(knowledge_directory, as_of=date(2026, 9, 30))
public_payload = result['public']
private_inventory = result['inventory']
```

`validate_profile(profile)` returns sorted stable error codes without writing.
`review_bindings(profile, knowledge_directory)` returns the two binding hashes or
raises ValueError for an invalid record. `public_projection` requires an explicit
`datetime.date`; it uses the existing date-aware `evaluate_release_gate` and
rechecks it at each projection. Time is not part of the review fingerprint;
expiry still excludes a record without any file changing.

Publishability requires **all** of:

1. Valid known profile schema and route
2. Explicit current semantic review bound to content and upstream dependencies
3. Source hazard in the existing Gate's `eligible_hazards`
4. Every selected link in `eligible_links`, referencing this source hazard, with
   role `direct` or `fallback` (never `supporting` alone)
5. Complete selected dependency chain, reviews and referenced evidence objects;
   selected version effective/end dates must be real ISO calendar days, with
   exclusive end strictly after effective date. Only absent/null/empty end dates
   are open-ended; malformed nonempty values never imply unlimited validity
6. Explicit selected-chain and source-hazard review dates (`checkedAt`,
   `reviewedAt`, `reviewedOn`), when present, must parse as ISO dates/timestamps
   and must not be after asOf. Timestamp comparison uses its written calendar
   date, without timezone conversion. Missing legacy review dates are not
   inferred or newly required; explicit malformed values fail closed.
7. Safe allowlisted public text and basis fields

Unselected proposed associations are still fingerprinted but do not themselves
satisfy or defeat selected-link eligibility. An unreviewed new association first
invalidates the previous semantic review and requires fresh judgment.

`public` is exactly `{schemaVersion, asOf, records}`. `FIELDS` remains the required
field set; `PUBLIC_FIELDS` additionally allows `profileKind`, emitted only when
explicitly authored. Records have those allowlisted record fields plus:

- `recordKind: reusable_field_profile`
- `observedViolation: false`
- `sourceHazard`: source ID, title and verbatim conditions (nullable if absent)
- `bases`: selected link IDs, clause IDs, role, verbatim applicability,
  jurisdictionCode (nullable when not supplied upstream), lawVersionId, lawId,
  lawJurisdictionCode

The downstream UI must preserve these restrictions and distinguish routes.
It must never interpret inclusion, routing review, template approval, or an empty enterprise-fact
form as proof of a real violation. It must escape all text when rendering HTML.
Legal quote/detail text can be joined from the existing Gate-approved bundle by
the emitted stable IDs; private entity/review objects must not be copied wholesale.

`inventory` is private, containing profileCount, publishedCount,
excludedProfiles `{profileId, reasons}`, hazardsWithoutProfiles, and orphanReviewIds.
Do **not** bundle inventory publicly. Unknown/unreviewed/malformed profiles receive
exclusion reasons; absent profiles are inventoried by hazard ID. Malformed JSON,
non-object entity files and duplicate identities abort the entire operation.

### Aggregate validation and public release

`validate_all.py` includes blocking `check_field_profiles.py`: profile schema and
selected source-entity/evidence reference integrity. It rejects malformed JSON,
ambiguous identities, invalid profile schemas and dangling selected dependencies.
Missing upstream/profile reviews, stale semantic approvals, orphan review counts,
undetermined routes and hazards with no profile are **not** completion failures.
Passing this check certifies structural integrity only, not semantic approval or
classification coverage. Publication eligibility is still evaluated separately.

`build_unified_release.py` requires an explicit `--as-of` and uses it for both the
existing Gate and `public_projection`. Omitted `--data-version` is derived from
that date as `YYYY.MM.DD.current`; no historical date default is used. It writes only the latter's `public` object to
`data/field-profiles.json`. The public contract adds:

- `data/manifest.json.files.fieldProfiles = "data/field-profiles.json"`
- `data/manifest.json.counts.fieldProfiles` and `release.json.counts.fieldProfiles`,
  both counting only published records
- The file's SHA-256 in `site-manifest.json.fileHashes` and `checksums.json`, and
  inclusion in the deterministic business `releaseHash`

The formal frontend consumes the advertised path through `VerifiedFiles.read`
and the strict UI contract linked above. It adds optional purpose/scene selection
inside existing search and detail, with no populated onsite facts, longform
reports or automatic findings. Zero published profiles is valid;
the existing hazard, legal basis and search collections remain unchanged. No
private coverage totals, inventory, excluded IDs, drafting metadata, review
objects or evidence objects are serialized into the new payload or manifests.

The builder and verifier capture a private temporary knowledge snapshot, compare
source hashes before/after capture and against the copy, and perform all Gate,
projection and source-reference reads against that copy. Concurrent edits during
capture abort the operation. `release.json.knowledge.snapshotSha256` binds the
relevant formal JSON source snapshot; the existing `manifestSha256` and
`sourceRevision` retain their previous meanings. Normal formal snapshots exclude
the pilot. Quiescent authoring remains required during capture; this is not a
transactional database lock or a defense against malicious change-and-revert races.

`verify_unified_bundle.py` recomputes the complete profile payload at the release
date, including every allowlisted field, selected link identity/scope/role, exact
source conditions and public hazard/clause/version joins. It checks the profile
count, manifest reference, checksum coverage and source snapshot. Its strict file
allowlist rejects arbitrary additional JSON, including private inventories or pilot
records; structural private profile/review fields are rejected anywhere in JSON.

## Operational boundaries and limitations

- The production builder imports this module; formal search/detail consumes only
  its verified public projection under the separate UI contract. No real record is automatically approved. An empty profile result never
  replaces the existing public hazard bundle.
- Direct calls to `public_projection` must use a stable read-only knowledge source.
  The unified builder and verifier provide the capture mechanism described above.
- No cryptographic reviewer authentication, permissions service, review UI,
  human review, semantic legal inference or per-use fact/evidence verification is
  supplied. The trusted authoring workflow must establish reviewer authority.
- Allowlisting prevents review/drafting fields leaking. Common absolute paths
  are rejected in public fields. Automated scanning cannot identify arbitrary
  personal/company secrets written into approved prose; reviewers must check it.
- No hardcoded record count, accounts, new forms, archive/SQLite mutation,
  candidate conversion, source approval, deployment or external publishing.

## Verification

Synthetic module tests: `python -m unittest discover -s tools/pipeline/tests -p test_field_profiles.py -v`.
They cover content/revision and dependency changes, association additions/removals,
expiry, missing evidence/data, unknown/unreviewed profiles, explicit semantic
review and per-link scope, proposed isolation, non-onsite routes, public allowlists,
empty and variable inventories, duplicate IDs, malformed data and date handling.
The full governance suite runs for legacy implicit templates, explicit conditional
templates and routing-only records. Additional checks cover malformed kinds,
mandatory null routing templates, identical semantic-check requirements,
kind/private-metadata review binding, no default injection and onsite facts.

Release regression tests:
`python -m unittest discover -s tools/pipeline/tests -p test_field_profile_release.py -v`.
They cover aggregate registration, schema/reference failures, absent/unreviewed/
undetermined coverage, exact data preservation, public consumer joins, expiry,
field/link/condition/routing/type tampering, private metadata and extra-file
rejection, pilot isolation and snapshot mutation detection. This suite also runs
for all three kind representations and verifies that resealing kind/template
tampering cannot bypass the exact public projection. The existing release
reproducibility test compares all production data bytes across discovery/hash-seed
orders, including the new governed payload.
