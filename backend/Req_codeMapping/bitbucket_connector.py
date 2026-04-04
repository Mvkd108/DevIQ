"""
Bitbucket connector implementation for DevHouse26 delivery timeline.

This connector integrates with Bitbucket's REST API v2.0 to fetch pull requests,
CI pipeline runs (Bitbucket Pipelines), and deployment events.

API Documentation:
- Pull Requests: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/
- Pipelines: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pipelines/
- Deployments: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-deployments/

Authentication:
- App Password (for Bitbucket Cloud)
- OAuth 2.0 (for team/organization access)
- Repository Access Token

Rate Limits:
- Bitbucket Cloud: 1,000 requests/hour per user
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterator, Optional

from connector_base import (
    ConnectorAPIError,
    ConnectorAuthError,
    ConnectorCapabilities,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
    ConnectorTimeoutError,
    PaginationCursor,
    ProviderConnector,
    RepositoryFilter,
    TimeRangeFilter,
)
from connector_schemas import (
    ConnectorMetadata,
    NormalizedCIRun,
    NormalizedDeployment,
    NormalizedPullRequest,
    datetime_to_iso,
)


class BitbucketConnector(ProviderConnector):
    """
    Bitbucket connector for fetching delivery timeline data.

    Integrates with Bitbucket REST API v2.0 to fetch:
    - Pull requests (/repositories/{workspace}/{repo}/pullrequests)
    - Pipeline runs (/repositories/{workspace}/{repo}/pipelines/)
    - Deployments (/repositories/{workspace}/{repo}/environments/)

    Example:
        >>> connector = BitbucketConnector(
        ...     api_token="ATCTT3xFfGNxxxxx",
        ...     username="myuser"
        ... )
        >>> repo_filter = RepositoryFilter(owner="myworkspace", repo_name="myrepo")
        >>> for pr in connector.get_pull_requests(repo_filter):
        ...     print(f"PR #{pr.id}: {pr.title}")
    """

    DEFAULT_API_URL = "https://api.bitbucket.org/2.0"
    PROVIDER_NAME = "bitbucket"
    CONNECTOR_VERSION = "0.1.0"

    def __init__(
        self,
        api_token: Optional[str] = None,
        username: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: int = 30,
        **kwargs: Any,
    ):
        """
        Initialize Bitbucket connector.

        Args:
            api_token: Bitbucket App Password or OAuth token
            username: Bitbucket username (required for App Password auth)
            api_url: Custom API URL for Bitbucket Data Center
            timeout: Request timeout in seconds
            **kwargs: Additional configuration options
        """
        super().__init__(api_token, api_url, **kwargs)
        self.api_url = api_url or self.DEFAULT_API_URL
        self.username = username
        self.timeout = timeout
        self._session = None

    def get_metadata(self) -> ConnectorMetadata:
        """Return connector metadata."""
        is_authenticated = self._test_authentication()

        return ConnectorMetadata(
            provider=self.PROVIDER_NAME,
            connector_version=self.CONNECTOR_VERSION,
            api_version="2.0",
            api_url=self.api_url,
            is_authenticated=is_authenticated,
            capabilities=ConnectorCapabilities(
                supports_pull_requests=True,
                supports_ci_runs=True,
                supports_deployments=True,
                supports_incremental_sync=True,
                supports_pagination=True,
                supports_webhooks=True,
                max_page_size=100,
                rate_limit_per_hour=1000 if self.api_token else 60,
            ),
        )

    def _test_authentication(self) -> bool:
        """Test if API token is valid."""
        return bool(self.api_token)

    def _headers(self) -> dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Accept": "application/json",
        }
        if self.api_token and self.username:
            # Basic auth with App Password
            import base64
            credentials = base64.b64encode(f"{self.username}:{self.api_token}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        elif self.api_token:
            # OAuth Bearer token
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _get_repo_path(self, repo_filter: RepositoryFilter) -> str:
        """Convert repo filter to Bitbucket repository path."""
        workspace = repo_filter.owner
        repo_slug = repo_filter.repo_name

        if not workspace or not repo_slug:
            raise ConnectorAPIError("Both owner (workspace) and repo_name (slug) required")

        return f"repositories/{workspace}/{repo_slug}"

    def get_pull_requests(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedPullRequest]:
        """
        Fetch pull requests from Bitbucket.

        Bitbucket API Endpoint:
            GET /repositories/{workspace}/{repo_slug}/pullrequests?state=ALL

        Args:
            repo_filter: Repository to fetch PRs from
            time_filter: Time-range filter for incremental sync
            pagination: Pagination state

        Yields:
            NormalizedPullRequest objects
        """
        repo_path = self._get_repo_path(repo_filter)
        endpoint = f"{self.api_url}/{repo_path}/pullrequests"

        params = {
            "state": "ALL",
            "sort": "-updated_on",
            "pagelen": pagination.per_page if pagination else 30,
            "page": pagination.page if pagination else 1,
        }

        # Bitbucket uses 'q' for filtering by date
        if time_filter and time_filter.since:
            since_str = datetime_to_iso(time_filter.since)
            params["q"] = f'updated_on>="{since_str}"'

        # TODO: Implement actual API call
        return
        yield

    def _normalize_pull_request(self, bb_pr: dict[str, Any]) -> NormalizedPullRequest:
        """Convert Bitbucket PR API response to normalized schema."""
        # Bitbucket PR states: OPEN, MERGED, DECLINED, SUPERSEDED
        state = bb_pr.get("state", "unknown").lower()
        is_merged = state == "merged"
        is_draft = False  # Bitbucket doesn't have draft PRs natively

        status_map = {
            "open": "open",
            "merged": "merged",
            "declined": "closed",
            "superseded": "closed",
        }

        # Extract branch info
        source_branch = bb_pr.get("source", {}).get("branch", {}).get("name")
        target_branch = bb_pr.get("destination", {}).get("branch", {}).get("name")
        head_commit = bb_pr.get("source", {}).get("commit", {}).get("hash")

        # Extract author
        author_data = bb_pr.get("author", {})
        author_username = author_data.get("username") or author_data.get("account_id", "")
        author_display = author_data.get("display_name") or author_username

        return NormalizedPullRequest(
            id=str(bb_pr["id"]),
            url=bb_pr.get("links", {}).get("html", {}).get("href"),
            status=status_map.get(state, state),
            is_draft=is_draft,
            is_merged=is_merged,
            title=bb_pr["title"],
            description=bb_pr.get("description"),
            author=author_username,
            author_display_name=author_display,
            reviewers=[r.get("username") for r in bb_pr.get("reviewers", [])],
            approvers=[p.get("user", {}).get("username")
                      for p in bb_pr.get("participants", [])
                      if p.get("approved")],
            repository_name=repo_slug if 'repo_slug' in locals() else "",
            source_branch=source_branch,
            target_branch=target_branch,
            head_commit_sha=head_commit,
            created_at=bb_pr["created_on"],
            updated_at=bb_pr["updated_on"],
            merged_at=bb_pr.get("merged_on"),
            closed_at=bb_pr.get("closed_on") or bb_pr.get("declined_on"),
            additions=bb_pr.get("summary", {}).get("added"),
            deletions=bb_pr.get("summary", {}).get("removed"),
            provider=self.PROVIDER_NAME,
            fetched_at=datetime_to_iso(datetime.utcnow()),
            raw_metadata=bb_pr,
        )

    def get_ci_runs(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedCIRun]:
        """
        Fetch Bitbucket Pipeline runs.

        Bitbucket API Endpoint:
            GET /repositories/{workspace}/{repo_slug}/pipelines/

        Args:
            repo_filter: Repository to fetch pipelines from
            time_filter: Time-range filter
            pagination: Pagination state

        Yields:
            NormalizedCIRun objects
        """
        repo_path = self._get_repo_path(repo_filter)
        endpoint = f"{self.api_url}/{repo_path}/pipelines/"

        params = {
            "sort": "-created_on",
            "pagelen": pagination.per_page if pagination else 30,
            "page": pagination.page if pagination else 1,
        }

        # Bitbucket uses 'q' for filtering
        if time_filter and time_filter.since:
            since_str = datetime_to_iso(time_filter.since)
            params["q"] = f'created_on>="{since_str}"'

        # TODO: Implement actual API call
        return
        yield

    def _normalize_ci_run(self, bb_pipeline: dict[str, Any]) -> NormalizedCIRun:
        """Convert Bitbucket pipeline to normalized schema."""
        # Bitbucket states: PENDING, BUILDING, SUCCESSFUL, FAILED, STOPPED, ERROR, PAUSED
        state = bb_pipeline.get("state", {}).get("name", "UNKNOWN").lower()

        status_map = {
            "pending": "queued",
            "building": "running",
            "successful": "completed",
            "failed": "completed",
            "stopped": "completed",
            "error": "completed",
            "paused": "running",
        }

        conclusion_map = {
            "successful": "success",
            "failed": "failure",
            "stopped": "cancelled",
            "error": "failure",
        }

        # Build number
        build_number = bb_pipeline.get("build_number", bb_pipeline.get("uuid", ""))

        # Trigger info
        trigger = bb_pipeline.get("trigger", {})
        trigger_name = trigger.get("name", "unknown")

        return NormalizedCIRun(
            id=str(bb_pipeline["uuid"]),
            status=status_map.get(state, "unknown"),
            conclusion=conclusion_map.get(state),
            name=f"Pipeline #{build_number}",
            display_title=bb_pipeline.get("target", {}).get("ref_name", "Unknown"),
            trigger_event=trigger_name,
            triggered_by=bb_pipeline.get("creator", {}).get("username"),
            commit_sha=bb_pipeline.get("target", {}).get("commit", {}).get("hash"),
            branch=bb_pipeline.get("target", {}).get("ref_name"),
            pull_request_number=None,
            created_at=bb_pipeline["created_on"],
            updated_at=bb_pipeline.get("updated_on") or bb_pipeline["created_on"],
            provider=self.PROVIDER_NAME,
            fetched_at=datetime_to_iso(datetime.utcnow()),
            raw_metadata=bb_pipeline,
        )

    def get_deployments(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedDeployment]:
        """
        Fetch Bitbucket deployments.

        Bitbucket API Endpoint:
            GET /repositories/{workspace}/{repo_slug}/environments/

        Args:
            repo_filter: Repository to fetch deployments from
            time_filter: Time-range filter
            pagination: Pagination state

        Yields:
            NormalizedDeployment objects
        """
        repo_path = self._get_repo_path(repo_filter)
        endpoint = f"{self.api_url}/{repo_path}/environments/"

        params = {
            "pagelen": pagination.per_page if pagination else 30,
            "page": pagination.page if pagination else 1,
        }

        # TODO: Implement actual API call
        return
        yield

    def _normalize_deployment(self, bb_env: dict[str, Any]) -> NormalizedDeployment:
        """Convert Bitbucket environment deployment to normalized schema."""
        # Get latest deployment info
        env_name = bb_env.get("name", "unknown")
        env_type = bb_env.get("environment_type", {}).get("name", "unknown")

        # Bitbucket environment status
        status = bb_env.get("status", {})
        state = status.get("name", "unknown").lower()

        status_map = {
            "pending": "pending",
            "in_progress": "in_progress",
            "successful": "success",
            "failed": "failed",
            "cancelled": "cancelled",
        }

        return NormalizedDeployment(
            id=str(bb_env["uuid"]),
            status=status_map.get(state, "unknown"),
            environment=env_name,
            environment_url=bb_env.get("links", {}).get("self", {}).get("href"),
            description=f"Type: {env_type}",
            deployed_by=None,  # Not directly available in env API
            commit_sha=status.get("commit", {}).get("hash"),
            ref=status.get("branch", {}).get("name"),
            created_at=bb_env["created_on"],
            updated_at=bb_env["updated_on"],
            deployed_at=status.get("created_on"),
            provider=self.PROVIDER_NAME,
            fetched_at=datetime_to_iso(datetime.utcnow()),
            raw_metadata=bb_env,
        )
