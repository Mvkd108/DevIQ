# Connector Testing Plan

## Overview

Comprehensive testing strategy for the connector abstraction layer, ensuring reliability, backward compatibility, and graceful degradation.

## Testing Pyramid

```
                    /\
                   /  \
                  /E2E \           1-2 tests
                 /------\
                /        \
               /Integration\       5-10 tests
              /------------\
             /              \
            /  Unit Tests    \    50+ tests
           /------------------\
```

## 1. Unit Tests

### 1.1 Connector Base Tests

**File:** `tests/test_connector_base.py`

**Test Coverage:**
- Abstract class cannot be instantiated
- Concrete implementations must implement all abstract methods
- ConnectorCapabilities dataclass
- RepositoryFilter validation
- TimeRangeFilter validation
- PaginationCursor state management
- Exception hierarchy

```python
import pytest
from connector_base import (
    ProviderConnector,
    ConnectorCapabilities,
    RepositoryFilter,
    TimeRangeFilter,
    PaginationCursor,
    ConnectorError,
    ConnectorAuthError,
    ConnectorRateLimitError,
)

class TestProviderConnectorAbstract:
    """Test abstract base class behavior."""
    
    def test_cannot_instantiate_abstract_class(self):
        """Abstract ProviderConnector cannot be instantiated."""
        with pytest.raises(TypeError):
            ProviderConnector()
    
    def test_concrete_class_must_implement_methods(self):
        """Concrete connector must implement all abstract methods."""
        class IncompleteConnector(ProviderConnector):
            pass
        
        with pytest.raises(TypeError):
            IncompleteConnector()

class TestConnectorCapabilities:
    """Test ConnectorCapabilities dataclass."""
    
    def test_default_capabilities(self):
        """Default capabilities are reasonable."""
        caps = ConnectorCapabilities()
        assert caps.supports_pull_requests is True
        assert caps.supports_ci_runs is True
        assert caps.supports_deployments is True
        assert caps.max_page_size == 100
    
    def test_custom_capabilities(self):
        """Can customize capabilities."""
        caps = ConnectorCapabilities(
            supports_deployments=False,
            max_page_size=50,
        )
        assert caps.supports_deployments is False
        assert caps.max_page_size == 50

class TestRepositoryFilter:
    """Test RepositoryFilter."""
    
    def test_minimal_filter(self):
        """Can create filter with just repo name."""
        filter = RepositoryFilter(repo_name="myapp")
        assert filter.repo_name == "myapp"
        assert filter.owner is None
    
    def test_full_filter(self):
        """Can create filter with all fields."""
        filter = RepositoryFilter(
            owner="myorg",
            repo_name="myapp",
            branch="main",
        )
        assert filter.owner == "myorg"
        assert filter.repo_name == "myapp"
        assert filter.branch == "main"

class TestExceptionHierarchy:
    """Test connector exception classes."""
    
    def test_auth_error_is_connector_error(self):
        """ConnectorAuthError extends ConnectorError."""
        err = ConnectorAuthError("Invalid token")
        assert isinstance(err, ConnectorError)
    
    def test_rate_limit_error_has_retry_after(self):
        """ConnectorRateLimitError tracks retry_after."""
        err = ConnectorRateLimitError("Rate limited", retry_after=60)
        assert err.retry_after == 60
```

### 1.2 Schema Tests

**File:** `tests/test_connector_schemas.py`

**Test Coverage:**
- Dataclass creation and defaults
- Field type validation
- datetime_to_iso() helper
- Raw metadata storage
- Provenance tracking

