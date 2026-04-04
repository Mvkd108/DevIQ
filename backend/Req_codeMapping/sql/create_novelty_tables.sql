-- ================================================================
-- Burnout Detection & Predictive Delivery Tables
-- For DevHouse26 Novelty Features (Option A Implementation)
-- ================================================================

-- ================================================================
-- Section 1: Burnout Detection Tables
-- ================================================================

-- Developer wellness settings (opt-out and preferences)
CREATE TABLE IF NOT EXISTS developer_wellness_settings (
  developer_id TEXT PRIMARY KEY,
  monitoring_enabled BOOLEAN DEFAULT TRUE,
  alert_notifications_enabled BOOLEAN DEFAULT TRUE,
  can_be_visible_in_hero_leaderboard BOOLEAN DEFAULT FALSE,
  preferred_contact_method TEXT DEFAULT 'email', -- email, slack, none
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Weekly burnout risk snapshots per developer
CREATE TABLE IF NOT EXISTS burnout_risk_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  developer_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  overall_score NUMERIC(5,2) NOT NULL, -- 0-100
  risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'moderate', 'high', 'critical')),
  trend TEXT CHECK (trend IN ('improving', 'stable', 'worsening')),
  
  -- Component scores
  work_pattern_score NUMERIC(5,2),
  sustainability_score NUMERIC(5,2),
  activity_score NUMERIC(5,2),
  isolation_score NUMERIC(5,2),
  
  -- Detailed data
  contributing_factors JSONB DEFAULT '[]'::JSONB,
  recommended_actions JSONB DEFAULT '[]'::JSONB,
  
  -- Metadata
  calculated_at TIMESTAMPTZ DEFAULT NOW(),
  lookback_days INTEGER DEFAULT 21,
  
  UNIQUE(developer_id, calculated_at)
);

-- Burnout alerts (for deduplication and history)
CREATE TABLE IF NOT EXISTS burnout_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  developer_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  risk_level TEXT NOT NULL,
  alert_sent_at TIMESTAMPTZ DEFAULT NOW(),
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by TEXT,
  message TEXT,
  channels JSONB DEFAULT '[]'::JSONB -- ['email', 'slack']
);

-- ================================================================
-- Section 2: Predictive Delivery Tables
-- ================================================================

-- Delivery predictions per requirement
CREATE TABLE IF NOT EXISTS delivery_predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  requirement_id TEXT NOT NULL,
  requirement_title TEXT,
  project_id TEXT,
  
  -- Prediction results
  delivery_probability NUMERIC(5,2) NOT NULL, -- 0-100
  probability_category TEXT CHECK (probability_category IN ('very_likely', 'likely', 'uncertain', 'unlikely', 'very_unlikely')),
  predicted_completion_date TIMESTAMPTZ,
  predicted_days_remaining NUMERIC(6,2),
  
  -- Timeline
  target_date TIMESTAMPTZ,
  days_until_deadline INTEGER,
  expected_delay_days NUMERIC(6,2),
  
  -- Analysis
  risk_factors JSONB DEFAULT '[]'::JSONB,
  contributing_developers JSONB DEFAULT '[]'::JSONB,
  confidence_level TEXT CHECK (confidence_level IN ('high', 'medium', 'low')),
  
  -- Explanation
  primary_risk_driver TEXT,
  recommendation TEXT,
  
  -- Metadata
  calculated_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ, -- Cache expiration
  model_version TEXT DEFAULT 'heuristic-v1',
  
  UNIQUE(requirement_id, calculated_at)
);

-- At-risk requirements tracking (for quick queries)
CREATE TABLE IF NOT EXISTS at_risk_requirements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id TEXT NOT NULL,
  requirement_id TEXT NOT NULL UNIQUE,
  requirement_title TEXT,
  delivery_probability NUMERIC(5,2),
  risk_level TEXT CHECK (risk_level IN ('critical', 'high', 'moderate')),
  detected_at TIMESTAMPTZ DEFAULT NOW(),
  last_updated_at TIMESTAMPTZ DEFAULT NOW(),
  is_acknowledged BOOLEAN DEFAULT FALSE,
  acknowledged_by TEXT,
  mitigation_plan TEXT
);

-- ================================================================
-- Section 3: Indexes for Performance
-- ================================================================

-- Burnout detection indexes
CREATE INDEX IF NOT EXISTS idx_burnout_snapshots_dev_lookup 
  ON burnout_risk_snapshots (developer_id, calculated_at DESC);

CREATE INDEX IF NOT EXISTS idx_burnout_snapshots_team_lookup 
  ON burnout_risk_snapshots (team_id, calculated_at DESC);

CREATE INDEX IF NOT EXISTS idx_burnout_snapshots_risk_level 
  ON burnout_risk_snapshots (risk_level, calculated_at DESC) 
  WHERE risk_level IN ('high', 'critical');

