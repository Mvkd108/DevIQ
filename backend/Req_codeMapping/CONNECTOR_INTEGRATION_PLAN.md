# Connector Integration Plan

## Overview

This document outlines how to integrate the connector abstraction layer into `delivery_timeline.py` to enable real GitHub/GitLab/Bitbucket data while maintaining backward compatibility with inference-based timeline.

## Integration Strategy

### 1. Connector Instantiation

**Decision: Application Startup (Singleton Pattern)**

Instantiate connectors once at application startup and reuse them across requests.

**Rationale:**
- Connectors maintain HTTP session pools and rate limit state
- Avoid overhead of creating new sessions per request
- Centralized configuration and credential management

**Implementation Location:** `main.py`

```python
# main.py
from github_connector import GitHubConnector
from typing import Optional
import os

# Global connector instances
_github_connector: Optional[GitHubConnector] = None

def initialize_connectors():
    """Initialize all connectors at startup."""
    global _github_connector
    
    github_token = os.getenv("DEVHOUSE_GITHUB_TOKEN")
    github_url = os.getenv("DEVHOUSE_GITHUB_ENTERPRISE_URL")
    
    if github_token:
        _github_connector = GitHubConnector(
            api_token=github_token,
            api_url=github_url,
        )
        if _github_connector.test_connection():
            print(f"✓ GitHub connector initialized and authenticated")
        else:
            print(f"⚠ GitHub connector initialized but authentication failed")
            _github_connector = None
    else:
        print(f"ℹ GitHub connector disabled (no token provided)")

def get_github_connector() -> Optional[GitHubConnector]:
    """Get the global GitHub connector instance."""
    return _github_connector

# Call during app startup
@app.on_event("startup")
async def startup_event():
    initialize_connectors()
```

### 2. Pass Connector to Timeline Functions

**Current Function Signature:**
```python
def build_delivery_timeline_response(
    issue: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    ...
```

**New Signature (Backward Compatible):**
```python
def build_delivery_timeline_response(
    issue: dict[str, Any],
    events: list[dict[str, Any]],
    connector: Optional[ProviderConnector] = None,
) -> dict[str, Any]:
    ...
```

**Key Points:**
- `connector` parameter is optional (default `None`)
- If `None`, existing inference logic is used
- If provided, connector data is used with fallback to inference

### 3. Modify Extract Functions to Use Connector

**Current Pattern:**
```python
def extract_pull_request_record(events: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    # Parse events looking for connector fields
    ...
```

**New Pattern:**
```python
def extract_pull_request_record(
    events: list[dict[str, Any]],
    connector: Optional[ProviderConnector] = None,
    repo_context: Optional[dict[str, str]] = None,
) -> Optional[dict[str, Any]]:
    """
    Extract PR record from connector or events.
    
    Args:
        events: Existing event stream (may contain connector webhooks)
        connector: Optional connector for fetching real data
        repo_context: Repository context (owner, repo_name) for connector queries
    
    Returns:
        PR record dict or None
    """
    # STRATEGY 1: Try connector first (highest trust)
    if connector and repo_context:
        pr_record = fetch_pr_from_connector(connector, repo_context, events)
        if pr_record:
            return pr_record
    
    # STRATEGY 2: Parse events for connector webhook data
    pr_record = extract_pr_from_events(events)
    if pr_record:
        return pr_record
    
    # STRATEGY 3: No connector data found
    return None

def fetch_pr_from_connector(
    connector: ProviderConnector,
    repo_context: dict[str, str],
    events: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Fetch PR data from live connector."""
    try:
        # Extract PR number from events if available
        pr_number = extract_pr_number_from_events(events)
        if not pr_number:
            return None
        
        # Build repo filter
        repo_filter = RepositoryFilter(
            owner=repo_context["owner"],
            repo_name=repo_context["repo_name"],
        )
        
        # Fetch PRs from connector (may need to filter by number)
        for normalized_pr in connector.get_pull_requests(repo_filter):
            if normalized_pr.id == str(pr_number):
                # Convert NormalizedPullRequest → stage record format
                return convert_normalized_pr_to_stage_record(normalized_pr)
        
        return None
    except (ConnectorAPIError, ConnectorAuthError, ConnectorTimeoutError) as e:
        # Log error but don't crash - fall back to inference
        print(f"Connector error fetching PR: {e}")
        return None

def convert_normalized_pr_to_stage_record(pr: NormalizedPullRequest) -> dict[str, Any]:
    """Convert normalized PR schema to delivery_timeline stage record format."""
    return build_stage_record(
        source="connector",
        status=pr.status,
        summary=f"PR #{pr.id}" if pr.id else "Pull request",
        note="Connector-backed pull request metadata.",
        provenance_detail="github connector",
        evidence=[
            f"PR #{pr.id} from GitHub API",
            f"Status: {pr.status}",
            f"Author: {pr.author}" if pr.author else None,
        ],
        number=int(pr.id) if pr.id and pr.id.isdigit() else None,
        title=pr.title,
        author=pr.author or pr.author_display_name,
        url=pr.url,
        merged_at=pr.merged_at,
        created_at=pr.created_at,
        updated_at=pr.updated_at,
        reviewers=pr.reviewers,
        source_branch=pr.source_branch,
        target_branch=pr.target_branch,
        additions=pr.additions,
        deletions=pr.deletions,
        changed_files=pr.changed_files,
        # Store raw metadata for debugging
        raw_connector_data=pr.raw_metadata,
    )
```

