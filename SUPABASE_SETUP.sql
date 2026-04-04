-- ================================================================
-- DEVHOUSE26 SUPABASE SETUP - SINGLE FILE
-- Copy this ENTIRE file and paste into Supabase SQL Editor
-- Run it ONCE - tables will be created in correct order
-- ================================================================

-- ================================================================
-- STEP 1: Create the core requirement-to-code mapping table
-- This is the FOUNDATION - must be first
-- ================================================================

CREATE TABLE IF NOT EXISTS req_code_mapping (
  issue_id        VARCHAR(50)   PRIMARY KEY,
  title           TEXT          NOT NULL,
  description     TEXT,
  status          VARCHAR(50),
  issue_type      VARCHAR(50),
  priority        VARCHAR(20),
  project_key     VARCHAR(50),
  assignee_email  VARCHAR(255),
  reporter_email  VARCHAR(255),
  jira_created_at TIMESTAMPTZ,
  jira_updated_at TIMESTAMPTZ,
  commits         JSONB         NOT NULL DEFAULT '[]'::JSONB,
  source          TEXT          NOT NULL DEFAULT 'jira',
  created_at      TIMESTAMPTZ   DEFAULT NOW(),
  updated_at      TIMESTAMPTZ   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rcm_status   ON req_code_mapping (status);
CREATE INDEX IF NOT EXISTS idx_rcm_project  ON req_code_mapping (project_key);
CREATE INDEX IF NOT EXISTS idx_rcm_commits_gin ON req_code_mapping USING GIN (commits);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_rcm_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_rcm_updated_at ON req_code_mapping;
CREATE TRIGGER trg_rcm_updated_at
  BEFORE UPDATE ON req_code_mapping
  FOR EACH ROW EXECUTE FUNCTION update_rcm_updated_at();

-- Helper: safely append a commit to a requirement (idempotent)
CREATE OR REPLACE FUNCTION append_commit_to_req(
  p_issue_id    TEXT,
  p_commit_hash TEXT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE req_code_mapping
  SET commits = commits || to_jsonb(p_commit_hash)
  WHERE issue_id = p_issue_id
    AND NOT (commits @> to_jsonb(p_commit_hash));
END;
$$;

-- ================================================================
-- STEP 2: Create VS Code extension events table
-- Stores telemetry and commit data from developers
-- ================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS extension_events (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type             TEXT         NOT NULL DEFAULT 'commit_event',
  schema_version         TEXT         NOT NULL DEFAULT '1.1',
  developer_id           TEXT         NOT NULL,
  commit_id              TEXT         NOT NULL,
  author                 TEXT         NOT NULL,
  author_email           TEXT,
  message                TEXT         NOT NULL,
  repository_owner       TEXT,
  repository_name        TEXT         NOT NULL,
  timestamp              TIMESTAMPTZ  NOT NULL,
  branch                 TEXT,
  additions              INTEGER      NOT NULL DEFAULT 0,
  deletions              INTEGER      NOT NULL DEFAULT 0,
  commit_type            TEXT,
  parent_commit_id       TEXT,
  commit_category        TEXT,
  commit_message_length  INTEGER,
  total_changes          INTEGER      NOT NULL DEFAULT 0,
  commit_size            INTEGER      NOT NULL DEFAULT 0,
  is_merge_commit        BOOLEAN      NOT NULL DEFAULT FALSE,
  linked_issue           TEXT,
  issue_id               TEXT,
  pull_request_number    INTEGER,
  pr_title               TEXT,
  pr_labels              JSONB        NOT NULL DEFAULT '[]'::JSONB,
  files                  JSONB        NOT NULL DEFAULT '[]'::JSONB,
  files_changed_count    INTEGER      NOT NULL DEFAULT 0,
  net_loc                INTEGER      NOT NULL DEFAULT 0,
  diff_patch             TEXT,
  files_json             JSONB        NOT NULL DEFAULT '{}'::JSONB,
  modules_touched        JSONB        NOT NULL DEFAULT '[]'::JSONB,
  background_apps        JSONB        NOT NULL DEFAULT '[]'::JSONB,
  attendance_pct         NUMERIC(5,2),
  presence_total_checks  INTEGER,
  presence_present_count INTEGER,
  session_duration_secs  INTEGER,
  session_start          TIMESTAMPTZ,
  active_minutes         INTEGER      NOT NULL DEFAULT 0,
  idle_minutes           INTEGER,
  focus_ratio            NUMERIC(6,3),
  debug_session_count    INTEGER,
  created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_extension_events_identity
  ON extension_events (commit_id, developer_id, repository_name);

CREATE INDEX IF NOT EXISTS idx_extension_events_timestamp
  ON extension_events (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_extension_events_issue_id
  ON extension_events (issue_id);

CREATE INDEX IF NOT EXISTS idx_extension_events_background_apps_gin
  ON extension_events USING GIN (background_apps);

CREATE INDEX IF NOT EXISTS idx_extension_events_modules_touched_gin
  ON extension_events USING GIN (modules_touched);

CREATE INDEX IF NOT EXISTS idx_extension_events_files_json_gin
  ON extension_events USING GIN (files_json);

CREATE OR REPLACE FUNCTION update_extension_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_extension_events_updated_at ON extension_events;
CREATE TRIGGER trg_extension_events_updated_at
  BEFORE UPDATE ON extension_events
  FOR EACH ROW EXECUTE FUNCTION update_extension_events_updated_at();

-- ================================================================
-- STEP 3: Create mapping feedback table
-- Stores human reviews of AI commit-to-issue matches
-- ================================================================

CREATE TABLE IF NOT EXISTS mapping_feedback (
  commit_id            TEXT PRIMARY KEY,
  feedback_type        TEXT NOT NULL CHECK (feedback_type IN ('approved', 'rejected', 'reassigned', 'cleared')),
  predicted_issue_id   TEXT,
  corrected_issue_id   TEXT,
  reviewed_by          TEXT NOT NULL,
  reviewed_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mapping_feedback_reviewed_at
  ON mapping_feedback (reviewed_at DESC);

CREATE OR REPLACE FUNCTION update_mapping_feedback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_mapping_feedback_updated_at ON mapping_feedback;
CREATE TRIGGER trg_mapping_feedback_updated_at
  BEFORE UPDATE ON mapping_feedback
  FOR EACH ROW EXECUTE FUNCTION update_mapping_feedback_updated_at();

-- ================================================================
-- STEP 4: Create project intake records table
-- Stores manual requirements entered via dashboard
-- ================================================================

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

-- ================================================================
-- STEP 5: Create analytics snapshots table
-- Caches dashboard data for fast loading
-- ================================================================

CREATE TABLE IF NOT EXISTS analytics_snapshots (
  snapshot_key TEXT PRIMARY KEY,
  scope_type TEXT NOT NULL DEFAULT 'global',
  scope_id TEXT NOT NULL DEFAULT 'dashboard',
  payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS analytics_snapshots_generated_at_idx
  ON analytics_snapshots (generated_at DESC);

CREATE INDEX IF NOT EXISTS analytics_snapshots_payload_gin_idx
  ON analytics_snapshots USING GIN (payload);

-- ================================================================
-- VERIFICATION: Check that all tables were created
-- Run these queries to verify setup worked
-- ================================================================

-- Check tables exist:
-- SELECT table_name FROM information_schema.tables 
-- WHERE table_schema = 'public' 
-- ORDER BY table_name;

-- Expected result:
-- analytics_snapshots
-- extension_events
-- mapping_feedback
-- project_intake_records
-- req_code_mapping

-- ================================================================
-- RLS (Row Level Security) - OPTIONAL but recommended for production
-- Uncomment and customize if needed:
-- ================================================================

-- -- Enable RLS on tables:
-- ALTER TABLE req_code_mapping ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE extension_events ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE mapping_feedback ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE project_intake_records ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE analytics_snapshots ENABLE ROW LEVEL SECURITY;

-- -- Create policy to allow all operations for authenticated service role:
-- CREATE POLICY service_all ON req_code_mapping FOR ALL USING (true);
-- CREATE POLICY service_all ON extension_events FOR ALL USING (true);
-- CREATE POLICY service_all ON mapping_feedback FOR ALL USING (true);
-- CREATE POLICY service_all ON project_intake_records FOR ALL USING (true);
-- CREATE POLICY service_all ON analytics_snapshots FOR ALL USING (true);

-- ================================================================
-- SETUP COMPLETE!
-- ================================================================
