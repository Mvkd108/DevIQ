-- ============================================================================
-- Burnout Detection & Predictive Delivery Tables
-- Run this in Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Extension events from VS Code telemetry
CREATE TABLE IF NOT EXISTS extension_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    developer_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    project_id TEXT,
    team_id TEXT,
    payload JSONB DEFAULT '{}',
    source TEXT DEFAULT 'vs_code_extension',
    session_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily aggregated developer activity
CREATE TABLE IF NOT EXISTS developer_activity (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    developer_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    date DATE NOT NULL,
    commits_count INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,
    pr_reviews_count INTEGER DEFAULT 0,
    focus_sessions_count INTEGER DEFAULT 0,
    total_work_hours DECIMAL(4,2) DEFAULT 0,
    after_hours_work BOOLEAN DEFAULT FALSE,
    weekend_work BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(developer_id, date)
);

-- Team membership
CREATE TABLE IF NOT EXISTS team_members (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    developer_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    email TEXT,
    name TEXT,
    role TEXT DEFAULT 'developer',
    status TEXT DEFAULT 'active',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(developer_id, team_id)
);

-- Weekly burnout risk snapshots
CREATE TABLE IF NOT EXISTS burnout_risk_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    developer_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    overall_score DECIMAL(5,2) NOT NULL,  -- 0-100
    risk_level TEXT NOT NULL,  -- low, moderate, high, critical
    trend TEXT DEFAULT 'stable',  -- improving, stable, worsening
    work_pattern_score DECIMAL(5,2) DEFAULT 0,
    sustainability_score DECIMAL(5,2) DEFAULT 0,
    activity_score DECIMAL(5,2) DEFAULT 0,
    isolation_score DECIMAL(5,2) DEFAULT 0,
    contributing_factors JSONB DEFAULT '[]',
    recommended_actions JSONB DEFAULT '[]',
    lookback_days INTEGER DEFAULT 21,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by TEXT,
    UNIQUE(developer_id, calculated_at)
);

-- Alert history for deduplication
CREATE TABLE IF NOT EXISTS burnout_alerts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    developer_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    channel TEXT DEFAULT 'slack',  -- slack, email, etc.
    status TEXT DEFAULT 'sent',  -- sent, delivered, failed
    message TEXT,
    error TEXT
);

-- Requirements table for predictive delivery
CREATE TABLE IF NOT EXISTS requirements (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    req_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'backlog',  -- backlog, in_progress, done
    assigned_to TEXT,
    priority TEXT DEFAULT 'medium',
    story_points INTEGER,
    created_date DATE,
    target_date DATE,
    started_date DATE,
    completed_date DATE,
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Developer wellness settings (opt-out, preferences)
CREATE TABLE IF NOT EXISTS developer_wellness_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    developer_id TEXT NOT NULL UNIQUE,
    monitoring_opt_out BOOLEAN DEFAULT FALSE,
    alert_preferences JSONB DEFAULT '{"slack": true, "email": true}',
    work_hours_start TIME DEFAULT '09:00',
    work_hours_end TIME DEFAULT '17:00',
    timezone TEXT DEFAULT 'UTC',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- VIEWS
-- ============================================================================

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

-- Team burnout summary (privacy-preserving)
CREATE OR REPLACE VIEW team_burnout_summary AS
SELECT
    team_id,
    COUNT(*) as member_count,
    COUNT(*) FILTER (WHERE risk_level = 'low') as low_count,
    COUNT(*) FILTER (WHERE risk_level = 'moderate') as moderate_count,
    COUNT(*) FILTER (WHERE risk_level = 'high') as high_count,
    COUNT(*) FILTER (WHERE risk_level = 'critical') as critical_count,
    ROUND(AVG(overall_score), 2) as avg_team_score,
    MAX(calculated_at) as last_calculated
FROM latest_burnout_risk
GROUP BY team_id;

-- Developers needing attention (for manager dashboard)
CREATE OR REPLACE VIEW developers_needing_attention AS
SELECT
    developer_id,
    team_id,
    overall_score,
    risk_level,
    trend,
    recommended_actions,
    calculated_at,
    CASE
        WHEN risk_level = 'critical' THEN 1
        WHEN risk_level = 'high' THEN 2
        WHEN risk_level = 'moderate' AND trend = 'worsening' THEN 3
        ELSE 4
    END as priority_order
FROM latest_burnout_risk
WHERE risk_level IN ('high', 'critical') 
   OR (risk_level = 'moderate' AND trend = 'worsening')
ORDER BY priority_order, overall_score DESC;

-- Weekly burnout trends
CREATE OR REPLACE VIEW burnout_trend_weekly AS
SELECT
    DATE_TRUNC('week', calculated_at) as week,
    team_id,
    COUNT(*) as developers_count,
    ROUND(AVG(overall_score), 2) as avg_score,
    ROUND(AVG(work_pattern_score), 2) as avg_work_pattern,
    ROUND(AVG(sustainability_score), 2) as avg_sustainability,
    ROUND(AVG(activity_score), 2) as avg_activity,
    ROUND(AVG(isolation_score), 2) as avg_isolation
FROM burnout_risk_snapshots
GROUP BY DATE_TRUNC('week', calculated_at), team_id
ORDER BY week DESC;

-- At-risk requirements view
CREATE OR REPLACE VIEW at_risk_requirements AS
SELECT
    r.*,
    tm.name as assignee_name,
    CASE
        WHEN r.target_date < CURRENT_DATE AND r.status != 'done' THEN 'overdue'
        WHEN r.target_date < CURRENT_DATE + INTERVAL '7 days' AND r.status = 'in_progress' THEN 'at_risk'
        ELSE 'on_track'
    END as delivery_status
FROM requirements r
LEFT JOIN team_members tm ON r.assigned_to = tm.developer_id
WHERE r.status IN ('in_progress', 'backlog');

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_extension_events_dev_id ON extension_events(developer_id);
CREATE INDEX IF NOT EXISTS idx_extension_events_timestamp ON extension_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_extension_events_team_id ON extension_events(team_id);

CREATE INDEX IF NOT EXISTS idx_dev_activity_dev_id ON developer_activity(developer_id);
CREATE INDEX IF NOT EXISTS idx_dev_activity_date ON developer_activity(date);
CREATE INDEX IF NOT EXISTS idx_dev_activity_team_id ON developer_activity(team_id);

CREATE INDEX IF NOT EXISTS idx_burnout_snapshots_dev_id ON burnout_risk_snapshots(developer_id);
CREATE INDEX IF NOT EXISTS idx_burnout_snapshots_calculated ON burnout_risk_snapshots(calculated_at);
CREATE INDEX IF NOT EXISTS idx_burnout_snapshots_team_id ON burnout_risk_snapshots(team_id);

CREATE INDEX IF NOT EXISTS idx_burnout_alerts_dev_id ON burnout_alerts(developer_id);
CREATE INDEX IF NOT EXISTS idx_burnout_alerts_sent_at ON burnout_alerts(sent_at);

CREATE INDEX IF NOT EXISTS idx_team_members_dev_id ON team_members(developer_id);
CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);

