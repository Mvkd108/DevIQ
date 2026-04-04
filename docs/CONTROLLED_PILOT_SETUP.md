# Controlled Pilot Setup

Use this path when you are setting up a small-team pilot rather than a one-person local demo.

## Goal

Reach a stable, honest, low-risk pilot state for a small team before enabling richer optional flows.

## Minimum pilot scope

Start with these only:

- `backend/Req_codeMapping`
- `Manager_Dashboard`

Add these later only after the base flow is stable:

- `backend/JIRA_tokenFetching`
- `telemetry-extension`

## Minimum configuration for pilot

Required:

- all SQL migrations applied
- `backend/Req_codeMapping/.env` filled
- `Manager_Dashboard/.env` filled
- `/api/health` returns `ready: true`
- `rollout_assessment.pilot.status` is `ready` or `caution`

Strongly recommended:

- `DEVHOUSE_WRITE_API_KEY` enabled
- `VITE_WRITE_API_KEY` matched
- `DEVHOUSE_ANALYTICS_SNAPSHOTS_ENABLED=true`
- storage modes understood before pilot kickoff

## What to disable initially

Disable or delay these until the pilot base is stable:

- extension presence monitoring if Python is not already validated
- extension upload testing if `extension_events` is not confirmed
- Jira auto-sync on startup
- any demo flow that depends on thin, inferred, or mocked downstream stages

## Suggested pilot rollout order

1. Stand up backend and dashboard only.
2. Verify health, storage modes, snapshot health, `/api/dashboard`, and `/api/delivery-timeline`.
3. Run a read-only walkthrough first.
4. Enable write actions only after write-key alignment is confirmed.
5. Add Jira sync only after base mapping flow is stable.
6. Add extension uploads only after the pilot team understands truthfulness and maturity limits.

## What to monitor during pilot

Check these regularly:

- `operating_mode`
- `rollout_assessment.pilot`
- `feedback_storage_mode`
- `intake_storage_mode`
- `analytics_storage_mode`
- `snapshot_health.dashboard_analytics`
- `snapshot_health.delivery_timeline`
- dashboard sections for timeline and summaries

## Minimum acceptable pilot state

Run a controlled pilot if all are true:

- backend health endpoint responds
- dashboard and timeline endpoints respond with JSON
- dashboard loads
- mapping data exists
- timeline renders
- summaries render or their absence is understood and disclosed
- storage modes are acceptable
- rollout assessment for pilot is not `blocked`

## If something breaks during pilot

Use this order:

1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. [DEMO_OPERATOR_RUNBOOK.md](DEMO_OPERATOR_RUNBOOK.md)
3. [backend/Req_codeMapping/DEPLOYMENT.md](../backend/Req_codeMapping/DEPLOYMENT.md)
