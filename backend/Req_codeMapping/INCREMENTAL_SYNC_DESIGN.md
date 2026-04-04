# Incremental Sync Design

## Overview

Design for tracking and executing incremental synchronization of delivery timeline data from Git providers, avoiding full rescans and optimizing API usage.

## Problem Statement

**Without incremental sync:**
- Every timeline request fetches all PRs/CI runs/deployments
- Wastes API rate limits on unchanged data
- High latency for repos with many events
- Redundant data transfer and processing

**With incremental sync:**
- Fetch only new/updated records since last sync
- Minimize API calls and rate limit consumption
- Lower latency and resource usage
- Maintain freshness without full scans

## Design Goals

1. **Efficiency:** Only fetch what changed since last sync
2. **Reliability:** Handle partial failures, resume from crashes
3. **Simplicity:** Straightforward state tracking and recovery
4. **Flexibility:** Support different sync strategies (polling, webhook, on-demand)
5. **Observable:** Track sync health, lag, and coverage

## Sync State Schema

### Database Table: `connector_sync_state`

```sql
CREATE TABLE connector_sync_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Identify what's being synced
    provider TEXT NOT NULL,              -- "github", "gitlab", etc.
    repository_owner TEXT NOT NULL,      -- Org or user
    repository_name TEXT NOT NULL,       -- Repo name
    repository_id TEXT,                  -- Provider-specific repo ID
    
    -- Sync stage tracking
    stage TEXT NOT NULL,                 -- "pull_requests", "ci_runs", "deployments"
    
    -- Sync timestamps
    last_sync_at TIMESTAMP,              -- When last sync completed successfully
    last_sync_started_at TIMESTAMP,      -- When current/last sync started
    next_sync_at TIMESTAMP,              -- Scheduled next sync (for polling)
    
    -- Cursor/pagination state (provider-specific)
    last_cursor TEXT,                    -- Opaque pagination cursor
    last_page INTEGER,                   -- Last page fetched (offset pagination)
    last_updated_at TIMESTAMP,           -- Filter: records updated after this time
    
    -- Sync metadata
    total_records_synced INTEGER DEFAULT 0,  -- Cumulative count
    last_sync_record_count INTEGER,          -- Records from last sync
    last_sync_duration_seconds INTEGER,      -- How long last sync took
    sync_status TEXT DEFAULT 'pending',      -- "pending", "running", "completed", "failed"
    sync_error TEXT,                         -- Error message if failed
    
    -- Configuration
    sync_enabled BOOLEAN DEFAULT TRUE,       -- Can disable per repo/stage
    sync_interval_seconds INTEGER DEFAULT 300,  -- How often to poll (5 min)
    backfill_days INTEGER,                   -- How far back to fetch on first sync
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(provider, repository_owner, repository_name, stage)
);

CREATE INDEX idx_sync_state_next_sync ON connector_sync_state(next_sync_at, sync_enabled);
CREATE INDEX idx_sync_state_status ON connector_sync_state(sync_status);
CREATE INDEX idx_sync_state_repo ON connector_sync_state(provider, repository_owner, repository_name);
```

### Example Records

```sql
-- GitHub PRs for myorg/myapp
INSERT INTO connector_sync_state (
    provider, repository_owner, repository_name, stage,
    last_sync_at, last_updated_at, sync_status, total_records_synced
) VALUES (
    'github', 'myorg', 'myapp', 'pull_requests',
    '2024-01-15 12:00:00', '2024-01-15 11:55:00', 'completed', 42
);

-- GitHub CI runs for myorg/myapp
INSERT INTO connector_sync_state (
    provider, repository_owner, repository_name, stage,
    last_sync_at, last_updated_at, sync_status, total_records_synced
) VALUES (
    'github', 'myorg', 'myapp', 'ci_runs',
    '2024-01-15 12:00:00', '2024-01-15 11:50:00', 'completed', 156
);
```

## Sync Strategies

### Strategy 1: On-Demand Sync (Initial Implementation)

Sync when timeline is requested and data is stale.

**Trigger:** Timeline API request  
**Logic:**
1. Check sync state for repo
2. If never synced OR last_sync_at > TTL: trigger sync
3. Sync in background, return cached data immediately
4. Next request gets fresh data

