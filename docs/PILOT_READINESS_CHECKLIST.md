# Pilot Readiness Checklist

Use this before a customer pilot, evaluator walkthrough, or internal launch demo.

## Core platform

- [ ] `backend/Req_codeMapping/.env` is filled with production or pilot-ready values
- [ ] `Manager_Dashboard/.env` points at the correct backend URL
- [ ] All required SQL migrations have been applied
- [ ] `GET /api/health` returns `status: "ok"`
- [ ] `GET /api/health` returns `ready: true`
- [ ] `missing_required_env` is empty
- [ ] `operating_mode` is acceptable for the pilot

## Persistence and auth

- [ ] `DEVHOUSE_WRITE_API_KEY` is set if write endpoints must be protected
- [ ] `VITE_WRITE_API_KEY` matches the backend write key when write auth is enabled
- [ ] `feedback_storage_mode` is acceptable for the environment
- [ ] `intake_storage_mode` is acceptable for the environment
- [ ] `analytics_storage_mode` is acceptable for the environment

## Snapshots and analytics

- [ ] `DEVHOUSE_ANALYTICS_SNAPSHOTS_ENABLED=true`
- [ ] `create_analytics_snapshots.sql` has been applied
- [ ] dashboard metadata shows snapshots are available or intentionally disabled
- [ ] `snapshot_health` is acceptable for pilot use
- [ ] timeline section renders
- [ ] showcase summaries are visible when data exists

## Jira integration

- [ ] `backend/JIRA_tokenFetching/.env` is complete
- [ ] Jira service starts on the intended port
- [ ] `GET /health` on the Jira service is healthy
- [ ] `GET /jira/sync` succeeds
- [ ] `req_code_mapping` has current records

## Extension readiness

- [ ] `create_extension_events.sql` has been applied
- [ ] extension compiles successfully
- [ ] `devintel.supabaseUrl` is set
- [ ] `devintel.supabaseKey` is set
- [ ] telemetry enabled setting is verified
- [ ] extension can upload a commit event
- [ ] extension-only local mode behavior is understood if uploads are intentionally disabled

## Dashboard validation

- [ ] dashboard loads without the backend connection warning
- [ ] dashboard does not show degraded-readiness guidance for a ready-mode demo
- [ ] sync action works
- [ ] intake action works if used in the demo
- [ ] feedback action works if used in the demo
- [ ] timeline and summary sections show expected content
- [ ] timeline provenance is understood before presenting it as customer evidence
- [ ] real vs inferred vs mocked data has been reviewed by the demo operator

## Final operator check

- [ ] startup order is documented for the demo operator
- [ ] local URLs or pilot URLs are written down
- [ ] fallback plan exists if Jira sync or extension upload is unavailable
- [ ] operator knows whether the demo is minimal, data-backed, or full showcase
- [ ] storage modes are understood and acceptable
