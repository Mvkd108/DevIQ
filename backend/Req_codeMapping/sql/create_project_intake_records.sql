CREATE TABLE IF NOT EXISTS project_intake_records (
  issue_id        TEXT PRIMARY KEY,
  title           TEXT NOT NULL,
  description     TEXT NOT NULL,
  project_key     TEXT NOT NULL,
  issue_type      TEXT,
  priority        TEXT,
  status          TEXT,
  owner_email     TEXT,
  reporter_email  TEXT,
  timeline_start  TIMESTAMPTZ,
  timeline_end    TIMESTAMPTZ,
  source          TEXT NOT NULL DEFAULT 'manual',
  submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_intake_records_project_key
  ON project_intake_records (project_key);

CREATE OR REPLACE FUNCTION update_project_intake_records_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_project_intake_records_updated_at ON project_intake_records;
CREATE TRIGGER trg_project_intake_records_updated_at
  BEFORE UPDATE ON project_intake_records
  FOR EACH ROW EXECUTE FUNCTION update_project_intake_records_updated_at();

ALTER TABLE req_code_mapping
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'jira';
