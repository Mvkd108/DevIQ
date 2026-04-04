# DevHouse26

DevHouse26 can be stood up in stages. A new evaluator should not need to reverse-engineer which services matter, which SQL must be applied first, or what a healthy launch looks like.

## Start here first

If this is your first run, open:

- [docs/START_HERE.md](docs/START_HERE.md)

Then continue with:

- [docs/FIRST_10_MINUTES.md](docs/FIRST_10_MINUTES.md)
- [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md)
- [docs/CONTROLLED_PILOT_SETUP.md](docs/CONTROLLED_PILOT_SETUP.md) for small-team pilot rollout
- [docs/PILOT_HANDOFF_SUMMARY.md](docs/PILOT_HANDOFF_SUMMARY.md) if you are handing this to a third party

Core services:

- `backend/Req_codeMapping`: primary FastAPI backend and readiness source of truth
- `Manager_Dashboard`: React dashboard for demos and evaluation
- `backend/JIRA_tokenFetching`: optional Jira ingestion service
- `telemetry-extension`: optional VS Code extension for commit telemetry uploads

## Repo map

| Service | Path | Role | Core for evaluator path |
| --- | --- | --- | --- |
| Main backend | `backend/Req_codeMapping` | Readiness source of truth, storage modes, timeline and summary APIs | Yes |
| Dashboard | `Manager_Dashboard` | Main evaluation UI | Yes |
| Jira sync | `backend/JIRA_tokenFetching` | Optional issue ingestion from Jira | Optional |
| Extension | `telemetry-extension` | Optional commit telemetry enrichment | Optional |
| Docs | `docs` | Startup, pilot, troubleshooting, operator flow, truthfulness | Yes |

## Choose your path

Pick the smallest path that proves what you need.

| Path | Start these | Use this when | Success looks like |
| --- | --- | --- | --- |
| Quick dashboard-only demo | `backend/Req_codeMapping`, `Manager_Dashboard` | You want a fast evaluator walkthrough of startup, readiness, and UI flow | Dashboard loads at `http://127.0.0.1:5173`; backend health responds at `http://127.0.0.1:8000/api/health` |
| Data-backed local demo | Dashboard-only path plus Supabase config and SQL migrations | You want real persistence, storage-mode clarity, timeline data, intake, and snapshots | `ready: true`, acceptable `operating_mode`, storage modes visible, snapshots available |
| Full showcase demo | Data-backed path plus Jira service and extension | You want Jira ingestion, extension uploads, richer timeline coverage, and summary cards | Jira sync works, extension uploads succeed, timeline and summaries populate |
| Extension demo path | `telemetry-extension` only or extension plus full stack | You want to validate VS Code behavior before or alongside the main product | Extension compiles, launches in Extension Development Host, and optionally uploads to Supabase |
| Controlled pilot setup | Backend and dashboard first, optional enrichments added later | You need a lower-risk small-team pilot handoff | Pilot assessment is not blocked and operator knows storage/provenance limits |

## Exact startup order

Use this order unless you are doing extension-only work:

1. Clone or open the repo.
2. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local.ps1
```

3. Fill `backend/Req_codeMapping/.env`.
4. Apply the SQL files listed in [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md#5-supabase-sql-setup).
5. Start `backend/Req_codeMapping`.
6. Open `http://127.0.0.1:8000/api/health`.
7. Confirm:
   - `status` is `ok`
   - `ready` is `true` for a fully ready local demo
   - `operating_mode` is acceptable for your goal
8. Smoke-test the data routes before opening the UI:
   - `http://127.0.0.1:8000/api/dashboard`
   - `http://127.0.0.1:8000/api/delivery-timeline`
   Both should return JSON instead of a backend exception page.
9. Fill `Manager_Dashboard/.env`.
10. Start `Manager_Dashboard`.
11. Open `http://127.0.0.1:5173`.
12. Optionally start `backend/JIRA_tokenFetching` on `8001`.
13. Optionally run `telemetry-extension`.

Why this order matters:

- the dashboard depends on `backend/Req_codeMapping`
- the health endpoint is the fastest way to catch missing env, write auth, or snapshot/storage issues before opening the UI
- Jira sync and the extension add data richness, but should not block the first healthy dashboard run

## First 10 minutes

Use [docs/FIRST_10_MINUTES.md](docs/FIRST_10_MINUTES.md) for the short evaluator path.

That path covers:

- clone/open repo
- create env files
- apply SQL
- start backend
- check `/api/health`
- verify snapshots, storage, and auth state
- start dashboard
- optionally add extension telemetry

## Quickstart commands

### 1. Create env files

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local.ps1
```

### 2. Start the main backend

```powershell
cd .\backend\Req_codeMapping
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

If `python -m venv .venv` fails on a locked-down Windows image, install the backend requirements into another working Python environment first, then rerun the `uvicorn` command from that environment. Do not treat `/api/health` alone as sufficient; also smoke-test `/api/dashboard` and `/api/delivery-timeline`.

### 3. Check backend health

Open:

- `http://127.0.0.1:8000/api/health`

### 4. Start the dashboard

```powershell
cd .\Manager_Dashboard
npm install
npm run dev
```

### 5. Open the UI

Open:

- `http://127.0.0.1:5173`

## Ready mode vs degraded mode

### Ready mode

Good local demo state at `GET /api/health`:

- `status: "ok"`
- `ready: true`
- `missing_required_env: []`

Recommended additional checks:

