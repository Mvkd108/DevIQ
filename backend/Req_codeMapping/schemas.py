from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class MappingFeedbackPayload(BaseModel):
    commit_id: str = Field(..., min_length=1)
    feedback_type: Literal["approved", "rejected", "reassigned", "cleared"]
    predicted_issue_id: Optional[str] = None
    corrected_issue_id: Optional[str] = None
    reviewed_by: str = Field(default="dashboard-reviewer", min_length=1)


class ProjectIntakePayload(BaseModel):
    issue_id: Optional[str] = None
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    project_key: str = Field(default="MANUAL", min_length=2)
    issue_type: str = Field(default="Requirement")
    priority: str = Field(default="Medium")
    status: str = Field(default="Draft")
    owner_email: Optional[str] = None
    assignee_email: Optional[str] = None
    reporter_email: Optional[str] = None
    timeline_start: Optional[str] = None
    timeline_end: Optional[str] = None


class FlexibleResponse(BaseModel):
    class Config:
        extra = "allow"


class MappingFeedbackRecord(BaseModel):
    commit_id: str
    feedback_type: str
    predicted_issue_id: Optional[str] = None
    corrected_issue_id: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None


class ProjectIntakeRecord(BaseModel):
    issue_id: str
    title: str
    description: Optional[str] = None
    project_key: Optional[str] = None
    issue_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    owner_email: Optional[str] = None
    reporter_email: Optional[str] = None
    timeline_start: Optional[str] = None
    timeline_end: Optional[str] = None
    source: Optional[str] = None
    submitted_at: Optional[str] = None


class ReadinessCheck(BaseModel):
    key: str
    label: str
    category: Literal["configuration", "security", "persistence", "caching", "optional-modules"]
    status: Literal["healthy", "warning", "degraded"]
    severity: Literal["info", "warning", "critical"] = "info"
    current: str
    desired: str
    action: Optional[str] = None


class RolloutAssessment(BaseModel):
    status: Literal["blocked", "caution", "ready"]
    summary: str
    blocker_count: int = 0
    blockers: list[dict[str, str]] = []
    next_actions: list[str] = []


class HealthResponse(BaseModel):
    status: str
    ready: bool = False
    operating_mode: str = "local-demo"
    supabase_configured: bool = False
    write_auth_enabled: bool = False
    file_fallback_disabled: bool = False
    analytics_storage_mode: str = "live-only"
    analytics_snapshots_enabled: bool = True
    match_model: str = ""
    missing_required_env: list[str] = []
    allowed_origins: list[str] = []
    optional_modules: dict[str, bool] = {}
    optional_module_details: dict[str, dict[str, Any]] = {}
    feedback_storage_mode: str = "memory"
    intake_storage_mode: str = "memory"
    degraded_reasons: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    configuration: dict[str, Any] = {}
    configuration_audit: dict[str, Any] = {}
    readiness_checks: list[ReadinessCheck] = []
    readiness_overview: dict[str, Any] = {}
    setup_progress: dict[str, Any] = {}
    snapshot_health: dict[str, Any] = {}
    capabilities: dict[str, bool] = {}
    rollout_blockers: list[dict[str, str]] = []
    rollout_assessment: dict[str, RolloutAssessment] = {}


class StorageMeta(BaseModel):
    supabase_configured: bool = False
    write_auth_enabled: bool = False
    feedback_storage_mode: str = "memory"
    intake_storage_mode: str = "memory"
    analytics_storage_mode: str = "live-only"
    analytics_source: str = "live"
    analytics_generated_at: Optional[str] = None
    analytics_snapshot_age_seconds: Optional[int] = None
    file_fallback_active: bool = False
    storage_probe_ttl_seconds: int = 30


class DashboardResponse(BaseModel):
    sync: dict[str, Any]
    issues: list[dict[str, Any]]
    events: list[dict[str, Any]]
    feedback: list[MappingFeedbackRecord]
    analytics: dict[str, Any]
    meta: StorageMeta


