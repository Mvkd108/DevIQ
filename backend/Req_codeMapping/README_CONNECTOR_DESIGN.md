# Connector Abstraction Layer - Design Summary

## 🎯 Mission Accomplished

Provider-agnostic connector abstraction layer designed for DevHouse26 to integrate real GitHub/GitLab/Bitbucket data into delivery timeline.

## 📦 Deliverables

### 1. Core Abstraction Layer

#### `connector_base.py` (9KB)
**Abstract base class for all provider connectors.**

- ✅ `ProviderConnector` abstract class with required methods:
  - `get_metadata()` - Connector info and capabilities
  - `get_pull_requests()` - Fetch PRs with filtering and pagination
  - `get_ci_runs()` - Fetch CI/CD runs
  - `get_deployments()` - Fetch deployment events
  - `test_connection()` - Validate authentication

- ✅ Helper dataclasses:
  - `ConnectorCapabilities` - What connector supports
  - `RepositoryFilter` - Filter by owner/repo/branch
  - `TimeRangeFilter` - Incremental sync support (since/until)
  - `PaginationCursor` - Page/cursor-based pagination

- ✅ Exception hierarchy:
  - `ConnectorError` (base)
  - `ConnectorAuthError` (401/403)
  - `ConnectorRateLimitError` (429, with retry_after)
  - `ConnectorAPIError` (API errors with status codes)
  - `ConnectorTimeoutError` (request timeouts)
  - `ConnectorNotFoundError` (404)

**Key Design Decision:**
- Iterator-based methods (`Iterator[NormalizedPullRequest]`) for memory efficiency with large datasets
- Optional parameters throughout for backward compatibility
- Provider-agnostic filters work across GitHub/GitLab/Bitbucket

---

#### `connector_schemas.py` (10KB)
**Normalized data schemas that all connectors must produce.**

- ✅ `NormalizedPullRequest` dataclass:
  - Common fields: id, url, status, title, author, reviewers, branches, timestamps
  - Metrics: additions, deletions, changed_files, comments_count
  - Provenance: provider, fetched_at, raw_metadata
  - Works for GitHub PRs, GitLab MRs, Bitbucket PRs

- ✅ `NormalizedCIRun` dataclass:
  - Common fields: id, status, conclusion, name, trigger_event, commit_sha, branch
  - Timestamps: created_at, started_at, completed_at
  - Associated PR info: pull_request_number, pull_request_url
  - Works for GitHub Actions, GitLab CI, Bitbucket Pipelines

- ✅ `NormalizedDeployment` dataclass:
  - Common fields: id, status, environment, commit_sha, deployed_by
  - Environment info: environment_url, version, release_name
  - Associated CI/PR: ci_run_id, pull_request_number
  - Works for GitHub Deployments, GitLab Deployments, etc.

- ✅ `ConnectorMetadata` - Connector version and capabilities
- ✅ `SyncState` - State tracking for incremental sync

**Key Design Decision:**
- All timestamps are UTC ISO 8601 strings (consistent across providers)
- `raw_metadata` field preserves original API response for debugging
- Nullable fields handle missing data gracefully
- Provider-specific data stored separately, not in common schema

---

#### `github_connector.py` (20KB)
**GitHub connector stub implementation with TODOs.**

- ✅ `GitHubConnector(ProviderConnector)` class
- ✅ Initialization with token and API URL (supports GitHub Enterprise)
- ✅ Stub methods with detailed TODO comments:
  - `get_pull_requests()` - Documented GitHub API endpoint and mapping
  - `get_ci_runs()` - GitHub Actions workflow runs
  - `get_deployments()` - GitHub deployments + statuses
  - `_normalize_pull_request()` - Schema mapping example
  - `_normalize_pr_status()` - Status normalization logic
  - `_headers()` - Authentication headers

- ✅ Documented API endpoints:
  - PRs: `GET /repos/{owner}/{repo}/pulls`
  - CI: `GET /repos/{owner}/{repo}/actions/runs`
  - Deployments: `GET /repos/{owner}/{repo}/deployments`

- ✅ Error handling patterns:
  - 401/403 → ConnectorAuthError
  - 404 → ConnectorNotFoundError
  - 429 → ConnectorRateLimitError
  - 5xx → Retry with exponential backoff

**Key Design Decision:**
- Stub implementation with TODOs shows exact mapping needed
- Each TODO includes example code and API response schema
- Ready to implement - just fill in HTTP request logic

---

### 2. Integration Documentation

#### `CONNECTOR_INTEGRATION_PLAN.md` (19KB)
**Complete integration guide for wiring connectors into delivery_timeline.py.**

**Contents:**
1. **Connector Instantiation** - Singleton pattern in `main.py`
2. **Function Signatures** - Backward-compatible parameter additions
3. **Extract Function Modifications** - Use connector first, fall back to inference
4. **Repository Context Extraction** - Get owner/repo from events/issue
5. **Backward Compatibility** - Ensure existing 22 tests pass
6. **Provenance Tracking** - Update sources to include "github_api", "gitlab_api"
7. **Error Handling** - Safe connector fetch with graceful degradation
8. **Configuration** - Environment variables for tokens and settings
9. **Caching Strategy** - In-memory cache to avoid repeated API calls
10. **Implementation Checklist** - 20-item task list
11. **Example End-to-End Flow** - Complete request flow with connector
12. **Monitoring & Observability** - Metrics and logging

