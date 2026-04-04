# Req_codeMapping Deployment Notes

This file is the backend deployment and rollout note set. For the evaluator-oriented local path, start with:

- `../../docs/START_HERE.md`
- `../../docs/FIRST_10_MINUTES.md`
- `../../docs/LOCAL_SETUP.md`
- `../../docs/CONTROLLED_PILOT_SETUP.md`
- `../../docs/HEALTH_AND_READINESS_REFERENCE.md`
- `../../docs/PILOT_HANDOFF_SUMMARY.md`
- `../../docs/OPERATOR_CHEAT_SHEET.md`
- `../../docs/FEATURE_MATURITY_MATRIX.md`
- `../../docs/PILOT_READINESS_CHECKLIST.md`
- `../../docs/DEMO_OPERATOR_RUNBOOK.md`

## 1. Apply SQL migrations in Supabase

Run these SQL files in order:

1. `sql/create_extension_events.sql`
2. `../JIRA_tokenFetching/sql/create_req_code_mapping.sql`
3. `sql/create_mapping_feedback.sql`
4. `sql/create_project_intake_records.sql`
5. `sql/create_analytics_snapshots.sql`

The last migration also adds the `source` column to `req_code_mapping`.

## 2. Configure environment variables

Copy `.env.example` to `.env` and set:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `FRONTEND_URL`
- `ALLOWED_ORIGINS`

Optional:

- `DEVHOUSE_WRITE_API_KEY`
- `DEVHOUSE_DISABLE_FILE_FALLBACK=true`
- `DEVHOUSE_STORAGE_PROBE_TTL_SECONDS=30`
- `DEVHOUSE_ANALYTICS_SNAPSHOTS_ENABLED=true`
- `DEVHOUSE_ANALYTICS_SNAPSHOT_MAX_AGE_SECONDS=120`

If `DEVHOUSE_WRITE_API_KEY` is set, the following endpoints require it:

- `POST /api/sync`
- `POST /api/mapping-feedback`
- `POST /api/project-intake`
- `POST /api/match-commit`
- `POST /api/extension-events/webhook`

Send it using:

- `X-API-Key: <value>`
or
- `Authorization: Bearer <value>`

## 3. Dashboard configuration

If write auth is enabled, set `VITE_WRITE_API_KEY` in the dashboard `.env` file so sync and feedback actions continue to work from the UI.

The dashboard should also point `VITE_API_BASE_URL` at this backend, typically:

- `http://127.0.0.1:8000`

Pilot smoke-test order after backend startup:

1. `GET /api/health`
2. `GET /api/dashboard`
3. `GET /api/delivery-timeline`
4. Open the dashboard

Do not treat `/api/health` alone as sufficient. A backend can report a degraded state cleanly while data-backed routes still fail because Supabase is not actually configured for dashboard reads.

## 4. Current fallback behavior

Until the new tables exist, the backend can still fall back to local JSON for mapping feedback. Once the SQL migrations are applied successfully, set `DEVHOUSE_DISABLE_FILE_FALLBACK=true` to enforce Supabase-backed persistence only and avoid local state drift across deployments.

## 5. Manual intake expectations

The dashboard manual intake form now supports:

- `status`
- `priority`
- `issue_type`
- `owner_email`
- `reporter_email`
- `timeline_start`
- `timeline_end`

Timeline inputs are normalized to ISO timestamps on the backend. Invalid timestamps or an end time earlier than the start time are rejected with `400` responses.

Operational note:

- `POST /api/project-intake` still requires the backend to reach `req_code_mapping`. If `SUPABASE_URL` is missing or invalid, the route should be treated as unavailable even when write auth is disabled.
- `description` must be at least 10 characters because it is validated by `ProjectIntakePayload`.

## 6. Readiness and health

Use `GET /api/health` to verify launch readiness.

The response now includes:

- `ready`
- `operating_mode`
- `missing_required_env`
- `supabase_configured`
- `write_auth_enabled`
- `file_fallback_disabled`
- `optional_modules`
- `optional_module_details`
- `feedback_storage_mode`
- `intake_storage_mode`
- `analytics_storage_mode`
- `analytics_snapshots_enabled`
- `allowed_origins`
- `match_model`
- `degraded_reasons`
- `warnings`
- `recommendations`
- `readiness_checks`
- `configuration`
- `configuration_audit`
- `snapshot_health`
- `readiness_overview`
- `setup_progress`
- `capabilities`
- `rollout_blockers`
- `rollout_assessment`

If `ready` is `false`, the service will still start, but it should be treated as a degraded environment until the required configuration is supplied.

`operating_mode` is intended to make rollout state obvious:

