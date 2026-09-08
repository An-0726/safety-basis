-- Append-only audit records for catalog-v1 requests.  The business rows stay
-- in master.sql; this schema is installed by catalog.apply inside its write
-- transaction so a partially applied proposal cannot leave an audit record.
CREATE TABLE IF NOT EXISTS catalog_actions (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL UNIQUE,
  proposal_hash TEXT NOT NULL UNIQUE,
  base_state_hash TEXT NOT NULL,
  result_state_hash TEXT NOT NULL,
  actor TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('applied')),
  created_at TEXT NOT NULL,
  applied_at TEXT NOT NULL,
  request_json TEXT NOT NULL,
  proposal_json TEXT NOT NULL,
  receipt_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS catalog_events (
  action_id TEXT NOT NULL REFERENCES catalog_actions(id),
  ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  operation TEXT NOT NULL,
  source_json TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT NOT NULL,
  PRIMARY KEY(action_id, ordinal)
);

CREATE TRIGGER IF NOT EXISTS catalog_actions_no_update
BEFORE UPDATE ON catalog_actions
BEGIN SELECT RAISE(ABORT,'catalog actions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS catalog_actions_no_delete
BEFORE DELETE ON catalog_actions
BEGIN SELECT RAISE(ABORT,'catalog actions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS catalog_events_no_update
BEFORE UPDATE ON catalog_events
BEGIN SELECT RAISE(ABORT,'catalog events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS catalog_events_no_delete
BEFORE DELETE ON catalog_events
BEGIN SELECT RAISE(ABORT,'catalog events are append-only'); END;
