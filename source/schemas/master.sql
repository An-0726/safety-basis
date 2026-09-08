PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS db_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS migration_runs (
  id TEXT PRIMARY KEY,
  dataset_hash TEXT NOT NULL UNIQUE,
  source_commit TEXT NOT NULL,
  created_at TEXT NOT NULL,
  manifest_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  sha256 TEXT NOT NULL UNIQUE,
  original_name TEXT NOT NULL,
  media_type TEXT NOT NULL,
  byte_size INTEGER NOT NULL,
  visibility TEXT NOT NULL DEFAULT 'private',
  storage_ref TEXT NOT NULL,
  source_commit TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_locations (
  source_id TEXT NOT NULL REFERENCES sources(id),
  relative_path TEXT NOT NULL,
  PRIMARY KEY(source_id, relative_path)
);
CREATE TABLE IF NOT EXISTS batches (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(id),
  file_pointer TEXT NOT NULL,
  raw_payload TEXT NOT NULL,
  ingestion_summary TEXT,
  UNIQUE(source_id, file_pointer)
);
CREATE TABLE IF NOT EXISTS source_rows (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(id),
  sheet TEXT NOT NULL,
  row_number INTEGER NOT NULL,
  json_pointer TEXT NOT NULL,
  raw_payload TEXT NOT NULL,
  UNIQUE(source_id, json_pointer)
);
CREATE TABLE IF NOT EXISTS hazards (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  measures TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT '',
  conditions TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  mode TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL CHECK(status IN ('原始数据','待整理','待核验','已核验','已失效','merged','rejected')),
  checked TEXT NOT NULL DEFAULT '',
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  merged_into TEXT REFERENCES hazards(id),
  legacy_payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hazard_tags (
  hazard_id TEXT NOT NULL REFERENCES hazards(id),
  kind TEXT NOT NULL,
  value TEXT NOT NULL,
  ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
  PRIMARY KEY(hazard_id, kind, ordinal)
);
CREATE TABLE IF NOT EXISTS laws (
  id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  issuer TEXT NOT NULL DEFAULT '',
  jurisdiction_code TEXT NOT NULL DEFAULT '',
  document_kind TEXT NOT NULL DEFAULT '',
  identity_key TEXT NOT NULL UNIQUE,
  identity_status TEXT NOT NULL DEFAULT 'provisional' CHECK(identity_status IN ('provisional','confirmed','merged')),
  status TEXT NOT NULL DEFAULT '' CHECK(status IN ('','待整理','待核验','已核验','已失效','现行有效','即将生效','已废止')),
  checked TEXT NOT NULL DEFAULT '',
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  legacy_payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS law_aliases (
  law_id TEXT NOT NULL REFERENCES laws(id),
  alias TEXT NOT NULL,
  ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
  PRIMARY KEY(law_id, ordinal)
);
CREATE TABLE IF NOT EXISTS law_versions (
  id TEXT PRIMARY KEY,
  law_id TEXT NOT NULL REFERENCES laws(id),
  version_key TEXT NOT NULL,
  document_number TEXT NOT NULL DEFAULT '',
  official_name TEXT NOT NULL,
  level TEXT NOT NULL DEFAULT '',
  scope TEXT NOT NULL DEFAULT '',
  effective_date TEXT NOT NULL DEFAULT '',
  end_date TEXT NOT NULL DEFAULT '',
  validity_status TEXT NOT NULL DEFAULT '' CHECK(validity_status IN ('','待核验','现行有效','即将生效','已废止')),
  review_status TEXT NOT NULL DEFAULT '' CHECK(review_status IN ('','legacy_inherited','待整理','待核验','已核验','已失效')),
  source_url TEXT NOT NULL DEFAULT '',
  checked TEXT NOT NULL DEFAULT '',
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  legacy_payload TEXT NOT NULL,
  UNIQUE(law_id, version_key)
);
CREATE TABLE IF NOT EXISTS law_successions (
  old_version_id TEXT NOT NULL REFERENCES law_versions(id),
  new_version_id TEXT NOT NULL REFERENCES law_versions(id),
  relation TEXT NOT NULL,
  scope TEXT NOT NULL DEFAULT '',
  effective_date TEXT NOT NULL DEFAULT '',
  verification_id TEXT,
  PRIMARY KEY(old_version_id, new_version_id, relation)
);
CREATE TABLE IF NOT EXISTS clauses (
  id TEXT PRIMARY KEY,
  law_version_id TEXT NOT NULL REFERENCES law_versions(id),
  article_path TEXT NOT NULL,
  quote TEXT NOT NULL DEFAULT '',
  source_url TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT '' CHECK(status IN ('','待整理','待核验','已核验','已失效')),
  checked TEXT NOT NULL DEFAULT '',
  identity_status TEXT NOT NULL DEFAULT 'legacy_unreviewed' CHECK(identity_status IN ('legacy_unreviewed','unresolved','confirmed_locator')),
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  legacy_payload TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS clauses_confirmed_locator
  ON clauses(law_version_id, article_path)
  WHERE identity_status = 'confirmed_locator';
CREATE TABLE IF NOT EXISTS links (
  id TEXT PRIMARY KEY,
  hazard_id TEXT NOT NULL REFERENCES hazards(id),
  clause_id TEXT NOT NULL REFERENCES clauses(id),
  role TEXT NOT NULL DEFAULT '',
  priority INTEGER NOT NULL DEFAULT 0,
  applicability TEXT NOT NULL DEFAULT '',
  jurisdiction_code TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT '待核验' CHECK(status IN ('待整理','待核验','已核验','已失效')),
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  legacy_payload TEXT NOT NULL,
  UNIQUE(hazard_id, clause_id)
);
CREATE TABLE IF NOT EXISTS legacy_payloads (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES sources(id),
  json_pointer TEXT NOT NULL,
  raw_payload TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  batch_id TEXT REFERENCES batches(id),
  UNIQUE(source_id, json_pointer)
);
CREATE INDEX IF NOT EXISTS legacy_payload_entity ON legacy_payloads(entity_type, entity_id);
CREATE TABLE IF NOT EXISTS provenance (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  source_row_id TEXT NOT NULL REFERENCES source_rows(id),
  field_path TEXT NOT NULL,
  transform_run_id TEXT NOT NULL REFERENCES migration_runs(id),
  UNIQUE(entity_type, entity_id, source_row_id, field_path)
);
CREATE TABLE IF NOT EXISTS migration_conflicts (
  id TEXT PRIMARY KEY,
  conflict_type TEXT NOT NULL,
  identity_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unresolved',
  details_json TEXT NOT NULL,
  UNIQUE(conflict_type, identity_key)
);
CREATE TABLE IF NOT EXISTS verification (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  entity_revision INTEGER NOT NULL CHECK(entity_revision > 0),
  dependency_hash TEXT NOT NULL,
  check_type TEXT NOT NULL,
  result TEXT NOT NULL CHECK(result IN ('passed','failed','legacy_inherited','pending','not_applicable')),
  reviewer TEXT NOT NULL DEFAULT '',
  model TEXT NOT NULL DEFAULT '',
  checked_at TEXT NOT NULL DEFAULT '',
  review_due_at TEXT NOT NULL DEFAULT '',
  evidence_id TEXT,
  reason TEXT NOT NULL DEFAULT '',
  supersedes TEXT,
  FOREIGN KEY(evidence_id) REFERENCES evidence(id)
);
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY,
  official_url TEXT NOT NULL,
  retrieved_at TEXT NOT NULL DEFAULT '',
  snapshot_ref TEXT NOT NULL DEFAULT '',
  sha256 TEXT NOT NULL DEFAULT '',
  page TEXT NOT NULL DEFAULT '',
  locator TEXT NOT NULL DEFAULT ''
);

-- Excel and future UI edits are applied as immutable, reviewed change sets.
-- These tables are deliberately excluded from the logical master-state hash.
CREATE TABLE IF NOT EXISTS change_sets (
  id TEXT PRIMARY KEY,
  proposal_hash TEXT NOT NULL UNIQUE,
  base_state_hash TEXT NOT NULL,
  result_state_hash TEXT NOT NULL,
  workbook_sha256 TEXT NOT NULL,
  actor TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('applied')),
  created_at TEXT NOT NULL,
  applied_at TEXT NOT NULL,
  proposal_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS change_events (
  change_set_id TEXT NOT NULL REFERENCES change_sets(id),
  ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  base_revision INTEGER NOT NULL CHECK(base_revision > 0),
  result_revision INTEGER NOT NULL CHECK(result_revision > base_revision),
  before_json TEXT NOT NULL,
  after_json TEXT NOT NULL,
  PRIMARY KEY(change_set_id, ordinal)
);
CREATE TRIGGER IF NOT EXISTS change_sets_no_update BEFORE UPDATE ON change_sets
BEGIN SELECT RAISE(ABORT,'change sets are append-only'); END;
CREATE TRIGGER IF NOT EXISTS change_sets_no_delete BEFORE DELETE ON change_sets
BEGIN SELECT RAISE(ABORT,'change sets are append-only'); END;
CREATE TRIGGER IF NOT EXISTS change_events_no_update BEFORE UPDATE ON change_events
BEGIN SELECT RAISE(ABORT,'change events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS change_events_no_delete BEFORE DELETE ON change_events
BEGIN SELECT RAISE(ABORT,'change events are append-only'); END;

CREATE TRIGGER IF NOT EXISTS verification_target_insert
BEFORE INSERT ON verification
BEGIN
  SELECT CASE
    WHEN NEW.entity_type='hazard' AND NOT EXISTS(SELECT 1 FROM hazards WHERE id=NEW.entity_id AND revision=NEW.entity_revision) THEN RAISE(ABORT,'verification target/revision missing')
    WHEN NEW.entity_type='law' AND NOT EXISTS(SELECT 1 FROM laws WHERE id=NEW.entity_id AND revision=NEW.entity_revision) THEN RAISE(ABORT,'verification target/revision missing')
    WHEN NEW.entity_type='law_version' AND NOT EXISTS(SELECT 1 FROM law_versions WHERE id=NEW.entity_id AND revision=NEW.entity_revision) THEN RAISE(ABORT,'verification target/revision missing')
    WHEN NEW.entity_type='clause' AND NOT EXISTS(SELECT 1 FROM clauses WHERE id=NEW.entity_id AND revision=NEW.entity_revision) THEN RAISE(ABORT,'verification target/revision missing')
    WHEN NEW.entity_type='link' AND NOT EXISTS(SELECT 1 FROM links WHERE id=NEW.entity_id AND revision=NEW.entity_revision) THEN RAISE(ABORT,'verification target/revision missing')
    WHEN NEW.entity_type NOT IN ('hazard','law','law_version','clause','link') THEN RAISE(ABORT,'unknown verification entity type')
  END;
END;
CREATE TRIGGER IF NOT EXISTS verification_target_update
BEFORE UPDATE ON verification
BEGIN
  SELECT CASE
    WHEN NEW.entity_type='hazard' AND NOT EXISTS(SELECT 1 FROM hazards WHERE id=NEW.entity_id AND revision=NEW.entity_revision) THEN RAISE(ABORT,'verification target/revision missing')
    WHEN NEW.entity_type='law' AND NOT EXISTS(SELECT 1 FROM laws WHERE id=NEW.entity_id AND revision=NEW.entity_revision) THEN RAISE(ABORT,'verification target/revision missing')
    WHEN NEW.entity_type='law_version' AND NOT EXISTS(SELECT 1 FROM law_versions WHERE id=NEW.entity_id AND revision=NEW.entity_revision) THEN RAISE(ABORT,'verification target/revision missing')
    WHEN NEW.entity_type='clause' AND NOT EXISTS(SELECT 1 FROM clauses WHERE id=NEW.entity_id AND revision=NEW.entity_revision) THEN RAISE(ABORT,'verification target/revision missing')
    WHEN NEW.entity_type='link' AND NOT EXISTS(SELECT 1 FROM links WHERE id=NEW.entity_id AND revision=NEW.entity_revision) THEN RAISE(ABORT,'verification target/revision missing')
    WHEN NEW.entity_type NOT IN ('hazard','law','law_version','clause','link') THEN RAISE(ABORT,'unknown verification entity type')
  END;
END;
