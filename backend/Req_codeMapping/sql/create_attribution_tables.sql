-- ============================================================================
-- Attribution & Dependency Mapping Tables
-- Run this in Supabase SQL Editor
-- 
-- Purpose: Store canonical developer identities, attribution decisions,
--          and cross-team dependency mappings with full auditability.
-- ============================================================================

-- ============================================================================
-- CORE IDENTITY TABLES
-- ============================================================================

-- Canonical developer identities (unified view across all source systems)
CREATE TABLE IF NOT EXISTS canonical_identities (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    canonical_id TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    primary_email TEXT,
    primary_team_id TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    metadata JSONB DEFAULT '{}',
    -- Time-aware fields for auditability
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    effective_to TIMESTAMPTZ,  -- NULL means current
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Identity aliases (maps source system identifiers to canonical IDs)
CREATE TABLE IF NOT EXISTS identity_aliases (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    alias_id TEXT NOT NULL UNIQUE,
    source_system TEXT NOT NULL,  -- 'jira', 'github', 'gitlab', 'git', 'azure_devops'
    source_identifier TEXT NOT NULL,  -- username, email, employee ID
    canonical_id TEXT NOT NULL REFERENCES canonical_identities(canonical_id) ON DELETE CASCADE,
    alias_type TEXT DEFAULT 'username' CHECK (alias_type IN ('email', 'username', 'employee_id', 'sso_id', 'api_key')),
    is_primary BOOLEAN DEFAULT FALSE,
    -- Time-aware fields
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    effective_to TIMESTAMPTZ,  -- NULL means current
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Confidence and evidence fields (required for all mapping records)
    confidence_score DECIMAL(3,2) NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    confidence_label TEXT NOT NULL CHECK (confidence_label IN ('high', 'medium', 'low')),
    evidence JSONB DEFAULT '[]',
    provenance TEXT NOT NULL,  -- 'hr_system', 'manual', 'inferred'
    ambiguity_flag BOOLEAN DEFAULT FALSE,
    ambiguity_reasons JSONB DEFAULT '[]',
    manual_review_required BOOLEAN DEFAULT FALSE,
    -- Ensure unique aliases per source system
    UNIQUE(source_system, source_identifier)
);

-- ============================================================================
-- TEAM STRUCTURE TABLES
-- ============================================================================

-- Team memberships (with historical tracking)
CREATE TABLE IF NOT EXISTS team_memberships (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    membership_id TEXT NOT NULL UNIQUE,
    canonical_id TEXT NOT NULL REFERENCES canonical_identities(canonical_id) ON DELETE CASCADE,
    team_id TEXT NOT NULL,
    role TEXT DEFAULT 'developer' CHECK (role IN ('developer', 'senior_developer', 'tech_lead', 'architect', 'contractor', 'intern')),
    allocation_percent INTEGER DEFAULT 100 CHECK (allocation_percent >= 0 AND allocation_percent <= 100),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'pending', 'transferred', 'inactive')),
    -- Time-aware fields
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,  -- NULL means current
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    -- Confidence and evidence fields
    confidence_score DECIMAL(3,2) NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    confidence_label TEXT NOT NULL CHECK (confidence_label IN ('high', 'medium', 'low')),
    evidence JSONB DEFAULT '[]',
    provenance TEXT NOT NULL,  -- 'hr_system', 'manual', 'jira'
    ambiguity_flag BOOLEAN DEFAULT FALSE,
    ambiguity_reasons JSONB DEFAULT '[]',
    manual_review_required BOOLEAN DEFAULT FALSE
);

