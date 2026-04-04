"""
GitHub Connector for DevHouse26

Production-ready connector for GitHub API with pagination, rate limiting,
and comprehensive error handling.
"""

import os
import time
import logging
from typing import Optional, Iterator, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


@dataclass
class ConnectorMetadata:
    """Metadata about the connector capabilities."""
    provider_name: str
    provider_version: str
    supports_pull_requests: bool
    supports_ci_runs: bool
    supports_deployments: bool
    supports_webhooks: bool
    base_url: str


@dataclass
class NormalizedPullRequest:
    """Normalized pull request data."""
    id: str
    number: int
    title: str
    status: str  # open, closed, merged, draft
    is_draft: bool
    is_merged: bool
    author: str
    author_display_name: str
    source_branch: str
    target_branch: str
    head_commit_sha: str
    base_commit_sha: str
    created_at: datetime
    updated_at: Optional[datetime]
    merged_at: Optional[datetime]
    url: str
    additions: int
    deletions: int
    changed_files: int


@dataclass
class NormalizedCIRun:
    """Normalized CI/CD run data."""
    id: str
    run_number: int
    name: str
    status: str  # success, failure, pending, running
    conclusion: Optional[str]
    commit_sha: str
    branch: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    url: str
    duration_seconds: Optional[int]


@dataclass
class NormalizedDeployment:
    """Normalized deployment data."""
    id: str
    status: str  # success, failure, pending, in_progress
    environment: str
    commit_sha: str
    created_at: datetime
    updated_at: Optional[datetime]
    deployed_at: Optional[datetime]
    url: str
    duration_seconds: Optional[int]


