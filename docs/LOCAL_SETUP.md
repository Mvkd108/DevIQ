# Local Setup

This guide is for a new evaluator, demo operator, or pilot team running DevHouse26 locally on Windows PowerShell.

Before using this full guide, if you are starting from zero use:

- [START_HERE.md](START_HERE.md)
- [FIRST_10_MINUTES.md](FIRST_10_MINUTES.md)
- [CONTROLLED_PILOT_SETUP.md](CONTROLLED_PILOT_SETUP.md) if the goal is a small-team pilot rather than a solo local demo
- [HEALTH_AND_READINESS_REFERENCE.md](HEALTH_AND_READINESS_REFERENCE.md) if you need field-level health interpretation

## 1. Prerequisites

Install these first:

- Node.js 20+ with `npm`
- Python 3.11.x
- VS Code if you plan to run the extension
- A Supabase project for any ready-mode or data-backed demo

## 2. Decide your target outcome

Pick one path before you start:

| Outcome | Required services | Requires Supabase | Best for |
| --- | --- | --- | --- |
| Quick dashboard-only demo | `backend/Req_codeMapping`, `Manager_Dashboard` | Recommended | Fast evaluator walkthrough |
| Data-backed local demo | Same services with real env and SQL | Yes | Real storage, timeline, summaries, and health clarity |
| Full showcase demo | Data-backed demo plus Jira service and extension | Yes | Richest pilot/demo path |
| Extension demo path | `telemetry-extension` only or extension plus full stack | Optional for local-only, yes for uploads | VS Code extension validation |
| Controlled pilot setup | Backend and dashboard first, optional enrichments later | Yes | Small-team pilot with tighter operational control |

## 3. Create local env files

From the repo root:

```powershell
cd C:\Users\madha\DevHouse26-main\DevHouse26-main
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local.ps1
```

This creates these files if missing:

- `backend/Req_codeMapping/.env`
- `backend/JIRA_tokenFetching/.env`
- `Manager_Dashboard/.env`

## 4. Fill the env files

### `backend/Req_codeMapping/.env`

This file matters first.

Required for ready mode:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` or `SUPABASE_ANON_KEY`

Recommended local values:

- `FRONTEND_URL=http://localhost:5173`
- `ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
- `DEVHOUSE_ANALYTICS_SNAPSHOTS_ENABLED=true`
- `DEVHOUSE_ANALYTICS_SNAPSHOT_MAX_AGE_SECONDS=120`

Optional:

- `DEVHOUSE_WRITE_API_KEY`
- `DEVHOUSE_DISABLE_FILE_FALLBACK=false`
- `DEVHOUSE_STORAGE_PROBE_TTL_SECONDS=30`

### `Manager_Dashboard/.env`

Required:

- `VITE_API_BASE_URL=http://127.0.0.1:8000`

Optional:

- `VITE_WRITE_API_KEY`

Rule:

- if the backend sets `DEVHOUSE_WRITE_API_KEY`, the dashboard must use the same value in `VITE_WRITE_API_KEY`

### `backend/JIRA_tokenFetching/.env`

Only fill this if you want Jira-backed demos.

Required:

- `JIRA_URL`
- `JIRA_EMAIL`
- `JIRA_TOKEN`
- `JIRA_PROJECT`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

Recommended local values:

- `PORT=8001`
- `AUTO_SYNC_ON_STARTUP=false`
- `ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173`

## 5. Supabase SQL setup

Apply these SQL files in this exact order:

1. `backend/Req_codeMapping/sql/create_extension_events.sql`
2. `backend/JIRA_tokenFetching/sql/create_req_code_mapping.sql`
3. `backend/Req_codeMapping/sql/create_mapping_feedback.sql`
4. `backend/Req_codeMapping/sql/create_project_intake_records.sql`
5. `backend/Req_codeMapping/sql/create_analytics_snapshots.sql`

Why the order matters:

- `create_req_code_mapping.sql` creates the issue table used by the dashboard and Jira sync
- `create_project_intake_records.sql` adds intake storage and the `source` column used in newer flows
- `create_extension_events.sql` must exist before the extension can upload
- `create_mapping_feedback.sql` controls feedback persistence
- `create_analytics_snapshots.sql` enables snapshot-backed analytics and readiness checks

## 6. Exact startup order

Use this order for normal local evaluation:

1. Create env files
2. Fill `backend/Req_codeMapping/.env`
3. Apply SQL migrations
4. Start `backend/Req_codeMapping`
5. Check `GET http://127.0.0.1:8000/api/health`
6. Confirm storage, auth, and snapshot state
7. Fill `Manager_Dashboard/.env`
8. Start `Manager_Dashboard`
9. Open `http://127.0.0.1:5173`
10. Optionally start `backend/JIRA_tokenFetching`
11. Optionally run `telemetry-extension`

Do not start with the extension or Jira service unless the main backend and dashboard are already known-good.

## 7. Start the main backend first

Service: `backend/Req_codeMapping`