-- Manager mappings (team to manager relationships)
CREATE TABLE IF NOT EXISTS manager_mappings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    mapping_id TEXT NOT NULL UNIQUE,
    team_id TEXT NOT NULL,
    manager_canonical_id TEXT NOT NULL REFERENCES canonical_identities(canonical_id) ON DELETE CASCADE,
    manager_role TEXT DEFAULT 'engineering_manager' CHECK (manager_role IN ('engineering_manager', 'product_manager', 'team_lead', 'director', 'vp')),
    is_primary BOOLEAN DEFAULT TRUE,
    -- Time-aware fields
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,  -- NULL means current
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    -- Confidence and evidence fields
    confidence_score DECIMAL(3,2) NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    confidence_label TEXT NOT NULL CHECK (confidence_label IN ('high', 'medium', 'low')),
    evidence JSONB DEFAULT '[]',
    provenance TEXT NOT NULL,  -- 'hr_system', 'manual', 'jira'
    ambiguity_flag BOOLEAN DEFAULT FALSE,
    ambiguity_reasons JSONB DEFAULT '[]',
    manual_review_required BOOLEAN DEFAULT FALSE
);

-- ============================================================================
-- ATTRIBUTION TABLES
-- ============================================================================

-- Attribution decisions (work item to developer mapping)
CREATE TABLE IF NOT EXISTS attribution_decisions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    decision_id TEXT NOT NULL UNIQUE,
    work_item_id TEXT NOT NULL,
    work_item_type TEXT NOT NULL CHECK (work_item_type IN ('issue', 'pull_request', 'commit', 'deployment', 'requirement', 'task')),
    canonical_id TEXT NOT NULL REFERENCES canonical_identities(canonical_id) ON DELETE CASCADE,
    -- Attribution factors
    ownership_factors JSONB DEFAULT '[]',  -- e.g., ['author', 'assignee', 'reviewer']
    ownership_score DECIMAL(4,3) NOT NULL CHECK (ownership_score >= 0.0 AND ownership_score <= 1.0),
    decision_type TEXT DEFAULT 'automatic' CHECK (decision_type IN ('automatic', 'manual', 'hybrid', 'inferred')),
    -- Review tracking
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    -- Time-aware fields
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,  -- NULL means current
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    -- Confidence and evidence fields (core requirements)
    confidence_score DECIMAL(3,2) NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    confidence_label TEXT NOT NULL CHECK (confidence_label IN ('high', 'medium', 'low')),
    evidence JSONB DEFAULT '[]',
    provenance TEXT NOT NULL,  -- 'commit_history', 'jira_api', 'manual_assignment'
    ambiguity_flag BOOLEAN DEFAULT FALSE,
    ambiguity_reasons JSONB DEFAULT '[]',
    manual_review_required BOOLEAN DEFAULT FALSE,
    -- Index for efficient work item lookups
    UNIQUE(work_item_id, work_item_type, effective_from)
);

-- Ambiguity queue (unresolved/ambiguous mappings requiring review)
CREATE TABLE IF NOT EXISTS ambiguity_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ambiguity_id TEXT NOT NULL UNIQUE,
    work_item_id TEXT NOT NULL,
    work_item_type TEXT NOT NULL CHECK (work_item_type IN ('issue', 'pull_request', 'commit', 'deployment', 'requirement', 'task')),
    ambiguity_type TEXT NOT NULL CHECK (ambiguity_type IN (
        'multiple_contributors', 'unknown_author', 'ambiguous_alias',
        'team_owned', 'automated_commit', 'merge_commit', 'fork_contribution',
        'identity_conflict', 'other'
    )),
    possible_canonical_ids JSONB DEFAULT '[]',
    source_identifiers JSONB DEFAULT '[]',
    -- Status and resolution
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_review', 'resolved', 'escalated', 'deferred')),
    resolution TEXT,
    resolved_by TEXT,
    resolved_at TIMESTAMPTZ,
    -- Assignment
    assigned_reviewer TEXT,
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    -- Confidence and evidence fields
    confidence_score DECIMAL(3,2) NOT NULL DEFAULT 0.30 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    confidence_label TEXT NOT NULL DEFAULT 'low' CHECK (confidence_label IN ('high', 'medium', 'low')),
    evidence JSONB DEFAULT '[]',
    provenance TEXT NOT NULL,
    ambiguity_flag BOOLEAN DEFAULT TRUE,
    ambiguity_reasons JSONB NOT NULL DEFAULT '[]',
    manual_review_required BOOLEAN DEFAULT TRUE
);

