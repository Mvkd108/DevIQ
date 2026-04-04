-- SQL Schema for Code Complexity Analysis
-- Run this in Supabase SQL Editor

-- Table to store commit complexity analysis results
CREATE TABLE IF NOT EXISTS commit_complexity_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commit_id TEXT NOT NULL,
    repository_name TEXT NOT NULL,
    author TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Complexity metrics
    files_changed INTEGER DEFAULT 0,
    total_complexity_delta FLOAT DEFAULT 0,
    max_file_complexity FLOAT DEFAULT 0,
    
    -- Impact assessment
    architectural_impact TEXT DEFAULT 'low', -- low, medium, high, critical
    complexity_trend TEXT DEFAULT 'stable', -- decreased, stable, increased
    
    -- Per-file breakdown (JSONB for flexibility)
    file_metrics JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_commit_analysis UNIQUE (commit_id)
);

-- Table to store file-level complexity snapshots
CREATE TABLE IF NOT EXISTS file_complexity_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path TEXT NOT NULL,
    repository_name TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    
    -- Language detection
    language TEXT NOT NULL,
    
    -- Basic metrics
    lines_of_code INTEGER DEFAULT 0,
    blank_lines INTEGER DEFAULT 0,
    comment_lines INTEGER DEFAULT 0,
    
    -- Complexity metrics
    cyclomatic_complexity INTEGER DEFAULT 0,
    cognitive_complexity INTEGER DEFAULT 0,
    max_nesting_depth INTEGER DEFAULT 0,
    
    -- Function metrics
    function_count INTEGER DEFAULT 0,
    average_function_length FLOAT DEFAULT 0,
    max_function_complexity INTEGER DEFAULT 0,
    
    -- Halstead metrics
    halstead_volume FLOAT DEFAULT 0,
    halstead_difficulty FLOAT DEFAULT 0,
    halstead_effort FLOAT DEFAULT 0,
    
    -- Dependencies
    imports_count INTEGER DEFAULT 0,
    dependencies TEXT[] DEFAULT '{}',
    
    -- Risk score (0-100)
    risk_score FLOAT DEFAULT 0,
    
    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_file_snapshot UNIQUE (file_path, commit_id)
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_commit_complexity_author ON commit_complexity_analysis(author);
CREATE INDEX IF NOT EXISTS idx_commit_complexity_repo ON commit_complexity_analysis(repository_name);
CREATE INDEX IF NOT EXISTS idx_commit_complexity_timestamp ON commit_complexity_analysis(timestamp);
CREATE INDEX IF NOT EXISTS idx_commit_complexity_impact ON commit_complexity_analysis(architectural_impact);

CREATE INDEX IF NOT EXISTS idx_file_complexity_repo ON file_complexity_snapshots(repository_name);
CREATE INDEX IF NOT EXISTS idx_file_complexity_language ON file_complexity_snapshots(language);
CREATE INDEX IF NOT EXISTS idx_file_complexity_risk ON file_complexity_snapshots(risk_score);

-- View: High complexity commits (for manager alerts)
CREATE OR REPLACE VIEW high_complexity_commits AS
SELECT 
    ca.*,
    CASE 
        WHEN ca.architectural_impact = 'critical' THEN 4
        WHEN ca.architectural_impact = 'high' THEN 3
        WHEN ca.architectural_impact = 'medium' THEN 2
        ELSE 1
    END as impact_level
FROM commit_complexity_analysis ca
WHERE ca.architectural_impact IN ('high', 'critical')
   OR ca.max_file_complexity > 50
ORDER BY ca.max_file_complexity DESC;

-- View: Developer complexity trends
CREATE OR REPLACE VIEW developer_complexity_trends AS
SELECT 
    author,
    repository_name,
    DATE_TRUNC('week', timestamp) as week,
    COUNT(*) as commit_count,
    AVG(total_complexity_delta) as avg_complexity_delta,
    SUM(CASE WHEN architectural_impact IN ('high', 'critical') THEN 1 ELSE 0 END) as high_impact_commits,
    MAX(max_file_complexity) as max_complexity_seen
FROM commit_complexity_analysis
GROUP BY author, repository_name, DATE_TRUNC('week', timestamp)
ORDER BY week DESC;

-- View: Repository complexity overview
CREATE OR REPLACE VIEW repository_complexity_overview AS
SELECT 
    repository_name,
    COUNT(DISTINCT commit_id) as total_commits_analyzed,
    AVG(max_file_complexity) as avg_max_complexity,
    MAX(max_file_complexity) as overall_max_complexity,
    SUM(CASE WHEN architectural_impact = 'critical' THEN 1 ELSE 0 END) as critical_commits,
    SUM(CASE WHEN architectural_impact = 'high' THEN 1 ELSE 0 END) as high_impact_commits,
    SUM(CASE WHEN complexity_trend = 'increased' THEN 1 ELSE 0 END) as complexity_increasing,
    COUNT(DISTINCT author) as contributing_developers
FROM commit_complexity_analysis
GROUP BY repository_name;

-- Function: Get complexity score for a commit
CREATE OR REPLACE FUNCTION get_commit_complexity(p_commit_id TEXT)
RETURNS TABLE (
    commit_id TEXT,
    author TEXT,
    files_changed INTEGER,
    total_complexity_delta FLOAT,
    max_file_complexity FLOAT,
    architectural_impact TEXT,
    complexity_trend TEXT,
    risk_level TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ca.commit_id,
        ca.author,
        ca.files_changed,
        ca.total_complexity_delta,
        ca.max_file_complexity,
        ca.architectural_impact,
        ca.complexity_trend,
        CASE 
            WHEN ca.max_file_complexity > 70 OR ca.architectural_impact = 'critical' THEN 'critical'
            WHEN ca.max_file_complexity > 50 OR ca.architectural_impact = 'high' THEN 'high'
            WHEN ca.max_file_complexity > 30 THEN 'medium'
            ELSE 'low'
        END as risk_level
    FROM commit_complexity_analysis ca
    WHERE ca.commit_id = p_commit_id;
END;
$$ LANGUAGE plpgsql;

-- Enable RLS
ALTER TABLE commit_complexity_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_complexity_snapshots ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "complexity_read_own_team" ON commit_complexity_analysis
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM team_members 
            WHERE team_members.developer_id = auth.uid()::text
            AND team_members.team_id IN (
                SELECT team_id FROM developer_activity 
                WHERE developer_activity.developer_id = commit_complexity_analysis.author
            )
        )
        OR auth.role() = 'service_role'
    );

CREATE POLICY "complexity_read_own_team_files" ON file_complexity_snapshots
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM team_members 
            WHERE team_members.developer_id = auth.uid()::text
        )
        OR auth.role() = 'service_role'
    );

-- Grant permissions
GRANT SELECT ON commit_complexity_analysis TO anon, authenticated;
GRANT SELECT ON file_complexity_snapshots TO anon, authenticated;
GRANT SELECT ON high_complexity_commits TO anon, authenticated;
GRANT SELECT ON developer_complexity_trends TO anon, authenticated;
GRANT SELECT ON repository_complexity_overview TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_commit_complexity TO anon, authenticated;
