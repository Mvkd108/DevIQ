# First 10 Minutes

Use this checklist if you are evaluating the repo for the first time.

## Goal

Get the dashboard running in ready mode with the shortest reliable path.

## Steps

1. Open a PowerShell terminal at:

```powershell
cd C:\Users\madha\DevHouse26-main\DevHouse26-main
```

2. Create local env files:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local.ps1
```

3. Fill `backend/Req_codeMapping/.env` with:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` or `SUPABASE_ANON_KEY`

4. Fill `Manager_Dashboard/.env` with:

- `VITE_API_BASE_URL=http://127.0.0.1:8000`

5. Apply these SQL files in order:

- `backend/Req_codeMapping/sql/create_extension_events.sql`
- `backend/JIRA_tokenFetching/sql/create_req_code_mapping.sql`
- `backend/Req_codeMapping/sql/create_mapping_feedback.sql`
- `backend/Req_codeMapping/sql/create_project_intake_records.sql`
- `backend/Req_codeMapping/sql/create_analytics_snapshots.sql`

6. Start the backend:

```powershell
cd .\backend\Req_codeMapping
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

If `python -m venv .venv` fails on your machine, install `requirements.txt` into another working Python environment first, then rerun the backend start command there.

7. In a browser, open:

- `http://127.0.0.1:8000/api/health`

8. Confirm this before moving on:

- request succeeds
- `ready` is `true`
- `missing_required_env` is empty
- `feedback_storage_mode` is acceptable
- `intake_storage_mode` is acceptable
- `analytics_storage_mode` is acceptable
- `operating_mode` is acceptable for your evaluation goal
- `http://127.0.0.1:8000/api/dashboard` returns JSON
- `http://127.0.0.1:8000/api/delivery-timeline` returns JSON

9. Start the dashboard in a second terminal:

```powershell
cd C:\Users\madha\DevHouse26-main\DevHouse26-main\Manager_Dashboard
npm install
npm run dev
```

10. Open:

- `http://127.0.0.1:5173`

11. Confirm:

- the page renders
- no backend connection panel is shown
- timeline section is visible
- storage/auth state shown by the backend matches what you intended

## Optional next steps

### Add Jira data

1. Fill `backend/JIRA_tokenFetching/.env`
2. Start the Jira service on `8001`
3. Open `http://127.0.0.1:8001/jira/sync`

### Add extension telemetry

1. Open [../telemetry-extension/README.md](../telemetry-extension/README.md)
2. Compile the extension
3. Run it in VS Code
4. Configure `devintel.supabaseUrl` and `devintel.supabaseKey`

## If something goes wrong

- Dashboard offline: check `Manager_Dashboard/.env` and backend `8000`
- Backend degraded: check Supabase env and SQL migrations
- `/api/health` works but `/api/dashboard` or `/api/delivery-timeline` fails: backend env is still not usable for data-backed routes
- 401 on writes: match write keys between backend and dashboard
- Snapshots missing: apply `create_analytics_snapshots.sql` and recheck `/api/health`
- Extension not uploading: check `extension_events` and extension settings

Use [LOCAL_SETUP.md](LOCAL_SETUP.md) for the full setup guide and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for the symptom matrix.