```python
import pytest
from datetime import datetime
from connector_schemas import (
    NormalizedPullRequest,
    NormalizedCIRun,
    NormalizedDeployment,
    datetime_to_iso,
)

class TestNormalizedPullRequest:
    """Test NormalizedPullRequest schema."""
    
    def test_minimal_pr(self):
        """Can create PR with just ID."""
        pr = NormalizedPullRequest(id="123")
        assert pr.id == "123"
        assert pr.status == "unknown"
        assert pr.is_merged is False
        assert pr.reviewers == []
    
    def test_full_pr(self):
        """Can create PR with all fields."""
        pr = NormalizedPullRequest(
            id="42",
            url="https://github.com/org/repo/pull/42",
            status="merged",
            is_merged=True,
            title="Add feature",
            author="alice",
            reviewers=["bob", "charlie"],
            source_branch="feature",
            target_branch="main",
            merged_at="2024-01-01T00:00:00Z",
            provider="github",
        )
        assert pr.id == "42"
        assert pr.status == "merged"
        assert len(pr.reviewers) == 2
    
    def test_raw_metadata_preserved(self):
        """Raw API response stored in raw_metadata."""
        raw = {"github_specific": "data"}
        pr = NormalizedPullRequest(id="1", raw_metadata=raw)
        assert pr.raw_metadata == raw

class TestNormalizedCIRun:
    """Test NormalizedCIRun schema."""
    
    def test_minimal_ci_run(self):
        """Can create CI run with just ID."""
        ci = NormalizedCIRun(id="123")
        assert ci.id == "123"
        assert ci.status == "unknown"
        assert ci.has_artifacts is False
    
    def test_duration_calculation(self):
        """Duration can be set explicitly."""
        ci = NormalizedCIRun(id="1", duration_seconds=300)
        assert ci.duration_seconds == 300

class TestDatetimeHelper:
    """Test datetime_to_iso helper."""
    
    def test_none_returns_none(self):
        """None datetime returns None."""
        assert datetime_to_iso(None) is None
    
    def test_naive_datetime_gets_z_suffix(self):
        """Naive datetime gets Z suffix."""
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = datetime_to_iso(dt)
        assert result.endswith("Z")
```

### 1.3 GitHub Connector Tests (Mocked)

**File:** `tests/test_github_connector.py`

**Test Coverage:**
- Connector initialization
- Metadata and capabilities
- Header building
- Response normalization
- Error handling
- Pagination logic

```python
import pytest
from unittest.mock import Mock, patch
from github_connector import GitHubConnector
from connector_base import (
    RepositoryFilter,
    ConnectorAuthError,
    ConnectorNotFoundError,
)
from connector_schemas import NormalizedPullRequest

class TestGitHubConnectorInit:
    """Test GitHubConnector initialization."""
    
    def test_default_api_url(self):
        """Default API URL is github.com."""
        connector = GitHubConnector()
        assert connector.api_url == "https://api.github.com"
    
    def test_custom_api_url(self):
        """Can set custom API URL for GHE."""
        connector = GitHubConnector(api_url="https://github.company.com/api/v3")
        assert connector.api_url == "https://github.company.com/api/v3"
    
    def test_token_stored(self):
        """API token is stored."""
        connector = GitHubConnector(api_token="ghp_test123")
        assert connector.api_token == "ghp_test123"

class TestGitHubConnectorMetadata:
    """Test connector metadata."""
    
    def test_metadata_provider_name(self):
        """Metadata has correct provider name."""
        connector = GitHubConnector()
        metadata = connector.get_metadata()
        assert metadata.provider == "github"
    
    def test_capabilities(self):
        """Capabilities are correct."""
        connector = GitHubConnector(api_token="ghp_test")
        metadata = connector.get_metadata()
        caps = metadata.capabilities
        assert caps.supports_pull_requests is True
        assert caps.supports_ci_runs is True
        assert caps.supports_deployments is True
        assert caps.max_page_size == 100

class TestGitHubConnectorHeaders:
    """Test HTTP header construction."""
    
    def test_headers_without_token(self):
        """Headers without auth token."""
        connector = GitHubConnector()
        headers = connector._headers()
        assert "Accept" in headers
        assert "Authorization" not in headers
    
    def test_headers_with_token(self):
        """Headers include Bearer token."""
        connector = GitHubConnector(api_token="ghp_test123")
        headers = connector._headers()
        assert headers["Authorization"] == "Bearer ghp_test123"

class TestGitHubConnectorNormalization:
    """Test GitHub API response normalization."""
    
    def test_normalize_pr_status_merged(self):
        """Merged PR gets 'merged' status."""
        connector = GitHubConnector()
        github_pr = {
            "number": 42,
            "state": "closed",
            "merged": True,
            "draft": False,
            "title": "Test PR",
            "html_url": "https://github.com/org/repo/pull/42",
        }
        status = connector._normalize_pr_status(github_pr)
        assert status == "merged"
    
    def test_normalize_pr_status_draft(self):
        """Draft PR gets 'draft' status."""
        connector = GitHubConnector()
        github_pr = {"draft": True, "state": "open", "merged": False}
        status = connector._normalize_pr_status(github_pr)
        assert status == "draft"
    
    def test_normalize_pr_full(self):
        """Full PR normalization."""
        connector = GitHubConnector()
        github_pr = {
            "number": 42,
            "state": "open",
            "title": "Add feature",
            "body": "Description",
            "html_url": "https://github.com/org/repo/pull/42",
            "user": {"login": "alice"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "merged_at": None,
            "merged": False,
            "draft": False,
            "head": {"ref": "feature", "sha": "abc123"},
            "base": {"ref": "main", "sha": "def456"},
            "additions": 100,
            "deletions": 50,
        }
        pr = connector._normalize_pull_request(github_pr)
        assert isinstance(pr, NormalizedPullRequest)
        assert pr.id == "42"
        assert pr.title == "Add feature"
        assert pr.provider == "github"
```