```powershell
cd C:\Users\madha\DevHouse26-main\DevHouse26-main\backend\Req_codeMapping
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

If `python -m venv .venv` fails on a managed Windows image, use any other working Python environment, install `requirements.txt` there, then rerun the backend start command from that environment.

### Main backend URLs

- Health: `http://127.0.0.1:8000/api/health`
- Dashboard feed: `http://127.0.0.1:8000/api/dashboard`
- Delivery timeline: `http://127.0.0.1:8000/api/delivery-timeline`

### What to verify at `/api/health`

If you need example healthy and degraded states, use [HEALTH_AND_READINESS_REFERENCE.md](HEALTH_AND_READINESS_REFERENCE.md).

Minimum ready-state checks:

- `status` is `ok`
- `ready` is `true`
- `missing_required_env` is empty

Operational checks that matter for pilots:

- `operating_mode` is acceptable
- `feedback_storage_mode` is acceptable
- `intake_storage_mode` is acceptable
- `analytics_storage_mode` is acceptable
- `analytics_snapshots_enabled` matches intent
- `snapshot_health` is acceptable if snapshots are enabled
- `GET /api/dashboard` returns JSON
- `GET /api/delivery-timeline` returns JSON

Practical interpretation:

- `degraded`: missing required env or rollout blockers remain
- `local-demo`: works for local evaluation, but not fully hardened
- `pilot-ready`: acceptable for pilot/demo use
- `production-ready`: launch-hardened path with stricter persistence and auth

## 8. Start the dashboard second

Service: `Manager_Dashboard`

```powershell
cd C:\Users\madha\DevHouse26-main\DevHouse26-main\Manager_Dashboard
npm install
npm run dev
```

Open:

- `http://127.0.0.1:5173`

### Healthy dashboard state

Expected:

- the page loads
- the overview renders
- no backend connection warning
- no degraded-readiness panel for a fully ready demo
- timeline section is visible
- summary sections render when data exists
- knowledge risk section renders
- manual intake form loads without a validation or auth mismatch banner unless that state is expected

### Dashboard startup depends on these files

- `Manager_Dashboard/.env`
- `backend/Req_codeMapping/.env`

If the dashboard cannot connect, check the backend first before debugging the UI.

## 9. Quick dashboard-only demo

Use this path when you want the shortest evaluator flow:

1. Run `scripts/bootstrap-local.ps1`
2. Fill `backend/Req_codeMapping/.env`
3. Apply SQL
4. Start backend on `8000`
5. Verify `/api/health`
6. Fill `Manager_Dashboard/.env`
7. Start dashboard on `5173`
8. Open the dashboard

## 10. Data-backed local demo

Use this path when you want real storage and clearer readiness:

1. Complete the quick dashboard-only demo
2. Confirm all five SQL files were applied
3. Confirm `/api/health` shows:
   - `ready: true`
   - acceptable `operating_mode`
   - acceptable `feedback_storage_mode`
   - acceptable `intake_storage_mode`
   - acceptable `analytics_storage_mode`
4. Verify snapshot health if snapshots are enabled
5. Verify the dashboard shows timeline and summaries
6. Verify the dashboard shows knowledge risk content and the manual intake section

## 11. Full showcase demo

Use this path when you want the richest end-to-end story:

1. Complete the data-backed local demo
2. Start `backend/JIRA_tokenFetching` on `8001`
3. Open `http://127.0.0.1:8001/health`
4. Trigger `http://127.0.0.1:8001/jira/sync`
5. Run the extension in VS Code
6. Make a commit in a monitored repo
7. Refresh the dashboard and validate new activity, timeline, and summaries

## 12. Controlled pilot setup

Use this when a small team will evaluate the product over more than one session.

Start with:

- backend
- dashboard

Delay until stable:

- Jira sync
- extension uploads
- presence monitoring

Read:

- [CONTROLLED_PILOT_SETUP.md](CONTROLLED_PILOT_SETUP.md)
- [PILOT_READINESS_CHECKLIST.md](PILOT_READINESS_CHECKLIST.md)
- [FEATURE_MATURITY_MATRIX.md](FEATURE_MATURITY_MATRIX.md)

## 13. Extension demo path

Use this when you only need extension validation or want to add extension data later:

1. Open [../telemetry-extension/README.md](../telemetry-extension/README.md)
2. `cd telemetry-extension`
3. `npm install`
4. `npm run compile`
5. Launch the Extension Development Host with `F5`
6. Leave Supabase settings blank for local-only testing, or configure them for upload testing

## 14. First 10 minutes checklist

Use [FIRST_10_MINUTES.md](FIRST_10_MINUTES.md) for the short version.

That checklist covers:

- clone/open repo
- apply SQL
- configure env
- start backend
- start dashboard
- check `/api/health`
- verify snapshots, storage, and auth state
- optionally start extension

## 15. Common failure recovery

Fast recovery order:

