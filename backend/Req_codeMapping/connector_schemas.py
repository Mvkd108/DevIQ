"""
Normalized data schemas for provider-agnostic connector abstraction.

These dataclasses define the common schema that all provider connectors
(GitHub, GitLab, Bitbucket) must normalize their API responses into.

Design Principles:
- Provider-agnostic: Common fields work across all Git providers
- Provenance tracking: Every record knows where it came from
- Raw metadata preservation: Provider-specific data stored separately
- Timestamp consistency: All times are UTC ISO 8601 strings
- Nullable fields: Handle missing data gracefully
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ConnectorMetadata:
    """Metadata about the connector itself."""

    provider: str  # "github", "gitlab", "bitbucket", etc.
    connector_version: str  # Connector implementation version
    api_version: Optional[str] = None  # Provider API version
    api_url: Optional[str] = None  # Base API URL (for self-hosted)
    is_authenticated: bool = False  # Whether API token is valid
    capabilities: Optional[Any] = None  # ConnectorCapabilities (avoid circular import)


@dataclass
class SyncState:
    """
    State tracking for incremental synchronization.

    Stores the last successful sync information so subsequent syncs
    can fetch only new/updated records.
    """

    repository_id: str  # Unique repo identifier
    provider: str  # Provider name
    last_sync_at: datetime  # When last sync completed
    last_pr_sync_cursor: Optional[str] = None  # Last cursor for PRs
    last_ci_sync_cursor: Optional[str] = None  # Last cursor for CI runs
    last_deployment_sync_cursor: Optional[str] = None  # Last cursor for deployments
    sync_metadata: dict[str, Any] = field(default_factory=dict)  # Provider-specific state


@dataclass
class NormalizedPullRequest:
    """
    Normalized pull request record across all Git providers.

    Common fields present in GitHub PRs, GitLab MRs, Bitbucket PRs, etc.
    Provider-specific data stored in raw_metadata.
    """

    # Primary identifiers
    id: str  # Provider-specific unique ID (GitHub PR number, GitLab MR IID, etc.)
    url: Optional[str] = None  # Web URL to view PR/MR

    # Status and lifecycle
    status: str = "unknown"  # "open", "merged", "closed", "draft", "unknown"
    is_draft: bool = False  # Draft/WIP status
    is_merged: bool = False  # Whether PR was merged

    # Content
    title: Optional[str] = None  # PR title
    description: Optional[str] = None  # PR description/body

    # People
    author: Optional[str] = None  # PR author username/email
    author_display_name: Optional[str] = None  # PR author display name
    reviewers: list[str] = field(default_factory=list)  # Requested reviewers
    approvers: list[str] = field(default_factory=list)  # Who approved the PR

    # Repository context
    repository_name: Optional[str] = None  # Repo name
    repository_owner: Optional[str] = None  # Repo owner/org
    repository_url: Optional[str] = None  # Repo URL

    # Branch information
    source_branch: Optional[str] = None  # Head branch
    target_branch: Optional[str] = None  # Base branch (usually main/master)

    # Commit information
    head_commit_sha: Optional[str] = None  # Latest commit in PR
    base_commit_sha: Optional[str] = None  # Base commit being merged into
    commit_count: Optional[int] = None  # Number of commits in PR

    # Timestamps (all UTC ISO 8601 strings)
    created_at: Optional[str] = None  # When PR was created
    updated_at: Optional[str] = None  # Last update time
    merged_at: Optional[str] = None  # When PR was merged (if merged)
    closed_at: Optional[str] = None  # When PR was closed (if closed)

    # Review and CI status
    review_status: Optional[str] = None  # "approved", "changes_requested", "pending"
    ci_status: Optional[str] = None  # "success", "failure", "pending", "running"
    mergeable_status: Optional[str] = None  # "mergeable", "conflicting", "unknown"

    # Metrics
    additions: Optional[int] = None  # Lines added
    deletions: Optional[int] = None  # Lines deleted
    changed_files: Optional[int] = None  # Files changed
    comments_count: Optional[int] = None  # Number of comments

    # Labels and metadata
    labels: list[str] = field(default_factory=list)  # PR labels/tags
    milestone: Optional[str] = None  # Milestone name

    # Provenance
    provider: str = "unknown"  # "github", "gitlab", "bitbucket", etc.
    fetched_at: Optional[str] = None  # When this record was fetched (UTC ISO 8601)
    raw_metadata: dict[str, Any] = field(default_factory=dict)  # Original API response


@dataclass
class NormalizedCIRun:
    """
    Normalized CI/CD run record across all Git providers.

    Represents a pipeline run, workflow run, build, etc.
    Maps GitHub Actions runs, GitLab CI pipelines, Bitbucket Pipelines, etc.
    """

    # Primary identifiers
    id: str  # Provider-specific unique ID
    url: Optional[str] = None  # Web URL to view CI run

    # Status and lifecycle
    status: str = "unknown"  # "success", "failure", "pending", "running", "cancelled", "skipped", "unknown"
    conclusion: Optional[str] = None  # Final result: "success", "failure", "cancelled", "timed_out"

    # Identity
    name: Optional[str] = None  # Workflow/pipeline name
    display_title: Optional[str] = None  # Human-readable title
    run_number: Optional[int] = None  # Sequential run number

    # Trigger information
    trigger_event: Optional[str] = None  # "push", "pull_request", "schedule", "manual", etc.
    triggered_by: Optional[str] = None  # User who triggered the run

    # Repository context
    repository_name: Optional[str] = None  # Repo name
    repository_owner: Optional[str] = None  # Repo owner/org
    repository_url: Optional[str] = None  # Repo URL

    # Commit and branch
    commit_sha: Optional[str] = None  # Commit SHA being tested
    branch: Optional[str] = None  # Branch name
    ref: Optional[str] = None  # Git ref (refs/heads/main, refs/tags/v1.0, etc.)

    # Pull request association
    pull_request_number: Optional[int] = None  # Associated PR number (if triggered by PR)
    pull_request_url: Optional[str] = None  # Associated PR URL

    # Timestamps (all UTC ISO 8601 strings)
    created_at: Optional[str] = None  # When run was created
    started_at: Optional[str] = None  # When run started executing
    completed_at: Optional[str] = None  # When run finished
    updated_at: Optional[str] = None  # Last update time

    # Duration
    duration_seconds: Optional[int] = None  # Total run duration in seconds

    # Jobs and stages
    job_count: Optional[int] = None  # Number of jobs in pipeline
    failed_job_count: Optional[int] = None  # Number of failed jobs
    jobs: list[dict[str, Any]] = field(default_factory=list)  # Job details (optional)

    # Artifacts and logs
    has_artifacts: bool = False  # Whether run produced artifacts
    log_url: Optional[str] = None  # URL to logs

    # Provenance
    provider: str = "unknown"  # "github", "gitlab", "bitbucket", etc.
    fetched_at: Optional[str] = None  # When this record was fetched (UTC ISO 8601)
    raw_metadata: dict[str, Any] = field(default_factory=dict)  # Original API response


@dataclass
class NormalizedDeployment:
    """
    Normalized deployment record across all Git providers.

    Represents a deployment event to an environment.
    Maps GitHub Deployments, GitLab Deployments, Bitbucket Deployments, etc.
    """

    # Primary identifiers
    id: str  # Provider-specific unique ID
    url: Optional[str] = None  # Web URL to view deployment

    # Status and lifecycle
    status: str = "unknown"  # "success", "failure", "pending", "in_progress", "queued", "cancelled", "unknown"
    state: Optional[str] = None  # Deployment state (provider-specific)

    # Environment
    environment: str = "unknown"  # "production", "staging", "development", "qa", etc.
    environment_url: Optional[str] = None  # URL of deployed environment

    # Identity
    description: Optional[str] = None  # Deployment description
    task: Optional[str] = None  # Deployment task type ("deploy", "rollback", etc.)

    # Actor
    deployed_by: Optional[str] = None  # User who triggered deployment
    deployed_by_display_name: Optional[str] = None  # Display name

    # Repository context
    repository_name: Optional[str] = None  # Repo name
    repository_owner: Optional[str] = None  # Repo owner/org
    repository_url: Optional[str] = None  # Repo URL

    # Commit and branch
    commit_sha: Optional[str] = None  # Deployed commit SHA
    branch: Optional[str] = None  # Deployed branch
    ref: Optional[str] = None  # Git ref

    # Timestamps (all UTC ISO 8601 strings)
    created_at: Optional[str] = None  # When deployment was created
    started_at: Optional[str] = None  # When deployment started
    deployed_at: Optional[str] = None  # When deployment completed successfully
    updated_at: Optional[str] = None  # Last update time

    # Duration
    duration_seconds: Optional[int] = None  # Deployment duration in seconds

    # Associated CI run
    ci_run_id: Optional[str] = None  # Associated CI run ID
    ci_run_url: Optional[str] = None  # Associated CI run URL

    # Pull request association
    pull_request_number: Optional[int] = None  # Associated PR number
    pull_request_url: Optional[str] = None  # Associated PR URL

    # Version information
    version: Optional[str] = None  # Deployed version/tag
    release_name: Optional[str] = None  # Release name

    # Provenance
    provider: str = "unknown"  # "github", "gitlab", "bitbucket", etc.
    fetched_at: Optional[str] = None  # When this record was fetched (UTC ISO 8601)
    raw_metadata: dict[str, Any] = field(default_factory=dict)  # Original API response


# Helper function to convert datetime to ISO 8601 string
def datetime_to_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to UTC ISO 8601 string."""
    if dt is None:
        return None
    return dt.isoformat() + "Z" if dt.tzinfo is None else dt.isoformat()