**Pros:** Simple, no background jobs needed  
**Cons:** First request after TTL is slow

```python
def get_timeline_with_sync(issue, events, connector):
    """Get timeline with on-demand sync."""
    repo = extract_repo_context(events, issue)
    if not repo or not connector:
        return build_timeline_without_connector(issue, events)
    
    sync_state = get_sync_state(connector.PROVIDER_NAME, repo["owner"], repo["repo_name"])
    
    # Check if sync needed
    if should_sync(sync_state, ttl_seconds=300):
        # Trigger async sync (non-blocking)
        trigger_sync(connector, repo, sync_state)
    
    # Build timeline from current data (may be slightly stale)
    return build_timeline_with_connector(issue, events, connector, repo)

def should_sync(sync_state, ttl_seconds=300):
    """Check if sync is needed."""
    if not sync_state:
        return True  # Never synced
    
    if sync_state.sync_status == "running":
        return False  # Already syncing
    
    if not sync_state.last_sync_at:
        return True  # No successful sync yet
    
    age = datetime.utcnow() - sync_state.last_sync_at
    return age.total_seconds() > ttl_seconds
```

### Strategy 2: Background Polling (Future Enhancement)

Periodic background job syncs repos independently of requests.

**Trigger:** Cron/scheduler every N minutes  
**Logic:**
1. Find repos with next_sync_at <= now
2. For each repo, sync all stages (PRs, CI, deployments)
3. Update sync state
4. Schedule next sync

**Pros:** Data always fresh, requests fast  
**Cons:** Requires background worker, syncs inactive repos

```python
import schedule
import time

def background_sync_worker():
    """Background worker for scheduled syncs."""
    while True:
        # Find repos needing sync
        repos = get_repos_needing_sync()
        
        for repo_state in repos:
            try:
                connector = get_connector_for_provider(repo_state.provider)
                sync_repository(connector, repo_state)
            except Exception as e:
                mark_sync_failed(repo_state, str(e))
        
        time.sleep(60)  # Check every minute

def get_repos_needing_sync():
    """Get repos where next_sync_at <= now."""
    return db.query("""
        SELECT * FROM connector_sync_state
        WHERE sync_enabled = TRUE
        AND next_sync_at <= CURRENT_TIMESTAMP
        AND sync_status != 'running'
        ORDER BY next_sync_at ASC
    """)
```

### Strategy 3: Webhook-Triggered Sync (Future Enhancement)

Real-time sync on GitHub/GitLab webhook events.

**Trigger:** Webhook from provider (PR opened, CI completed, etc.)  
**Logic:**
1. Receive webhook
2. Validate signature
3. Extract repo + event type
4. Sync specific stage immediately
5. Update sync state

**Pros:** Real-time data, minimal API usage  
**Cons:** Requires webhook infrastructure, only for events

```python
@app.post("/webhooks/github")
async def github_webhook(request: Request):
    """Handle GitHub webhook events."""
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event")
    
    if event_type == "pull_request":
        repo = payload["repository"]["full_name"]
        owner, name = repo.split("/")
        
        # Sync PRs for this repo immediately
        connector = get_github_connector()
        sync_state = get_sync_state("github", owner, name, "pull_requests")
        sync_repository_stage(connector, sync_state, stage="pull_requests")
    
    return {"status": "ok"}
```

## Sync Implementation

### Core Sync Function