**Key Integration Points:**
```python
# Function signature (backward compatible)
def build_delivery_timeline_response(
    issue: dict[str, Any],
    events: list[dict[str, Any]],
    connector: Optional[ProviderConnector] = None,  # NEW: Optional connector
) -> dict[str, Any]:
    ...

# Connector usage pattern
if connector and repo_context:
    pr = fetch_pr_from_connector(connector, repo_context, events)
    if pr:
        return pr  # connector source, high trust

# Fall back to inference
return extract_pr_from_events(events)  # existing logic
```

**Environment Variables:**
```bash
DEVHOUSE_GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
DEVHOUSE_GITHUB_ENTERPRISE_URL=https://github.company.com/api/v3  # Optional
DEVHOUSE_ENABLE_GITHUB_CONNECTOR=true
DEVHOUSE_CONNECTOR_CACHE_TTL=300  # 5 minutes
```

---

#### `CONNECTOR_TESTING_PLAN.md` (23KB)
**Comprehensive testing strategy with code examples.**

**Test Pyramid:**
- **Unit Tests (50+):** Connector base, schemas, GitHub connector (mocked)
- **Integration Tests (5-10):** Full flow with mocked API, timeline integration
- **E2E Tests (1-2):** Real GitHub API (optional, requires token)

**Key Test Files:**
- `test_connector_base.py` - Abstract class, exceptions, dataclasses
- `test_connector_schemas.py` - Schema validation, defaults, normalization
- `test_github_connector.py` - GitHub connector with mocked responses
- `test_connector_integration.py` - Mocked API responses (using `responses` lib)
- `test_delivery_timeline_with_connector.py` - Timeline + connector integration
- `test_github_connector_e2e.py` - Real API tests (skip if no token)

**Example Test (Integration):**
```python
@responses.activate
def test_get_pull_requests_success():
    """Fetch PRs successfully from mocked API."""
    responses.add(
        responses.GET,
        "https://api.github.com/repos/myorg/myapp/pulls",
        json=[{"number": 42, "state": "open", ...}],
        status=200,
    )
    
    connector = GitHubConnector(api_token="ghp_test")
    repo_filter = RepositoryFilter(owner="myorg", repo_name="myapp")
    
    prs = list(connector.get_pull_requests(repo_filter))
    
    assert len(prs) == 1
    assert prs[0].id == "42"
```

**Success Criteria:**
- ✅ All existing 68 tests pass (verified ✅)
- ✅ New unit tests achieve >90% code coverage
- ✅ Backward compatibility maintained (connector=None works)
- ✅ Graceful degradation on connector failures

---

#### `INCREMENTAL_SYNC_DESIGN.md` (18KB)
**Design for efficient incremental synchronization.**

**Problem:** Avoid full rescans every request, minimize API usage.

**Solution:** Track sync state per repo/stage, fetch only updates.

**Database Schema:**
```sql
CREATE TABLE connector_sync_state (
    provider TEXT NOT NULL,
    repository_owner TEXT NOT NULL,
    repository_name TEXT NOT NULL,
    stage TEXT NOT NULL,  -- "pull_requests", "ci_runs", "deployments"
    last_sync_at TIMESTAMP,
    last_updated_at TIMESTAMP,  -- Filter: fetch records updated after this
    sync_status TEXT,  -- "pending", "running", "completed", "failed"
    total_records_synced INTEGER,
    UNIQUE(provider, repository_owner, repository_name, stage)
);
```

**Sync Strategies:**
1. **On-Demand Sync (Initial):** Sync when timeline requested and data stale
2. **Background Polling (Future):** Periodic background job syncs repos
3. **Webhook-Triggered (Future):** Real-time sync on GitHub/GitLab webhooks

**First Sync (Backfill):**
- Default: Fetch last 30 days of data
- Configurable per repo: `backfill_days=30`
- After backfill: Use `last_updated_at` for incremental

**Cached Data Storage:**
```sql
CREATE TABLE connector_pull_requests (
    provider TEXT,
    repository_owner TEXT,
    repository_name TEXT,
    pr_id TEXT,
    title TEXT,
    status TEXT,
    raw_data JSON,
    synced_at TIMESTAMP,
    UNIQUE(provider, repository_owner, repository_name, pr_id)
);
```

**Key Design Decision:**
- Time-based filtering (`since=last_updated_at`) for incremental sync
- Sync state per stage (PRs, CI, deployments) for granularity
- On-demand sync initially (simple), background polling later (optimal)

---

## 🎨 Design Decisions

### 1. Provider-Agnostic Abstraction
**Decision:** Abstract base class + normalized schemas  
**Rationale:** GitHub, GitLab, Bitbucket have different APIs but similar concepts  
**Benefit:** Add new provider by implementing `ProviderConnector` interface

### 2. Backward Compatibility First
**Decision:** All connector parameters are optional with `None` default  
**Rationale:** Existing 68 tests must pass without changes  
**Benefit:** Gradual rollout, no breaking changes