## 2. Integration Tests

### 2.1 Connector with Mocked API

**File:** `tests/test_connector_integration.py`

**Test Coverage:**
- End-to-end connector flow with mocked HTTP responses
- Pagination handling
- Time-range filtering
- Error recovery

```python
import pytest
import responses
from github_connector import GitHubConnector
from connector_base import RepositoryFilter, TimeRangeFilter

class TestGitHubConnectorIntegration:
    """Integration tests with mocked GitHub API."""
    
    @responses.activate
    def test_get_pull_requests_success(self):
        """Fetch PRs successfully from mocked API."""
        # Mock GitHub API response
        responses.add(
            responses.GET,
            "https://api.github.com/repos/myorg/myapp/pulls",
            json=[
                {
                    "number": 1,
                    "state": "open",
                    "title": "First PR",
                    "html_url": "https://github.com/myorg/myapp/pull/1",
                    "user": {"login": "alice"},
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "merged": False,
                    "draft": False,
                },
                {
                    "number": 2,
                    "state": "merged",
                    "title": "Second PR",
                    "html_url": "https://github.com/myorg/myapp/pull/2",
                    "user": {"login": "bob"},
                    "created_at": "2024-01-02T00:00:00Z",
                    "updated_at": "2024-01-02T12:00:00Z",
                    "merged_at": "2024-01-02T12:00:00Z",
                    "merged": True,
                    "draft": False,
                },
            ],
            status=200,
        )
        
        connector = GitHubConnector(api_token="ghp_test")
        repo_filter = RepositoryFilter(owner="myorg", repo_name="myapp")
        
        prs = list(connector.get_pull_requests(repo_filter))
        
        assert len(prs) == 2
        assert prs[0].id == "1"
        assert prs[0].status == "open"
        assert prs[1].id == "2"
        assert prs[1].status == "merged"
    
    @responses.activate
    def test_get_pull_requests_auth_error(self):
        """Handle authentication error."""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/myorg/myapp/pulls",
            json={"message": "Bad credentials"},
            status=401,
        )
        
        connector = GitHubConnector(api_token="invalid")
        repo_filter = RepositoryFilter(owner="myorg", repo_name="myapp")
        
        with pytest.raises(ConnectorAuthError):
            list(connector.get_pull_requests(repo_filter))
    
    @responses.activate
    def test_get_pull_requests_not_found(self):
        """Handle repository not found."""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/myorg/nonexistent/pulls",
            json={"message": "Not Found"},
            status=404,
        )
        
        connector = GitHubConnector(api_token="ghp_test")
        repo_filter = RepositoryFilter(owner="myorg", repo_name="nonexistent")
        
        with pytest.raises(ConnectorNotFoundError):
            list(connector.get_pull_requests(repo_filter))
```

