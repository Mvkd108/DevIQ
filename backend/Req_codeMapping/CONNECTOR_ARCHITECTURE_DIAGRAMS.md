# Connector Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DevHouse26 Backend                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                            │
│                                                                     │
│  GET /api/requirements/{issue_id}/timeline                          │
│      │                                                              │
│      └──> build_delivery_timeline_response(issue, events, connector)│
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   delivery_timeline.py                              │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ extract_pull_    │  │ extract_ci_      │  │ extract_deploy-  │ │
│  │ request_record() │  │ record()         │  │ ment_record()    │ │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘ │
│           │                     │                      │           │
│           │  Try connector      │  Try connector       │  Try      │
│           │  first ↓            │  first ↓             │  connector│
└───────────┼─────────────────────┼──────────────────────┼───────────┘
            │                     │                      │
            ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Connector Abstraction Layer                            │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │         ProviderConnector (Abstract Base Class)            │   │
│  │                                                             │   │
│  │  + get_metadata() → ConnectorMetadata                      │   │
│  │  + get_pull_requests(filter) → Iterator[NormalizedPR]     │   │
│  │  + get_ci_runs(filter) → Iterator[NormalizedCIRun]        │   │
│  │  + get_deployments(filter) → Iterator[NormalizedDeploy]   │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              ▲                                      │
│                              │ implements                           │
│           ┌──────────────────┼──────────────────┐                  │
│           │                  │                  │                  │
│           ▼                  ▼                  ▼                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │
│  │ GitHub         │  │ GitLab         │  │ Bitbucket      │      │
│  │ Connector      │  │ Connector      │  │ Connector      │      │
│  │                │  │ (future)       │  │ (future)       │      │
│  └────────┬───────┘  └────────────────┘  └────────────────┘      │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            │ HTTP API calls
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     External Git Providers                          │
│                                                                     │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │
│  │ GitHub         │  │ GitLab         │  │ Bitbucket      │      │
│  │ REST API       │  │ REST API       │  │ REST API       │      │
│  │                │  │                │  │                │      │
│  │ /repos/.../    │  │ /projects/.../  │  │ /repositories/ │      │
│  │   pulls        │  │   merge_requests│  │   pullrequests│      │
│  │ /actions/runs  │  │ /pipelines     │  │ /pipelines    │      │
│  │ /deployments   │  │ /deployments   │  │ /deployments  │      │
│  └────────────────┘  └────────────────┘  └────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Request Flow (with connector):
1. API Request → /api/requirements/ISSUE-123/timeline
2. Fetch issue and events from database
3. Get connector instance (GitHubConnector)
4. Extract repo context from events (owner/repo)
5. build_delivery_timeline_response(issue, events, connector)
   │
   ├─> extract_pull_request_record(events, connector, repo_context)
   │   ├─> fetch_pr_from_connector(connector, repo_context, events)
   │   │   ├─> connector.get_pull_requests(repo_filter, time_filter)
   │   │   │   └─> HTTP GET /repos/owner/repo/pulls?state=all
   │   │   │       └─> Returns: List[GitHub PR JSON objects]
   │   │   └─> Normalize GitHub PR → NormalizedPullRequest
   │   │       └─> Convert to stage record format
   │   │           └─> source="connector", provenance="github_api"
   │   │
   │   └─> FALLBACK: extract_pr_from_events(events)  [if connector fails]
   │       └─> source="connector" or "inferred"
   │
   ├─> extract_ci_record(events, connector, repo_context)
   │   └─> Similar flow for CI runs
   │
   └─> extract_deployment_record(events, connector, repo_context)
       └─> Similar flow for deployments
   
6. Combine stages into timeline response
7. Track provenance: "connector" vs "inferred" vs "mixed"
8. Return JSON response
```

## Schema Transformation

```
GitHub API Response → Normalized Schema → Stage Record

GitHub PR Object:                NormalizedPullRequest:        Stage Record:
{                                {                             {
  "number": 42,                    "id": "42",                   "source": "connector",
  "state": "closed",               "status": "merged",           "status": "merged",
  "merged": true,                  "is_merged": true,            "summary": "PR #42",
  "title": "Add feature",          "title": "Add feature",       "title": "Add feature",
  "user": {                        "author": "alice",            "author": "alice",
    "login": "alice"               "provider": "github",         "number": 42,
  },                               "fetched_at": "2024-...",     "url": "https://...",
  "html_url": "https://...",       "url": "https://...",         "provenance_detail":
  "created_at": "2024-...",        "created_at": "2024-...",       "github connector",
  "merged_at": "2024-...",         "merged_at": "2024-...",      "evidence": [
  ...                              "raw_metadata": {...}           "PR #42 from GitHub API"
}                                }                             ]
                                                              }
