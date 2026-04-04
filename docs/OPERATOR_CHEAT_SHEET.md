# Operator Cheat Sheet

Use this during a live session when you need the minimum set of commands, URLs, and checks.

## Commands

### Create env files

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local.ps1
```

### Start backend

```powershell
cd .\backend\Req_codeMapping
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Start dashboard

```powershell
cd .\Manager_Dashboard
npm install
npm run dev
```

## URLs

- backend health: `http://127.0.0.1:8000/api/health`
- dashboard: `http://127.0.0.1:5173`
- dashboard data: `http://127.0.0.1:8000/api/dashboard`
- delivery timeline: `http://127.0.0.1:8000/api/delivery-timeline`
- Jira health: `http://127.0.0.1:8001/health`
- Jira sync: `http://127.0.0.1:8001/jira/sync`

## Fast checks

Before the session:

- `status` is `ok`
- `ready` is `true`
- `rollout_assessment.pilot.status` is not `blocked`
- write keys match if write actions are in scope
- timeline renders
- summaries render or their gaps are understood

## Fast recovery

- backend degraded: fix env or SQL first
- write actions fail: check key mismatch
- snapshots weak: disclose freshness limits
- extension not uploading: verify extension settings and `extension_events`
- timeline/summaries thin: explain source-data limits and provenance class