-- Ownership evidence (weighted factors for attribution)
CREATE TABLE IF NOT EXISTS ownership_evidence (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    evidence_id TEXT NOT NULL UNIQUE,
    decision_id TEXT NOT NULL REFERENCES attribution_decisions(decision_id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN (
        'commit_author', 'commit_committer', 'pr_author', 'pr_merger', 'pr_reviewer',
        'jira_assignee', 'jira_reporter', 'jira_commenter', 'issue_assignee',
        'code_owner', 'file_path_pattern', 'review_approval', 'time_correlation', 'manual_assignment', 'inferred_from_team'
    )),
    source_identifier TEXT NOT NULL,  -- email, username from source system
    canonical_id TEXT NOT NULL REFERENCES canonical_identities(canonical_id) ON DELETE CASCADE,
    weight DECIMAL(3,2) NOT NULL CHECK (weight >= 0.0 AND weight <= 1.0),
    source_system TEXT NOT NULL,
    source_reference TEXT NOT NULL,  -- commit SHA, PR number, etc.
    source_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Confidence and evidence fields
    confidence_score DECIMAL(3,2) NOT NULL DEFAULT 0.80 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    confidence_label TEXT NOT NULL DEFAULT 'high' CHECK (confidence_label IN ('high', 'medium', 'low')),
    evidence JSONB DEFAULT '[]',
    provenance TEXT NOT NULL,
    ambiguity_flag BOOLEAN DEFAULT FALSE,
    ambiguity_reasons JSONB DEFAULT '[]',
    manual_review_required BOOLEAN DEFAULT FALSE
);

-- ============================================================================
-- DEPENDENCY TABLES
-- ============================================================================

-- Dependency edges (cross-team dependency relationships)
CREATE TABLE IF NOT EXISTS dependency_edges (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    edge_id TEXT NOT NULL UNIQUE,
    source_work_item_id TEXT NOT NULL,
    source_work_item_type TEXT NOT NULL CHECK (source_work_item_type IN ('issue', 'pull_request', 'commit', 'deployment', 'requirement', 'task')),
    source_team_id TEXT NOT NULL,
    target_work_item_id TEXT NOT NULL,
    target_work_item_type TEXT NOT NULL CHECK (target_work_item_type IN ('issue', 'pull_request', 'commit', 'deployment', 'requirement', 'task')),
    target_team_id TEXT NOT NULL,
    dependency_type TEXT DEFAULT 'depends_on' CHECK (dependency_type IN ('blocks', 'depends_on', 'relates_to', 'duplicates', 'parent_child', 'references')),
    strength TEXT DEFAULT 'moderate' CHECK (strength IN ('strong', 'moderate', 'weak')),
    is_cross_team BOOLEAN GENERATED ALWAYS AS (source_team_id != target_team_id) STORED,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'resolved', 'broken', 'deprecated')),
    -- Timestamps
    detected_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    -- Time-aware fields
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,  -- NULL means current
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    -- Detection metadata
    detection_method TEXT NOT NULL CHECK (detection_method IN (
        'jira_link', 'pr_description_reference', 'commit_message_reference',
        'github_linked_issue', 'file_dependency', 'api_contract', 'manual_annotation', 'inferred_from_timing'
    )),
    -- Confidence and evidence fields
    confidence_score DECIMAL(3,2) NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    confidence_label TEXT NOT NULL CHECK (confidence_label IN ('high', 'medium', 'low')),
    evidence JSONB DEFAULT '[]',
    provenance TEXT NOT NULL,
    ambiguity_flag BOOLEAN DEFAULT FALSE,
    ambiguity_reasons JSONB DEFAULT '[]',
    manual_review_required BOOLEAN DEFAULT FALSE,
    -- Prevent duplicate edges
    UNIQUE(source_work_item_id, target_work_item_id, dependency_type, effective_from)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Canonical identities indexes
CREATE INDEX IF NOT EXISTS idx_canonical_identities_canonical_id ON canonical_identities(canonical_id);
CREATE INDEX IF NOT EXISTS idx_canonical_identities_status ON canonical_identities(status);
CREATE INDEX IF NOT EXISTS idx_canonical_identities_email ON canonical_identities(primary_email);
CREATE INDEX IF NOT EXISTS idx_canonical_identities_effective ON canonical_identities(effective_from, effective_to);