class GitHubConnector:
    """
    Production-ready GitHub API connector.
    
    Features:
    - Pagination support
    - Rate limit handling with exponential backoff
    - Connection pooling
    - Enterprise GitHub support
    - Comprehensive error handling
    """
    
    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize GitHub connector.
        
        Args:
            token: GitHub personal access token (or from DEVHOUSE_GITHUB_TOKEN env var)
            base_url: Base URL for GitHub Enterprise (or from DEVHOUSE_GITHUB_ENTERPRISE_URL)
        """
        self.token = token or os.getenv('DEVHOUSE_GITHUB_TOKEN')
        self.base_url = base_url or os.getenv(
            'DEVHOUSE_GITHUB_ENTERPRISE_URL', 
            'https://api.github.com'
        )
        self.session: Optional[requests.Session] = None
        self.per_page = 100
        
        # Ensure base_url ends with /api/v3 for enterprise
        if 'github.com' not in self.base_url and not self.base_url.endswith('/api/v3'):
            self.base_url = urljoin(self.base_url, '/api/v3')
    
    def connect(self) -> None:
        """Initialize HTTP session with connection pooling."""
        if self.session is not None:
            logger.debug("Already connected")
            return
            
        if not self.token:
            raise ValueError("GitHub token required. Set DEVHOUSE_GITHUB_TOKEN env var.")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'DevHouse26-GitHubConnector/1.0'
        })
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=0  # We handle retries manually
        )
        self.session.mount('https://', adapter)
        
        logger.info(f"GitHubConnector connected to {self.base_url}")
    
    def disconnect(self) -> None:
        """Close HTTP session."""
        if self.session:
            self.session.close()
            self.session = None
            logger.info("GitHubConnector disconnected")
    
    def __enter__(self) -> 'GitHubConnector':
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()
    
    def get_metadata(self) -> ConnectorMetadata:
        """Return connector metadata and capabilities."""
        return ConnectorMetadata(
            provider_name='github',
            provider_version='v3',
            supports_pull_requests=True,
            supports_ci_runs=True,
            supports_deployments=True,
            supports_webhooks=True,
            base_url=self.base_url
        )
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry and rate limit handling.
        
        Implements exponential backoff for 5xx errors and
        respects GitHub's rate limit headers.
        """
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
        
        url = urljoin(self.base_url, endpoint)
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff
        
        for attempt in range(max_retries):
            try:
                response = self.session.request(
                    method, 
                    url, 
                    timeout=30,
                    **kwargs
                )
                
                # Handle rate limiting
                if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
                    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                    if remaining == 0:
                        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                        sleep_duration = max(reset_time - int(time.time()), 0) + 1
                        logger.warning(f"Rate limit hit. Sleeping for {sleep_duration}s")
                        time.sleep(sleep_duration)
                        continue  # Retry after rate limit reset
                
                # Handle 429 Too Many Requests
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(f"429 received. Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                
                # Handle server errors (5xx) with retry
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(f"Server error {response.status_code}. Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                
                # Handle authentication errors
                if response.status_code == 401:
                    raise ValueError("GitHub authentication failed. Check your token.")
                
                if response.status_code == 403:
                    raise PermissionError(f"GitHub permission denied: {response.text}")
                
                if response.status_code == 404:
                    raise ValueError(f"Resource not found: {endpoint}")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(f"Request timeout. Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                raise
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(f"Connection error. Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                raise
        
        raise RuntimeError(f"Max retries exceeded for {url}")
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string."""
        if not dt_str:
            return None
        try:
            # Handle Z suffix
            dt_str = dt_str.replace('Z', '+00:00')
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            return None
    
    def get_pull_requests(
        self,
        repo_owner: str,
        repo_name: str,
        state: str = 'all',
        since: Optional[datetime] = None,
        head: Optional[str] = None
    ) -> Iterator[NormalizedPullRequest]:
        """
        Fetch pull requests from GitHub.
        
        Args:
            repo_owner: Repository owner (e.g., 'octocat')
            repo_name: Repository name (e.g., 'hello-world')
            state: PR state filter ('open', 'closed', 'all')
            since: Only PRs updated after this datetime
            head: Filter by head branch (format: 'user:branch')
        
        Yields:
            NormalizedPullRequest objects
        """
        logger.debug(f"Fetching PRs for {repo_owner}/{repo_name} (state={state})")
        
        page = 1
        params = {
            'state': state,
            'per_page': self.per_page,
            'sort': 'updated',
            'direction': 'desc'
        }
        
        if head:
            params['head'] = head
        
        while True:
            params['page'] = page
            
            try:
                data = self._make_request(
                    'GET',
                    f'/repos/{repo_owner}/{repo_name}/pulls',
                    params=params
                )
            except ValueError as e:
                if 'not found' in str(e).lower():
                    logger.warning(f"Repository {repo_owner}/{repo_name} not found")
                    return
                raise
            
            if not data:
                break
            
            for pr in data:
                updated_at = self._parse_datetime(pr.get('updated_at'))
                
                # Filter by since date
                if since and updated_at and updated_at < since:
                    return  # PRs are sorted by updated desc, so we can stop
                
                yield self._normalize_pr(pr)
            
            if len(data) < self.per_page:
                break
            
            page += 1
    
    def _normalize_pr(self, pr: Dict[str, Any]) -> NormalizedPullRequest:
        """Convert GitHub PR to normalized format."""
        return NormalizedPullRequest(
            id=str(pr.get('id')),
            number=pr.get('number', 0),
            title=pr.get('title', ''),
            status=self._map_pr_state(pr.get('state'), pr.get('merged'), pr.get('draft')),
            is_draft=pr.get('draft', False),
            is_merged=pr.get('merged', False),
            author=pr.get('user', {}).get('login', ''),
            author_display_name=pr.get('user', {}).get('login', ''),
            source_branch=pr.get('head', {}).get('ref', ''),
            target_branch=pr.get('base', {}).get('ref', ''),
            head_commit_sha=pr.get('head', {}).get('sha', ''),
            base_commit_sha=pr.get('base', {}).get('sha', ''),
            created_at=self._parse_datetime(pr.get('created_at')) or datetime.now(timezone.utc),
            updated_at=self._parse_datetime(pr.get('updated_at')),
            merged_at=self._parse_datetime(pr.get('merged_at')),
            url=pr.get('html_url', ''),
            additions=pr.get('additions', 0),
            deletions=pr.get('deletions', 0),
            changed_files=pr.get('changed_files', 0)
        )
    
    def _map_pr_state(self, state: str, merged: bool, draft: bool) -> str:
        """Map GitHub PR state to normalized status."""
        if merged:
            return 'merged'
        if draft:
            return 'draft'
        return state  # 'open' or 'closed'
    
    def get_ci_runs(
        self,
        repo_owner: str,
        repo_name: str,
        branch: Optional[str] = None,
        since: Optional[datetime] = None,
        workflow_id: Optional[str] = None
    ) -> Iterator[NormalizedCIRun]:
        """
        Fetch CI/CD workflow runs from GitHub Actions.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            branch: Filter by branch name
            since: Only runs after this datetime
            workflow_id: Filter by specific workflow
        
        Yields:
            NormalizedCIRun objects
        """
        logger.debug(f"Fetching CI runs for {repo_owner}/{repo_name}")
        
        page = 1
        params = {
            'per_page': self.per_page
        }
        
        if branch:
            params['branch'] = branch
        
        if workflow_id:
            endpoint = f'/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_id}/runs'
        else:
            endpoint = f'/repos/{repo_owner}/{repo_name}/actions/runs'
        
        while True:
            params['page'] = page
            
            try:
                data = self._make_request('GET', endpoint, params=params)
            except ValueError as e:
                if 'not found' in str(e).lower():
                    logger.warning(f"Repository {repo_owner}/{repo_name} not found or Actions disabled")
                    return
                raise
            
            runs = data.get('workflow_runs', [])
            if not runs:
                break
            
            for run in runs:
                updated_at = self._parse_datetime(run.get('updated_at'))
                
                if since and updated_at and updated_at < since:
                    return
                
                yield self._normalize_ci_run(run)
            
            if len(runs) < self.per_page:
                break
            
            page += 1
    
    def _normalize_ci_run(self, run: Dict[str, Any]) -> NormalizedCIRun:
        """Convert GitHub Actions run to normalized format."""
        started_at = self._parse_datetime(run.get('run_started_at'))
        completed_at = self._parse_datetime(run.get('updated_at'))
        
        duration = None
        if started_at and completed_at:
            duration = int((completed_at - started_at).total_seconds())
        
        return NormalizedCIRun(
            id=str(run.get('id')),
            run_number=run.get('run_number', 0),
            name=run.get('name', ''),
            status=self._map_ci_status(run.get('status'), run.get('conclusion')),
            conclusion=run.get('conclusion'),
            commit_sha=run.get('head_sha', ''),
            branch=run.get('head_branch', ''),
            started_at=started_at,
            completed_at=completed_at,
            url=run.get('html_url', ''),
            duration_seconds=duration
        )
    
    def _map_ci_status(self, status: str, conclusion: Optional[str]) -> str:
        """Map GitHub Actions status to normalized status."""
        if status == 'completed':
            return conclusion or 'unknown'
        return status  # 'queued', 'in_progress', 'waiting', etc.
    
    def get_deployments(
        self,
        repo_owner: str,
        repo_name: str,
        environment: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Iterator[NormalizedDeployment]:
        """
        Fetch deployment records from GitHub.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            environment: Filter by environment name (e.g., 'production')
            since: Only deployments after this datetime
        
        Yields:
            NormalizedDeployment objects
        """
        logger.debug(f"Fetching deployments for {repo_owner}/{repo_name}")
        
        # Get deployments
        page = 1
        params = {
            'per_page': self.per_page
        }
        
        if environment:
            params['environment'] = environment
        
        while True:
            params['page'] = page
            
            try:
                deployments = self._make_request(
                    'GET',
                    f'/repos/{repo_owner}/{repo_name}/deployments',
                    params=params
                )
            except ValueError as e:
                if 'not found' in str(e).lower():
                    logger.warning(f"Repository {repo_owner}/{repo_name} not found or Deployments disabled")
                    return
                raise
            
            if not deployments:
                break
            
            for deployment in deployments:
                created_at = self._parse_datetime(deployment.get('created_at'))
                
                if since and created_at and created_at < since:
                    return
                
                # Get deployment status
                status_data = self._get_deployment_status(
                    repo_owner, 
                    repo_name, 
                    deployment.get('id')
                )
                
                yield self._normalize_deployment(deployment, status_data)
            
            if len(deployments) < self.per_page:
                break
            
            page += 1
    
    def _get_deployment_status(
        self,
        repo_owner: str,
        repo_name: str,
        deployment_id: int
    ) -> Dict[str, Any]:
        """Get the latest status for a deployment."""
        try:
            statuses = self._make_request(
                'GET',
                f'/repos/{repo_owner}/{repo_name}/deployments/{deployment_id}/statuses',
                params={'per_page': 1}
            )
            return statuses[0] if statuses else {}
        except Exception as e:
            logger.warning(f"Failed to get deployment status: {e}")
            return {}
    
    def _normalize_deployment(
        self,
        deployment: Dict[str, Any],
        status: Dict[str, Any]
    ) -> NormalizedDeployment:
        """Convert GitHub deployment to normalized format."""
        created_at = self._parse_datetime(deployment.get('created_at'))
        updated_at = self._parse_datetime(status.get('created_at'))
        deployed_at = updated_at if status.get('state') == 'success' else None
        
        return NormalizedDeployment(
            id=str(deployment.get('id')),
            status=status.get('state', 'unknown'),
            environment=deployment.get('environment', ''),
            commit_sha=deployment.get('sha', ''),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at,
            deployed_at=deployed_at,
            url=deployment.get('url', ''),
            duration_seconds=None  # GitHub doesn't provide this directly
        )