```

## Fallback Strategy

```
┌─────────────────────────────────────┐
│  Try Connector (highest trust)      │
│  ├─ GitHub API available?           │
│  ├─ Repository found?                │
│  ├─ PR data exists?                  │
│  └─ ✓ Return connector data          │
│      provenance: "connector"         │
└──────────────┬──────────────────────┘
               │
               │ If connector fails/unavailable
               ▼
┌─────────────────────────────────────┐
│  Parse Events (medium trust)        │
│  ├─ Events contain PR fields?       │
│  ├─ Connector webhook data?         │
│  └─ ✓ Return parsed event data      │
│      provenance: "connector" or      │
│                  "inferred"          │
└──────────────┬──────────────────────┘
               │
               │ If no PR data in events
               ▼
┌─────────────────────────────────────┐
│  Infer from Commits (low trust)     │
│  ├─ Commits mention PR #?           │
│  ├─ Branch name indicates PR?       │
│  └─ ✓ Return inferred PR record     │
│      provenance: "inferred"         │
└──────────────┬──────────────────────┘
               │
               │ If no commit signals
               ▼
┌─────────────────────────────────────┐
│  Mock Fallback (placeholder)        │
│  └─ ✓ Return mock record            │
│      provenance: "mock"             │
└─────────────────────────────────────┘
```

## Incremental Sync Flow

```
On-Demand Sync Strategy:

┌─────────────────────────────────────┐
│  Timeline API Request               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Check Sync State                   │
│  ├─ Last sync: 10 minutes ago       │
│  ├─ TTL: 5 minutes                  │
│  └─ Data is STALE                   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Trigger Async Sync (non-blocking)  │
│  └─ sync_repository(connector, ...)  │
│      ├─ TimeRangeFilter(since=      │
│      │     last_sync_at)            │
│      ├─ Fetch updated PRs           │
│      ├─ Upsert to database          │
│      └─ Update sync_state           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Return Timeline (current data)     │
│  └─ May be slightly stale, but      │
│      next request will be fresh     │
└─────────────────────────────────────┘


Database Tables:

┌─────────────────────────────────────┐
│  connector_sync_state               │
│  ├─ provider, owner, repo, stage    │
│  ├─ last_sync_at                    │
│  ├─ last_updated_at (for filtering) │
│  ├─ sync_status, sync_error         │
│  └─ total_records_synced            │
└─────────────────────────────────────┘
               │
               │ tracks sync for
               ▼
┌─────────────────────────────────────┐
│  connector_pull_requests            │
│  ├─ provider, owner, repo, pr_id    │
│  ├─ title, status, author, ...      │
│  ├─ raw_data (full normalized PR)   │
│  └─ synced_at                       │
└─────────────────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────────────────────────┐
│  connector.get_pull_requests()      │
└──────────────┬──────────────────────┘
               │
               ▼
         HTTP Request
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌─────────┐
│ Success │         │  Error  │
└────┬────┘         └────┬────┘
     │                   │
     │              ┌────┴────────────────┐
     │              │                     │
     │              ▼                     ▼
     │         ┌─────────┐          ┌─────────┐
     │         │ 401/403 │          │   429   │
     │         │  Auth   │          │  Rate   │
     │         │ Error   │          │ Limit   │
     │         └────┬────┘          └────┬────┘
     │              │                     │
     │              ▼                     ▼
     │    ConnectorAuthError    ConnectorRateLimitError
     │              │                     │
     │              │      ┌──────────────┤
     │              │      │              │
     │              ▼      ▼              ▼
     │         ┌─────────────────────────────┐
     │         │  Log error, return None     │
     │         │  (Timeline falls back to    │
     │         │   inference)                │
     │         └─────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  Parse response, normalize data     │
│  Return NormalizedPullRequest       │
└─────────────────────────────────────┘
```

## Configuration Flow

```
Environment Variables:
DEVHOUSE_GITHUB_TOKEN=ghp_xxxxx
DEVHOUSE_ENABLE_GITHUB_CONNECTOR=true
     │
     ▼
┌─────────────────────────────────────┐
│  main.py: initialize_connectors()   │
│  ├─ Load env vars                   │
│  ├─ Create GitHubConnector          │
│  ├─ Test authentication             │
│  └─ Store in global instance        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  get_github_connector()             │
│  └─ Returns connector or None       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Pass to timeline builder           │
│  build_delivery_timeline_response(  │
│      issue, events,                 │
│      connector=get_github_connector()│
│  )                                   │
└─────────────────────────────────────┘
```