-- Identity aliases indexes
CREATE INDEX IF NOT EXISTS idx_identity_aliases_canonical_id ON identity_aliases(canonical_id);
CREATE INDEX IF NOT EXISTS idx_identity_aliases_source ON identity_aliases(source_system, source_identifier);
CREATE INDEX IF NOT EXISTS idx_identity_aliases_effective ON identity_aliases(effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_identity_aliases_ambiguity ON identity_aliases(ambiguity_flag) WHERE ambiguity_flag = TRUE;
CREATE INDEX IF NOT EXISTS idx_identity_aliases_review ON identity_aliases(manual_review_required) WHERE manual_review_required = TRUE;

-- Team memberships indexes
CREATE INDEX IF NOT EXISTS idx_team_memberships_canonical_id ON team_memberships(canonical_id);
CREATE INDEX IF NOT EXISTS idx_team_memberships_team_id ON team_memberships(team_id);
CREATE INDEX IF NOT EXISTS idx_team_memberships_effective ON team_memberships(effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_team_memberships_status ON team_memberships(status);

-- Manager mappings indexes
CREATE INDEX IF NOT EXISTS idx_manager_mappings_team_id ON manager_mappings(team_id);
CREATE INDEX IF NOT EXISTS idx_manager_mappings_manager ON manager_mappings(manager_canonical_id);
CREATE INDEX IF NOT EXISTS idx_manager_mappings_effective ON manager_mappings(effective_from, effective_to);

-- Attribution decisions indexes
CREATE INDEX IF NOT EXISTS idx_attribution_decisions_work_item ON attribution_decisions(work_item_id, work_item_type);
CREATE INDEX IF NOT EXISTS idx_attribution_decisions_canonical_id ON attribution_decisions(canonical_id);
CREATE INDEX IF NOT EXISTS idx_attribution_decisions_effective ON attribution_decisions(effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_attribution_decisions_confidence ON attribution_decisions(confidence_score);
CREATE INDEX IF NOT EXISTS idx_attribution_decisions_ambiguity ON attribution_decisions(ambiguity_flag) WHERE ambiguity_flag = TRUE;
CREATE INDEX IF NOT EXISTS idx_attribution_decisions_review ON attribution_decisions(manual_review_required) WHERE manual_review_required = TRUE;

-- Ambiguity queue indexes
CREATE INDEX IF NOT EXISTS idx_ambiguity_queue_status ON ambiguity_queue(status);
CREATE INDEX IF NOT EXISTS idx_ambiguity_queue_work_item ON ambiguity_queue(work_item_id, work_item_type);
CREATE INDEX IF NOT EXISTS idx_ambiguity_queue_priority ON ambiguity_queue(priority, created_at);
CREATE INDEX IF NOT EXISTS idx_ambiguity_queue_assigned ON ambiguity_queue(assigned_reviewer);
CREATE INDEX IF NOT EXISTS idx_ambiguity_queue_type ON ambiguity_queue(ambiguity_type);

-- Ownership evidence indexes
CREATE INDEX IF NOT EXISTS idx_ownership_evidence_decision ON ownership_evidence(decision_id);
CREATE INDEX IF NOT EXISTS idx_ownership_evidence_canonical ON ownership_evidence(canonical_id);
CREATE INDEX IF NOT EXISTS idx_ownership_evidence_type ON ownership_evidence(evidence_type);

-- Dependency edges indexes
CREATE INDEX IF NOT EXISTS idx_dependency_edges_source ON dependency_edges(source_work_item_id, source_work_item_type);
CREATE INDEX IF NOT EXISTS idx_dependency_edges_target ON dependency_edges(target_work_item_id, target_work_item_type);
CREATE INDEX IF NOT EXISTS idx_dependency_edges_teams ON dependency_edges(source_team_id, target_team_id);
CREATE INDEX IF NOT EXISTS idx_dependency_edges_cross_team ON dependency_edges(is_cross_team) WHERE is_cross_team = TRUE;
CREATE INDEX IF NOT EXISTS idx_dependency_edges_status ON dependency_edges(status);
CREATE INDEX IF NOT EXISTS idx_dependency_edges_effective ON dependency_edges(effective_from, effective_to);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Current active developers (as-of-now view)
CREATE OR REPLACE VIEW current_developers AS
SELECT * FROM canonical_identities
WHERE status = 'active'
    AND (effective_to IS NULL OR effective_to > NOW());

-- Current team memberships
CREATE OR REPLACE VIEW current_team_members AS
SELECT tm.*, ci.display_name, ci.primary_email
FROM team_memberships tm
JOIN canonical_identities ci ON tm.canonical_id = ci.canonical_id
WHERE tm.status = 'active'
    AND (tm.effective_to IS NULL OR tm.effective_to > NOW());

-- Current team managers
CREATE OR REPLACE VIEW current_team_managers AS
SELECT mm.*, ci.display_name AS manager_name, ci.primary_email AS manager_email
FROM manager_mappings mm
JOIN canonical_identities ci ON mm.manager_canonical_id = ci.canonical_id
WHERE mm.is_primary = TRUE
    AND (mm.effective_to IS NULL OR mm.effective_to > NOW());

-- Active attribution decisions
CREATE OR REPLACE VIEW active_attributions AS
SELECT ad.*, ci.display_name AS developer_name
FROM attribution_decisions ad
JOIN canonical_identities ci ON ad.canonical_id = ci.canonical_id
WHERE (ad.effective_to IS NULL OR ad.effective_to > NOW());

-- Pending ambiguities
CREATE OR REPLACE VIEW pending_ambiguities AS
SELECT * FROM ambiguity_queue
WHERE status IN ('pending', 'in_review')
ORDER BY 
    CASE priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    created_at;

-- Cross-team dependencies
CREATE OR REPLACE VIEW cross_team_dependencies AS
SELECT de.*,
    source_work_item_id || ' (' || source_work_item_type || ')' AS source_label,
    target_work_item_id || ' (' || target_work_item_type || ')' AS target_label
FROM dependency_edges de
WHERE is_cross_team = TRUE
    AND status = 'active'
    AND (effective_to IS NULL OR effective_to > NOW());

-- Attribution confidence summary by developer
CREATE OR REPLACE VIEW developer_attribution_summary AS
SELECT 
    ad.canonical_id,
    ci.display_name,
    COUNT(*) AS total_attributions,
    COUNT(*) FILTER (WHERE ad.confidence_label = 'high') AS high_confidence_count,
    COUNT(*) FILTER (WHERE ad.confidence_label = 'medium') AS medium_confidence_count,
    COUNT(*) FILTER (WHERE ad.confidence_label = 'low') AS low_confidence_count,
    COUNT(*) FILTER (WHERE ad.ambiguity_flag = TRUE) AS ambiguous_count,
    COUNT(*) FILTER (WHERE ad.manual_review_required = TRUE) AS pending_review_count,
    ROUND(AVG(ad.confidence_score), 2) AS avg_confidence_score,
    MAX(ad.updated_at) AS last_attribution_at
FROM attribution_decisions ad
JOIN canonical_identities ci ON ad.canonical_id = ci.canonical_id
WHERE (ad.effective_to IS NULL OR ad.effective_to > NOW())
GROUP BY ad.canonical_id, ci.display_name;

-- Team dependency summary
CREATE OR REPLACE VIEW team_dependency_summary AS
SELECT 
    source_team_id,
    target_team_id,
    COUNT(*) AS dependency_count,
    COUNT(*) FILTER (WHERE strength = 'strong') AS strong_dependencies,
    COUNT(*) FILTER (WHERE strength = 'moderate') AS moderate_dependencies,
    COUNT(*) FILTER (WHERE strength = 'weak') AS weak_dependencies,
    COUNT(*) FILTER (WHERE status = 'active') AS active_dependencies,
    COUNT(*) FILTER (WHERE status = 'broken') AS broken_dependencies,
    ROUND(AVG(confidence_score), 2) AS avg_confidence
FROM dependency_edges
WHERE is_cross_team = TRUE
GROUP BY source_team_id, target_team_id;

-- ============================================================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE canonical_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_aliases ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE manager_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE attribution_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ambiguity_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE ownership_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE dependency_edges ENABLE ROW LEVEL SECURITY;

-- Developers can see their own identity
CREATE POLICY dev_own_identity ON canonical_identities
    FOR SELECT USING (canonical_id = current_setting('app.current_user_id', true));

-- Developers can see their own aliases
CREATE POLICY dev_own_aliases ON identity_aliases
    FOR SELECT USING (canonical_id = current_setting('app.current_user_id', true));

-- Developers can see their own memberships
CREATE POLICY dev_own_memberships ON team_memberships
    FOR SELECT USING (canonical_id = current_setting('app.current_user_id', true));

-- Developers can see their own attributions
CREATE POLICY dev_own_attributions ON attribution_decisions
    FOR SELECT USING (canonical_id = current_setting('app.current_user_id', true));

-- Team members can see team data
CREATE POLICY team_identities ON canonical_identities
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM team_memberships tm
            WHERE tm.team_id = canonical_identities.primary_team_id
            AND tm.canonical_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY team_aliases ON identity_aliases
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM team_memberships tm
            WHERE tm.canonical_id = identity_aliases.canonical_id
            AND tm.team_id IN (
                SELECT team_id FROM team_memberships 
                WHERE canonical_id = current_setting('app.current_user_id', true)
            )
        )
    );

CREATE POLICY team_memberships_view ON team_memberships
    FOR SELECT USING (
        team_id IN (
            SELECT team_id FROM team_memberships 
            WHERE canonical_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY team_attributions ON attribution_decisions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM team_memberships tm
            WHERE tm.canonical_id = attribution_decisions.canonical_id
            AND tm.team_id IN (
                SELECT team_id FROM team_memberships 
                WHERE canonical_id = current_setting('app.current_user_id', true)
            )
        )
    );

-- Managers can see their team ambiguity queue
CREATE POLICY manager_ambiguity ON ambiguity_queue
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM manager_mappings mm
            WHERE mm.team_id IN (
                SELECT team_id FROM team_memberships tm
                JOIN attribution_decisions ad ON tm.canonical_id = ad.canonical_id
                WHERE ad.work_item_id = ambiguity_queue.work_item_id
            )
            AND mm.manager_canonical_id = current_setting('app.current_user_id', true)
        )
    );