class SyncResponse(FlexibleResponse):
    updated_issues: int
    matched_issues: int
    linked_commits: int
    unmatched_commits: list[dict[str, Any]]
    feedback_count: int
    updates: list[dict[str, Any]]


class MappingFeedbackListResponse(BaseModel):
    feedback: list[MappingFeedbackRecord]


class MappingFeedbackSaveResponse(BaseModel):
    status: str
    feedback: Optional[MappingFeedbackRecord] = None


class ProjectIntakeResponse(BaseModel):
    status: str
    record: dict[str, Any]
    intake_record: ProjectIntakeRecord
    roles: dict[str, Optional[str]]


class ProjectIntakeListResponse(BaseModel):
    records: list[ProjectIntakeRecord]


class MatchCommitResponse(FlexibleResponse):
    status: str


class DeliveryTimelineResponse(FlexibleResponse):
    generated_at: str
    summary: dict[str, Any]
    meta: dict[str, Any]
    records: list[dict[str, Any]]


# ============================================================================
# ATTRIBUTION & DEPENDENCY MAPPING SCHEMAS
# ============================================================================

class ConfidenceMixin(BaseModel):
    """Mixin providing confidence tracking for all attribution mappings."""
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 (lowest) to 1.0 (highest)",
    )
    confidence_label: Literal["high", "medium", "low"] = Field(
        ...,
        description="Human-readable confidence classification",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Concrete reasons/evidence supporting this mapping",
    )
    provenance: str = Field(
        ...,
        min_length=1,
        description="Source system that generated this mapping (e.g., 'jira', 'github', 'git', 'manual', 'inferred')",
    )
    ambiguity_flag: bool = Field(
        default=False,
        description="True if this mapping has unresolved ambiguity",
    )
    ambiguity_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons for ambiguity if ambiguity_flag is True",
    )
    manual_review_required: bool = Field(
        default=False,
        description="True if this mapping requires human review",
    )

    @field_validator("confidence_label")
    @classmethod
    def validate_confidence_label(cls, v: str, info: Any) -> str:
        """Ensure confidence_label aligns with confidence_score."""
        score = info.data.get("confidence_score", 0.5)
        expected = "high" if score >= 0.8 else "medium" if score >= 0.5 else "low"
        return v if v == expected else expected


class CanonicalDeveloper(BaseModel):
    """
    Unified developer identity that consolidates multiple source identifiers
    (Jira, GitHub, Git, etc.) into a single canonical record.
    """
    canonical_id: str = Field(
        ...,
        min_length=1,
        description="Unique canonical identifier for this developer",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name for display purposes",
    )
    primary_email: Optional[str] = Field(
        default=None,
        description="Primary email address for this developer",
    )
    primary_team_id: Optional[str] = Field(
        default=None,
        description="Current primary team assignment",
    )
    status: Literal["active", "inactive", "suspended"] = Field(
        default="active",
        description="Current status of the developer record",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional developer metadata (hire_date, location, etc.)",
    )
    # Time-aware fields for auditability
    effective_from: Optional[str] = Field(
        default=None,
        description="ISO timestamp when this record became effective",
    )
    effective_to: Optional[str] = Field(
        default=None,
        description="ISO timestamp when this record expires (null = current)",
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was last updated",
    )