### 2.2 Timeline Integration with Connector

**File:** `tests/test_delivery_timeline_with_connector.py`

**Test Coverage:**
- Timeline with connector enabled
- Fallback to inference when connector fails
- Provenance tracking
- Backward compatibility

```python
import pytest
from unittest.mock import Mock
from delivery_timeline import build_delivery_timeline_response
from connector_schemas import NormalizedPullRequest

class TestDeliveryTimelineWithConnector:
    """Test delivery timeline with connector integration."""
    
    def test_timeline_without_connector(self):
        """Timeline works without connector (backward compatibility)."""
        issue = {"issue_id": "ISSUE-1", "title": "Test"}
        events = []
        
        timeline = build_delivery_timeline_response(issue, events)
        
        assert timeline["issue_id"] == "ISSUE-1"
        # Should use inference or mock
        assert timeline["provenance_rollup"] in ("inferred", "mock")
    
    def test_timeline_with_connector_success(self):
        """Timeline uses connector when available."""
        issue = {"issue_id": "ISSUE-1", "title": "Test"}
        events = [
            {
                "repository_name": "myapp",
                "repository_owner": "myorg",
                "pull_request_number": 42,
            }
        ]
        
        # Mock connector
        mock_connector = Mock()
        mock_connector.get_pull_requests.return_value = [
            NormalizedPullRequest(
                id="42",
                title="Real PR from GitHub",
                status="merged",
                provider="github",
            )
        ]
        
        timeline = build_delivery_timeline_response(
            issue, events, connector=mock_connector
        )
        
        assert timeline["pull_request"]["source"] == "connector"
        assert timeline["pull_request"]["title"] == "Real PR from GitHub"
        assert "github" in timeline["pull_request"]["provenance_detail"]
    
    def test_timeline_connector_fails_gracefully(self):
        """Timeline falls back when connector fails."""
        issue = {"issue_id": "ISSUE-1", "title": "Test"}
        events = []
        
        # Mock connector that raises error
        mock_connector = Mock()
        mock_connector.get_pull_requests.side_effect = Exception("API down")
        
        # Should not crash, should fall back to inference
        timeline = build_delivery_timeline_response(
            issue, events, connector=mock_connector
        )
        
        assert timeline["issue_id"] == "ISSUE-1"
        # Should fall back to inference/mock
        assert timeline["provenance_rollup"] in ("inferred", "mock")
```

## 3. End-to-End Tests

### 3.1 Real API Tests (Optional, Requires Credentials)

**File:** `tests/test_github_connector_e2e.py`

**Test Coverage:**
- Real GitHub API calls (skipped if no token)
- Rate limiting behavior
- Pagination across multiple pages
- Real data validation

```python
import pytest
import os
from github_connector import GitHubConnector
from connector_base import RepositoryFilter

@pytest.mark.skipif(
    not os.getenv("DEVHOUSE_GITHUB_TOKEN"),
    reason="No GitHub token available"
)
class TestGitHubConnectorE2E:
    """E2E tests against real GitHub API (requires token)."""
    
    def test_fetch_real_pull_requests(self):
        """Fetch real PRs from public repo."""
        token = os.getenv("DEVHOUSE_GITHUB_TOKEN")
        connector = GitHubConnector(api_token=token)
        
        # Use a well-known public repo
        repo_filter = RepositoryFilter(
            owner="octocat",
            repo_name="Hello-World",
        )
        
        prs = list(connector.get_pull_requests(repo_filter))
        
        # Should get some PRs (may be 0 if repo has none)
        assert isinstance(prs, list)
        if prs:
            assert prs[0].provider == "github"
            assert prs[0].id is not None
```

