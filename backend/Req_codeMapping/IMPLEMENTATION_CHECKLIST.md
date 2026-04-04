# Connector Implementation Checklist

Use this checklist to implement the connector abstraction layer step-by-step.

## Phase 1: Implement GitHub Connector Core (4-8 hours)

### Setup
- [ ] Install dependencies: `pip install requests`
- [ ] Create test environment with GitHub token
- [ ] Set environment variable: `export DEVHOUSE_GITHUB_TOKEN=ghp_xxxxx`

### Implement HTTP Client
- [ ] Add `requests.Session` initialization in `__init__`
- [ ] Implement retry logic with exponential backoff (use `urllib3.Retry`)
- [ ] Add request timeout handling (default 30s)
- [ ] Test connection to GitHub API: `GET /user`

### Implement Authentication
- [ ] Implement `_test_authentication()` method
- [ ] Test with valid token → returns True
- [ ] Test with invalid token → returns False
- [ ] Test with no token → returns False

### Implement Pull Requests
- [ ] Implement `get_pull_requests()`:
  - [ ] Build API URL: `f"{self.api_url}/repos/{owner}/{repo}/pulls"`
  - [ ] Add query parameters: `state=all`, `sort=updated`, `direction=desc`
  - [ ] Handle pagination with `page` and `per_page`
  - [ ] Parse response JSON
  - [ ] Handle errors (401, 403, 404, 429, 5xx)
  - [ ] Yield normalized PRs

- [ ] Implement `_normalize_pull_request()`:
  - [ ] Map all fields from GitHub API to NormalizedPullRequest
  - [ ] Handle missing/null fields gracefully
  - [ ] Store full API response in raw_metadata
  - [ ] Test with sample GitHub PR JSON

- [ ] Test `get_pull_requests()`:
  - [ ] Mock API response with `responses` library
  - [ ] Test successful fetch
  - [ ] Test authentication error (401)
  - [ ] Test not found error (404)
  - [ ] Test rate limit error (429)

### Implement CI Runs
- [ ] Implement `get_ci_runs()`:
  - [ ] Build API URL: `f"{self.api_url}/repos/{owner}/{repo}/actions/runs"`
  - [ ] Add query parameters
  - [ ] Handle pagination
  - [ ] Parse response JSON
  - [ ] Yield normalized CI runs

- [ ] Implement `_normalize_ci_run()`:
  - [ ] Map GitHub Actions run to NormalizedCIRun
  - [ ] Handle job details if needed
  - [ ] Test with sample GitHub Actions JSON

- [ ] Test `get_ci_runs()` (same pattern as PRs)

### Implement Deployments
- [ ] Implement `get_deployments()`:
  - [ ] Fetch deployments: `GET /repos/{owner}/{repo}/deployments`
  - [ ] For each deployment, fetch status: `GET /repos/{owner}/{repo}/deployments/{id}/statuses`
  - [ ] Combine deployment + status
  - [ ] Yield normalized deployments

- [ ] Implement `_normalize_deployment()`:
  - [ ] Map GitHub deployment + status to NormalizedDeployment
  - [ ] Test with sample GitHub deployment JSON

- [ ] Test `get_deployments()` (same pattern as PRs)

### Unit Tests
- [ ] Write test_github_connector.py
- [ ] Test connector initialization
- [ ] Test metadata and capabilities
- [ ] Test header building
- [ ] Test PR status normalization
- [ ] Test full PR normalization
- [ ] Test CI run normalization
- [ ] Test deployment normalization

### Integration Tests (Mocked API)
- [ ] Write test_connector_integration.py
- [ ] Use `responses` library to mock GitHub API
- [ ] Test successful PR fetch
- [ ] Test successful CI fetch
- [ ] Test successful deployment fetch
- [ ] Test authentication errors
- [ ] Test rate limit handling
- [ ] Test pagination

### E2E Tests (Optional, Real API)
- [ ] Write test_github_connector_e2e.py
- [ ] Mark tests as `@pytest.mark.skipif(not token)`
- [ ] Test against real GitHub API (public repo)
- [ ] Verify real data normalization

**Phase 1 Complete:** GitHub connector fetches real data ✓

---

## Phase 2: Integrate with Timeline (4-6 hours)

