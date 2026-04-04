# Health And Readiness Reference

Use this file when you need to interpret `GET /api/health` quickly and consistently.

Primary endpoint:

- `http://127.0.0.1:8000/api/health`

## What to check first

Check these fields in this order:

1. `status`
2. `ready`
3. `operating_mode`
4. `missing_required_env`
5. `feedback_storage_mode`
6. `intake_storage_mode`
7. `analytics_storage_mode`
8. `snapshot_health`
9. `rollout_assessment.pilot`

## Healthy example

Example of an acceptable pilot-oriented state:

```json
{
  "status": "ok",
  "ready": true,
  "operating_mode": "pilot-ready",
  "missing_required_env": [],
  "feedback_storage_mode": "supabase",
  "intake_storage_mode": "supabase",
  "analytics_storage_mode": "supabase",
  "analytics_snapshots_enabled": true,
  "rollout_assessment": {
    "pilot": {
      "status": "ready",
      "blocker_count": 0
    }
  }
}
```

Interpretation:

- backend is ready for pilot-style use
- required env is present
- launch-critical persistence is available
- snapshots are enabled and expected to work

## Degraded example

Example of a still-runnable but not-ready state:

```json
{
  "status": "degraded",
  "ready": false,
  "operating_mode": "degraded",
  "missing_required_env": [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY_OR_ANON_KEY"
  ],
  "feedback_storage_mode": "memory",
  "intake_storage_mode": "derived",
  "analytics_storage_mode": "live-only",
  "rollout_assessment": {
    "pilot": {
      "status": "blocked",
      "blocker_count": 3
    }
  }
}
```

Interpretation:

- backend may start, but the environment is not acceptable for pilot use
- persistence is incomplete
- analytics are running without snapshot-backed support

## Operating mode guide

| `operating_mode` | Meaning | Safe language |
| --- | --- | --- |
| `degraded` | Required env or rollout blockers still exist | Debug/local recovery state |
| `local-demo` | Good enough for local walkthroughs but not hardened | Local demo only |
| `pilot-ready` | Acceptable for small-team pilot use | Controlled pilot state |
| `production-ready` | Strongest rollout posture exposed by the backend | Launch-ready backend posture |

## Storage mode guide

| Field | Stronger state | Weaker state |
| --- | --- | --- |
| `feedback_storage_mode` | `supabase` | `file-fallback`, `memory`, `strict-supabase` with missing table |
| `intake_storage_mode` | `supabase` | `derived` |
| `analytics_storage_mode` | `supabase` | `live-only` |

Interpretation rule:

- stronger states are safer to present as durable pilot behavior
- weaker states may still be useful for evaluation, but should be disclosed clearly

## Snapshot health guide

Look at:

- `snapshot_health.dashboard_analytics`
- `snapshot_health.delivery_timeline`

For each one, check:

- `enabled`
- `available`
- `fresh`
- `source`
- `age_seconds`

Fast interpretation:

- enabled + available + fresh: good snapshot-backed state
- enabled + not available: table/row missing or not yet populated
- enabled + available + not fresh: stale snapshot, still usable only if freshness is disclosed
- disabled: live-only mode by intent

## Pilot assessment guide

Check:

- `rollout_assessment.pilot.status`
- `rollout_assessment.pilot.blocker_count`
- `rollout_assessment.pilot.blockers`

Interpretation:

- `ready`: acceptable pilot posture
- `caution`: pilot can proceed if the operator understands the caveats
- `blocked`: do not represent the system as pilot-ready

## Recovery shortcuts

- missing env: fix `.env`, restart backend, re-open `/api/health`
- weak storage mode: apply the missing SQL and verify Supabase config
- write failures: align `DEVHOUSE_WRITE_API_KEY` and `VITE_WRITE_API_KEY`
- snapshot problems: apply `create_analytics_snapshots.sql` and recheck `snapshot_health`