-- Service role can do everything
CREATE POLICY service_all_identities ON canonical_identities
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

CREATE POLICY service_all_aliases ON identity_aliases
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

CREATE POLICY service_all_memberships ON team_memberships
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

CREATE POLICY service_all_managers ON manager_mappings
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

CREATE POLICY service_all_attributions ON attribution_decisions
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

CREATE POLICY service_all_ambiguity ON ambiguity_queue
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

CREATE POLICY service_all_evidence ON ownership_evidence
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

CREATE POLICY service_all_dependencies ON dependency_edges
    FOR ALL USING (current_setting('app.is_service_role', true) = 'true');

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
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
CREATE TRIGGER update_canonical_identities_updated_at
    BEFORE UPDATE ON canonical_identities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_identity_aliases_updated_at
    BEFORE UPDATE ON identity_aliases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_team_memberships_updated_at
    BEFORE UPDATE ON team_memberships
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_manager_mappings_updated_at
    BEFORE UPDATE ON manager_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_attribution_decisions_updated_at
    BEFORE UPDATE ON attribution_decisions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ambiguity_queue_updated_at
    BEFORE UPDATE ON ambiguity_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dependency_edges_updated_at
    BEFORE UPDATE ON dependency_edges
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate confidence_label from confidence_score
CREATE OR REPLACE FUNCTION calculate_confidence_label(score DECIMAL(3,2))
RETURNS TEXT AS $$
BEGIN
    IF score >= 0.8 THEN RETURN 'high';
    ELSIF score >= 0.5 THEN RETURN 'medium';
    ELSE RETURN 'low';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to expire old records when inserting new effective version