### 4. Repository Context Extraction

Need to determine repository owner/name for connector queries.

**Options:**

**Option A: Extract from events**
```python
def extract_repo_context(events: list[dict[str, Any]], issue: dict[str, Any]) -> Optional[dict[str, str]]:
    """Extract repository owner and name from events or issue."""
    # Try from events first
    for event in events:
        repo_name = event.get("repository_name")
        repo_owner = event.get("repository_owner")
        if repo_name and repo_owner:
            return {"owner": repo_owner, "repo_name": repo_name}
        
        # Try nested repository object
        repo = event.get("repository", {})
        if isinstance(repo, dict):
            full_name = repo.get("full_name")  # "owner/repo"
            if full_name and "/" in full_name:
                owner, name = full_name.split("/", 1)
                return {"owner": owner, "repo_name": name}
    
    # Try from issue metadata
    repo_url = issue.get("repository_url")
    if repo_url:
        # Parse github.com/owner/repo from URL
        return parse_repo_from_url(repo_url)
    
    return None
```

**Option B: Pass as parameter to build_delivery_timeline_response**
```python
def build_delivery_timeline_response(
    issue: dict[str, Any],
    events: list[dict[str, Any]],
    connector: Optional[ProviderConnector] = None,
    repository: Optional[dict[str, str]] = None,  # {"owner": "...", "repo_name": "..."}
) -> dict[str, Any]:
    ...
```

**Recommendation:** Use Option A with fallback to Option B for flexibility.

### 5. Backward Compatibility

**Ensure existing tests pass:**

```python
# Current usage (no changes needed)
timeline = build_delivery_timeline_response(issue, events)
# Works as before - uses inference only

# New usage (opt-in to connector)
from main import get_github_connector
connector = get_github_connector()
timeline = build_delivery_timeline_response(issue, events, connector=connector)
# Uses connector + inference fallback
```

**Migration Path:**
1. Phase 1: Add connector parameter (optional, default None)
2. Phase 2: Test with connector enabled for subset of requests
3. Phase 3: Enable connector by default, keep inference as fallback
4. Phase 4: Monitor provenance metrics (connector vs inferred vs mixed)

### 6. Provenance Tracking

**Current provenance sources:**
- `"connector"` - Data from connector webhooks in events
- `"inferred"` - Derived from heuristics
- `"mock"` - Placeholder data

**New provenance tracking:**
- `"github_api"` - Fetched via GitHub REST API
- `"gitlab_api"` - Fetched via GitLab API
- `"bitbucket_api"` - Fetched via Bitbucket API
- `"connector_webhook"` - Real-time webhook data
- `"inferred"` - Existing inference logic
- `"mock"` - Placeholder data

**Update `build_stage_record()`:**
```python
def build_stage_record(
    source: str,  # Now can be "github_api", "gitlab_api", etc.
    provenance_detail: str,  # e.g., "github connector v0.1.0"
    ...
):
    ...
```

**Update provenance rollup logic:**
```python
def classify_requirement_provenance(source_breakdown: dict[str, int]) -> str:
    """Classify overall provenance with API-aware logic."""
    api_sources = {"github_api", "gitlab_api", "bitbucket_api", "connector_webhook"}
    
    # Count API-backed stages
    api_count = sum(source_breakdown.get(s, 0) for s in api_sources)
    inferred_count = source_breakdown.get("inferred", 0)
    mock_count = source_breakdown.get("mock", 0)
    
    if api_count > 0 and inferred_count == 0 and mock_count == 0:
        return "connector"  # All stages from real APIs
    elif inferred_count > 0 and api_count == 0 and mock_count == 0:
        return "inferred"  # All stages inferred
    elif mock_count > 0 and api_count == 0 and inferred_count == 0:
        return "mock"  # All stages mocked
    elif api_count > 0 or inferred_count > 0:
        return "mixed"  # Mix of real and inferred
    else:
        return "unknown"
```

