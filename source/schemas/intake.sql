PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  sha256 TEXT NOT NULL UNIQUE,
  archive_path TEXT NOT NULL,
  byte_size INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT '原始数据' CHECK(status = '原始数据')
);
CREATE TABLE IF NOT EXISTS source_locations (
  source_id TEXT NOT NULL REFERENCES sources(id),
  original_path TEXT NOT NULL,
  PRIMARY KEY(source_id, original_path)
);
CREATE TABLE IF NOT EXISTS import_runs (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(id),
  parser_version TEXT NOT NULL,
  mapping_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('complete','rejected')),
  row_count INTEGER NOT NULL,
  error TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_rows (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(id),
  sheet TEXT NOT NULL,
  row_number INTEGER NOT NULL,
  raw_json TEXT NOT NULL,
  UNIQUE(source_id, sheet, row_number)
);
CREATE TABLE IF NOT EXISTS candidates (
  id TEXT PRIMARY KEY,
  fingerprint TEXT NOT NULL UNIQUE,
  normalized_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT '待整理' CHECK(status = '待整理')
);
CREATE TABLE IF NOT EXISTS candidate_sources (
  candidate_id TEXT NOT NULL REFERENCES candidates(id),
  source_row_id TEXT NOT NULL REFERENCES source_rows(id),
  run_id TEXT NOT NULL REFERENCES import_runs(id),
  PRIMARY KEY(candidate_id, source_row_id, run_id)
);
CREATE INDEX IF NOT EXISTS candidate_sources_row ON candidate_sources(source_row_id);
CREATE TABLE IF NOT EXISTS parsed_rows (
  run_id TEXT NOT NULL REFERENCES import_runs(id),
  source_row_id TEXT NOT NULL REFERENCES source_rows(id),
  raw_json TEXT NOT NULL,
  PRIMARY KEY(run_id, source_row_id)
);
