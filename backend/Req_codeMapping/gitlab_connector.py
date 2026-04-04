"""
GitLab connector implementation for DevHouse26 delivery timeline.

This connector integrates with GitLab's REST API to fetch merge requests,
CI pipeline runs, and deployment events.

API Documentation:
- Merge Requests: https://docs.gitlab.com/ee/api/merge_requests.html
- Pipelines: https://docs.gitlab.com/ee/api/pipelines.html
- Deployments: https://docs.gitlab.com/ee/api/deployments.html

Authentication:
- Personal Access Token (scope: api, read_repository)
- OAuth 2.0 token
- Job token (for CI/CD integration)

Rate Limits:
- GitLab.com: 600 requests/minute per user
- Self-hosted: Configurable
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


class GitLabConnector(ProviderConnector):
    """
    GitLab connector for fetching delivery timeline data.

    Integrates with GitLab REST API to fetch:
    - Merge requests (/projects/:id/merge_requests)
    - CI pipeline runs (/projects/:id/pipelines)
    - Deployments (/projects/:id/deployments)

    Example:
        >>> connector = GitLabConnector(api_token="glpat-xxxxx")
        >>> repo_filter = RepositoryFilter(repo_id="12345")
        >>> for mr in connector.get_pull_requests(repo_filter):
        ...     print(f"MR !{mr.id}: {mr.title}")
    """

    DEFAULT_API_URL = "https://gitlab.com/api/v4"
    PROVIDER_NAME = "gitlab"
    CONNECTOR_VERSION = "0.1.0"

    def __init__(
        self,
        api_token: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: int = 30,
        **kwargs: Any,
    ):
        """
        Initialize GitLab connector.

        Args:
            api_token: GitLab Personal Access Token or OAuth token
            api_url: Custom API URL for self-hosted GitLab
            timeout: Request timeout in seconds
            **kwargs: Additional configuration options
        """
        super().__init__(api_token, api_url, **kwargs)
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout = timeout
        self._session = None

    def get_metadata(self) -> ConnectorMetadata:
        """Return connector metadata."""
        is_authenticated = self._test_authentication()

        return ConnectorMetadata(
            provider=self.PROVIDER_NAME,
            connector_version=self.CONNECTOR_VERSION,
            api_version="v4",
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
                rate_limit_per_hour=36000 if self.api_token else 600,  # 600/min
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
        if self.api_token:
            headers["PRIVATE-TOKEN"] = self.api_token
        return headers

    def _get_project_path(self, repo_filter: RepositoryFilter) -> str:
        """Convert repo filter to GitLab project path."""
        if repo_filter.repo_id:
            return f"projects/{repo_filter.repo_id}"
        elif repo_filter.owner and repo_filter.repo_name:
            # URL encode the path
            path = f"{repo_filter.owner}/{repo_filter.repo_name}"
            return f"projects/{path.replace('/', '%2F')}"
        else:
            raise ConnectorAPIError("Either repo_id or owner+repo_name required")

    def get_pull_requests(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedPullRequest]:
        """
        Fetch merge requests from GitLab.

        GitLab API Endpoint:
            GET /projects/:id/merge_requests?state=all

        Args:
            repo_filter: Repository to fetch MRs from
            time_filter: Time-range filter for incremental sync
            pagination: Pagination state

        Yields:
            NormalizedPullRequest objects
        """
        project_path = self._get_project_path(repo_filter)
        endpoint = f"{self.api_url}/{project_path}/merge_requests"

        params = {
            "state": "all",
            "per_page": pagination.per_page if pagination else 30,
            "page": pagination.page if pagination else 1,
            "order_by": "updated_at",
            "sort": "desc",
        }

        if time_filter and time_filter.since:
            params["updated_after"] = datetime_to_iso(time_filter.since)

        # TODO: Implement actual API call
        # For now, return empty iterator (implement when needed)
        return
        yield  # Make this a generator

    def _normalize_pull_request(self, gitlab_mr: dict[str, Any]) -> NormalizedPullRequest:
        """Convert GitLab MR API response to normalized schema."""
        # Map GitLab MR states to normalized status
        state = gitlab_mr.get("state", "unknown")
        is_merged = gitlab_mr.get("state") == "merged"
        is_draft = gitlab_mr.get("draft", False) or gitlab_mr.get("work_in_progress", False)

        status_map = {
            "merged": "merged",
            "opened": "open",
            "closed": "closed",
        }

        return NormalizedPullRequest(
            id=str(gitlab_mr["iid"]),  # Internal ID (like MR number)
            url=gitlab_mr["web_url"],
            status=status_map.get(state, state),
            is_draft=is_draft,
            is_merged=is_merged,
            title=gitlab_mr["title"],
            description=gitlab_mr.get("description"),
            author=gitlab_mr["author"]["username"],
            author_display_name=gitlab_mr["author"].get("name") or gitlab_mr["author"]["username"],
            reviewers=[r["username"] for r in gitlab_mr.get("reviewers", [])],
            approvers=[],  # Need separate API call for approvals
            repository_name=gitlab_mr["references"]["full"].split("!")[0].strip(),
            source_branch=gitlab_mr["source_branch"],
            target_branch=gitlab_mr["target_branch"],
            head_commit_sha=gitlab_mr["sha"],
            created_at=gitlab_mr["created_at"],
            updated_at=gitlab_mr["updated_at"],
            merged_at=gitlab_mr.get("merged_at"),
            closed_at=gitlab_mr.get("closed_at"),
            additions=gitlab_mr.get("changes_count"),  # Approximate
            provider=self.PROVIDER_NAME,
            fetched_at=datetime_to_iso(datetime.utcnow()),
            raw_metadata=gitlab_mr,
        )

    def get_ci_runs(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedCIRun]:
        """
        Fetch GitLab CI pipeline runs.

        GitLab API Endpoint:
            GET /projects/:id/pipelines

        Args:
            repo_filter: Repository to fetch pipelines from
            time_filter: Time-range filter
            pagination: Pagination state

        Yields:
            NormalizedCIRun objects
        """
        project_path = self._get_project_path(repo_filter)
        endpoint = f"{self.api_url}/{project_path}/pipelines"

        params = {
            "per_page": pagination.per_page if pagination else 30,
            "page": pagination.page if pagination else 1,
            "order_by": "updated_at",
            "sort": "desc",
        }

        if time_filter and time_filter.since:
            params["updated_after"] = datetime_to_iso(time_filter.since)

        # TODO: Implement actual API call
        return
        yield

    def _normalize_ci_run(self, gitlab_pipeline: dict[str, Any]) -> NormalizedCIRun:
        """Convert GitLab pipeline to normalized schema."""
        # Map GitLab pipeline status to normalized
        status_map = {
            "running": "running",
            "pending": "queued",
            "success": "completed",
            "failed": "completed",
            "canceled": "completed",
            "skipped": "completed",
        }

        conclusion_map = {
            "success": "success",
            "failed": "failure",
            "canceled": "cancelled",
            "skipped": "skipped",
        }

        return NormalizedCIRun(
            id=str(gitlab_pipeline["id"]),
            status=status_map.get(gitlab_pipeline["status"], "unknown"),
            conclusion=conclusion_map.get(gitlab_pipeline["status"]),
            name=f"Pipeline #{gitlab_pipeline['id']}",
            display_title=gitlab_pipeline.get("source"),
            trigger_event=gitlab_pipeline.get("source"),
            triggered_by=gitlab_pipeline.get("user", {}).get("username"),
            commit_sha=gitlab_pipeline["sha"],
            branch=gitlab_pipeline.get("ref"),
            pull_request_number=None,  # Can be derived from MR API
            created_at=gitlab_pipeline["created_at"],
            updated_at=gitlab_pipeline["updated_at"],
            provider=self.PROVIDER_NAME,
            fetched_at=datetime_to_iso(datetime.utcnow()),
            raw_metadata=gitlab_pipeline,
        )

    def get_deployments(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedDeployment]:
        """
        Fetch GitLab deployments.

        GitLab API Endpoint:
            GET /projects/:id/deployments

        Args:
            repo_filter: Repository to fetch deployments from
            time_filter: Time-range filter
            pagination: Pagination state

        Yields:
            NormalizedDeployment objects
        """
        project_path = self._get_project_path(repo_filter)
        endpoint = f"{self.api_url}/{project_path}/deployments"

        params = {
            "per_page": pagination.per_page if pagination else 30,
            "page": pagination.page if pagination else 1,
        }

        if time_filter and time_filter.since:
            params["updated_after"] = datetime_to_iso(time_filter.since)

        # TODO: Implement actual API call
        return
        yield

    def _normalize_deployment(self, gitlab_deployment: dict[str, Any]) -> NormalizedDeployment:
        """Convert GitLab deployment to normalized schema."""
        status_map = {
            "created": "pending",
            "running": "in_progress",
            "success": "success",
            "failed": "failed",
            "canceled": "cancelled",
        }

        return NormalizedDeployment(
            id=str(gitlab_deployment["id"]),
            status=status_map.get(gitlab_deployment.get("status"), "unknown"),
            environment=gitlab_deployment["environment"]["name"],
            environment_url=gitlab_deployment.get("environment", {}).get("external_url"),
            description=gitlab_deployment.get("ref"),
            deployed_by=gitlab_deployment.get("user", {}).get("username"),
            commit_sha=gitlab_deployment["sha"],
            ref=gitlab_deployment["ref"],
            created_at=gitlab_deployment["created_at"],
            updated_at=gitlab_deployment["updated_at"],
            deployed_at=gitlab_deployment.get("finished_at"),
            provider=self.PROVIDER_NAME,
            fetched_at=datetime_to_iso(datetime.utcnow()),
            raw_metadata=gitlab_deployment,
        )