class IdentityAlias(BaseModel):
    """
    Maps a source system identifier to a canonical developer identity.
    Used to resolve "alice@github.com" and "alice.smith@company.com" to the
    same canonical developer "alice-smith-001".
    """
    alias_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this alias mapping",
    )
    source_system: str = Field(
        ...,
        min_length=1,
        description="Source system (e.g., 'jira', 'github', 'gitlab', 'git', 'azure_devops')",
    )
    source_identifier: str = Field(
        ...,
        min_length=1,
        description="Identifier in the source system (username, email, ID)",
    )
    canonical_id: str = Field(
        ...,
        min_length=1,
        description="Reference to the canonical developer identity",
    )
    alias_type: Literal["email", "username", "employee_id", "sso_id", "api_key"] = Field(
        default="username",
        description="Type of identifier being mapped",
    )
    is_primary: bool = Field(
        default=False,
        description="True if this is the primary alias for this source system",
    )
    # Time-aware fields
    effective_from: Optional[str] = Field(
        default=None,
        description="ISO timestamp when this alias became effective",
    )
    effective_to: Optional[str] = Field(
        default=None,
        description="ISO timestamp when this alias expires (null = current)",
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was created",
    )
    # Confidence and evidence from mixin
    confidence_score: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
    )
    confidence_label: Literal["high", "medium", "low"] = Field(default="high")
    evidence: list[str] = Field(default_factory=list)
    provenance: str = Field(
        default="manual",
        description="Source of this mapping (e.g., 'hr_system', 'manual', 'inferred')",
    )
    ambiguity_flag: bool = Field(default=False)
    ambiguity_reasons: list[str] = Field(default_factory=list)
    manual_review_required: bool = Field(default=False)


class TeamMembership(BaseModel):
    """
    Tracks developer membership in teams over time.
    Supports historical queries via effective_from/effective_to dates.
    """
    membership_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this membership record",
    )
    canonical_id: str = Field(
        ...,
        min_length=1,
        description="Reference to the canonical developer identity",
    )
    team_id: str = Field(
        ...,
        min_length=1,
        description="Team identifier",
    )
    role: Literal["developer", "senior_developer", "tech_lead", "architect", "contractor", "intern"] = Field(
        default="developer",
        description="Role within the team",
    )
    allocation_percent: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Percentage of time allocated to this team",
    )
    status: Literal["active", "pending", "transferred", "inactive"] = Field(
        default="active",
        description="Current status of this membership",
    )
    # Time-aware fields
    effective_from: str = Field(
        ...,
        min_length=1,
        description="ISO timestamp when membership became effective",
    )
    effective_to: Optional[str] = Field(
        default=None,
        description="ISO timestamp when membership ended (null = current)",
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was last updated",
    )
    # Confidence and evidence
    confidence_score: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
    )
    confidence_label: Literal["high", "medium", "low"] = Field(default="high")
    evidence: list[str] = Field(default_factory=list)
    provenance: str = Field(
        default="hr_system",
        description="Source of this mapping (e.g., 'hr_system', 'manual', 'jira')",
    )
    ambiguity_flag: bool = Field(default=False)
    ambiguity_reasons: list[str] = Field(default_factory=list)
    manual_review_required: bool = Field(default=False)


class ManagerMapping(BaseModel):
    """
    Maps teams to their managers, supporting hierarchical reporting structures.
    """
    mapping_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this manager mapping",
    )
    team_id: str = Field(
        ...,
        min_length=1,
        description="Team identifier",
    )
    manager_canonical_id: str = Field(
        ...,
        min_length=1,
        description="Canonical ID of the team manager",
    )
    manager_role: Literal["engineering_manager", "product_manager", "team_lead", "director", "vp"] = Field(
        default="engineering_manager",
        description="Type of management role",
    )
    is_primary: bool = Field(
        default=True,
        description="True if this is the primary manager for the team",
    )
    # Time-aware fields
    effective_from: str = Field(
        ...,
        min_length=1,
        description="ISO timestamp when this mapping became effective",
    )
    effective_to: Optional[str] = Field(
        default=None,
        description="ISO timestamp when this mapping ended (null = current)",
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was last updated",
    )
    # Confidence and evidence
    confidence_score: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
    )
    confidence_label: Literal["high", "medium", "low"] = Field(default="high")
    evidence: list[str] = Field(default_factory=list)
    provenance: str = Field(
        default="hr_system",
        description="Source of this mapping (e.g., 'hr_system', 'manual', 'jira')",
    )
    ambiguity_flag: bool = Field(default=False)
    ambiguity_reasons: list[str] = Field(default_factory=list)
    manual_review_required: bool = Field(default=False)


