-- ================================================================
-- DevHouse / DevPulse — extension_events table
-- Includes the active telemetry payload shape used by the VS Code
-- extension, including background_apps.
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

ALTER TABLE extension_events
  ADD COLUMN IF NOT EXISTS event_type             TEXT         NOT NULL DEFAULT 'commit_event',
  ADD COLUMN IF NOT EXISTS schema_version         TEXT         NOT NULL DEFAULT '1.1',
  ADD COLUMN IF NOT EXISTS developer_id           TEXT,
  ADD COLUMN IF NOT EXISTS commit_id              TEXT,
  ADD COLUMN IF NOT EXISTS author                 TEXT,
  ADD COLUMN IF NOT EXISTS author_email           TEXT,
  ADD COLUMN IF NOT EXISTS message                TEXT,
  ADD COLUMN IF NOT EXISTS repository_owner       TEXT,
  ADD COLUMN IF NOT EXISTS repository_name        TEXT,
  ADD COLUMN IF NOT EXISTS timestamp              TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS branch                 TEXT,
  ADD COLUMN IF NOT EXISTS additions              INTEGER      NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS deletions              INTEGER      NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS commit_type            TEXT,
  ADD COLUMN IF NOT EXISTS parent_commit_id       TEXT,
  ADD COLUMN IF NOT EXISTS commit_category        TEXT,
  ADD COLUMN IF NOT EXISTS commit_message_length  INTEGER,
  ADD COLUMN IF NOT EXISTS total_changes          INTEGER      NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS commit_size            INTEGER      NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS is_merge_commit        BOOLEAN      NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS linked_issue           TEXT,
  ADD COLUMN IF NOT EXISTS issue_id               TEXT,
  ADD COLUMN IF NOT EXISTS pull_request_number    INTEGER,
  ADD COLUMN IF NOT EXISTS pr_title               TEXT,
  ADD COLUMN IF NOT EXISTS pr_labels              JSONB        NOT NULL DEFAULT '[]'::JSONB,
  ADD COLUMN IF NOT EXISTS files                  JSONB        NOT NULL DEFAULT '[]'::JSONB,
  ADD COLUMN IF NOT EXISTS files_changed_count    INTEGER      NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS net_loc                INTEGER      NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS diff_patch             TEXT,
  ADD COLUMN IF NOT EXISTS files_json             JSONB        NOT NULL DEFAULT '{}'::JSONB,
  ADD COLUMN IF NOT EXISTS modules_touched        JSONB        NOT NULL DEFAULT '[]'::JSONB,
  ADD COLUMN IF NOT EXISTS background_apps        JSONB        NOT NULL DEFAULT '[]'::JSONB,
  ADD COLUMN IF NOT EXISTS attendance_pct         NUMERIC(5,2),
  ADD COLUMN IF NOT EXISTS presence_total_checks  INTEGER,
  ADD COLUMN IF NOT EXISTS presence_present_count INTEGER,
  ADD COLUMN IF NOT EXISTS session_duration_secs  INTEGER,
  ADD COLUMN IF NOT EXISTS session_start          TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS active_minutes         INTEGER      NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS idle_minutes           INTEGER,
  ADD COLUMN IF NOT EXISTS focus_ratio            NUMERIC(6,3),
  ADD COLUMN IF NOT EXISTS debug_session_count    INTEGER,
  ADD COLUMN IF NOT EXISTS created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW();

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