### Add Connector Parameter
- [ ] Update `build_delivery_timeline_response()` signature:
  ```python
  def build_delivery_timeline_response(
      issue: dict[str, Any],
      events: list[dict[str, Any]],
      connector: Optional[ProviderConnector] = None,
  ) -> dict[str, Any]:
  ```

- [ ] Update `extract_pull_request_record()` signature:
  ```python
  def extract_pull_request_record(
      events: list[dict[str, Any]],
      connector: Optional[ProviderConnector] = None,
      repo_context: Optional[dict[str, str]] = None,
  ) -> Optional[dict[str, Any]]:
  ```

- [ ] Update `extract_ci_record()` signature (same pattern)
- [ ] Update `extract_deployment_record()` signature (same pattern)

### Implement Repository Context Extraction
- [ ] Create `extract_repo_context()` function:
  - [ ] Try extracting from events (repository_name, repository_owner)
  - [ ] Try nested repository object
  - [ ] Try parsing from issue metadata
  - [ ] Return `{"owner": "...", "repo_name": "..."}` or None

- [ ] Test `extract_repo_context()` with sample events

### Implement Connector Fetch Functions
- [ ] Create `fetch_pr_from_connector()`:
  - [ ] Build RepositoryFilter from repo_context
  - [ ] Extract PR number from events (if available)
  - [ ] Call `connector.get_pull_requests()`
  - [ ] Find matching PR by ID
  - [ ] Convert to stage record format
  - [ ] Handle errors gracefully (log and return None)

- [ ] Create `fetch_ci_from_connector()` (same pattern)
- [ ] Create `fetch_deployment_from_connector()` (same pattern)

### Implement Schema Converters
- [ ] Create `convert_normalized_pr_to_stage_record()`:
  - [ ] Map NormalizedPullRequest fields to stage record format
  - [ ] Set source="connector"
  - [ ] Set provenance_detail="github connector"
  - [ ] Build evidence list
  - [ ] Store raw_connector_data

- [ ] Create `convert_normalized_ci_to_stage_record()` (same pattern)
- [ ] Create `convert_normalized_deployment_to_stage_record()` (same pattern)

### Update Extract Functions Logic
- [ ] Update `extract_pull_request_record()`:
  ```python
  # Try connector first
  if connector and repo_context:
      pr = fetch_pr_from_connector(connector, repo_context, events)
      if pr:
          return pr
  
  # Fall back to parsing events
  pr = extract_pr_from_events(events)
  if pr:
      return pr
  
  return None
  ```

- [ ] Update `extract_ci_record()` (same pattern)
- [ ] Update `extract_deployment_record()` (same pattern)

### Wire into Timeline Builder
- [ ] Update `build_delivery_timeline_response()`:
  - [ ] Extract repo_context from events/issue
  - [ ] Pass connector and repo_context to extract functions
  - [ ] Ensure fallback chain works (connector → events → inference)

### Update Provenance Tracking
- [ ] Update provenance sources to include API providers:
  - [ ] "github_api"
  - [ ] "gitlab_api" (future)
  - [ ] "bitbucket_api" (future)
  - [ ] "connector_webhook"

- [ ] Update `classify_requirement_provenance()`:
  - [ ] Count API-backed stages
  - [ ] Distinguish "connector" (API) from "inferred"

### Connector Initialization
- [ ] Add connector initialization to `main.py`:
  ```python
  _github_connector: Optional[GitHubConnector] = None
  
  def initialize_connectors():
      global _github_connector
      github_token = os.getenv("DEVHOUSE_GITHUB_TOKEN")
      if github_token:
          _github_connector = GitHubConnector(api_token=github_token)
  
  def get_github_connector():
      return _github_connector
  
  @app.on_event("startup")
  async def startup_event():
      initialize_connectors()
  ```

- [ ] Update API endpoints to pass connector:
  ```python
  @app.get("/api/requirements/{issue_id}/timeline")
  async def get_timeline(issue_id: str):
      issue = storage.get_issue(issue_id)
      events = storage.get_events_for_issue(issue_id)
      connector = get_github_connector()
      return build_delivery_timeline_response(issue, events, connector)
  ```