class AttributionDecision(BaseModel):
    """
    Records a decision about which developer owns/is responsible for a work item.
    Includes confidence scoring and evidence for auditability.
    """
    decision_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this attribution decision",
    )
    work_item_id: str = Field(
        ...,
        min_length=1,
        description="Work item being attributed (issue ID, PR ID, commit SHA, etc.)",
    )
    work_item_type: Literal["issue", "pull_request", "commit", "deployment", "requirement", "task"] = Field(
        ...,
        description="Type of work item being attributed",
    )
    canonical_id: str = Field(
        ...,
        min_length=1,
        description="Canonical developer ID this work is attributed to",
    )
    # Attribution factors
    ownership_factors: list[str] = Field(
        default_factory=list,
        description="Factors contributing to this attribution (e.g., 'author', 'assignee', 'reviewer')",
    )
    ownership_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Calculated ownership score based on weighted factors",
    )
    decision_type: Literal["automatic", "manual", "hybrid", "inferred"] = Field(
        default="automatic",
        description="How this decision was made",
    )
    # Time-aware fields
    effective_from: str = Field(
        ...,
        min_length=1,
        description="ISO timestamp when this decision became effective",
    )
    effective_to: Optional[str] = Field(
        default=None,
        description="ISO timestamp when this decision expires (null = current)",
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was last updated",
    )
    # Confidence and evidence (core requirements)
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this attribution decision",
    )
    confidence_label: Literal["high", "medium", "low"] = Field(
        ...,
        description="Human-readable confidence classification",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Concrete evidence supporting this decision (e.g., 'commit authored by developer', 'Jira assignee since 2024-01-15')",
    )
    provenance: str = Field(
        ...,
        min_length=1,
        description="Source system that generated this decision (e.g., 'commit_history', 'jira_api', 'manual_assignment')",
    )
    ambiguity_flag: bool = Field(
        default=False,
        description="True if this attribution has unresolved ambiguity",
    )
    ambiguity_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons for ambiguity (e.g., 'multiple_committers', 'merged_pr_from_fork')",
    )
    manual_review_required: bool = Field(
        default=False,
        description="True if this attribution requires human verification",
    )
    # Review tracking
    reviewed_by: Optional[str] = Field(
        default=None,
        description="Canonical ID of reviewer who verified this decision",
    )
    reviewed_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when this decision was reviewed",
    )


class AmbiguityRecord(BaseModel):
    """
    Tracks unresolved or ambiguous mappings that require human review.
    This is essentially a "todo queue" for attribution cleanup.
    """
    ambiguity_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this ambiguity record",
    )
    work_item_id: str = Field(
        ...,
        min_length=1,
        description="Work item with ambiguous attribution",
    )
    work_item_type: Literal["issue", "pull_request", "commit", "deployment", "requirement", "task"] = Field(
        ...,
        description="Type of work item",
    )
    # Ambiguity details
    ambiguity_type: Literal[
        "multiple_contributors",
        "unknown_author",
        "ambiguous_alias",
        "team_owned",
        "automated_commit",
        "merge_commit",
        "fork_contribution",
        "identity_conflict",
        "other",
    ] = Field(
        ...,
        description="Category of ambiguity",
    )
    possible_canonical_ids: list[str] = Field(
        default_factory=list,
        description="List of possible developer IDs this could be attributed to",
    )
    source_identifiers: list[str] = Field(
        default_factory=list,
        description="Raw identifiers from source systems (emails, usernames, etc.)",
    )
    # Status and resolution
    status: Literal["pending", "in_review", "resolved", "escalated", "deferred"] = Field(
        default="pending",
        description="Current status of this ambiguity",
    )
    resolution: Optional[str] = Field(
        default=None,
        description="How this was resolved (if status is 'resolved')",
    )
    resolved_by: Optional[str] = Field(
        default=None,
        description="Canonical ID of user who resolved this ambiguity",
    )
    resolved_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when resolved",
    )
    # Timestamps
    created_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was last updated",
    )
    # Confidence and evidence
    confidence_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Low confidence due to ambiguity",
    )
    confidence_label: Literal["high", "medium", "low"] = Field(default="low")
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence that led to this ambiguity",
    )
    provenance: str = Field(
        ...,
        min_length=1,
        description="Source system that detected this ambiguity",
    )
    ambiguity_flag: bool = Field(default=True)  # Always True for ambiguity records
    ambiguity_reasons: list[str] = Field(
        ...,
        min_length=1,
        description="Detailed reasons for the ambiguity",
    )
    manual_review_required: bool = Field(default=True)  # Always True for ambiguity records
    # Assignment
    assigned_reviewer: Optional[str] = Field(
        default=None,
        description="Canonical ID of assigned reviewer (if any)",
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        default="medium",
        description="Priority for resolving this ambiguity",
    )


