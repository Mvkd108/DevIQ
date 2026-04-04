# Demo Operator Runbook

Use this when handing the product to a third-party evaluator or running a live pilot/demo session.

For a shorter live-session reference, use [OPERATOR_CHEAT_SHEET.md](OPERATOR_CHEAT_SHEET.md).

## Before demo

Complete this before screen-sharing or inviting a pilot team:

1. Open `http://127.0.0.1:8000/api/health`.
2. Confirm:
   - `status` is `ok`
   - `ready` is `true`
   - `rollout_assessment.pilot.status` is `ready` or `caution`
3. Confirm storage modes are understood:
   - `feedback_storage_mode`
   - `intake_storage_mode`
   - `analytics_storage_mode`
4. Confirm snapshots are acceptable if enabled:
   - `snapshot_health.dashboard_analytics`
   - `snapshot_health.delivery_timeline`
5. If write actions are part of the session, confirm:
   - backend `DEVHOUSE_WRITE_API_KEY`
   - dashboard `VITE_WRITE_API_KEY`
   - values match
6. Open `http://127.0.0.1:5173` and confirm the dashboard loads.
7. Read:
   - [DATA_PROVENANCE.md](DATA_PROVENANCE.md)
   - [FEATURE_MATURITY_MATRIX.md](FEATURE_MATURITY_MATRIX.md)

## Controlled pilot checklist

Use this checklist whenever you are handing the system to a small-team pilot or external evaluator.

1. Limit the stack to the backend and dashboard; add Jira and the extension only after the base path is stable.
2. Confirm each SQL file from [LOCAL_SETUP.md](LOCAL_SETUP.md#5-supabase-sql-setup) exists in Supabase.
3. Verify `/api/health` shows `ready: true` and that `configuration_audit.table_dependencies` no longer list missing tables.
4. Record `rollout_assessment.pilot.status`, `configuration_audit`, and `readiness_overview` before the session for later reference.
5. Match `DEVHOUSE_WRITE_API_KEY` with `VITE_WRITE_API_KEY` if write actions will run.
6. For every section you will present, note its truthfulness class (real/inferred/heuristic/fallback) per [FEATURE_MATURITY_MATRIX.md](FEATURE_MATURITY_MATRIX.md).
7. Keep a short log of blockers, warnings, and follow-up actions to close afterwards.

## During demo

Use this order to keep the walkthrough honest and stable:

1. Start with health/readiness.
2. State operating mode and pilot status.
3. Show overview and mapping sections.
4. Show delivery timeline and call out provenance.
5. Show summaries and explain whether they are inferred or heuristic.
6. Show optional write flows only if write auth is confirmed.
7. Show extension enrichment last, not first.

## Truthfulness script

Use these terms consistently:

- real: direct records or explicit persisted data
- connector-backed: explicit delivery-stage evidence
- inferred: deterministic interpretation from linked activity
- heuristic: directional scoring or synthesized judgment
- fallback/mock: placeholder continuity only

Avoid:

- calling inferred or heuristic sections “ground truth”
- presenting mocked stages as direct PR/CI/deployment proof
- presenting fallback storage as durable persistence

## If something breaks during demo

### Backend is degraded

Do:

1. read `rollout_assessment.pilot`
2. summarize blockers
3. switch to a reduced read-only walkthrough if needed

### Dashboard loads but write actions fail

Do:

1. check write-key alignment
2. skip write actions
3. continue with read-only sections

### Extension tracks but does not upload

Do:

1. confirm extension settings
2. confirm `extension_events` exists
3. explain extension as optional enrichment, not core dependency

### Snapshots are missing or stale

Do:

1. disclose live-only fallback or stale snapshot state
2. continue only if the operator is comfortable explaining freshness limits

### Timeline or summaries are partially unavailable

Do:

1. explain whether source data is sparse, inferred, or mocked
2. continue with readiness, mapping, and other available sections

For deeper recovery, use [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
For health field interpretation, use [HEALTH_AND_READINESS_REFERENCE.md](HEALTH_AND_READINESS_REFERENCE.md).

## After demo

Capture these immediately after the session:

- operating mode during session
- `rollout_assessment.pilot.status`
- sections shown
- sections skipped
- failures observed
- whether truthfulness disclaimers were needed
- follow-up fixes required before next session

## Operator go/no-go rule

Run the session as a full pilot demo only if all are true:

- backend health responds
- dashboard loads
- pilot rollout assessment is not `blocked`
- operator understands storage modes
- operator understands provenance and feature maturity

Otherwise, run a reduced evaluation walkthrough instead of implying full pilot readiness.