### 7. Error Handling

**Connector failures should not break timeline:**

```python
def safe_connector_fetch(connector, fetch_fn, *args, **kwargs):
    """Safely call connector with error handling."""
    try:
        return fetch_fn(*args, **kwargs)
    except ConnectorAuthError as e:
        logger.error(f"Connector authentication failed: {e}")
        return None
    except ConnectorRateLimitError as e:
        logger.warning(f"Connector rate limited: {e} (retry after {e.retry_after}s)")
        return None
    except ConnectorTimeoutError as e:
        logger.error(f"Connector timeout: {e}")
        return None
    except ConnectorAPIError as e:
        logger.error(f"Connector API error: {e} (status={e.status_code})")
        return None
    except Exception as e:
        logger.error(f"Unexpected connector error: {e}")
        return None
```

### 8. Configuration (Environment Variables)

**Required environment variables:**

```bash
# GitHub Configuration
DEVHOUSE_GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
DEVHOUSE_GITHUB_ENTERPRISE_URL=https://github.company.com/api/v3  # Optional for GHE

# GitLab Configuration (future)
DEVHOUSE_GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
DEVHOUSE_GITLAB_URL=https://gitlab.com  # Or self-hosted URL

# Bitbucket Configuration (future)
DEVHOUSE_BITBUCKET_USERNAME=username
DEVHOUSE_BITBUCKET_APP_PASSWORD=xxxxxxxxxxxxxxxxxxxx
DEVHOUSE_BITBUCKET_URL=https://api.bitbucket.org/2.0

# Cache Configuration
DEVHOUSE_CONNECTOR_CACHE_TTL=300  # Cache connector responses for 5 minutes

# Feature Flags
DEVHOUSE_ENABLE_GITHUB_CONNECTOR=true
DEVHOUSE_ENABLE_GITLAB_CONNECTOR=false
DEVHOUSE_ENABLE_BITBUCKET_CONNECTOR=false
```

**Loading configuration:**
```python
import os
from typing import Optional

class ConnectorConfig:
    """Centralized connector configuration."""
    
    # GitHub
    GITHUB_TOKEN: Optional[str] = os.getenv("DEVHOUSE_GITHUB_TOKEN")
    GITHUB_URL: Optional[str] = os.getenv("DEVHOUSE_GITHUB_ENTERPRISE_URL")
    GITHUB_ENABLED: bool = os.getenv("DEVHOUSE_ENABLE_GITHUB_CONNECTOR", "true").lower() == "true"
    
    # GitLab
    GITLAB_TOKEN: Optional[str] = os.getenv("DEVHOUSE_GITLAB_TOKEN")
    GITLAB_URL: Optional[str] = os.getenv("DEVHOUSE_GITLAB_URL")
    GITLAB_ENABLED: bool = os.getenv("DEVHOUSE_ENABLE_GITLAB_CONNECTOR", "false").lower() == "true"
    
    # Cache
    CACHE_TTL: int = int(os.getenv("DEVHOUSE_CONNECTOR_CACHE_TTL", "300"))
```

### 9. Caching Strategy

**Problem:** Avoid repeated API calls for same data within short time window.

**Solution:** Cache normalized connector responses in memory or Redis.

```python
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import hashlib
import json

class ConnectorCache:
    """Simple in-memory cache for connector responses."""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
    
    def _make_key(self, connector: str, method: str, **params) -> str:
        """Generate cache key from connector method and parameters."""
        key_data = f"{connector}:{method}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, connector: str, method: str, **params) -> Optional[Any]:
        """Get cached value if not expired."""
        key = self._make_key(connector, method, **params)
        if key in self._cache:
            cached_at, value = self._cache[key]
            if datetime.utcnow() - cached_at < self.ttl:
                return value
            else:
                del self._cache[key]  # Expired
        return None
    
    def set(self, connector: str, method: str, value: Any, **params):
        """Cache a value."""
        key = self._make_key(connector, method, **params)
        self._cache[key] = (datetime.utcnow(), value)
    
    def clear(self):
        """Clear all cached values."""
        self._cache.clear()

# Global cache instance
_connector_cache = ConnectorCache(ttl_seconds=ConnectorConfig.CACHE_TTL)

def get_cached_or_fetch(connector, method, cache_key_params, fetch_fn):
    """Get from cache or fetch and cache."""
    cached = _connector_cache.get(connector.PROVIDER_NAME, method, **cache_key_params)
    if cached is not None:
        return cached
    
    result = fetch_fn()
    if result is not None:
        _connector_cache.set(connector.PROVIDER_NAME, method, result, **cache_key_params)
    
    return result
```

