-- ================================================================
-- DevHouse26 Connector Tables
-- Stores cached data from GitHub/GitLab/Bitbucket connectors
-- and tracks sync state for incremental updates
-- ================================================================

-- ================================================================
-- Table 1: Cached Pull Requests from connectors
-- ================================================================
CREATE TABLE IF NOT EXISTS connector_pull_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL CHECK (provider IN ('github', 'gitlab', 'bitbucket')),
  repo_owner TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  pr_id TEXT NOT NULL,
  pr_number INTEGER,
  title TEXT,
  status TEXT CHECK (status IN ('open', 'closed', 'merged', 'draft')),
  is_draft BOOLEAN DEFAULT FALSE,
  is_merged BOOLEAN DEFAULT FALSE,
  author TEXT,
  source_branch TEXT,
  target_branch TEXT,
  head_commit_sha TEXT,
  created_at TIMESTAMPTZ,
  merged_at TIMESTAMPTZ,
  url TEXT,
  raw_data JSONB DEFAULT '{}'::JSONB,
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(provider, repo_owner, repo_name, pr_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_connector_prs_repo 
  ON connector_pull_requests (provider, repo_owner, repo_name);
CREATE INDEX IF NOT EXISTS idx_connector_prs_status 
  ON connector_pull_requests (status);
CREATE INDEX IF NOT EXISTS idx_connector_prs_commit_sha 
  ON connector_pull_requests (head_commit_sha);
CREATE INDEX IF NOT EXISTS idx_connector_prs_raw_data_gin 
  ON connector_pull_requests USING GIN (raw_data);

COMMENT ON TABLE connector_pull_requests IS 'Cached pull requests from Git providers';

-- ================================================================
-- Table 2: Cached CI/CD Runs from connectors
-- ================================================================
CREATE TABLE IF NOT EXISTS connector_ci_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL CHECK (provider IN ('github', 'gitlab', 'bitbucket')),
  repo_owner TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  run_id TEXT NOT NULL,
  run_number INTEGER,
  name TEXT,
  status TEXT CHECK (status IN ('success', 'failure', 'pending', 'running', 'cancelled')),
  conclusion TEXT,
  commit_sha TEXT,
  branch TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  url TEXT,
  raw_data JSONB DEFAULT '{}'::JSONB,
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(provider, repo_owner, repo_name, run_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_connector_ci_repo 
  ON connector_ci_runs (provider, repo_owner, repo_name);
CREATE INDEX IF NOT EXISTS idx_connector_ci_status 
  ON connector_ci_runs (status);
CREATE INDEX IF NOT EXISTS idx_connector_ci_commit_sha 
  ON connector_ci_runs (commit_sha);
CREATE INDEX IF NOT EXISTS idx_connector_ci_branch 
  ON connector_ci_runs (branch);
CREATE INDEX IF NOT EXISTS idx_connector_ci_raw_data_gin 
  ON connector_ci_runs USING GIN (raw_data);

COMMENT ON TABLE connector_ci_runs IS 'Cached CI/CD runs from Git providers';

-- ================================================================
-- Table 3: Cached Deployments from connectors
-- ================================================================
CREATE TABLE IF NOT EXISTS connector_deployments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL CHECK (provider IN ('github', 'gitlab', 'bitbucket')),
  repo_owner TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  deployment_id TEXT NOT NULL,
  status TEXT CHECK (status IN ('success', 'failure', 'pending', 'in_progress')),
  environment TEXT,
  commit_sha TEXT,
  deployed_at TIMESTAMPTZ,
  url TEXT,
  raw_data JSONB DEFAULT '{}'::JSONB,
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(provider, repo_owner, repo_name, deployment_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_connector_deployments_repo 
  ON connector_deployments (provider, repo_owner, repo_name);
CREATE INDEX IF NOT EXISTS idx_connector_deployments_status 
  ON connector_deployments (status);
CREATE INDEX IF NOT EXISTS idx_connector_deployments_env 
  ON connector_deployments (environment);
CREATE INDEX IF NOT EXISTS idx_connector_deployments_commit_sha 
  ON connector_deployments (commit_sha);
CREATE INDEX IF NOT EXISTS idx_connector_deployments_raw_data_gin 
  ON connector_deployments USING GIN (raw_data);

COMMENT ON TABLE connector_deployments IS 'Cached deployment records from Git providers';

-- ================================================================
-- Table 4: Sync State Tracking
-- Tracks incremental sync progress and cursor state
-- ================================================================
CREATE TABLE IF NOT EXISTS connector_sync_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  repo_owner TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('prs', 'ci_runs', 'deployments')),
  last_synced_at TIMESTAMPTZ,
  cursor_data JSONB DEFAULT '{}'::JSONB,
  status TEXT DEFAULT 'idle' CHECK (status IN ('idle', 'running', 'completed', 'failed', 'rate_limited')),
  error_message TEXT,
  records_synced INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(provider, repo_owner, repo_name, entity_type)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_connector_sync_repo 
  ON connector_sync_state (provider, repo_owner, repo_name);
CREATE INDEX IF NOT EXISTS idx_connector_sync_status 
  ON connector_sync_state (status);
CREATE INDEX IF NOT EXISTS idx_connector_sync_last_sync 
  ON connector_sync_state (last_synced_at);
CREATE INDEX IF NOT EXISTS idx_connector_sync_cursor_gin 
  ON connector_sync_state USING GIN (cursor_data);

COMMENT ON TABLE connector_sync_state IS 'Tracks sync progress and cursor state for incremental updates';

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_connector_sync_state_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_connector_sync_state_updated_at ON connector_sync_state;
CREATE TRIGGER trg_connector_sync_state_updated_at
  BEFORE UPDATE ON connector_sync_state
  FOR EACH ROW EXECUTE FUNCTION update_connector_sync_state_updated_at();

-- ================================================================
-- Verification Query (run after setup)
-- ================================================================
-- SELECT table_name, 
--        (SELECT COUNT(*) FROM information_schema.columns 
--         WHERE table_name = t.table_name) as column_count
-- FROM information_schema.tables t
-- WHERE table_schema = 'public' 
--   AND table_name LIKE 'connector_%'
-- ORDER BY table_name;