1. check `/api/health`
2. read `rollout_assessment.pilot`
3. confirm storage modes
4. move to [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

Most common recoveries:

- backend degraded: fix env or SQL first
- dashboard write failures: verify write-key match
- extension tracks but does not upload: verify extension settings and `extension_events`
- stale or missing snapshots: disclose fallback and verify snapshot health
- partial timeline or summaries: explain source-data gaps and provenance class

## 16. Troubleshooting

If you want the shortest symptom-to-fix lookup, use [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Backend degraded because of missing env

Symptoms:

- `/api/health` shows `ready: false`
- `missing_required_env` is populated
- dashboard shows degraded-readiness guidance

Fix:

1. Open `backend/Req_codeMapping/.env`
2. set `SUPABASE_URL`
3. set `SUPABASE_SERVICE_KEY` or `SUPABASE_ANON_KEY`
4. restart backend
5. recheck `/api/health`

### Write auth mismatch

Symptoms:

- sync, feedback, or intake actions return `401`

Check:

- `DEVHOUSE_WRITE_API_KEY` in `backend/Req_codeMapping/.env`
- `VITE_WRITE_API_KEY` in `Manager_Dashboard/.env`
- values are identical

### Analytics snapshot table missing

Symptoms:

- `analytics_storage_mode` stays `live-only`
- snapshot health reports unavailable or missing snapshot rows
- dashboard relies on live fallback only

Check:

- `backend/Req_codeMapping/sql/create_analytics_snapshots.sql` was applied
- `DEVHOUSE_ANALYTICS_SNAPSHOTS_ENABLED=true`
- `/api/health` snapshot-related warnings

### Feedback not persisting

Symptoms:

- feedback review actions do not remain after refresh
- `feedback_storage_mode` is `memory` or `file-fallback`

Check:

- `create_mapping_feedback.sql` was applied
- Supabase env is correct
- backend reports the expected `feedback_storage_mode`

### Manual intake not persisting

Symptoms:

- intake submission appears to succeed locally but does not persist as expected
- `intake_storage_mode` is not `supabase`

Check:

- `create_project_intake_records.sql` was applied
- Supabase env is set correctly
- backend storage mode in `/api/health`

### Timeline not loading

Symptoms:

- timeline section is empty or reduced

Check:

- `http://127.0.0.1:8000/api/delivery-timeline`
- `req_code_mapping` contains issue data
- extension events or linked commits exist
- health endpoint shows optional modules are enabled

### Summaries not loading

Symptoms:

- summary sections do not appear
- summaries load but look thin or incomplete

Check:

- dashboard analytics data exists
- enough issue and event data exists to generate summaries
- snapshot health is acceptable if snapshots are enabled
- see [DATA_PROVENANCE.md](DATA_PROVENANCE.md) before treating inferred or placeholder sections as stronger evidence than they are

### Extension not uploading

Symptoms:

- commits happen but no new extension activity appears

Check:

- `devintel.supabaseUrl`
- `devintel.supabaseKey`
- `devintel.telemetryEnabled`
- `extension_events` table exists

### Dashboard cannot reach backend

Symptoms:

- UI shows backend not reachable
- fetch errors on startup

Check:

- backend is running on `8000`
- `Manager_Dashboard/.env` points to `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/api/health` responds
- Vite was restarted after `.env` edits

## Focused troubleshooting matrix

| Symptom | Most likely cause | First response |
| --- | --- | --- |
| Backend degraded | missing Supabase env or dropped SQL migrations | Apply missing env/SQ L files, restart backend |
| Missing SQL migrations | table absence prevents storage modes | Apply the specific SQL file(s) in documented order |
| Write key mismatch | backend and dashboard keys disagree | Align `DEVHOUSE_WRITE_API_KEY`/`VITE_WRITE_API_KEY` |
| Stale snapshots | `analytics_storage_mode` = `live-only` or snapshots invalid | Run a write path (`sync`, `match_commit`, `project_intake`); reopen `/api/health` |
| Extension tracks but no uploads | Supabase config missing or targets unmatched | Confirm `devintel.supabaseUrl/Key` and `extension_events` table |

Reference this table from [DEMO_OPERATOR_RUNBOOK.md](DEMO_OPERATOR_RUNBOOK.md) when you need a quick fix for a pilot transaction.

## 17. Real vs inferred vs mocked guidance

Before any demo, read [DATA_PROVENANCE.md](DATA_PROVENANCE.md).

For a stricter feature classification view, also read [FEATURE_MATURITY_MATRIX.md](FEATURE_MATURITY_MATRIX.md).

Short version:

- requirement and commit records are the most direct evidence
- connector-backed stages are stronger than inferred stages
- inferred stages are deterministic but still interpreted
- mocked stages are placeholders and should be disclosed clearly
- some scores and summary judgments are heuristic, so present them as directional rather than definitive

For live evaluator sessions, use [DEMO_OPERATOR_RUNBOOK.md](DEMO_OPERATOR_RUNBOOK.md).
For a shorter live-session reference, use [OPERATOR_CHEAT_SHEET.md](OPERATOR_CHEAT_SHEET.md).