## Implementation Checklist

- [ ] Add connector parameter to `build_delivery_timeline_response()`
- [ ] Add connector parameter to `extract_pull_request_record()`
- [ ] Add connector parameter to `extract_ci_record()`
- [ ] Add connector parameter to `extract_deployment_record()`
- [ ] Implement `fetch_pr_from_connector()` helper
- [ ] Implement `fetch_ci_from_connector()` helper
- [ ] Implement `fetch_deployment_from_connector()` helper
- [ ] Implement `extract_repo_context()` helper
- [ ] Implement `convert_normalized_pr_to_stage_record()` converter
- [ ] Implement `convert_normalized_ci_to_stage_record()` converter
- [ ] Implement `convert_normalized_deployment_to_stage_record()` converter
- [ ] Update provenance tracking to handle API sources
- [ ] Add connector initialization to `main.py`
- [ ] Add configuration loading (`ConnectorConfig`)
- [ ] Add caching layer (`ConnectorCache`)
- [ ] Add error handling wrappers
- [ ] Update API endpoints to pass connector
- [ ] Add logging for connector usage metrics
- [ ] Run existing test suite (must pass)
- [ ] Add integration tests with mocked connector
- [ ] Document configuration in README

## Example: End-to-End Flow

```python
# 1. User makes API request
GET /api/requirements/ISSUE-123/timeline

# 2. API handler
@app.get("/api/requirements/{issue_id}/timeline")
async def get_timeline(issue_id: str):
    # Fetch issue and events from database
    issue = storage.get_issue(issue_id)
    events = storage.get_events_for_issue(issue_id)
    
    # Get connector (may be None if not configured)
    connector = get_github_connector()
    
    # Build timeline with optional connector
    timeline = build_delivery_timeline_response(
        issue=issue,
        events=events,
        connector=connector,
    )
    
    return timeline

# 3. Timeline builder tries connector first
def build_delivery_timeline_response(issue, events, connector=None):
    # Extract repo context from events
    repo_context = extract_repo_context(events, issue)
    
    # Extract stages (with connector fallback)
    pull_request = extract_pull_request_record(events, connector, repo_context) or infer_pull_request_record(...)
    ci = extract_ci_record(events, connector, repo_context) or infer_ci_record(...)
    deployment = extract_deployment_record(events, connector, repo_context) or infer_deployment_record(...)
    
    # Build response with provenance tracking
    ...

# 4. Extract PR uses connector
def extract_pull_request_record(events, connector=None, repo_context=None):
    if connector and repo_context:
        pr = fetch_pr_from_connector(connector, repo_context, events)
        if pr:
            return pr  # connector source
    
    # Fallback to events
    return extract_pr_from_events(events)

# 5. Fetch from connector
def fetch_pr_from_connector(connector, repo_context, events):
    try:
        repo_filter = RepositoryFilter(
            owner=repo_context["owner"],
            repo_name=repo_context["repo_name"],
        )
        
        pr_number = extract_pr_number_from_events(events)
        if not pr_number:
            return None
        
        # Fetch from GitHub API
        for pr in connector.get_pull_requests(repo_filter):
            if pr.id == str(pr_number):
                return convert_normalized_pr_to_stage_record(pr)
        
        return None
    except Exception as e:
        logger.error(f"Connector fetch failed: {e}")
        return None  # Fall back to inference
```

## Monitoring & Observability

**Metrics to track:**
- Connector usage rate (% of requests using connector vs inference)
- Connector success/failure rate
- Connector latency (p50, p95, p99)
- Cache hit rate
- Provenance distribution (connector/inferred/mixed/mock)
- API rate limit consumption

**Logging:**
```python
logger.info("Timeline built", extra={
    "issue_id": issue["issue_id"],
    "provenance": timeline["provenance_rollup"],
    "connector_used": connector is not None,
    "pr_source": timeline["pull_request"]["source"],
    "ci_source": timeline["ci"]["source"],
    "deployment_source": timeline["deployment"]["source"],
})
```
