# Pilot Operator Checklist

Use this sheet when you run a demo or pilot for an external evaluator or small team so they can self-check without your tribal knowledge.

## Before the session

1. Confirm `backend/Req_codeMapping` is running and `/api/health` responds with `ready: true` or acceptable pilot status.
2. Confirm `GET /api/dashboard` and `GET /api/delivery-timeline` both return JSON before you rely on the UI shell alone.
3. Review `configuration_audit` for missing env, write auth, or table dependencies; document any pending blockers.
4. Confirm `readiness_overview.blocking_categories` is empty or explains remaining caution.
5. Verify `rollout_assessment.pilot.status` is not `blocked`.
6. Confirm SQL migrations were applied in this order:
   - `create_extension_events.sql`
   - `create_req_code_mapping.sql`
   - `create_mapping_feedback.sql`
   - `create_project_intake_records.sql`
   - `create_analytics_snapshots.sql`
7. Confirm Supabase env is filled (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`/`ANON_KEY`), and if write actions are enabled the dashboard uses the same `DEVHOUSE_WRITE_API_KEY`/`VITE_WRITE_API_KEY`.
8. Turn the dashboard on and confirm it loads without the degraded guidance if you intend to run in ready mode.
9. Read the truthfulness matrix ([docs/FEATURE_MATURITY_MATRIX.md](FEATURE_MATURITY_MATRIX.md)) so you can explain whether each surface is real, inferred, heuristic, or fallback/mock.

## During the session

1. Start with `/api/health` and describe:
   - `operating_mode`
   - optional module availability
   - pilot vs launch blockers
2. Walk through the overview, mapping, timeline, and summary sections, calling out feature maturity when necessary.
3. Confirm the knowledge risk section and manual intake section are present before you present the dashboard as a pilot operator surface.
4. If you demonstrate write actions, pause before each to verify the write key is still intact and acknowledge when write endpoints are protected.
5. When showing the timeline, explain the provenance badges (connector vs inferred vs mock) and mention delivery quality indicators (coverage %, weakest stage, traceability strength).
6. When showing summaries, label them as inferred/heuristic and highlight confidence/freshness notes.
7. If extension telemetry is part of the story, remind viewers that uploads depend on Supabase config and `extension_events`.
8. Keep operators aware of any warnings in `/api/health` (`warnings`, `recommendations`) so you can honestly describe outstanding work.

## After the session

1. Capture the final `operating_mode` and `rollout_assessment` statuses.
2. Note any blockers, warnings, or degraded checks that remained.
3. Record the data provenance classification you used for contested features.
4. Confirm any follow-up actions (SQL, env, snapshots, extension config) that must happen before the next session.

## Quick verifications for common failures

- **Backend degraded**: re-check `/api/health`, read `missing_required_env`, `invalid_supabase_url`, and degrade reasons; restart after fixing env/migrations.
- **SQL missing**: confirm the relevant SQL file is applied before claiming the pilot is ready.
- **Write key mismatch**: compare backend `DEVHOUSE_WRITE_API_KEY` to dashboard `VITE_WRITE_API_KEY`.
- **Snapshots stale/missing**: trigger a sync or write path, refresh `/api/health`, and mention fallback modes.
- **Extension tracks but does not upload**: explain it as optional enrichment, check extension config, and confirm whether the upload target exists.

## Manual judgment

Operators must still interpret:

- whether `operating_mode` is acceptable for the chosen pilot (pilot vs self-serve).
- which readiness warnings can be tolerated during a quick demo.
- whether timeline or summary gaps are explainable given the truthfulness matrix.
- whether extension telemetry needs to be enabled or left optional for transparency.
