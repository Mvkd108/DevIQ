# Troubleshooting

Use this file when startup is blocked and you need the shortest route from symptom to fix.

## Fast triage order

Check these in order:

1. `http://127.0.0.1:8000/api/health`
2. `backend/Req_codeMapping/.env`
3. SQL migrations
4. `Manager_Dashboard/.env`
5. extension settings only after the backend and dashboard are already known-good

## Symptom matrix

| Symptom | Most likely cause | First check |
| --- | --- | --- |
| Backend is degraded | missing Supabase env or missing SQL | `/api/health` |
| Sync/intake/feedback returns `401` | write key mismatch | backend and dashboard env files |
| Snapshots are unavailable | snapshot table missing or disabled | `analytics_storage_mode`, `snapshot_health` |
| Feedback does not persist | feedback table missing or fallback mode active | `feedback_storage_mode` |
| Intake does not persist | intake table missing or derived mode active | `intake_storage_mode` |
| Timeline does not load | backend data missing or timeline module degraded | `/api/delivery-timeline` and health |
| Summaries do not load | insufficient source data or analytics degraded | dashboard plus health metadata |
| Extension does not upload | missing Supabase settings or missing `extension_events` | extension settings |
| Dashboard cannot reach backend | wrong API URL or backend not running | `VITE_API_BASE_URL` and `/api/health` |

## Backend degraded

Symptoms:

- `/api/health` shows `ready: false`
- `status` is `degraded`
- dashboard shows degraded-readiness guidance

Check:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` or `SUPABASE_ANON_KEY`
- SQL migrations were applied
- `operating_mode`
- `warnings`, `recommendations`, and `readiness_checks`

## Missing env

Symptoms:

- `missing_required_env` contains values
- startup logs warn about configuration

Fix:

1. open `backend/Req_codeMapping/.env`
2. add the missing values
3. restart the backend
4. re-open `/api/health`

## Write key mismatch

Symptoms:

- dashboard write actions fail with `401`

Check:

- `DEVHOUSE_WRITE_API_KEY` in `backend/Req_codeMapping/.env`
- `VITE_WRITE_API_KEY` in `Manager_Dashboard/.env`
- values match exactly

## Snapshot table missing

Symptoms:

- `analytics_storage_mode` remains `live-only`
- `snapshot_health` is unavailable, missing, or stale

Check:

- `backend/Req_codeMapping/sql/create_analytics_snapshots.sql` was applied
- `DEVHOUSE_ANALYTICS_SNAPSHOTS_ENABLED=true`
- health warnings mention snapshot availability

## Feedback not persisting

Symptoms:

- review action appears to run but does not stay persisted
- `feedback_storage_mode` is `memory` or `file-fallback`

Check:

- `create_mapping_feedback.sql` was applied
- Supabase env is correct
- health endpoint reports the expected `feedback_storage_mode`

## Intake not persisting

Symptoms:

- intake records do not remain after refresh
- `intake_storage_mode` is not `supabase`

Check:

- `create_project_intake_records.sql` was applied
- Supabase env is correct
- health endpoint reports the expected `intake_storage_mode`

## Timeline not loading

Symptoms:

- timeline section is empty
- delivery timeline endpoint errors or returns thin results

Check:

- `http://127.0.0.1:8000/api/delivery-timeline`
- `req_code_mapping` contains issue rows
- linked commit or extension event data exists
- health endpoint shows optional modules are enabled

## Summaries not loading

Symptoms:

- showcase summaries do not appear
- summary cards appear empty or unconvincing

Check:

- analytics data exists in `/api/dashboard`
- enough issue and event data exists to generate summaries
- snapshot health is acceptable if snapshots are enabled
- see [DATA_PROVENANCE.md](DATA_PROVENANCE.md) before assuming missing summaries indicate a product bug rather than missing source data

## Extension not uploading

Symptoms:

- commit happens
- no new activity appears later in the dashboard

Check:

- `devintel.supabaseUrl`
- `devintel.supabaseKey`
- `devintel.telemetryEnabled`
- `extension_events` table exists
- the extension and backend point at the same Supabase project

## Dashboard cannot reach backend

Symptoms:

- startup fetch errors
- "backend not reachable" guidance is shown

Check:

- backend is running on `8000`
- `Manager_Dashboard/.env` uses `VITE_API_BASE_URL=http://127.0.0.1:8000`
- Vite was restarted after `.env` edits
- `/api/health` responds directly in the browser