### Configuration
- [ ] Add environment variable support:
  - [ ] `DEVHOUSE_GITHUB_TOKEN`
  - [ ] `DEVHOUSE_GITHUB_ENTERPRISE_URL`
  - [ ] `DEVHOUSE_ENABLE_GITHUB_CONNECTOR`
  - [ ] `DEVHOUSE_CONNECTOR_CACHE_TTL`

- [ ] Create `.env.example` with connector config

### Error Handling
- [ ] Add `safe_connector_fetch()` wrapper:
  ```python
  def safe_connector_fetch(connector, fetch_fn, *args):
      try:
          return fetch_fn(*args)
      except ConnectorAuthError as e:
          logger.error(f"Auth failed: {e}")
          return None
      except ConnectorRateLimitError as e:
          logger.warning(f"Rate limited: {e}")
          return None
      except Exception as e:
          logger.error(f"Connector error: {e}")
          return None
  ```

- [ ] Use wrapper in fetch_*_from_connector functions

### Testing
- [ ] Run existing test suite: `pytest tests/ -v`
- [ ] Verify all 68 tests pass (backward compatibility)

- [ ] Write test_delivery_timeline_with_connector.py:
  - [ ] Test timeline without connector (backward compat)
  - [ ] Test timeline with connector (mocked)
  - [ ] Test connector failure falls back to inference
  - [ ] Test provenance tracking with connector

- [ ] Integration test with real GitHub token (manual):
  - [ ] Set DEVHOUSE_GITHUB_TOKEN
  - [ ] Start app: `python main.py`
  - [ ] Make timeline request
  - [ ] Verify connector data appears
  - [ ] Check logs for connector usage

**Phase 2 Complete:** Timeline uses real GitHub data ✓

---

## Phase 3: Add Caching (2-3 hours)

### Implement Cache
- [ ] Create `ConnectorCache` class:
  - [ ] In-memory dict with TTL
  - [ ] Cache key generation (provider + method + params)
  - [ ] `get()` method (returns None if expired)
  - [ ] `set()` method (stores with timestamp)
  - [ ] `clear()` method

- [ ] Add global cache instance:
  ```python
  _connector_cache = ConnectorCache(ttl_seconds=300)
  ```

### Use Cache in Fetch Functions
- [ ] Update `fetch_pr_from_connector()`:
  ```python
  cache_key = {"owner": owner, "repo": repo, "pr": pr_number}
  cached = _connector_cache.get("github", "pr", **cache_key)
  if cached:
      return cached
  
  result = fetch_from_api()
  _connector_cache.set("github", "pr", result, **cache_key)
  return result
  ```

- [ ] Update fetch_ci and fetch_deployment (same pattern)