```python
from datetime import datetime, timedelta
from typing import Optional
from connector_base import ProviderConnector, RepositoryFilter, TimeRangeFilter
from connector_schemas import NormalizedPullRequest, NormalizedCIRun, NormalizedDeployment

def sync_repository(
    connector: ProviderConnector,
    sync_state: SyncState,
) -> SyncResult:
    """
    Sync a repository stage using incremental sync.
    
    Args:
        connector: Provider connector instance
        sync_state: Current sync state from database
    
    Returns:
        SyncResult with stats and status
    """
    stage = sync_state.stage  # "pull_requests", "ci_runs", or "deployments"
    
    # Mark sync as running
    update_sync_state(sync_state, status="running", started_at=datetime.utcnow())
    
    try:
        # Build filters
        repo_filter = RepositoryFilter(
            owner=sync_state.repository_owner,
            repo_name=sync_state.repository_name,
        )
        
        time_filter = TimeRangeFilter(
            since=sync_state.last_updated_at,  # Only fetch records updated since last sync
        )
        
        # Fetch records from connector
        records_synced = 0
        start_time = datetime.utcnow()
        
        if stage == "pull_requests":
            for pr in connector.get_pull_requests(repo_filter, time_filter):
                upsert_pull_request(pr, sync_state)
                records_synced += 1
        
        elif stage == "ci_runs":
            for ci_run in connector.get_ci_runs(repo_filter, time_filter):
                upsert_ci_run(ci_run, sync_state)
                records_synced += 1
        
        elif stage == "deployments":
            for deployment in connector.get_deployments(repo_filter, time_filter):
                upsert_deployment(deployment, sync_state)
                records_synced += 1
        
        # Sync completed successfully
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        update_sync_state(
            sync_state,
            status="completed",
            last_sync_at=end_time,
            last_updated_at=end_time,  # Use current time for next sync
            last_sync_record_count=records_synced,
            last_sync_duration_seconds=int(duration),
            total_records_synced=sync_state.total_records_synced + records_synced,
            next_sync_at=end_time + timedelta(seconds=sync_state.sync_interval_seconds),
            sync_error=None,
        )
        
        return SyncResult(
            success=True,
            records_synced=records_synced,
            duration_seconds=duration,
        )
    
    except Exception as e:
        # Sync failed
        update_sync_state(
            sync_state,
            status="failed",
            sync_error=str(e),
            next_sync_at=datetime.utcnow() + timedelta(seconds=60),  # Retry in 1 min
        )
        
        return SyncResult(
            success=False,
            error=str(e),
        )

def upsert_pull_request(pr: NormalizedPullRequest, sync_state: SyncState):
    """Insert or update pull request record."""
    db.execute("""
        INSERT INTO connector_pull_requests (
            provider, repository_owner, repository_name, pr_id,
            pr_number, title, status, author, url,
            created_at, updated_at, merged_at,
            raw_data, synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(provider, repository_owner, repository_name, pr_id)
        DO UPDATE SET
            title = excluded.title,
            status = excluded.status,
            updated_at = excluded.updated_at,
            merged_at = excluded.merged_at,
            raw_data = excluded.raw_data,
            synced_at = excluded.synced_at
    """, (
        sync_state.provider,
        sync_state.repository_owner,
        sync_state.repository_name,
        pr.id,
        int(pr.id) if pr.id.isdigit() else None,
        pr.title,
        pr.status,
        pr.author,
        pr.url,
        pr.created_at,
        pr.updated_at,
        pr.merged_at,
        json.dumps(pr.raw_metadata),
        datetime.utcnow().isoformat(),
    ))
```

### Cached Data Schema

Store synced data for fast retrieval.

```sql
-- Pull requests
CREATE TABLE connector_pull_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    repository_owner TEXT NOT NULL,
    repository_name TEXT NOT NULL,
    pr_id TEXT NOT NULL,              -- Provider PR ID
    pr_number INTEGER,                -- Numeric PR number
    title TEXT,
    status TEXT,
    author TEXT,
    url TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    merged_at TIMESTAMP,
    raw_data JSON,                    -- Full normalized record
    synced_at TIMESTAMP,              -- When synced
    UNIQUE(provider, repository_owner, repository_name, pr_id)
);

-- CI runs
CREATE TABLE connector_ci_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    repository_owner TEXT NOT NULL,
    repository_name TEXT NOT NULL,
    run_id TEXT NOT NULL,
    run_number INTEGER,
    name TEXT,
    status TEXT,
    conclusion TEXT,
    commit_sha TEXT,
    branch TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    raw_data JSON,
    synced_at TIMESTAMP,
    UNIQUE(provider, repository_owner, repository_name, run_id)
);

-- Deployments
CREATE TABLE connector_deployments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    repository_owner TEXT NOT NULL,
    repository_name TEXT NOT NULL,
    deployment_id TEXT NOT NULL,
    environment TEXT,
    status TEXT,
    commit_sha TEXT,
    deployed_by TEXT,
    deployed_at TIMESTAMP,
    raw_data JSON,
    synced_at TIMESTAMP,
    UNIQUE(provider, repository_owner, repository_name, deployment_id)
);
```