- `degraded`: missing required environment or invalid origin configuration
- `local-demo`: backend can run locally, but write auth and/or Supabase persistence are not fully production-safe
- `pilot-ready`: required configuration is present and launch-critical persistence works, but some deployment hardening is still optional
- `production-ready`: required configuration is present, write auth is enabled, and feedback persistence is fully Supabase-backed

`readiness_checks` is a checklist-style breakdown used by the dashboard readiness panel. Each check includes:

- `key`
- `label`
- `category`
- `status`
- `severity`
- `current`
- `desired`
- `action`

Use this list to guide remediation rather than relying only on top-level warning strings.

`category` lets the dashboard and future setup tooling group problems into areas like configuration, security, persistence, caching, and optional module availability.

`readiness_overview` summarizes those checks into:

- `status_counts`
- `category_counts`
- `blocking_category_counts`
- `blocking_categories`
- `pilot_blockers`
- `launch_blockers`

Use it when you need a compact operational view of where setup debt is concentrated.

`setup_progress` provides a compact completion-style view for pilot operators:

- required environment values ready vs total
- SQL-backed dependencies ready vs total
- cached views ready vs total
- healthy readiness checks vs total
- pilot-ready vs launch-ready booleans

For rollout decisions:

- use `ready` and `operating_mode` first
- use `readiness_checks`, `warnings`, and `recommendations` to explain why the service is not yet acceptable
- use storage modes and snapshot health to decide whether the backend is only local-demo quality, pilot-ready, or more hardened

`snapshot_health` reports whether cached launch-critical views are actually available and fresh:

- `dashboard_analytics`
- `delivery_timeline`

Each entry includes:

- `enabled`
- `available`
- `fresh`
- `valid_payload`
- `source`
- `age_seconds`
- `generated_at`

This lets you distinguish between:

- snapshot-backed reads that are healthy
- missing snapshot rows
- stale snapshots that need a refresh
- invalid snapshots whose payload shape no longer matches the current code
- live-only fallback because the snapshot table is unavailable

If the snapshot table is missing, local demos may still work, but pilot operators should call out that analytics are running in live-only fallback.

`capabilities` is a boolean capability map that answers what the current backend instance can safely do right now, for example:

- persist feedback reviews
- persist manual intake
- protect write endpoints
- serve cached dashboard and timeline views
- support pilot rollout
- support self-serve launch expectations

`configuration_audit` is a machine-readable setup summary intended for dashboards and future setup automation. It includes:

- `required_env`
- `cors`
- `write_protection`
- `table_dependencies`
- `cached_views`
- `strict_mode`

Use it when you need to distinguish:

- missing environment variables vs invalid values
- optional demo-safe config vs required pilot/launch config
- missing SQL-backed tables vs merely stale cached views
- strict Supabase-only mode vs local fallback mode

`rollout_blockers` is derived from unhealthy readiness checks and is intended for dashboards or deployment tooling that needs a short list of concrete blockers before pilot or launch.

`optional_module_details` expands the simpler `optional_modules` booleans with:

- `available`
- `status`
- `reason`
- `action`

Use this when timeline or summary features disappear and you need to know whether the module is missing versus simply disabled by rollout state.

`rollout_assessment` separates:

- `pilot`
- `launch`

Each assessment includes:

- `status`: `blocked`, `caution`, or `ready`
- `summary`
- `blocker_count`
- `blockers`
- `next_actions`

Use this when you need a direct answer to:

- “Is this backend safe enough for a controlled pilot?”
- “Is this backend ready for broader self-serve launch expectations?”

The backend also validates numeric environment values such as:

- `REQ_MATCH_THRESHOLD`
- `REQ_MATCH_MAX_PATCH_CHARS`
- `REQ_MATCH_MAX_COMMIT_TEXT_CHARS`
- `REQ_MATCH_TOP_MATCHES`
- `DEVHOUSE_STORAGE_PROBE_TTL_SECONDS`
- `DEVHOUSE_ANALYTICS_SNAPSHOT_MAX_AGE_SECONDS`

If any of these are invalid or out of range, the service falls back to safe defaults and reports the problem through `warnings`, `recommendations`, and the dashboard readiness panel.

The backend also validates that `SUPABASE_URL` is a real `https://...` base URL. A value that is present but malformed is treated as a critical rollout blocker because REST calls will fail even though credentials appear configured.

## 7. Snapshot-backed analytics

If `analytics_snapshots` exists and `DEVHOUSE_ANALYTICS_SNAPSHOTS_ENABLED=true`, the backend will:

- read a fresh dashboard analytics snapshot when available
- fall back to live analytics computation when no fresh snapshot exists
- write the latest analytics snapshot back to Supabase after live computation

The dashboard metadata now exposes:

- `analytics_storage_mode`
- `analytics_source`
- `analytics_generated_at`
- `analytics_snapshot_age_seconds`

Use these fields to confirm whether the UI is serving live analytics or a fresh cached snapshot.
