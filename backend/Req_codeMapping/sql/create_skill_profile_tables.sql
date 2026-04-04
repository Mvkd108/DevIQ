-- ============================================================================
-- Developer Skill Profile Tables
-- Stores inferred developer skills from commit history analysis
-- ============================================================================

-- Main skill profile table
CREATE TABLE IF NOT EXISTS developer_skill_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    profile_id TEXT NOT NULL UNIQUE,
    
    -- Developer identification
    developer_id TEXT NOT NULL,
    developer_email TEXT,
    developer_name TEXT,
    
    -- Skill information
    skill_tag TEXT NOT NULL,  -- e.g., "debugging", "performance_tuning", "database_schema"
    skill_category TEXT NOT NULL DEFAULT 'technical',  -- 'technical', 'domain', 'process'
    
    -- Scoring (0-100 scale)
    score NUMERIC(5,2) NOT NULL CHECK (score >= 0 AND score <= 100),
    rank INTEGER NOT NULL DEFAULT 0,  -- Rank among this developer's skills
    
    -- Confidence and evidence
    confidence_score NUMERIC(3,2) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    confidence_label TEXT NOT NULL CHECK (confidence_label IN ('high', 'medium', 'low')),
    evidence_commits JSONB NOT NULL DEFAULT '[]'::JSONB,  -- Array of {commit_id, impact_score, timestamp}
    evidence_count INTEGER NOT NULL DEFAULT 0,
    
    -- Scoring components
    frequency_score NUMERIC(5,2) DEFAULT 0,  -- How often this skill is used
    recency_score NUMERIC(5,2) DEFAULT 0,    -- Weighted by recent activity
    complexity_score NUMERIC(5,2) DEFAULT 0, -- Complexity of related commits
    churn_score NUMERIC(5,2) DEFAULT 0,      -- Code churn contribution
    
    -- Metadata
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- Profile freshness (typically 90 days)
    calculation_version TEXT DEFAULT 'v1',
    
    -- Source tracking
    primary_source TEXT DEFAULT 'extension_events',  -- Where the data came from
    last_commit_at TIMESTAMPTZ,  -- Most recent commit contributing to this skill
    
    -- Constraints
    UNIQUE(developer_id, skill_tag)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_skill_profiles_developer_id 
    ON developer_skill_profiles(developer_id);
CREATE INDEX IF NOT EXISTS idx_skill_profiles_skill_tag 
    ON developer_skill_profiles(skill_tag);
CREATE INDEX IF NOT EXISTS idx_skill_profiles_score 
    ON developer_skill_profiles(score DESC);
CREATE INDEX IF NOT EXISTS idx_skill_profiles_category 
    ON developer_skill_profiles(skill_category);
CREATE INDEX IF NOT EXISTS idx_skill_profiles_calculated_at 
    ON developer_skill_profiles(calculated_at);

-- Partial index for high-confidence skills (useful for expert matching)
CREATE INDEX IF NOT EXISTS idx_skill_profiles_high_confidence 
    ON developer_skill_profiles(developer_id, score DESC) 
    WHERE confidence_label = 'high' AND score >= 50;

-- View: Top skills per developer (convenience view)
CREATE OR REPLACE VIEW developer_top_skills AS
SELECT 
    developer_id,
    developer_name,
    skill_tag,
    skill_category,
    score,
    confidence_label,
    evidence_count,
    calculated_at,
    expires_at,
    ROW_NUMBER() OVER (PARTITION BY developer_id ORDER BY score DESC) as skill_rank
FROM developer_skill_profiles
WHERE expires_at IS NULL OR expires_at > NOW();

-- View: Skill experts (find developers with specific skills)
CREATE OR REPLACE VIEW skill_experts AS
SELECT 
    skill_tag,
    developer_id,
    developer_name,
    score as expertise_score,
    confidence_label,
    evidence_count,
    calculated_at,
    ROW_NUMBER() OVER (PARTITION BY skill_tag ORDER BY score DESC) as expert_rank
FROM developer_skill_profiles
WHERE confidence_label = 'high' 
    AND score >= 50
    AND (expires_at IS NULL OR expires_at > NOW());

-- Function: Get developer's top N skills
CREATE OR REPLACE FUNCTION get_developer_top_skills(p_developer_id TEXT, p_limit INTEGER DEFAULT 5)
RETURNS TABLE (
    skill_tag TEXT,
    skill_category TEXT,
    score NUMERIC,
    confidence_label TEXT,
    evidence_count INTEGER,
    calculated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dsp.skill_tag,
        dsp.skill_category,
        dsp.score,
        dsp.confidence_label,
        dsp.evidence_count,
        dsp.calculated_at
    FROM developer_skill_profiles dsp
    WHERE dsp.developer_id = p_developer_id
        AND (dsp.expires_at IS NULL OR dsp.expires_at > NOW())
    ORDER BY dsp.score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function: Find experts for a skill
CREATE OR REPLACE FUNCTION find_skill_experts(p_skill_tag TEXT, p_limit INTEGER DEFAULT 5)
RETURNS TABLE (
    developer_id TEXT,
    developer_name TEXT,
    expertise_score NUMERIC,
    confidence_label TEXT,
    evidence_count INTEGER,
    calculated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dsp.developer_id,
        dsp.developer_name,
        dsp.score,
        dsp.confidence_label,
        dsp.evidence_count,
        dsp.calculated_at
    FROM developer_skill_profiles dsp
    WHERE dsp.skill_tag = p_skill_tag
        AND dsp.confidence_label = 'high'
        AND dsp.score >= 50
        AND (dsp.expires_at IS NULL OR dsp.expires_at > NOW())
    ORDER BY dsp.score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Row Level Security (managers see their team, developers see own data)
ALTER TABLE developer_skill_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "skill_profiles_read_own" ON developer_skill_profiles
    FOR SELECT
    TO authenticated
    USING (developer_id = current_setting('app.current_user_id', true));

CREATE POLICY "skill_profiles_read_team" ON developer_skill_profiles
    FOR SELECT  
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM team_memberships tm
            WHERE tm.canonical_id = developer_skill_profiles.developer_id
                AND tm.team_id IN (
                    SELECT team_id FROM team_memberships 
                    WHERE canonical_id = current_setting('app.current_user_id', true)
                        AND role IN ('manager', 'tech_lead')
                )
        )
    );

-- Grants
GRANT SELECT ON developer_skill_profiles TO anon, authenticated;
GRANT SELECT ON developer_top_skills TO anon, authenticated;
GRANT SELECT ON skill_experts TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_developer_top_skills TO anon, authenticated;
GRANT EXECUTE ON FUNCTION find_skill_experts TO anon, authenticated;
