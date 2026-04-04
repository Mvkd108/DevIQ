# Pilot Handoff Summary

Use this as the short document you send to a third-party evaluator or pilot operator.

## What this product is

Core evaluation flow:

1. `backend/Req_codeMapping`
2. `Manager_Dashboard`
3. optional `backend/JIRA_tokenFetching`
4. optional `telemetry-extension`

## What to start first

1. Create env files with `scripts/bootstrap-local.ps1`
2. Fill `backend/Req_codeMapping/.env`
3. Apply SQL in the documented order
4. Start the backend on `8000`
5. Check `http://127.0.0.1:8000/api/health`
6. Fill `Manager_Dashboard/.env`
7. Start the dashboard on `5173`

## Minimum pilot-safe checks

Before a pilot session, confirm:

- `status` is `ok`
- `ready` is `true`
- `rollout_assessment.pilot.status` is not `blocked`
- storage modes are understood
- timeline renders
- summaries render or their limits are understood

## What the operator must understand

- some sections are real records
- some sections are inferred
- some scores/judgments are heuristic
- some coverage may be fallback/mock

Read before presenting:

- [DATA_PROVENANCE.md](DATA_PROVENANCE.md)
- [FEATURE_MATURITY_MATRIX.md](FEATURE_MATURITY_MATRIX.md)

## If something breaks

Use these in order:

1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. [HEALTH_AND_READINESS_REFERENCE.md](HEALTH_AND_READINESS_REFERENCE.md)
3. [DEMO_OPERATOR_RUNBOOK.md](DEMO_OPERATOR_RUNBOOK.md)