CREATE INDEX IF NOT EXISTS idx_burnout_alerts_dev_lookup 
  ON burnout_alerts (developer_id, alert_sent_at DESC);

-- Predictive delivery indexes
CREATE INDEX IF NOT EXISTS idx_delivery_predictions_req_lookup 
  ON delivery_predictions (requirement_id, calculated_at DESC);

CREATE INDEX IF NOT EXISTS idx_delivery_predictions_project 
  ON delivery_predictions (project_id, delivery_probability ASC);

CREATE INDEX IF NOT EXISTS idx_delivery_predictions_expires 
  ON delivery_predictions (expires_at);

CREATE INDEX IF NOT EXISTS idx_at_risk_requirements_project 
  ON at_risk_requirements (project_id, delivery_probability ASC);

-- ================================================================
-- Section 4: Views for Dashboards
-- ================================================================

-- Latest burnout risk per developer
CREATE OR REPLACE VIEW latest_burnout_risk AS
SELECT DISTINCT ON (developer_id)
  developer_id,
  team_id,
  overall_score,
  risk_level,
  trend,
  work_pattern_score,
  sustainability_score,
  activity_score,
  isolation_score,
  contributing_factors,
  recommended_actions,
  calculated_at
FROM burnout_risk_snapshots
ORDER BY developer_id, calculated_at DESC;

-- Developers needing attention (high/critical risk)
CREATE OR REPLACE VIEW developers_needing_attention AS
SELECT 
  developer_id,
  team_id,
  overall_score,
  risk_level,
  trend,
  contributing_factors,
  recommended_actions,
  calculated_at
FROM latest_burnout_risk
WHERE risk_level IN ('high', 'critical')
ORDER BY overall_score DESC;

-- Latest delivery prediction per requirement
CREATE OR REPLACE VIEW latest_delivery_predictions AS
SELECT DISTINCT ON (requirement_id)
  requirement_id,
  requirement_title,
  project_id,
  delivery_probability,
  probability_category,
  predicted_completion_date,
  target_date,
  expected_delay_days,
  risk_factors,
  confidence_level,
  primary_risk_driver,
  recommendation,
  calculated_at
FROM delivery_predictions
WHERE expires_at > NOW() OR expires_at IS NULL
ORDER BY requirement_id, calculated_at DESC;

-- At-risk requirements summary
CREATE OR REPLACE VIEW at_risk_summary AS
SELECT 
  project_id,
  COUNT(*) as total_at_risk,
  COUNT(*) FILTER (WHERE risk_level = 'critical') as critical_count,
  COUNT(*) FILTER (WHERE risk_level = 'high') as high_count,
  AVG(delivery_probability) as avg_probability,
  MAX(detected_at) as last_detection
FROM at_risk_requirements
WHERE is_acknowledged = FALSE
GROUP BY project_id;

-- ================================================================
-- Section 5: RLS Policies (Row Level Security)
-- ================================================================

-- Enable RLS
ALTER TABLE burnout_risk_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE burnout_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_predictions ENABLE ROW LEVEL SECURITY;

-- Note: Actual RLS policies depend on your auth setup
-- Template policies (customize based on your auth):

-- Developers can see their own burnout data
-- CREATE POLICY burnout_self ON burnout_risk_snapshots 
--   FOR SELECT USING (developer_id = current_setting('app.current_user_id'));

-- Managers can see team members
-- CREATE POLICY burnout_team ON burnout_risk_snapshots 
--   FOR SELECT USING (team_id IN (
--     SELECT team_id FROM team_members 
--     WHERE member_id = current_setting('app.current_user_id') AND role = 'manager'
--   ));

-- ================================================================
-- Section 6: Helper Functions
-- ================================================================

-- Function to clean up old predictions
CREATE OR REPLACE FUNCTION cleanup_expired_predictions()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM delivery_predictions 
  WHERE expires_at < NOW() - INTERVAL '7 days';
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get burnout trend for a developer
CREATE OR REPLACE FUNCTION get_burnout_trend(
  p_developer_id TEXT,
  p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
  calculated_at TIMESTAMPTZ,
  overall_score NUMERIC,
  risk_level TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    brs.calculated_at,
    brs.overall_score,
    brs.risk_level
  FROM burnout_risk_snapshots brs
  WHERE brs.developer_id = p_developer_id
    AND brs.calculated_at > NOW() - (p_days || ' days')::INTERVAL
  ORDER BY brs.calculated_at ASC;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Section 7: Verification
-- ================================================================

-- Verify tables created
-- SELECT 
--   table_name,
--   (SELECT COUNT(*) FROM information_schema.columns c WHERE c.table_name = t.table_name) as column_count
-- FROM information_schema.tables t
-- WHERE table_schema = 'public' 
--   AND table_name IN (
--     'burnout_risk_snapshots',
--     'burnout_alerts', 
--     'delivery_predictions',
--     'at_risk_requirements',
--     'developer_wellness_settings'
--   )
-- ORDER BY table_name;
