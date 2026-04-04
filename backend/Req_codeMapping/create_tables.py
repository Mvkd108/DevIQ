#!/usr/bin/env python3
"""
Execute SQL schema for Burnout Detection tables in Supabase
"""

import os
import sys
import asyncio

# Supabase credentials
SUPABASE_URL = "https://jkwubrrronkyfpmdlvwd.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imprd3VicnJyb25reWZwbWRsdndkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTIwMTgyMCwiZXhwIjoyMDkwNzc3ODIwfQ.C7tkTm7xTYHEd266omj3F1b1FgImqb8wgc3t4DRniIc"

SQL_STATEMENTS = """
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
    overall_score DECIMAL(5,2) NOT NULL,
    risk_level TEXT NOT NULL,
    trend TEXT DEFAULT 'stable',
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
    channel TEXT DEFAULT 'slack',
    status TEXT DEFAULT 'sent',
    message TEXT,
    error TEXT
);

-- Requirements table for predictive delivery
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

-- Create indexes
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
"""

import httpx

async def execute_sql():
    """Execute SQL using Supabase Management API"""
    
    print("=" * 80)
    print("CREATING BURNOUT DETECTION TABLES IN SUPABASE")
    print("=" * 80)
    
    # Supabase Management API endpoint
    project_ref = "jkwubrrronkyfpmdlvwd"
    
    # Use Supabase REST API with service role to execute SQL
    url = f"{SUPABASE_URL}/rest/v1/"
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    # Split SQL into individual statements
    statements = [s.strip() for s in SQL_STATEMENTS.split(';') if s.strip()]
    
    print(f"\nFound {len(statements)} SQL statements to execute")
    print("\nNote: Direct SQL execution via REST API requires special setup.")
    print("\nALTERNATIVE: Please copy and run the following SQL in Supabase SQL Editor:")
    print("-" * 80)
    print(SQL_STATEMENTS)
    print("-" * 80)
    
    print("\n" + "=" * 80)
    print("MANUAL STEPS REQUIRED:")
    print("=" * 80)
    print("\n1. Go to https://supabase.com/dashboard")
    print("2. Select project: jkwubrrronkyfpmdlvwd")
    print("3. Go to SQL Editor (left sidebar)")
    print("4. Click 'New Query'")
    print("5. Copy the SQL above (between the dashed lines)")
    print("6. Paste into the SQL Editor")
    print("7. Click 'Run'")
    print("\nOnce done, run: python generate_test_profiles.py")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(execute_sql())
