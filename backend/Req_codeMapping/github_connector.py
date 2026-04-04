"""
GitHub connector implementation for DevHouse26 delivery timeline.

This connector integrates with GitHub's REST API to fetch pull requests,
CI workflow runs (GitHub Actions), and deployment events.

API Documentation:
- Pull Requests: https://docs.github.com/en/rest/pulls/pulls
- Actions Runs: https://docs.github.com/en/rest/actions/workflow-runs
- Deployments: https://docs.github.com/en/rest/deployments/deployments

Authentication:
- Personal Access Token (classic) with scopes: repo, workflow, read:org
- GitHub App installation token
- Fine-grained token with appropriate permissions

Rate Limits:
- Authenticated: 5,000 requests/hour
- Unauthenticated: 60 requests/hour
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


class GitHubConnector(ProviderConnector):
    """
    GitHub connector for fetching delivery timeline data.

    Integrates with GitHub REST API v3 to fetch:
    - Pull requests (/repos/{owner}/{repo}/pulls)
    - CI workflow runs (/repos/{owner}/{repo}/actions/runs)
    - Deployments (/repos/{owner}/{repo}/deployments)

    Example:
        >>> connector = GitHubConnector(api_token="ghp_xxxxx")
        >>> repo_filter = RepositoryFilter(owner="myorg", repo_name="myapp")
        >>> for pr in connector.get_pull_requests(repo_filter):
        ...     print(f"PR #{pr.id}: {pr.title}")
    """

    DEFAULT_API_URL = "https://api.github.com"
    PROVIDER_NAME = "github"
    CONNECTOR_VERSION = "0.1.0"

    def __init__(
        self,
        api_token: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: int = 30,
        **kwargs: Any,
    ):
        """
        Initialize GitHub connector.

        Args:
            api_token: GitHub Personal Access Token or App installation token
            api_url: Custom API URL for GitHub Enterprise Server
            timeout: Request timeout in seconds
            **kwargs: Additional configuration options
        """
        super().__init__(api_token, api_url, **kwargs)
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout = timeout
        self._session = None  # TODO: Initialize requests.Session with retry logic

    def get_metadata(self) -> ConnectorMetadata:
        """
        Return connector metadata.

        Returns:
            ConnectorMetadata with GitHub provider info
        """
        # TODO: Test authentication by making a lightweight API call
        # Example: GET /user or GET /rate_limit
        is_authenticated = self._test_authentication()

        return ConnectorMetadata(
            provider=self.PROVIDER_NAME,
            connector_version=self.CONNECTOR_VERSION,
            api_version="v3",  # GitHub REST API v3
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
                rate_limit_per_hour=5000 if self.api_token else 60,
            ),
        )

    def _test_authentication(self) -> bool:
        """
        Test if API token is valid.

        Returns:
            True if authenticated, False otherwise
        """
        # TODO: Implement authentication test
        # Example:
        #   response = requests.get(f"{self.api_url}/user", headers=self._headers())
        #   return response.status_code == 200
        return bool(self.api_token)

    def _headers(self) -> dict[str, str]:
        """
        Build request headers with authentication.

        Returns:
            Headers dictionary for API requests
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def get_pull_requests(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedPullRequest]:
        """
        Fetch pull requests from GitHub.

        GitHub API Endpoint:
            GET /repos/{owner}/{repo}/pulls?state=all&sort=updated&direction=desc

        API Response Schema (key fields):
            {
                "id": 123456,
                "number": 42,
                "state": "open",
                "title": "Add new feature",
                "body": "Description...",
                "user": {"login": "username", "id": 789},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
                "merged_at": "2024-01-02T10:30:00Z",
                "closed_at": "2024-01-02T10:30:00Z",
                "merged": true,
                "draft": false,
                "head": {"ref": "feature-branch", "sha": "abc123"},
                "base": {"ref": "main", "sha": "def456"},
                "html_url": "https://github.com/owner/repo/pull/42",
                "additions": 100,
                "deletions": 50,
                "changed_files": 5,
                "commits": 3,
                "requested_reviewers": [{"login": "reviewer1"}],
                "labels": [{"name": "bug"}]
            }

        Args:
            repo_filter: Repository to fetch PRs from
            time_filter: Time-range filter for incremental sync
            pagination: Pagination state

        Yields:
            NormalizedPullRequest objects

        Raises:
            ConnectorAuthError: If authentication fails
            ConnectorNotFoundError: If repository not found
        """
        # TODO: Implement actual API calls
        # Pseudocode:
        #
        # 1. Validate repo_filter has owner and repo_name
        # 2. Build API URL: f"{self.api_url}/repos/{owner}/{repo}/pulls"
        # 3. Add query parameters:
        #    - state=all (to get open, closed, merged)
        #    - sort=updated (for incremental sync)
        #    - direction=desc (newest first)
        #    - page={pagination.page}
        #    - per_page={pagination.per_page}
        # 4. Make GET request with timeout and retries
        # 5. Handle errors:
        #    - 401/403: raise ConnectorAuthError
        #    - 404: raise ConnectorNotFoundError
        #    - 429: raise ConnectorRateLimitError with retry_after
        #    - 5xx: retry with exponential backoff
        # 6. Parse response JSON (list of PR objects)
        # 7. For each PR in response:
        #    - If time_filter.since: skip if pr.updated_at < time_filter.since
        #    - Convert to NormalizedPullRequest using _normalize_pull_request()
        #    - Yield normalized PR
        # 8. If response has Link header with next page:
        #    - Update pagination.cursor
        #    - Continue fetching next page
        #
        # Example mapping:
        #   GitHub "number" → NormalizedPullRequest.id
        #   GitHub "state" + "merged" → NormalizedPullRequest.status
        #   GitHub "user.login" → NormalizedPullRequest.author
        #   GitHub "html_url" → NormalizedPullRequest.url
        #   Store full API response in raw_metadata

        raise NotImplementedError("get_pull_requests not yet implemented")

    def _normalize_pull_request(self, github_pr: dict[str, Any]) -> NormalizedPullRequest:
        """
        Convert GitHub PR API response to normalized schema.

        Args:
            github_pr: Raw GitHub API PR object

        Returns:
            NormalizedPullRequest with mapped fields
        """
        # TODO: Implement schema mapping
        # Key mappings:
        #   id: str(github_pr["number"])  # PR number is more useful than internal ID
        #   status: "merged" if github_pr["merged"] else github_pr["state"]
        #   is_merged: github_pr.get("merged", False)
        #   is_draft: github_pr.get("draft", False)
        #   title: github_pr["title"]
        #   description: github_pr.get("body")
        #   author: github_pr["user"]["login"]
        #   author_display_name: github_pr["user"]["name"] or github_pr["user"]["login"]
        #   reviewers: [u["login"] for u in github_pr.get("requested_reviewers", [])]
        #   approvers: [] (need separate API call to /pulls/{pr}/reviews)
        #   repository_name: github_pr["base"]["repo"]["name"]
        #   repository_owner: github_pr["base"]["repo"]["owner"]["login"]
        #   repository_url: github_pr["base"]["repo"]["html_url"]
        #   source_branch: github_pr["head"]["ref"]
        #   target_branch: github_pr["base"]["ref"]
        #   head_commit_sha: github_pr["head"]["sha"]
        #   base_commit_sha: github_pr["base"]["sha"]
        #   commit_count: github_pr.get("commits")
        #   created_at: github_pr["created_at"]
        #   updated_at: github_pr["updated_at"]
        #   merged_at: github_pr.get("merged_at")
        #   closed_at: github_pr.get("closed_at")
        #   additions: github_pr.get("additions")
        #   deletions: github_pr.get("deletions")
        #   changed_files: github_pr.get("changed_files")
        #   labels: [label["name"] for label in github_pr.get("labels", [])]
        #   provider: "github"
        #   fetched_at: datetime_to_iso(datetime.utcnow())
        #   raw_metadata: github_pr (entire API response)

        return NormalizedPullRequest(
            id=str(github_pr["number"]),
            url=github_pr["html_url"],
            status=self._normalize_pr_status(github_pr),
            is_draft=github_pr.get("draft", False),
            is_merged=github_pr.get("merged", False),
            title=github_pr["title"],
            # TODO: Map remaining fields
            provider=self.PROVIDER_NAME,
            fetched_at=datetime_to_iso(datetime.utcnow()),
            raw_metadata=github_pr,
        )

    def _normalize_pr_status(self, github_pr: dict[str, Any]) -> str:
        """Map GitHub PR state to normalized status."""
        if github_pr.get("merged"):
            return "merged"
        if github_pr.get("draft"):
            return "draft"
        return github_pr.get("state", "unknown")  # "open" or "closed"

    def get_ci_runs(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedCIRun]:
        """
        Fetch GitHub Actions workflow runs.

        GitHub API Endpoint:
            GET /repos/{owner}/{repo}/actions/runs

        API Response Schema (key fields):
            {
                "id": 123456,
                "name": "CI",
                "display_title": "Run CI tests",
                "run_number": 42,
                "status": "completed",
                "conclusion": "success",
                "event": "push",
                "actor": {"login": "username"},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:05:00Z",
                "run_started_at": "2024-01-01T00:00:30Z",
                "run_attempt": 1,
                "html_url": "https://github.com/owner/repo/actions/runs/123456",
                "head_branch": "main",
                "head_sha": "abc123",
                "pull_requests": [{"number": 42, "url": "..."}]
            }

        Args:
            repo_filter: Repository to fetch runs from
            time_filter: Time-range filter for incremental sync
            pagination: Pagination state

        Yields:
            NormalizedCIRun objects
        """
        # TODO: Implement actual API calls
        # Similar pattern to get_pull_requests but for:
        #   GET /repos/{owner}/{repo}/actions/runs?status=all
        #
        # Query parameters:
        #   - created: filter by date range (e.g., ">=2024-01-01")
        #   - page, per_page for pagination
        #
        # Mapping:
        #   GitHub "id" → NormalizedCIRun.id
        #   GitHub "status" → NormalizedCIRun.status
        #   GitHub "conclusion" → NormalizedCIRun.conclusion
        #   GitHub "event" → NormalizedCIRun.trigger_event
        #   GitHub "actor.login" → NormalizedCIRun.triggered_by
        #
        # Note: May need to make additional API calls to get job details:
        #   GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs

        raise NotImplementedError("get_ci_runs not yet implemented")

    def _normalize_ci_run(self, github_run: dict[str, Any]) -> NormalizedCIRun:
        """
        Convert GitHub Actions run to normalized schema.

        Args:
            github_run: Raw GitHub API workflow run object

        Returns:
            NormalizedCIRun with mapped fields
        """
        # TODO: Implement schema mapping
        # Key mappings:
        #   id: str(github_run["id"])
        #   url: github_run["html_url"]
        #   status: github_run["status"]
        #   conclusion: github_run.get("conclusion")
        #   name: github_run["name"]
        #   display_title: github_run.get("display_title")
        #   run_number: github_run["run_number"]
        #   trigger_event: github_run["event"]
        #   triggered_by: github_run["actor"]["login"]
        #   commit_sha: github_run["head_sha"]
        #   branch: github_run.get("head_branch")
        #   pull_request_number: github_run["pull_requests"][0]["number"] if github_run["pull_requests"] else None
        #   created_at: github_run["created_at"]
        #   started_at: github_run.get("run_started_at")
        #   updated_at: github_run["updated_at"]
        #   provider: "github"
        #   fetched_at: datetime_to_iso(datetime.utcnow())
        #   raw_metadata: github_run

        return NormalizedCIRun(
            id=str(github_run["id"]),
            status=github_run["status"],
            provider=self.PROVIDER_NAME,
            fetched_at=datetime_to_iso(datetime.utcnow()),
            raw_metadata=github_run,
        )

    def get_deployments(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedDeployment]:
        """
        Fetch GitHub deployment events.

        GitHub API Endpoint:
            GET /repos/{owner}/{repo}/deployments

        Note: GitHub deployments are split into two concepts:
        1. Deployment (the request to deploy)
        2. Deployment Status (the result of deployment)

        Need to fetch both:
        - GET /repos/{owner}/{repo}/deployments
        - GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses

        API Response Schema (deployment):
            {
                "id": 123456,
                "sha": "abc123",
                "ref": "main",
                "task": "deploy",
                "environment": "production",
                "description": "Deploy to prod",
                "creator": {"login": "username"},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:05:00Z"
            }

        API Response Schema (deployment status):
            {
                "state": "success",
                "environment_url": "https://app.example.com",
                "created_at": "2024-01-01T00:05:00Z",
                "updated_at": "2024-01-01T00:05:30Z"
            }

        Args:
            repo_filter: Repository to fetch deployments from
            time_filter: Time-range filter for incremental sync
            pagination: Pagination state

        Yields:
            NormalizedDeployment objects
        """
        # TODO: Implement actual API calls
        # Steps:
        # 1. Fetch deployments: GET /repos/{owner}/{repo}/deployments
        # 2. For each deployment:
        #    a. Fetch statuses: GET /repos/{owner}/{repo}/deployments/{id}/statuses
        #    b. Get latest status (first item in array)
        #    c. Combine deployment + status into NormalizedDeployment
        #    d. Yield normalized deployment
        #
        # Mapping:
        #   GitHub "id" → NormalizedDeployment.id
        #   GitHub "environment" → NormalizedDeployment.environment
        #   GitHub status "state" → NormalizedDeployment.status
        #   GitHub "creator.login" → NormalizedDeployment.deployed_by
        #   GitHub "sha" → NormalizedDeployment.commit_sha
        #   GitHub "ref" → NormalizedDeployment.ref
        #   GitHub status "environment_url" → NormalizedDeployment.environment_url

        raise NotImplementedError("get_deployments not yet implemented")

    def _normalize_deployment(
        self,
        github_deployment: dict[str, Any],
        github_status: Optional[dict[str, Any]] = None,
    ) -> NormalizedDeployment:
        """
        Convert GitHub deployment + status to normalized schema.

        Args:
            github_deployment: Raw GitHub deployment object
            github_status: Latest deployment status (optional)

        Returns:
            NormalizedDeployment with mapped fields
        """
        # TODO: Implement schema mapping
        # Key mappings:
        #   id: str(github_deployment["id"])
        #   status: github_status["state"] if github_status else "unknown"
        #   environment: github_deployment["environment"]
        #   environment_url: github_status.get("environment_url") if github_status else None
        #   description: github_deployment.get("description")
        #   task: github_deployment.get("task")
        #   deployed_by: github_deployment["creator"]["login"]
        #   commit_sha: github_deployment["sha"]
        #   ref: github_deployment["ref"]
        #   created_at: github_deployment["created_at"]
        #   updated_at: github_status["updated_at"] if github_status else github_deployment["updated_at"]
        #   deployed_at: github_status["created_at"] if github_status and github_status["state"] == "success" else None
        #   provider: "github"
        #   fetched_at: datetime_to_iso(datetime.utcnow())
        #   raw_metadata: {"deployment": github_deployment, "status": github_status}

        return NormalizedDeployment(
            id=str(github_deployment["id"]),
            environment=github_deployment["environment"],
            provider=self.PROVIDER_NAME,
            fetched_at=datetime_to_iso(datetime.utcnow()),
            raw_metadata={"deployment": github_deployment, "status": github_status},
        )


# Future: GitLabConnector, BitbucketConnector, etc. would follow same pattern