class OwnershipEvidence(BaseModel):
    """
    Tracks individual pieces of evidence for ownership attribution.
    These are weighted factors that contribute to AttributionDecision.
    """
    evidence_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this evidence record",
    )
    decision_id: str = Field(
        ...,
        min_length=1,
        description="Reference to the AttributionDecision this supports",
    )
    evidence_type: Literal[
        "commit_author",
        "commit_committer",
        "pr_author",
        "pr_merger",
        "pr_reviewer",
        "jira_assignee",
        "jira_reporter",
        "jira_commenter",
        "issue_assignee",
        "code_owner",
        "file_path_pattern",
        "review_approval",
        "time_correlation",
        "manual_assignment",
        "inferred_from_team",
    ] = Field(
        ...,
        description="Type of ownership evidence",
    )
    source_identifier: str = Field(
        ...,
        min_length=1,
        description="Identifier in source system (email, username, etc.)",
    )
    canonical_id: str = Field(
        ...,
        min_length=1,
        description="Canonical developer ID this evidence points to",
    )
    # Weighting
    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weight of this evidence factor (0.0 to 1.0)",
    )
    # Source data reference
    source_system: str = Field(
        ...,
        min_length=1,
        description="System where this evidence was found",
    )
    source_reference: str = Field(
        ...,
        min_length=1,
        description="Reference to source data (commit SHA, PR number, etc.)",
    )
    source_timestamp: Optional[str] = Field(
        default=None,
        description="ISO timestamp of the source event",
    )
    # Timestamps
    created_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was created",
    )
    # Confidence and evidence
    confidence_score: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
    )
    confidence_label: Literal["high", "medium", "low"] = Field(default="high")
    evidence: list[str] = Field(
        default_factory=list,
        description="Supporting details for this evidence",
    )
    provenance: str = Field(
        ...,
        min_length=1,
        description="How this evidence was discovered",
    )
    ambiguity_flag: bool = Field(default=False)
    ambiguity_reasons: list[str] = Field(default_factory=list)
    manual_review_required: bool = Field(default=False)


