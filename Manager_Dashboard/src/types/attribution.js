/**
 * Attribution System Type Definitions
 * 
 * JSDoc type definitions for the attribution system dashboard.
 * These ensure consistent data structures across attribution components.
 * 
 * @module types/attribution
 */

/**
 * @typedef {Object} CanonicalDeveloper
 * @property {string} canonical_id - Unique developer identifier
 * @property {string} display_name - Human-readable name
 * @property {string} [primary_email] - Primary email address
 * @property {string} [primary_team_id] - Default team assignment
 * @property {'active'|'inactive'|'suspended'} status - Developer status
 * @property {Object} [metadata] - Additional metadata
 */

/**
 * @typedef {Object} AttributionDecision
 * @property {string} decision_id - Unique decision identifier
 * @property {string} work_item_id - Issue/PR/commit ID
 * @property {'commit'|'pull_request'|'issue'|'deployment'} work_item_type - Type of work
 * @property {string} canonical_id - Assigned developer
 * @property {number} confidence_score - 0.0 to 1.0
 * @property {'high'|'medium'|'low'} confidence_label - Confidence category
 * @property {string[]} evidence - List of evidence signals
 * @property {string} provenance - Source of attribution ('explicit', 'inferred', 'heuristic')
 * @property {boolean} ambiguity_flag - True if ambiguous
 * @property {string[]} [ambiguity_reasons] - Reasons for ambiguity
 * @property {boolean} manual_review_required - Needs human review
 */

/**
 * @typedef {Object} OwnershipEvidence
 * @property {string} developer_id - Developer identifier
 * @property {string} target_path - File/module path
 * @property {number} recency_score - 0.0 to 1.0 (recent = higher)
 * @property {number} commit_count - Number of commits
 * @property {number} code_churn - Lines changed
 * @property {number} review_participation - Reviews given/received
 * @property {number} ownership_share - Percentage ownership (0-100)
 * @property {number} confidence_score - Overall confidence
 * @property {'high'|'medium'|'low'} confidence_label - Confidence level
 */

/**
 * @typedef {Object} DependencyEdge
 * @property {string} edge_id - Unique edge identifier
 * @property {string} source_work_item_id - Source item
 * @property {string} target_work_item_id - Target item
 * @property {string} source_team_id - Source team
 * @property {string} target_team_id - Target team
 * @property {'depends_on'|'relates_to'|'blocks'} dependency_type - Relationship type
 * @property {'strong'|'moderate'|'weak'} strength - Dependency strength
 * @property {boolean} is_cross_team - True if cross-team dependency
 * @property {number} confidence_score - Edge confidence
 */

/**
 * @typedef {Object} AmbiguityRecord
 * @property {string} ambiguity_id - Unique identifier
 * @property {string} work_item_id - Affected work item
 * @property {'developer_identity'|'work_item_mapping'|'ownership_conflict'|'org_ambiguity'} ambiguity_type - Type
 * @property {string[]} possible_canonical_ids - Candidate developers
 * @property {'pending'|'in_review'|'resolved'|'escalated'} status - Resolution status
 * @property {'low'|'medium'|'high'|'critical'} priority - Review priority
 * @property {string[]} ambiguity_reasons - Why it's ambiguous
 * @property {string} [assigned_reviewer] - Who is reviewing
 * @property {string} created_at - ISO timestamp
 */

/**
 * @typedef {Object} ManagerAttributionRollup
 * @property {string} manager_id - Manager identifier
 * @property {string} team_id - Team identifier
 * @property {number} total_work_items - Total attributed items
 * @property {Object} confidence_distribution - {high, medium, low, ambiguous} counts
 * @property {number} pending_ambiguities - Items needing review
 * @property {DependencyEdge[]} cross_team_dependencies - Incoming/outgoing deps
 * @property {Object[]} ownership_risks - Modules with bus factor concerns
 */

/**
 * @typedef {Object} ProvenanceBadgeProps
 * @property {'connector'|'inferred'|'mock'|'mixed'} source - Data source
 * @property {number} confidence_score - 0.0 to 1.0
 * @property {'high'|'medium'|'low'} confidence_label - Display label
 * @property {boolean} showDetails - Whether to show evidence details
 */

// Export type names for documentation purposes
export const AttributionTypes = {
  CanonicalDeveloper: 'CanonicalDeveloper',
  AttributionDecision: 'AttributionDecision',
  OwnershipEvidence: 'OwnershipEvidence',
  DependencyEdge: 'DependencyEdge',
  AmbiguityRecord: 'AmbiguityRecord',
  ManagerAttributionRollup: 'ManagerAttributionRollup',
  ProvenanceBadgeProps: 'ProvenanceBadgeProps',
};

// Provenance color mappings for UI consistency
export const PROVENANCE_COLORS = {
  connector: { bg: '#10b981', text: '#ffffff', label: 'Verified' },
  inferred: { bg: '#f59e0b', text: '#ffffff', label: 'Inferred' },
  heuristic: { bg: '#6366f1', text: '#ffffff', label: 'Heuristic' },
  mock: { bg: '#9ca3af', text: '#ffffff', label: 'Placeholder' },
  mixed: { bg: '#8b5cf6', text: '#ffffff', label: 'Mixed' },
};

// Confidence level color mappings
export const CONFIDENCE_COLORS = {
  high: { bg: '#10b981', text: '#ffffff', border: '#059669' },
  medium: { bg: '#f59e0b', text: '#ffffff', border: '#d97706' },
  low: { bg: '#ef4444', text: '#ffffff', border: '#dc2626' },
  ambiguous: { bg: '#6b7280', text: '#ffffff', border: '#4b5563' },
};

// Default export for module
export default AttributionTypes;