### 3. Graceful Degradation
**Decision:** Connector failures fall back to inference  
**Rationale:** Delivery timeline must work even if GitHub API is down  
**Benefit:** Reliability > completeness

### 4. Provenance Tracking
**Decision:** Track data source in every stage record  
**Rationale:** Know what's real vs inferred vs mock  
**Benefit:** Transparency, debugging, quality metrics

### 5. Iterator-Based Methods
**Decision:** Methods return `Iterator[Normalized*]` not lists  
**Rationale:** Memory efficiency for repos with thousands of PRs  
**Benefit:** Stream processing, low memory footprint

### 6. Raw Metadata Preservation
**Decision:** Store full API response in `raw_metadata` field  
**Rationale:** Provider-specific data may be useful later  
**Benefit:** Debugging, future enhancements, no data loss

### 7. Time-Based Incremental Sync
**Decision:** Filter by `updated_at > last_sync_at`  
**Rationale:** Simple, works across all providers  
**Benefit:** Minimize API calls, reduce rate limit consumption

## 📊 Test Status

**Existing Tests:** ✅ 68 passed (0.23s)
- 29 analytics tests
- 22 delivery timeline tests
- 11 knowledge risk tests
- 6 showcase summary tests

**Connector Tests:** 📝 Documented (not yet implemented)
- 50+ unit tests planned
- 5-10 integration tests planned
- 1-2 E2E tests planned

## 🚀 Next Steps

### Immediate: Implement GitHub Connector
1. Install dependencies: `pip install requests`
2. Fill in TODOs in `github_connector.py`:
   - [ ] Implement `_test_authentication()`
   - [ ] Implement `get_pull_requests()` with HTTP calls
   - [ ] Implement `_normalize_pull_request()` mapping
   - [ ] Implement `get_ci_runs()` with HTTP calls
   - [ ] Implement `get_deployments()` with HTTP calls
   - [ ] Add retry logic with exponential backoff
   - [ ] Add rate limit handling

3. Test with mocked API:
   ```bash
   pip install responses pytest
   pytest tests/test_connector_integration.py -v
   ```

4. Test with real API:
   ```bash
   export DEVHOUSE_GITHUB_TOKEN=ghp_xxxxx
   pytest tests/test_github_connector_e2e.py -v
   ```

### Phase 1: Wire into Timeline
1. Follow `CONNECTOR_INTEGRATION_PLAN.md` checklist
2. Add connector parameter to `build_delivery_timeline_response()`
3. Implement `fetch_pr_from_connector()` helper
4. Run existing tests (must pass: 68/68)
5. Add integration tests with connector
6. Deploy to staging

### Phase 2: Incremental Sync
1. Implement `connector_sync_state` database table
2. Implement `sync_repository()` function
3. Add on-demand sync to timeline endpoint
4. Monitor sync success rate and latency
5. Optimize: Add caching, background polling

### Phase 3: Additional Providers
1. Implement `GitLabConnector(ProviderConnector)`
2. Implement `BitbucketConnector(ProviderConnector)`
3. Test with real GitLab/Bitbucket APIs
4. Update integration plan for multi-provider support

## 📁 Files Created

```
connector_base.py                     (9 KB)  - Abstract connector interface
connector_schemas.py                  (10 KB) - Normalized data models
github_connector.py                   (20 KB) - GitHub stub implementation
CONNECTOR_INTEGRATION_PLAN.md         (19 KB) - Integration guide
CONNECTOR_TESTING_PLAN.md             (23 KB) - Testing strategy
INCREMENTAL_SYNC_DESIGN.md            (18 KB) - Sync design
README_CONNECTOR_DESIGN.md            (this)  - Summary and next steps
```

**Total:** 99 KB of production-quality design and stubs

## ✅ Success Criteria - Met

- ✅ **Clear Protocol/ABC** - `ProviderConnector` abstract class
- ✅ **Normalized schemas** - Work across GitHub/GitLab/Bitbucket
- ✅ **Integration path** - Doesn't break existing timeline code
- ✅ **Testing approach** - Comprehensive unit/integration/E2E strategy
- ✅ **Configuration** - Flexible environment variables, secure tokens
- ✅ **Backward compatible** - All 68 existing tests pass
- ✅ **Well documented** - Clear for future implementers

## 🎯 Key Takeaways

1. **Plug-and-play architecture:** Any provider can implement `ProviderConnector`
2. **Graceful degradation:** Connector failures don't break timeline
3. **Provenance transparency:** Know what's real vs inferred
4. **Incremental sync:** Efficient API usage, minimal rate limit consumption
5. **Production-ready design:** Error handling, caching, monitoring included

---

**Design Status:** ✅ Complete  
**Implementation Status:** 📝 Ready to implement  
**Test Coverage:** ✅ Existing tests pass, new tests designed  

**Estimated Implementation Time:**
- GitHub connector: 4-8 hours
- Integration with timeline: 4-6 hours
- Testing: 4-6 hours
- Incremental sync: 8-12 hours
**Total: 20-32 hours** for full production-ready connector system