CREATE OR REPLACE FUNCTION expire_previous_record()
RETURNS TRIGGER AS $$
BEGIN
    -- Expire previous record for the same entity
    IF TG_TABLE_NAME = 'identity_aliases' THEN
        UPDATE identity_aliases 
        SET effective_to = NEW.effective_from
        WHERE source_system = NEW.source_system 
        AND source_identifier = NEW.source_identifier
        AND effective_to IS NULL 
        AND id != NEW.id;
    ELSIF TG_TABLE_NAME = 'team_memberships' THEN
        UPDATE team_memberships 
        SET effective_to = NEW.effective_from
        WHERE canonical_id = NEW.canonical_id 
        AND team_id = NEW.team_id
        AND effective_to IS NULL 
        AND id != NEW.id;
    ELSIF TG_TABLE_NAME = 'manager_mappings' THEN
        UPDATE manager_mappings 
        SET effective_to = NEW.effective_from
        WHERE team_id = NEW.team_id 
        AND is_primary = NEW.is_primary
        AND effective_to IS NULL 
        AND id != NEW.id;
    ELSIF TG_TABLE_NAME = 'attribution_decisions' THEN
        UPDATE attribution_decisions 
        SET effective_to = NEW.effective_from
        WHERE work_item_id = NEW.work_item_id 
        AND work_item_type = NEW.work_item_type
        AND effective_to IS NULL 
        AND id != NEW.id;
    ELSIF TG_TABLE_NAME = 'dependency_edges' THEN
        UPDATE dependency_edges 
        SET effective_to = NEW.effective_from
        WHERE source_work_item_id = NEW.source_work_item_id 
        AND target_work_item_id = NEW.target_work_item_id
        AND dependency_type = NEW.dependency_type
        AND effective_to IS NULL 
        AND id != NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for time-aware expiration