## First Sync (Backfill)

When syncing a repo for the first time, how far back to fetch?

**Strategy:**
- **Default:** Last 30 days (`backfill_days=30`)
- **Configurable:** Per repo or global setting
- **Incremental:** After backfill, use last_updated_at

```python
def get_backfill_time_filter(sync_state: SyncState) -> TimeRangeFilter:
    """Get time filter for first sync."""
    if sync_state.last_sync_at:
        # Not first sync - use incremental
        return TimeRangeFilter(since=sync_state.last_updated_at)
    
    # First sync - backfill
    backfill_days = sync_state.backfill_days or 30
    since = datetime.utcnow() - timedelta(days=backfill_days)
    
    return TimeRangeFilter(since=since)
```

## Repository Discovery

How to know which repos to sync?

**Option 1: Explicit Configuration**
```python
# Manually register repos
register_repository("github", "myorg", "myapp")
register_repository("github", "myorg", "another-repo")
```

**Option 2: Auto-discovery from Events**
```python
# Auto-discover repos mentioned in events
for event in recent_events:
    repo = extract_repo_from_event(event)
    if repo:
        ensure_sync_state_exists(repo)
```

**Option 3: Provider Org Scan**
```python
# Scan all repos in org (GitHub API)
connector = get_github_connector()
for repo in connector.list_org_repos("myorg"):
    ensure_sync_state_exists("github", "myorg", repo.name)
```

**Recommendation:** Start with Option 2 (auto-discovery), add Option 1 for manual control.

## Monitoring & Observability

### Metrics to Track

```python
# Sync health metrics
sync_success_rate = completed_syncs / total_syncs
sync_lag = current_time - last_sync_at  # Data staleness
sync_duration_p95 = percentile(sync_durations, 95)

# Data coverage metrics
repos_with_connector_data = count(repos where last_sync_at is not null)
total_prs_synced = sum(total_records_synced where stage = 'pull_requests')

# API usage metrics
api_calls_per_sync = connector.api_calls_count / syncs_count
rate_limit_remaining = connector.rate_limit_remaining
```

### Sync Status Dashboard

```sql
-- Repos needing attention
SELECT 
    repository_owner || '/' || repository_name as repo,
    stage,
    sync_status,
    last_sync_at,
    CAST((julianday('now') - julianday(last_sync_at)) * 24 * 60 AS INTEGER) as minutes_since_sync,
    sync_error
FROM connector_sync_state
WHERE sync_enabled = TRUE
AND (
    sync_status = 'failed' 
    OR last_sync_at < datetime('now', '-30 minutes')
    OR last_sync_at IS NULL
)
ORDER BY last_sync_at ASC;
```

## Configuration Examples

```bash
# Environment variables
DEVHOUSE_SYNC_DEFAULT_INTERVAL=300       # Sync every 5 minutes
DEVHOUSE_SYNC_BACKFILL_DAYS=30           # Backfill 30 days on first sync
DEVHOUSE_SYNC_ENABLED=true               # Global enable/disable
DEVHOUSE_SYNC_STRATEGY=on_demand         # "on_demand", "polling", "webhook"
```

## Migration Plan

### Phase 1: Manual Sync
- Implement sync_repository() function
- Add CLI command: `python sync.py --repo myorg/myapp`
- Test with one repo

### Phase 2: On-Demand Sync
- Add sync state checks to timeline API
- Trigger sync when data stale
- Monitor sync success rate

### Phase 3: Background Polling
- Add background worker
- Schedule regular syncs
- Disable on-demand sync for repos with polling

### Phase 4: Webhooks
- Add webhook endpoint
- Configure GitHub/GitLab webhooks
- Real-time updates for critical events

## Future Enhancements

1. **Differential Sync:** Only fetch changed fields, not full records
2. **Bulk Sync:** Batch multiple repos in single sync job
3. **Priority Queues:** Sync active repos more frequently
4. **Smart Intervals:** Adjust sync frequency based on repo activity
5. **Sync Checkpoints:** Resume from failure mid-page
6. **Historical Backfill:** On-demand deep backfill for analytics
