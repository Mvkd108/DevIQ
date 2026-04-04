-- ============================================================================
-- CREATE MISSING TABLES ONLY
-- Run this in Supabase SQL Editor
-- ============================================================================

-- Create requirements table (missing)
CREATE TABLE IF NOT EXISTS requirements (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    req_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'backlog',
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

-- Create extension_events table if missing
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

-- Create indexes for requirements
CREATE INDEX IF NOT EXISTS idx_requirements_assigned ON requirements(assigned_to);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);
CREATE INDEX IF NOT EXISTS idx_requirements_req_id ON requirements(req_id);

-- Create indexes for extension_events
CREATE INDEX IF NOT EXISTS idx_extension_events_dev_id ON extension_events(developer_id);
CREATE INDEX IF NOT EXISTS idx_extension_events_timestamp ON extension_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_extension_events_team_id ON extension_events(team_id);