- `operating_mode` is acceptable for the environment
- `feedback_storage_mode` is understood
- `intake_storage_mode` is understood
- `analytics_storage_mode` is understood
- `snapshot_health` is acceptable if snapshots are enabled

### Degraded mode

The backend can still start while degraded. Common reasons:

- missing Supabase env
- missing SQL migrations
- snapshot table unavailable
- fallback or derived storage modes still active

Degraded mode is useful for local debugging, but should be called out honestly in a pilot or evaluator session.

## What is real vs inferred vs mocked

Do not present all dashboard data as equally sourced.

- `real`: requirement and commit data coming from actual backend records
- `connector-backed`: stage data populated from explicit connector fields or event records
- `inferred`: stage or summary conclusions derived deterministically from linked activity
- `mocked`: placeholder stage coverage used when no delivery signal exists

Use [docs/DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md) before any pilot or customer-facing demo.
Use [docs/FEATURE_MATURITY_MATRIX.md](docs/FEATURE_MATURITY_MATRIX.md) when you need explicit `real` vs `inferred` vs `heuristic` vs `fallback/mock` classification.

## Required local config files

| File | Required for | Notes |
| --- | --- | --- |
| `backend/Req_codeMapping/.env` | Every dashboard run | Highest-priority local config file |
| `Manager_Dashboard/.env` | Every dashboard run | Must point `VITE_API_BASE_URL` to the backend |
| `backend/JIRA_tokenFetching/.env` | Jira-backed demos only | Keep local port on `8001` |
| VS Code `devintel.*` settings | Extension demos only | Controls upload behavior |

## Health endpoints and local URLs

| Surface | URL | Purpose |
| --- | --- | --- |
| Main backend health | `http://127.0.0.1:8000/api/health` | Readiness, storage mode, snapshots, auth, warnings |
| Main dashboard feed | `http://127.0.0.1:8000/api/dashboard` | Dashboard data contract |
| Delivery timeline | `http://127.0.0.1:8000/api/delivery-timeline` | Timeline and provenance data |
| Dashboard UI | `http://127.0.0.1:5173` | Evaluator-facing UI |
| Jira service health | `http://127.0.0.1:8001/health` | Optional Jira service readiness |
| Jira manual sync | `http://127.0.0.1:8001/jira/sync` | Optional Jira ingest trigger |

## Docs to use next

- First-run entrypoint: [docs/START_HERE.md](docs/START_HERE.md)
- Short evaluator path: [docs/FIRST_10_MINUTES.md](docs/FIRST_10_MINUTES.md)
- Full setup and troubleshooting: [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md)
- Focused troubleshooting matrix: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- Health/readiness field guide: [docs/HEALTH_AND_READINESS_REFERENCE.md](docs/HEALTH_AND_READINESS_REFERENCE.md)
- Truthful pilot guidance: [docs/DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md)
- Feature maturity matrix: [docs/FEATURE_MATURITY_MATRIX.md](docs/FEATURE_MATURITY_MATRIX.md)
- Pilot readiness checklist: [docs/PILOT_READINESS_CHECKLIST.md](docs/PILOT_READINESS_CHECKLIST.md)
- Third-party handoff summary: [docs/PILOT_HANDOFF_SUMMARY.md](docs/PILOT_HANDOFF_SUMMARY.md)
- Live session operator flow: [docs/DEMO_OPERATOR_RUNBOOK.md](docs/DEMO_OPERATOR_RUNBOOK.md)
- Operator cheat sheet: [docs/OPERATOR_CHEAT_SHEET.md](docs/OPERATOR_CHEAT_SHEET.md)
- Controlled pilot path: [docs/CONTROLLED_PILOT_SETUP.md](docs/CONTROLLED_PILOT_SETUP.md)
- Backend deployment/readiness notes: [backend/Req_codeMapping/DEPLOYMENT.md](backend/Req_codeMapping/DEPLOYMENT.md)
- Extension setup path: [telemetry-extension/README.md](telemetry-extension/README.md)
- Pilot operator checklist: [docs/DEMO_OPERATOR_RUNBOOK.md](docs/DEMO_OPERATOR_RUNBOOK.md)

## Feature truthfulness matrix

Maintain an honest narrative by using [docs/FEATURE_MATURITY_MATRIX.md](docs/FEATURE_MATURITY_MATRIX.md) before every customer or pilot story. The short version:

| Class | Description | Present as |
| --- | --- | --- |
| Real | Persisted records (issues, commits, snapshots, feedback) | Observed data |
| Inferred | Deterministically calculated timeline stages or summary statements | Interpreted insight |
| Heuristic | Risk, confidence, or impact scores | Directional guidance |
| Fallback/Mock | Placeholder or continuity data where evidence is missing | Demo-only coverage |

## Controlled pilot checklist

Operators should follow [docs/DEMO_OPERATOR_RUNBOOK.md](docs/DEMO_OPERATOR_RUNBOOK.md) so a small-team pilot can run without tribal knowledge. It captures before/during/after steps, verification of truthfulness, and quick recovery instructions.

## Startup order checklist

1. Bootstrap env templates via `scripts/bootstrap-local.ps1`.
2. Configure `backend/Req_codeMapping/.env` (Supabase URL, keys, storage toggles, write auth).
3. Apply SQL migrations in the documented order.
4. Start `backend/Req_codeMapping`, confirm `/api/health`, `configuration_audit`, and `readiness_overview`.
5. Configure `Manager_Dashboard/.env` with `VITE_API_BASE_URL` and optional write key.
6. Start the dashboard, confirm it can fetch the backend.
7. Only add Jira sync or extension uploads after the base stack is stable.
