# Start Here

Use this file if you are opening the repo for the first time and need a reliable path without live guidance.

## 1. Choose your goal

| Goal | Start with | Time | Outcome |
| --- | --- | --- | --- |
| Quick evaluator walkthrough | [FIRST_10_MINUTES.md](FIRST_10_MINUTES.md) | 10-15 min | Backend plus dashboard running with health checks |
| Deeper local evaluation | [LOCAL_SETUP.md](LOCAL_SETUP.md) | 20-30 min | Data-backed local environment with storage and snapshot checks |
| Controlled small-team pilot | [CONTROLLED_PILOT_SETUP.md](CONTROLLED_PILOT_SETUP.md) | 30-45 min | Pilot-safe configuration with explicit limits and monitoring |
| Live demo operation | [DEMO_OPERATOR_RUNBOOK.md](DEMO_OPERATOR_RUNBOOK.md) | 10 min prep | Before/during/after checklist and failure recovery |

## 2. Understand the repo map

| Area | Path | What it does | Core for evaluation |
| --- | --- | --- | --- |
| Main backend | `backend/Req_codeMapping` | FastAPI API, readiness contract, storage modes, timeline data, summary data | Yes |
| Dashboard | `Manager_Dashboard` | Evaluator-facing UI for overview, timeline, summaries, and review flows | Yes |
| Jira sync service | `backend/JIRA_tokenFetching` | Optional Jira ingestion into `req_code_mapping` | Optional |
| VS Code extension | `telemetry-extension` | Optional commit telemetry capture and upload to Supabase | Optional |
| SQL migrations | `backend/Req_codeMapping/sql`, `backend/JIRA_tokenFetching/sql` | Required schema for events, mappings, feedback, intake, and snapshots | Yes for data-backed use |

Core evaluation flow:

1. Main backend
2. Dashboard
3. Optional Jira sync
4. Optional extension

## 3. Exact first-run order

1. Open the repo root in PowerShell.
2. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local.ps1
```

3. Fill `backend/Req_codeMapping/.env`.
4. Apply SQL in the documented order.
5. Start `backend/Req_codeMapping`.
6. Open `http://127.0.0.1:8000/api/health`.
7. Verify:
   - `status: "ok"`
   - `ready: true`
   - `rollout_assessment.pilot.status` is not `blocked`
8. Smoke-test:
   - `http://127.0.0.1:8000/api/dashboard`
   - `http://127.0.0.1:8000/api/delivery-timeline`
9. Fill `Manager_Dashboard/.env`.
10. Start `Manager_Dashboard`.
11. Open `http://127.0.0.1:5173`.

## 4. Truthfulness rule before any demo

Do not present all UI sections as equally sourced.

- real: direct records and persisted data
- inferred: deterministic interpretation from linked activity
- heuristic: best-effort scoring or synthesized judgment from available signals
- fallback/mock: placeholder continuity where evidence is absent

Read these before a customer or pilot session:

- [DATA_PROVENANCE.md](DATA_PROVENANCE.md)
- [FEATURE_MATURITY_MATRIX.md](FEATURE_MATURITY_MATRIX.md)

## 5. What to do next

- Need exact commands: [FIRST_10_MINUTES.md](FIRST_10_MINUTES.md)
- Need full setup plus troubleshooting: [LOCAL_SETUP.md](LOCAL_SETUP.md)
- Need controlled pilot guidance: [CONTROLLED_PILOT_SETUP.md](CONTROLLED_PILOT_SETUP.md)
- Need health field interpretation: [HEALTH_AND_READINESS_REFERENCE.md](HEALTH_AND_READINESS_REFERENCE.md)
- Need a short handoff doc for another team: [PILOT_HANDOFF_SUMMARY.md](PILOT_HANDOFF_SUMMARY.md)
- Need live session checklist: [DEMO_OPERATOR_RUNBOOK.md](DEMO_OPERATOR_RUNBOOK.md)
- Need a one-page live reference: [OPERATOR_CHEAT_SHEET.md](OPERATOR_CHEAT_SHEET.md)
- Need pilot sign-off: [PILOT_READINESS_CHECKLIST.md](PILOT_READINESS_CHECKLIST.md)
- Need symptom-to-fix lookup: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Truthfulness reminder

Startup note:

- `python -m venv .venv` is the recommended backend path, not a guaranteed one on every Windows image. If venv creation fails, install `backend/Req_codeMapping/requirements.txt` into another working Python environment, then retry the backend start and recheck `/api/health`, `/api/dashboard`, and `/api/delivery-timeline`.

Before running a pilot, review [FEATURE_MATURITY_MATRIX.md](FEATURE_MATURITY_MATRIX.md) and [DEMO_OPERATOR_RUNBOOK.md](DEMO_OPERATOR_RUNBOOK.md) so you can describe each section as real, inferred, heuristic, or fallback/mock.
