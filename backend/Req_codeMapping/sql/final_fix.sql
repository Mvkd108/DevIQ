-- ============================================================================
-- FINAL FIX: Create requirements table and add any missing columns
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

-- Add missing columns to extension_events (if not exist)
ALTER TABLE extension_events 
ADD COLUMN IF NOT EXISTS team_id TEXT;

ALTER TABLE extension_events 
ADD COLUMN IF NOT EXISTS payload JSONB DEFAULT '{}'::jsonb;

-- Add missing columns to team_members (if not exist)
ALTER TABLE team_members 
ADD COLUMN IF NOT EXISTS email TEXT;

ALTER TABLE team_members 
ADD COLUMN IF NOT EXISTS name TEXT;

-- Add missing columns to developer_activity (if not exist)
ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS after_hours_work BOOLEAN DEFAULT FALSE;

ALTER TABLE developer_activity 
ADD COLUMN IF NOT EXISTS weekend_work BOOLEAN DEFAULT FALSE;

-- Create indexes for requirements
CREATE INDEX IF NOT EXISTS idx_requirements_assigned ON requirements(assigned_to);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);
CREATE INDEX IF NOT EXISTS idx_requirements_req_id ON requirements(req_id);

-- Create index for extension_events team_id
CREATE INDEX IF NOT EXISTS idx_extension_events_team_id ON extension_events(team_id);