## 4. Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py                    # Pytest fixtures
├── test_connector_base.py         # Unit: Abstract base class
├── test_connector_schemas.py      # Unit: Schema dataclasses
├── test_github_connector.py       # Unit: GitHub connector (mocked)
├── test_connector_integration.py  # Integration: Full flow (mocked API)
├── test_delivery_timeline_with_connector.py  # Integration: Timeline + connector
├── test_github_connector_e2e.py   # E2E: Real API (optional)
└── fixtures/
    ├── github_pr_response.json    # Sample GitHub API responses
    ├── github_ci_response.json
    └── github_deployment_response.json
```

### Shared Fixtures

**File:** `tests/conftest.py`

```python
import pytest
from github_connector import GitHubConnector
from connector_schemas import NormalizedPullRequest, NormalizedCIRun

@pytest.fixture
def mock_github_connector():
    """Mock GitHub connector for testing."""
    return GitHubConnector(api_token="ghp_test_token")

@pytest.fixture
def sample_normalized_pr():
    """Sample normalized pull request."""
    return NormalizedPullRequest(
        id="42",
        url="https://github.com/org/repo/pull/42",
        status="merged",
        title="Test PR",
        author="alice",
        reviewers=["bob", "charlie"],
        provider="github",
        fetched_at="2024-01-01T00:00:00Z",
    )

@pytest.fixture
def sample_github_pr_response():
    """Sample GitHub API PR response."""
    return {
        "number": 42,
        "state": "closed",
        "title": "Test PR",
        "body": "Description",
        "html_url": "https://github.com/org/repo/pull/42",
        "user": {"login": "alice", "id": 123},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "merged_at": "2024-01-02T00:00:00Z",
        "closed_at": "2024-01-02T00:00:00Z",
        "merged": True,
        "draft": False,
        "head": {"ref": "feature", "sha": "abc123"},
        "base": {"ref": "main", "sha": "def456"},
        "additions": 100,
        "deletions": 50,
        "changed_files": 5,
        "commits": 3,
    }
```

## 5. Test Execution

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Suite
```bash
# Unit tests only
pytest tests/test_connector_base.py tests/test_connector_schemas.py -v

# Integration tests only
pytest tests/test_connector_integration.py -v

# Exclude E2E tests (no real API calls)
pytest tests/ -v -m "not e2e"
```

### Coverage Report
```bash
pytest tests/ --cov=connector_base --cov=connector_schemas --cov=github_connector --cov-report=html
```

### Continuous Integration
```yaml
# .github/workflows/test.yml
name: Test Connectors

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov responses
      - run: pytest tests/ --cov --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## 6. Backward Compatibility Tests

**Critical:** Ensure existing 22 tests still pass.

```bash
# Run existing test suite
pytest tests/test_delivery_timeline.py -v

# Should output:
# ✓ 22 passed
```

**Strategy:**
1. Run existing tests before any changes
2. Add connector parameter with default `None`
3. Run existing tests again - should still pass
4. Add new connector tests
5. Verify all tests pass together

## 7. Manual Testing Checklist

- [ ] Start app with no GitHub token → Connector disabled, uses inference
- [ ] Start app with invalid GitHub token → Connector disabled (auth fails), uses inference
- [ ] Start app with valid GitHub token → Connector enabled and authenticated
- [ ] Fetch timeline for issue with real PR → Uses GitHub API data
- [ ] Fetch timeline for issue without PR → Uses inference
- [ ] Fetch timeline when GitHub API is down → Falls back to inference
- [ ] Fetch timeline when rate limited → Falls back to inference
- [ ] Check provenance tracking → Shows "github_api" for connector data
- [ ] Check cache → Second request doesn't hit API (within TTL)
- [ ] Monitor logs → See connector usage metrics

## Success Criteria

- ✅ All existing 22 tests pass
- ✅ New unit tests achieve >90% code coverage
- ✅ Integration tests cover all error scenarios
- ✅ Backward compatibility maintained (connector=None works)
- ✅ Graceful degradation on connector failures
- ✅ Provenance tracking accurate
- ✅ Documentation clear for future implementers
