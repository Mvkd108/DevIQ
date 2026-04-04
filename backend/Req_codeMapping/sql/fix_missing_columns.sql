-- ============================================================================
-- FIX: Add missing columns to existing tables
-- Run this in Supabase SQL Editor
-- ============================================================================

-- Fix developer_activity table - add missing columns
ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS date DATE;

ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS commits_count INTEGER DEFAULT 0;

ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS lines_added INTEGER DEFAULT 0;

ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS lines_deleted INTEGER DEFAULT 0;

ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS pr_reviews_count INTEGER DEFAULT 0;

ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS focus_sessions_count INTEGER DEFAULT 0;

ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS total_work_hours DECIMAL(4,2) DEFAULT 0;

ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS after_hours_work BOOLEAN DEFAULT FALSE;

ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS weekend_work BOOLEAN DEFAULT FALSE;

-- Fix team_members table - add missing columns
ALTER TABLE team_members 
ADD COLUMN IF NOT EXISTS email TEXT;

ALTER TABLE team_members 
ADD COLUMN IF NOT EXISTS name TEXT;

-- Fix requirements table - add missing columns
ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS req_id TEXT UNIQUE;

ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS title TEXT;

ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS description TEXT;

ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'backlog';

ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS assigned_to TEXT;

ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT 'medium';

ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS story_points INTEGER;

ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS created_date DATE;

ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS target_date DATE;

ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS started_date DATE;

ALTER TABLE requirements 
ADD COLUMN IF NOT EXISTS completed_date DATE;

-- Fix extension_events table - add missing columns
ALTER TABLE extension_events 
ADD COLUMN IF NOT EXISTS team_id TEXT;

ALTER TABLE extension_events 
ADD COLUMN IF NOT EXISTS payload JSONB DEFAULT '{}';

ALTER TABLE extension_events 
ADD COLUMN IF NOT EXISTS project_id TEXT;

ALTER TABLE extension_events 
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'vs_code_extension';

ALTER TABLE extension_events 
ADD COLUMN IF NOT EXISTS session_id TEXT;

-- ============================================================================
-- CREATE INDEXES
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
CREATE INDEX IF NOT EXISTS idx_requirements_req_id ON requirements(req_id);

-- ============================================================================
-- VERIFY TABLES EXIST
-- ============================================================================

-- If requirements table doesn't have proper constraints, fix them
DO $$
BEGIN
    -- Make req_id not null if it exists and has data
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'requirements' AND column_name = 'req_id') THEN
        -- Add constraint if not exists
        IF NOT EXISTS (SELECT 1 FROM pg_constraint 
                       WHERE conname = 'requirements_req_id_unique') THEN
            ALTER TABLE requirements ADD CONSTRAINT requirements_req_id_unique UNIQUE (req_id);
        END IF;
    END IF;
END $$;
