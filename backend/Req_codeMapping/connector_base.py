"""
Provider-agnostic connector abstraction layer for DevHouse26.

This module defines the abstract base class that all Git provider connectors
(GitHub, GitLab, Bitbucket, etc.) must implement to provide normalized delivery
timeline data.

Design Principles:
- Provider-agnostic: Works across GitHub, GitLab, Bitbucket, self-hosted Git
- Normalized schemas: Different API schemas mapped to common format
- Incremental sync: Support for time-range filtering and pagination
- Provenance tracking: Know which connector provided which data
- Graceful degradation: Falls back to inference when connector unavailable
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator, Optional

from connector_schemas import (
    ConnectorMetadata,
    NormalizedCIRun,
    NormalizedDeployment,
    NormalizedPullRequest,
    SyncState,
)


@dataclass
class ConnectorCapabilities:
    """Describes what a connector can and cannot do."""

    supports_pull_requests: bool = True
    supports_ci_runs: bool = True
    supports_deployments: bool = True
    supports_incremental_sync: bool = True
    supports_pagination: bool = True
    supports_webhooks: bool = False  # Future: real-time updates
    max_page_size: int = 100
    rate_limit_per_hour: Optional[int] = None


@dataclass
class RepositoryFilter:
    """Filter criteria for querying connector data."""

    owner: Optional[str] = None  # GitHub org/user, GitLab group/user
    repo_name: Optional[str] = None  # Repository name
    repo_id: Optional[str] = None  # Provider-specific ID
    branch: Optional[str] = None  # Filter by specific branch
    include_forks: bool = False  # Include forked repositories


@dataclass
class TimeRangeFilter:
    """Time-based filtering for incremental sync."""

    since: Optional[datetime] = None  # Fetch records updated after this time
    until: Optional[datetime] = None  # Fetch records updated before this time
    sync_state: Optional[SyncState] = None  # Previous sync state for resumption


@dataclass
class PaginationCursor:
    """Cursor-based pagination state."""

    page: int = 1  # Page number (for offset-based pagination)
    per_page: int = 30  # Items per page
    cursor: Optional[str] = None  # Opaque cursor token (for cursor-based pagination)
    has_more: bool = True  # Whether more pages exist
    total_count: Optional[int] = None  # Total items (if known)


class ProviderConnector(ABC):
    """
    Abstract base class for all Git provider connectors.

    Each provider (GitHub, GitLab, Bitbucket) implements this interface to
    provide normalized delivery timeline data. The connector handles:
    - Authentication with provider API
    - API schema normalization
    - Pagination and rate limiting
    - Error handling and retries
    - Provenance tracking

    Usage:
        connector = GitHubConnector(token="ghp_...")
        for pr in connector.get_pull_requests(repo_filter, time_filter):
            # Process normalized PR data
            print(pr.number, pr.title, pr.status)
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        api_url: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Initialize the connector.

        Args:
            api_token: Authentication token for provider API
            api_url: Custom API URL (for self-hosted/enterprise instances)
            **kwargs: Provider-specific configuration options
        """
        self.api_token = api_token
        self.api_url = api_url
        self.config = kwargs

    @abstractmethod
    def get_metadata(self) -> ConnectorMetadata:
        """
        Return connector metadata (name, version, capabilities).

        Returns:
            ConnectorMetadata with provider info and capabilities
        """
        pass

    @abstractmethod
    def get_pull_requests(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedPullRequest]:
        """
        Fetch pull requests from the provider.

        Args:
            repo_filter: Repository filtering criteria
            time_filter: Time-range filtering for incremental sync
            pagination: Pagination state for batched fetching

        Yields:
            NormalizedPullRequest objects

        Raises:
            ConnectorAuthError: Authentication failed
            ConnectorRateLimitError: Rate limit exceeded
            ConnectorAPIError: Provider API error
            ConnectorTimeoutError: Request timeout

        Example:
            >>> filter = RepositoryFilter(owner="myorg", repo_name="myapp")
            >>> time_range = TimeRangeFilter(since=datetime(2024, 1, 1))
            >>> for pr in connector.get_pull_requests(filter, time_range):
            ...     print(f"PR #{pr.number}: {pr.title}")
        """
        pass

    @abstractmethod
    def get_ci_runs(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedCIRun]:
        """
        Fetch CI/CD pipeline runs from the provider.

        Args:
            repo_filter: Repository filtering criteria
            time_filter: Time-range filtering for incremental sync
            pagination: Pagination state for batched fetching

        Yields:
            NormalizedCIRun objects

        Raises:
            ConnectorAuthError: Authentication failed
            ConnectorRateLimitError: Rate limit exceeded
            ConnectorAPIError: Provider API error
            ConnectorTimeoutError: Request timeout

        Example:
            >>> filter = RepositoryFilter(owner="myorg", repo_name="myapp")
            >>> for ci_run in connector.get_ci_runs(filter):
            ...     print(f"CI Run {ci_run.id}: {ci_run.status}")
        """
        pass

    @abstractmethod
    def get_deployments(
        self,
        repo_filter: RepositoryFilter,
        time_filter: Optional[TimeRangeFilter] = None,
        pagination: Optional[PaginationCursor] = None,
    ) -> Iterator[NormalizedDeployment]:
        """
        Fetch deployment records from the provider.

        Args:
            repo_filter: Repository filtering criteria
            time_filter: Time-range filtering for incremental sync
            pagination: Pagination state for batched fetching

        Yields:
            NormalizedDeployment objects

        Raises:
            ConnectorAuthError: Authentication failed
            ConnectorRateLimitError: Rate limit exceeded
            ConnectorAPIError: Provider API error
            ConnectorTimeoutError: Request timeout

        Example:
            >>> filter = RepositoryFilter(owner="myorg", repo_name="myapp")
            >>> for deployment in connector.get_deployments(filter):
            ...     print(f"Deployment to {deployment.environment}: {deployment.status}")
        """
        pass

    def test_connection(self) -> bool:
        """
        Test if connector can authenticate with provider.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            metadata = self.get_metadata()
            return metadata.is_authenticated
        except Exception:
            return False

    def get_capabilities(self) -> ConnectorCapabilities:
        """
        Return connector capabilities.

        Returns:
            ConnectorCapabilities describing what this connector supports
        """
        return self.get_metadata().capabilities


class ConnectorError(Exception):
    """Base exception for connector errors."""

    pass


class ConnectorAuthError(ConnectorError):
    """Authentication with provider failed."""

    pass


class ConnectorRateLimitError(ConnectorError):
    """Provider rate limit exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after  # Seconds until rate limit resets


class ConnectorAPIError(ConnectorError):
    """Provider API returned an error."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ConnectorTimeoutError(ConnectorError):
    """Request to provider timed out."""

    pass


class ConnectorNotFoundError(ConnectorError):
    """Requested resource not found (404)."""

    pass
