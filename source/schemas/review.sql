CREATE TABLE IF NOT EXISTS review_actions (
  id TEXT PRIMARY KEY,
  proposal_hash TEXT NOT NULL UNIQUE,
  base_state_hash TEXT NOT NULL,
  result_state_hash TEXT NOT NULL,
  actor TEXT NOT NULL,
  applied_at TEXT NOT NULL,
  proposal_json TEXT NOT NULL,
  result_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verification_details (
  verification_id TEXT PRIMARY KEY REFERENCES verification(id),
  locator TEXT NOT NULL,
  public_fields_reviewed INTEGER NOT NULL CHECK(public_fields_reviewed IN (0,1)),
  action_id TEXT NOT NULL REFERENCES review_actions(id)
);
CREATE TRIGGER IF NOT EXISTS review_actions_no_update BEFORE UPDATE ON review_actions
BEGIN SELECT RAISE(ABORT,'review actions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS review_actions_no_delete BEFORE DELETE ON review_actions
BEGIN SELECT RAISE(ABORT,'review actions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS verification_no_update BEFORE UPDATE ON verification
BEGIN SELECT RAISE(ABORT,'verification is append-only'); END;
CREATE TRIGGER IF NOT EXISTS verification_no_delete BEFORE DELETE ON verification
BEGIN SELECT RAISE(ABORT,'verification is append-only'); END;
CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON evidence
BEGIN SELECT RAISE(ABORT,'evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON evidence
BEGIN SELECT RAISE(ABORT,'evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS verification_details_no_update BEFORE UPDATE ON verification_details
BEGIN SELECT RAISE(ABORT,'verification details are append-only'); END;
CREATE TRIGGER IF NOT EXISTS verification_details_no_delete BEFORE DELETE ON verification_details
BEGIN SELECT RAISE(ABORT,'verification details are append-only'); END;