CREATE INDEX IF NOT EXISTS idx_requirements_assigned ON requirements(assigned_to);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);

-- ============================================================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on tables
ALTER TABLE extension_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE developer_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE burnout_risk_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;

-- Developers can see their own data
CREATE POLICY dev_own_extension_events ON extension_events
    FOR SELECT USING (developer_id = current_setting('app.current_user_id', true));

CREATE POLICY dev_own_activity ON developer_activity
    FOR SELECT USING (developer_id = current_setting('app.current_user_id', true));

CREATE POLICY dev_own_burnout ON burnout_risk_snapshots
    FOR SELECT USING (developer_id = current_setting('app.current_user_id', true));

-- Managers can see their team data (simplified - in production use roles)
CREATE POLICY team_extension_events ON extension_events
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM team_members tm
            WHERE tm.team_id = extension_events.team_id
            AND tm.developer_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY team_activity ON developer_activity
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM team_members tm
            WHERE tm.team_id = developer_activity.team_id
            AND tm.developer_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY team_burnout ON burnout_risk_snapshots
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM team_members tm
            WHERE tm.team_id = burnout_risk_snapshots.team_id
            AND tm.developer_id = current_setting('app.current_user_id', true)
        )
    );

-- Service role can do everything (for backend)
CREATE POLICY service_all_extension_events ON extension_events
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

CREATE POLICY service_all_activity ON developer_activity
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

CREATE POLICY service_all_burnout ON burnout_risk_snapshots
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

CREATE POLICY service_all_team_members ON team_members
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_dev_activity_updated_at
    BEFORE UPDATE ON developer_activity
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wellness_settings_updated_at
    BEFORE UPDATE ON developer_wellness_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to check if alert was recently sent (cooldown)
CREATE OR REPLACE FUNCTION should_send_burnout_alert(
    p_developer_id TEXT,
    p_cooldown_hours INTEGER DEFAULT 24
)
RETURNS BOOLEAN AS $$
DECLARE
    last_alert TIMESTAMPTZ;
BEGIN
    SELECT MAX(sent_at) INTO last_alert
    FROM burnout_alerts
    WHERE developer_id = p_developer_id
    AND risk_level IN ('high', 'critical');
    
    IF last_alert IS NULL THEN
        RETURN TRUE;
    END IF;
    
    RETURN last_alert < NOW() - (p_cooldown_hours || ' hours')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE DATA (Optional - uncomment to insert test data)
-- ============================================================================

-- -- Insert sample team
-- INSERT INTO team_members (developer_id, team_id, email, name, role)
-- VALUES
--     ('dev-001', 'team-alpha', 'alice@deviq.ai', 'Alice Developer', 'developer'),
--     ('dev-002', 'team-alpha', 'bob@deviq.ai', 'Bob Coder', 'developer'),
--     ('manager-001', 'team-alpha', 'carol@deviq.ai', 'Carol Manager', 'manager');

-- -- Insert sample requirement
-- INSERT INTO requirements (req_id, title, description, assigned_to, status, story_points, target_date)
-- VALUES
--     ('REQ-001', 'Sample Feature', 'A sample requirement for testing', 'dev-001', 'in_progress', 8, CURRENT_DATE + INTERVAL '14 days');