### Test Caching
- [ ] Test cache hit (second request doesn't call API)
- [ ] Test cache miss (first request calls API)
- [ ] Test cache expiration (after TTL, calls API again)

**Phase 3 Complete:** Connector responses cached ✓

---

## Phase 4: Incremental Sync (8-12 hours)

### Database Schema
- [ ] Create migration: `CREATE TABLE connector_sync_state`
- [ ] Create migration: `CREATE TABLE connector_pull_requests`
- [ ] Create migration: `CREATE TABLE connector_ci_runs`
- [ ] Create migration: `CREATE TABLE connector_deployments`
- [ ] Run migrations

### Implement Sync State Management
- [ ] Create `get_sync_state(provider, owner, repo, stage)` function
- [ ] Create `update_sync_state()` function
- [ ] Create `ensure_sync_state_exists()` function

### Implement Sync Function
- [ ] Create `sync_repository(connector, sync_state)`:
  - [ ] Build RepositoryFilter
  - [ ] Build TimeRangeFilter (since=last_updated_at)
  - [ ] Mark sync as running
  - [ ] Fetch records from connector
  - [ ] Upsert to connector_* tables
  - [ ] Update sync_state on success/failure
  - [ ] Handle errors gracefully

- [ ] Create `upsert_pull_request()` (INSERT ... ON CONFLICT UPDATE)
- [ ] Create `upsert_ci_run()`
- [ ] Create `upsert_deployment()`

### Implement On-Demand Sync
- [ ] Create `should_sync(sync_state, ttl_seconds)` function
- [ ] Create `trigger_sync(connector, repo, sync_state)` function (async)

- [ ] Update timeline endpoint:
  ```python
  sync_state = get_sync_state("github", owner, repo, "pull_requests")
  if should_sync(sync_state, ttl_seconds=300):
      trigger_sync(connector, repo, sync_state)
  ```

### Repository Discovery
- [ ] Implement auto-discovery from events:
  - [ ] Extract repo from events
  - [ ] Call `ensure_sync_state_exists()`

### First Sync (Backfill)
- [ ] Implement backfill logic:
  - [ ] If first sync, use `since = now - backfill_days`
  - [ ] Default backfill_days = 30
  - [ ] Store backfill_days in sync_state

### Testing
- [ ] Test sync_repository() with mocked connector
- [ ] Test upsert functions
- [ ] Test should_sync() logic
- [ ] Test backfill on first sync
- [ ] Test incremental sync on subsequent syncs

### Monitoring
- [ ] Add logging for sync events
- [ ] Log sync duration, record count
- [ ] Log sync failures

**Phase 4 Complete:** Incremental sync working ✓

---

## Phase 5: Polish & Production (4-6 hours)

### Documentation
- [ ] Update main README with connector setup
- [ ] Document environment variables
- [ ] Add setup guide for GitHub token
- [ ] Document connector extension (add new provider)

### Monitoring & Metrics
- [ ] Add sync health metrics:
  - [ ] sync_success_rate
  - [ ] sync_lag (data staleness)
  - [ ] api_calls_per_sync
  - [ ] rate_limit_remaining

- [ ] Add provenance metrics:
  - [ ] % connector vs inferred vs mock
  - [ ] connector_usage_rate

### Error Handling & Recovery
- [ ] Add retry logic for transient failures
- [ ] Add circuit breaker for repeated failures
- [ ] Add sync failure alerting

### Performance Optimization
- [ ] Profile connector latency
- [ ] Optimize database queries (add indexes)
- [ ] Consider Redis cache for high-traffic

### Security
- [ ] Ensure tokens not logged
- [ ] Validate API responses (prevent injection)
- [ ] Add rate limiting to prevent abuse

### Testing
- [ ] Full end-to-end test with real GitHub repo
- [ ] Load testing (100+ concurrent requests)
- [ ] Verify backward compatibility (all tests pass)
- [ ] Test with GitHub Enterprise (if available)

**Phase 5 Complete:** Production-ready connector system ✓

---

## Future Enhancements

### GitLab Connector
- [ ] Implement `GitLabConnector(ProviderConnector)`
- [ ] Map GitLab MRs to NormalizedPullRequest
- [ ] Map GitLab CI to NormalizedCIRun
- [ ] Test with real GitLab instance

### Bitbucket Connector
- [ ] Implement `BitbucketConnector(ProviderConnector)`
- [ ] Map Bitbucket PRs to NormalizedPullRequest
- [ ] Map Bitbucket Pipelines to NormalizedCIRun
- [ ] Test with real Bitbucket instance

### Background Polling
- [ ] Implement background worker
- [ ] Schedule syncs every N minutes
- [ ] Prioritize active repos

### Webhook Integration
- [ ] Add webhook endpoint
- [ ] Validate webhook signatures
- [ ] Trigger real-time sync on events

### Advanced Features
- [ ] Differential sync (only changed fields)
- [ ] Bulk sync (multiple repos in parallel)
- [ ] Smart intervals (adjust based on activity)
- [ ] Historical backfill (on-demand deep dive)

---

## Estimated Timeline

**Total Implementation Time: 20-32 hours**

- Phase 1: GitHub Connector (4-8 hours) ⚡ Start here
- Phase 2: Timeline Integration (4-6 hours)
- Phase 3: Caching (2-3 hours)
- Phase 4: Incremental Sync (8-12 hours)
- Phase 5: Polish & Production (4-6 hours)

**Recommended Approach:**
1. Start with Phase 1 (GitHub connector core)
2. Get one method working end-to-end (PRs)
3. Then add CI and deployments
4. Move to Phase 2 (timeline integration)
5. Add caching (Phase 3) early for performance
6. Implement incremental sync (Phase 4) for production
7. Polish and monitor (Phase 5)

Good luck! 🚀
