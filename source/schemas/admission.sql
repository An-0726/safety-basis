-- Additive schema installed only inside a successful admission/merge transaction.
CREATE TABLE IF NOT EXISTS master_actions (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN ('admit','merge')),
  proposal_hash TEXT NOT NULL UNIQUE,
  base_state_hash TEXT NOT NULL,
  result_state_hash TEXT NOT NULL,
  actor TEXT NOT NULL,
  applied_at TEXT NOT NULL,
  proposal_json TEXT NOT NULL,
  result_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS intake_runs (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(id),
  parser_version TEXT NOT NULL,
  mapping_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status='complete'),
  row_count INTEGER NOT NULL,
  error TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS intake_candidates (
  id TEXT PRIMARY KEY,
  fingerprint TEXT NOT NULL UNIQUE,
  normalized_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidate_admissions (
  candidate_id TEXT NOT NULL REFERENCES intake_candidates(id),
  hazard_id TEXT NOT NULL REFERENCES hazards(id),
  action_id TEXT NOT NULL REFERENCES master_actions(id),
  PRIMARY KEY(candidate_id, hazard_id)
);
CREATE TABLE IF NOT EXISTS intake_derivations (
  id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL REFERENCES intake_candidates(id),
  hazard_id TEXT NOT NULL REFERENCES hazards(id),
  kind TEXT NOT NULL CHECK(kind='rule_template'),
  source_result TEXT NOT NULL,
  reviewed_basis TEXT NOT NULL,
  reviewed_quote TEXT NOT NULL,
  template_json TEXT NOT NULL,
  reason TEXT NOT NULL,
  action_id TEXT NOT NULL REFERENCES master_actions(id)
);
CREATE TABLE IF NOT EXISTS intake_parsed_rows (
  run_id TEXT NOT NULL REFERENCES intake_runs(id),
  source_row_id TEXT NOT NULL REFERENCES source_rows(id),
  raw_json TEXT NOT NULL,
  PRIMARY KEY(run_id, source_row_id)
);
CREATE TABLE IF NOT EXISTS intake_source_locations (
  source_id TEXT NOT NULL REFERENCES sources(id),
  original_path TEXT NOT NULL,
  PRIMARY KEY(source_id, original_path)
);
CREATE TABLE IF NOT EXISTS intake_provenance (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL CHECK(entity_type='hazard'),
  entity_id TEXT NOT NULL REFERENCES hazards(id),
  source_row_id TEXT NOT NULL REFERENCES source_rows(id),
  field_path TEXT NOT NULL DEFAULT '/',
  transform_run_id TEXT NOT NULL REFERENCES intake_runs(id),
  candidate_id TEXT NOT NULL REFERENCES intake_candidates(id),
  action_id TEXT NOT NULL REFERENCES master_actions(id),
  UNIQUE(entity_id, candidate_id, source_row_id, transform_run_id)
);
CREATE TABLE IF NOT EXISTS merge_decisions (
  id TEXT PRIMARY KEY REFERENCES master_actions(id),
  source_id TEXT NOT NULL REFERENCES hazards(id),
  target_id TEXT NOT NULL REFERENCES hazards(id),
  reason TEXT NOT NULL,
  source_revision INTEGER NOT NULL,
  target_revision INTEGER NOT NULL,
  CHECK(source_id <> target_id)
);
CREATE TRIGGER IF NOT EXISTS master_actions_no_update BEFORE UPDATE ON master_actions
BEGIN SELECT RAISE(ABORT,'master actions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS master_actions_no_delete BEFORE DELETE ON master_actions
BEGIN SELECT RAISE(ABORT,'master actions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS merge_decisions_no_update BEFORE UPDATE ON merge_decisions
BEGIN SELECT RAISE(ABORT,'merge decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS merge_decisions_no_delete BEFORE DELETE ON merge_decisions
BEGIN SELECT RAISE(ABORT,'merge decisions are append-only'); END;