CREATE TRIGGER expire_previous_alias
    AFTER INSERT ON identity_aliases
    FOR EACH ROW EXECUTE FUNCTION expire_previous_record();

CREATE TRIGGER expire_previous_membership
    AFTER INSERT ON team_memberships
    FOR EACH ROW EXECUTE FUNCTION expire_previous_record();

CREATE TRIGGER expire_previous_manager
    AFTER INSERT ON manager_mappings
    FOR EACH ROW EXECUTE FUNCTION expire_previous_record();

CREATE TRIGGER expire_previous_attribution
    AFTER INSERT ON attribution_decisions
    FOR EACH ROW EXECUTE FUNCTION expire_previous_record();

CREATE TRIGGER expire_previous_dependency
    AFTER INSERT ON dependency_edges
    FOR EACH ROW EXECUTE FUNCTION expire_previous_record();

-- Function to check for and flag ambiguous attributions
CREATE OR REPLACE FUNCTION flag_ambiguous_attribution()
RETURNS TRIGGER AS $$
DECLARE
    existing_count INTEGER;
BEGIN
    -- Check if there are other active attributions for the same work item
    SELECT COUNT(*) INTO existing_count
    FROM attribution_decisions
    WHERE work_item_id = NEW.work_item_id
    AND work_item_type = NEW.work_item_type
    AND canonical_id != NEW.canonical_id
    AND (effective_to IS NULL OR effective_to > NOW())
    AND id != NEW.id;
    
    IF existing_count > 0 THEN
        NEW.ambiguity_flag := TRUE;
        NEW.ambiguity_reasons := array_to_json(array_append(
            ARRAY(SELECT jsonb_array_elements_text(NEW.ambiguity_reasons)),
            'Multiple developers attributed to same work item'
        ))::jsonb;
        NEW.confidence_score := LEAST(NEW.confidence_score, 0.5);
        NEW.confidence_label := calculate_confidence_label(NEW.confidence_score);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_ambiguous_attribution
    BEFORE INSERT OR UPDATE ON attribution_decisions
    FOR EACH ROW EXECUTE FUNCTION flag_ambiguous_attribution();