class DependencyEdge(BaseModel):
    """
    Represents a cross-team dependency relationship between work items.
    """
    edge_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this dependency edge",
    )
    source_work_item_id: str = Field(
        ...,
        min_length=1,
        description="Work item that has the dependency (depends on target)",
    )
    source_work_item_type: Literal["issue", "pull_request", "commit", "deployment", "requirement", "task"] = Field(
        ...,
        description="Type of source work item",
    )
    source_team_id: str = Field(
        ...,
        min_length=1,
        description="Team that owns the source work item",
    )
    target_work_item_id: str = Field(
        ...,
        min_length=1,
        description="Work item that is depended upon",
    )
    target_work_item_type: Literal["issue", "pull_request", "commit", "deployment", "requirement", "task"] = Field(
        ...,
        description="Type of target work item",
    )
    target_team_id: str = Field(
        ...,
        min_length=1,
        description="Team that owns the target work item",
    )
    # Dependency classification
    dependency_type: Literal[
        "blocks",
        "depends_on",
        "relates_to",
        "duplicates",
        "parent_child",
        "references",
    ] = Field(
        default="depends_on",
        description="Nature of the dependency relationship",
    )
    strength: Literal["strong", "moderate", "weak"] = Field(
        default="moderate",
        description="Strength of the dependency",
    )
    is_cross_team: bool = Field(
        ...,
        description="True if this dependency crosses team boundaries",
    )
    # Status
    status: Literal["active", "resolved", "broken", "deprecated"] = Field(
        default="active",
        description="Current status of this dependency",
    )
    # Time-aware fields
    detected_at: str = Field(
        ...,
        min_length=1,
        description="ISO timestamp when this dependency was detected",
    )
    resolved_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when this dependency was resolved (if applicable)",
    )
    effective_from: str = Field(
        ...,
        min_length=1,
        description="ISO timestamp when this edge became effective",
    )
    effective_to: Optional[str] = Field(
        default=None,
        description="ISO timestamp when this edge expires (null = current)",
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when record was last updated",
    )
    # Confidence and evidence
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this dependency detection",
    )
    confidence_label: Literal["high", "medium", "low"] = Field(
        ...,
        description="Human-readable confidence classification",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Concrete evidence of this dependency (e.g., 'PR references issue #123', 'commit message mentions JIRA-456')",
    )
    provenance: str = Field(
        ...,
        min_length=1,
        description="Source system that detected this dependency (e.g., 'jira_link', 'pr_description', 'commit_message', 'manual')",
    )
    ambiguity_flag: bool = Field(default=False)
    ambiguity_reasons: list[str] = Field(default_factory=list)
    manual_review_required: bool = Field(default=False)
    # Detection metadata
    detection_method: Literal[
        "jira_link",
        "pr_description_reference",
        "commit_message_reference",
        "github_linked_issue",
        "file_dependency",
        "api_contract",
        "manual_annotation",
        "inferred_from_timing",
    ] = Field(
        ...,
        description="Method used to detect this dependency",
    )


class AttributionSummaryResponse(BaseModel):
    """Response model for attribution summary queries."""
    developer_id: str
    work_items_count: int
    attributed_by_type: dict[str, int]
    confidence_distribution: dict[str, int]
    pending_ambiguities: int
    last_updated: str


class DependencyGraphResponse(BaseModel):
    """Response model for dependency graph queries."""
    nodes: list[dict[str, Any]]
    edges: list[DependencyEdge]
    cross_team_count: int
    high_confidence_edges: int
    low_confidence_edges: int
    generated_at: str


class SkillEvidenceItem(BaseModel):
    """Evidence item for a skill."""
    commit_id: str
    timestamp: str
    impact_score: float
    file_paths: list[str]
    detection_method: str


class DeveloperSkillItem(BaseModel):
    """Individual skill item for a developer."""
    skill_tag: str
    skill_category: str
    score: float
    confidence_score: float
    confidence_label: Literal["high", "medium", "low"]
    frequency_score: float
    recency_score: float
    complexity_score: float
    churn_score: float
    evidence_count: int
    evidence_commits: list[SkillEvidenceItem]
    last_commit_at: Optional[str] = None


class DeveloperSkillsResponse(BaseModel):
    """Response model for developer skills query."""
    developer_id: str
    developer_name: Optional[str] = None
    developer_email: Optional[str] = None
    skills: list[DeveloperSkillItem]
    top_skill: Optional[str] = None
    skill_count: int
    calculated_at: str
    expires_at: Optional[str] = None
    
    @field_validator("skills")
    @classmethod
    def validate_skills(cls, v):
        # Sort skills by score descending
        return sorted(v, key=lambda x: x.score, reverse=True)
