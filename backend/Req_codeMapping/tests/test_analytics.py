from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def ensure_test_stubs() -> None:
    if "dotenv" not in sys.modules:
        dotenv = ModuleType("dotenv")
        dotenv.load_dotenv = lambda *args, **kwargs: None
        sys.modules["dotenv"] = dotenv

    if "fastapi" not in sys.modules:
        fastapi = ModuleType("fastapi")

        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class FastAPI:
            def __init__(self, *args, **kwargs):
                pass

            def add_middleware(self, *args, **kwargs):
                return None

            def get(self, *args, **kwargs):
                def decorator(func):
                    return func

                return decorator

            def post(self, *args, **kwargs):
                def decorator(func):
                    return func

                return decorator

        fastapi.FastAPI = FastAPI
        fastapi.HTTPException = HTTPException
        fastapi.Header = lambda default=None, alias=None: default
        sys.modules["fastapi"] = fastapi

    if "fastapi.middleware" not in sys.modules:
        sys.modules["fastapi.middleware"] = ModuleType("fastapi.middleware")

    if "fastapi.middleware.cors" not in sys.modules:
        cors = ModuleType("fastapi.middleware.cors")

        class CORSMiddleware:
            pass

        cors.CORSMiddleware = CORSMiddleware
        sys.modules["fastapi.middleware.cors"] = cors


ensure_test_stubs()

import main as main_module  # noqa: E402
from main import (  # noqa: E402
    build_dashboard_analytics,
    build_developer_metrics,
    build_effort_estimates,
    build_knowledge_risks,
    dashboard,
    extension_events_webhook,
    health,
    list_project_intake_records,
    match_commit_endpoint,
    persist_feedback_record,
    project_intake,
    require_write_access,
    save_mapping_feedback,
)
from schemas import MappingFeedbackPayload, ProjectIntakePayload  # noqa: E402


class AnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.issues = [
            {
                "issue_id": "KAN-1",
                "title": "Add login validation",
                "description": "Implement login validation, auth checks, and route guard handling.",
                "status": "In Progress",
                "issue_type": "Story",
                "priority": "High",
                "project_key": "KAN",
                "assignee_email": "alice@example.com",
                "reporter_email": "lead@example.com",
                "jira_created_at": "2026-03-20T09:00:00+00:00",
                "jira_updated_at": "2026-03-28T09:00:00+00:00",
                "created_at": "2026-03-20T09:00:00+00:00",
                "updated_at": "2026-03-28T09:00:00+00:00",
                "commits": ["c1", "c2"],
            },
            {
                "issue_id": "KAN-2",
                "title": "Refactor payments module",
                "description": "Refactor billing and payments module for provider migration and retries.",
                "status": "Review",
                "issue_type": "Task",
                "priority": "Medium",
                "project_key": "KAN",
                "assignee_email": "bob@example.com",
                "reporter_email": "lead@example.com",
                "jira_created_at": "2026-03-21T09:00:00+00:00",
                "jira_updated_at": "2026-03-29T09:00:00+00:00",
                "created_at": "2026-03-21T09:00:00+00:00",
                "updated_at": "2026-03-29T09:00:00+00:00",
                "commits": ["c3"],
            },
        ]
        self.events = [
            {
                "commit_id": "c1",
                "message": "Add login validation and route guard",
                "timestamp": "2026-03-25T10:00:00+00:00",
                "files": [{"file_path": "auth/login.ts", "patch": "+ validateLogin", "module": "auth", "directory": "auth"}],
                "files_json": {"files": [{"file_path": "auth/login.ts", "patch": "+ validateLogin", "module": "auth", "directory": "auth"}]},
                "diff_patch": "validateLogin route guard auth",
                "repository_name": "portal",
                "branch": "feature/KAN-1-login",
                "issue_id": "KAN-1",
                "linked_issue": "KAN-1",
                "modules_touched": ["auth"],
                "background_apps": [],
                "developer_id": "alice",
                "author": "Alice",
                "author_email": "alice@example.com",
                "additions": 50,
                "deletions": 10,
                "total_changes": 60,
                "attendance_pct": 100,
                "active_minutes": 90,
                "idle_minutes": 5,
                "focus_ratio": 0.96,
                "debug_session_count": 2,
            },
            {
                "commit_id": "c2",
                "message": "Harden auth middleware",
                "timestamp": "2026-03-29T22:15:00+00:00",
                "files": [{"file_path": "auth/middleware.ts", "patch": "+ auth middleware", "module": "auth", "directory": "auth"}],
                "files_json": {"files": [{"file_path": "auth/middleware.ts", "patch": "+ auth middleware", "module": "auth", "directory": "auth"}]},
                "diff_patch": "auth middleware validation",
                "repository_name": "portal",
                "branch": "feature/KAN-1-auth",
                "issue_id": "KAN-1",
                "linked_issue": "KAN-1",
                "modules_touched": ["auth"],
                "background_apps": [],
                "developer_id": "alice",
                "author": "Alice",
                "author_email": "alice@example.com",
                "additions": 10,
                "deletions": 3,
                "total_changes": 13,
                "attendance_pct": 100,
                "active_minutes": 40,
                "idle_minutes": 3,
                "focus_ratio": 0.91,
                "debug_session_count": 1,
            },
            {
                "commit_id": "c3",
                "message": "Refactor payments retries",
                "timestamp": "2026-03-26T11:30:00+00:00",
                "files": [{"file_path": "payments/retries.ts", "patch": "+ retries", "module": "payments", "directory": "payments"}],
                "files_json": {"files": [{"file_path": "payments/retries.ts", "patch": "+ retries", "module": "payments", "directory": "payments"}]},
                "diff_patch": "payments retries refactor provider",
                "repository_name": "portal",
                "branch": "task/KAN-2-payments",
                "issue_id": "KAN-2",
                "linked_issue": "KAN-2",
                "modules_touched": ["payments"],
                "background_apps": [],
                "developer_id": "bob",
                "author": "Bob",
                "author_email": "bob@example.com",
                "additions": 80,
                "deletions": 40,
                "total_changes": 120,
                "attendance_pct": 90,
                "active_minutes": 120,
                "idle_minutes": 10,
                "focus_ratio": 0.88,
                "debug_session_count": 3,
            },
        ]

    def test_effort_estimation_produces_progress_and_variance(self) -> None:
        estimates = build_effort_estimates(self.issues, {event["commit_id"]: event for event in self.events})
        self.assertEqual(len(estimates), 2)
        first = estimates[0]
        self.assertIn("planned_effort_points", first)
        self.assertIn("observed_effort_points", first)
        self.assertIn(first["variance"], {"above plan", "on plan", "below plan", "not started"})
        self.assertGreaterEqual(first["progress_pct"], 0)

    def test_developer_metrics_score_and_trend(self) -> None:
        linked_commit_ids = {"c1", "c2", "c3"}
        metrics = build_developer_metrics(self.events, self.issues, linked_commit_ids)
        self.assertEqual(len(metrics), 2)
        top = metrics[0]
        self.assertIn("impact_score", top)
        self.assertIn("performance_trend", top)
        self.assertIn(top["performance_trend"], {"rising", "stable", "slowing"})
        self.assertGreater(top["impact_score"], 0)

    def test_knowledge_risk_detects_concentration(self) -> None:
        risks = build_knowledge_risks(self.events)
        self.assertTrue(any(risk["module"] == "auth" for risk in risks))
        auth_risk = next(risk for risk in risks if risk["module"] == "auth")
        self.assertIn(auth_risk["severity"], {"high", "medium"})

    def test_dashboard_analytics_contract_contains_required_sections(self) -> None:
        analytics = build_dashboard_analytics(self.issues, self.events, {"updates": []})
        self.assertIn("project_intake", analytics)
        self.assertIn("effort_estimates", analytics)
        self.assertIn("developer_metrics", analytics)
        self.assertIn("impact_summaries", analytics)
        self.assertIn("transparency", analytics)
        self.assertIn("knowledge_risks", analytics)
        self.assertIn("activity_log", analytics)

    def test_require_write_access_rejects_invalid_key(self) -> None:
        with patch("main.WRITE_API_KEY", "secret-key"):
            with self.assertRaises(Exception) as error:
                require_write_access("wrong-key", None)
            self.assertEqual(getattr(error.exception, "status_code", None), 401)

    def test_require_write_access_accepts_bearer_token(self) -> None:
        with patch("main.WRITE_API_KEY", "secret-key"):
            require_write_access(None, "Bearer secret-key")

    def test_save_mapping_feedback_persists_when_authorized(self) -> None:
        payload = MappingFeedbackPayload(
            commit_id="c1",
            feedback_type="approved",
            predicted_issue_id="KAN-1",
            reviewed_by="tester",
        )
        with (
            patch("main.WRITE_API_KEY", "secret-key"),
            patch("main.persist_feedback_record") as persist_mock,
            patch("main.refresh_cached_views") as refresh_mock,
        ):
            response = save_mapping_feedback(payload, x_api_key="secret-key", authorization=None)
        persist_mock.assert_called_once()
        refresh_mock.assert_called_once()
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["feedback"]["commit_id"], "c1")

    def test_project_intake_persists_manual_record_when_authorized(self) -> None:
        payload = ProjectIntakePayload(
            title="Add audit timeline",
            description="Track audit timeline and ownership metadata for newly created requirements.",
            project_key="KAN",
            owner_email="owner@example.com",
            reporter_email="reporter@example.com",
            timeline_start="2026-04-02T10:00",
            timeline_end="2026-04-02T12:00",
        )
        with (
            patch("main.WRITE_API_KEY", "secret-key"),
            patch("main.post_rows") as post_rows_mock,
            patch("main.persist_project_intake_record") as persist_mock,
            patch("main.refresh_cached_views") as refresh_mock,
        ):
            response = project_intake(payload, x_api_key="secret-key", authorization=None)

        post_rows_mock.assert_called()
        persist_mock.assert_called_once()
        refresh_mock.assert_called_once()
        self.assertEqual(response["status"], "accepted")
        self.assertEqual(response["record"]["source"], "manual")
        self.assertTrue(str(response["record"]["jira_created_at"]).endswith("+00:00"))

    def test_project_intake_rejects_inverted_timeline(self) -> None:
        payload = ProjectIntakePayload(
            title="Add audit timeline",
            description="Track audit timeline and ownership metadata for newly created requirements.",
            project_key="KAN",
            timeline_start="2026-04-02T12:00",
            timeline_end="2026-04-02T10:00",
        )
        with patch("main.WRITE_API_KEY", "secret-key"):
            with self.assertRaises(Exception) as error:
                project_intake(payload, x_api_key="secret-key", authorization=None)
        self.assertEqual(getattr(error.exception, "status_code", None), 400)

    def test_project_intake_rejects_invalid_timestamp(self) -> None:
        payload = ProjectIntakePayload(
            title="Add audit timeline",
            description="Track audit timeline and ownership metadata for newly created requirements.",
            project_key="KAN",
            timeline_start="not-a-date",
        )
        with patch("main.WRITE_API_KEY", "secret-key"):
            with self.assertRaises(Exception) as error:
                project_intake(payload, x_api_key="secret-key", authorization=None)
        self.assertEqual(getattr(error.exception, "status_code", None), 400)

    def test_match_commit_endpoint_requires_write_access(self) -> None:
        payload = {"commit_id": "c1", "message": "test"}
        with patch("main.WRITE_API_KEY", "secret-key"):
            with self.assertRaises(Exception) as error:
                match_commit_endpoint(payload, x_api_key="wrong-key", authorization=None)
        self.assertEqual(getattr(error.exception, "status_code", None), 401)

    def test_match_commit_endpoint_refreshes_analytics_snapshot(self) -> None:
        payload = {"commit_id": "c1", "message": "test"}
        with (
            patch("main.WRITE_API_KEY", "secret-key"),
            patch("main.process_single_commit_event", return_value={"status": "mapped", "commit_id": "c1"}) as process_mock,
            patch("main.refresh_cached_views") as refresh_mock,
        ):
            response = match_commit_endpoint(payload, x_api_key="secret-key", authorization=None)
        process_mock.assert_called_once()
        refresh_mock.assert_called_once()
        self.assertEqual(response["status"], "mapped")

    def test_extension_webhook_accepts_authorized_non_insert_as_ignored(self) -> None:
        payload = {"type": "update", "commit_id": "c1"}
        with patch("main.WRITE_API_KEY", "secret-key"):
            response = extension_events_webhook(payload, x_api_key="secret-key", authorization=None)
        self.assertEqual(response["status"], "ignored")

    def test_extension_webhook_refreshes_analytics_snapshot_for_insert_events(self) -> None:
        payload = {"type": "insert", "record": {"commit_id": "c1", "message": "test"}}
        with (
            patch("main.WRITE_API_KEY", "secret-key"),
            patch("main.process_single_commit_event", return_value={"status": "mapped", "commit_id": "c1"}) as process_mock,
            patch("main.refresh_cached_views") as refresh_mock,
        ):
            response = extension_events_webhook(payload, x_api_key="secret-key", authorization=None)
        process_mock.assert_called_once()
        refresh_mock.assert_called_once()
        self.assertEqual(response["status"], "mapped")

    def test_health_reports_storage_modes(self) -> None:
        with (
            patch("main.SUPABASE_URL", "https://example.supabase.co"),
            patch("main.SUPABASE_API_KEY", "test-key"),
            patch("main.WRITE_API_KEY", "secret-key"),
            patch("main.DISABLE_FILE_FALLBACK", True),
            patch("main.supabase_feedback_available", return_value=True),
            patch("main.supabase_project_intake_available", return_value=False),
            patch("main.analytics_snapshots_available", return_value=True),
            patch(
                "main.fetch_analytics_snapshot",
                side_effect=lambda key: {
                    "snapshot_key": key,
                    "generated_at": "2026-04-02T10:00:00+00:00",
                    "payload": (
                        {
                            "project_intake": {},
                            "effort_estimates": [],
                            "developer_metrics": [],
                            "impact_summaries": {},
                            "transparency": {},
                            "knowledge_risks": [],
                            "activity_log": {},
                        }
                        if key == "dashboard_analytics_v1"
                        else {
                            "summary": {"requirements_total": 0},
                            "records": [],
                            "meta": {},
                            "generated_at": "2026-04-02T10:00:00+00:00",
                        }
                    ),
                },
            ),
            patch("main.snapshot_age_seconds", return_value=8),
        ):
            response = health()
        self.assertEqual(response["status"], "ok")
        self.assertTrue(response["ready"])
        self.assertTrue(response["supabase_configured"])
        self.assertTrue(response["write_auth_enabled"])
        self.assertTrue(response["file_fallback_disabled"])
        self.assertEqual(response["feedback_storage_mode"], "supabase")
        self.assertEqual(response["intake_storage_mode"], "derived")
        self.assertEqual(response["analytics_storage_mode"], "supabase")
        self.assertTrue(response["analytics_snapshots_enabled"])
        self.assertFalse(response["file_fallback_active"])
        self.assertEqual(response["storage_probe_ttl_seconds"], 30)
        self.assertEqual(response["missing_required_env"], [])
        self.assertEqual(response["degraded_reasons"], [])
        self.assertEqual(response["operating_mode"], "pilot-ready")
        self.assertTrue(response["warnings"])
        self.assertTrue(response["recommendations"])
        self.assertIn("frontend_url", response["configuration"])
        self.assertTrue(response["allowed_origins"])
        self.assertIn("delivery_timeline", response["optional_modules"])
        self.assertIn("showcase_summaries", response["optional_modules"])
        self.assertIn("delivery_timeline", response["optional_module_details"])
        self.assertTrue(response["optional_module_details"]["delivery_timeline"]["available"])
        self.assertTrue(response["readiness_checks"])
        self.assertIn("configuration_audit", response)
        self.assertIn("readiness_overview", response)
        self.assertIn("setup_progress", response)
        self.assertTrue(response["configuration_audit"]["required_env"])
        self.assertEqual(response["configuration_audit"]["write_protection"]["status"], "ready")
        self.assertEqual(len(response["configuration_audit"]["table_dependencies"]), 3)
        self.assertEqual(len(response["configuration_audit"]["cached_views"]), 2)
        self.assertGreaterEqual(response["readiness_overview"]["status_counts"]["healthy"], 1)
        self.assertIn("security", response["readiness_overview"]["category_counts"])
        self.assertEqual(response["setup_progress"]["required_env_ready"], 3)
        self.assertEqual(response["setup_progress"]["migrations_total"], 3)
        self.assertFalse(response["setup_progress"]["launch_ready"])
        self.assertTrue(any(check["key"] == "write_auth" for check in response["readiness_checks"]))
        self.assertTrue(any(check["key"] == "write_auth" and check["category"] == "security" for check in response["readiness_checks"]))
        self.assertTrue(any(check["key"] == "analytics_snapshots" for check in response["readiness_checks"]))
        self.assertIn("dashboard_analytics", response["snapshot_health"])
        self.assertTrue(response["snapshot_health"]["dashboard_analytics"]["fresh"])
        self.assertTrue(response["snapshot_health"]["dashboard_analytics"]["valid_payload"])
        self.assertTrue(response["capabilities"]["can_sync_requirements_and_events"])
        self.assertFalse(response["capabilities"]["can_persist_manual_intake"])
        self.assertTrue(response["capabilities"]["can_run_pilot"])
        self.assertFalse(response["capabilities"]["can_launch_self_serve"])
        self.assertTrue(response["rollout_blockers"])
        self.assertEqual(response["rollout_assessment"]["pilot"]["status"], "ready")
        self.assertEqual(response["rollout_assessment"]["launch"]["status"], "caution")
        self.assertTrue(response["rollout_assessment"]["launch"]["next_actions"])

    def test_health_reports_degraded_without_supabase_config(self) -> None:
        with (
            patch("main.SUPABASE_URL", ""),
            patch("main.SUPABASE_API_KEY", ""),
            patch("main.WRITE_API_KEY", ""),
            patch("main.DISABLE_FILE_FALLBACK", False),
        ):
            response = health()
        self.assertEqual(response["status"], "degraded")
        self.assertFalse(response["ready"])
        self.assertEqual(response["operating_mode"], "degraded")
        self.assertIn("SUPABASE_URL", response["missing_required_env"])
        self.assertIn("SUPABASE_SERVICE_KEY_OR_ANON_KEY", response["missing_required_env"])
        self.assertIn("missing_required_env", response["degraded_reasons"])
        self.assertEqual(response["configuration_audit"]["write_protection"]["status"], "demo-open")
        self.assertEqual(response["configuration_audit"]["required_env"][0]["status"], "missing")
        self.assertIn("configuration", response["readiness_overview"]["blocking_categories"])
        self.assertEqual(response["setup_progress"]["required_env_ready"], 0)
        self.assertFalse(response["setup_progress"]["pilot_ready"])
        self.assertTrue(any(check["key"] == "supabase_credentials" and check["status"] == "degraded" for check in response["readiness_checks"]))
        self.assertTrue(any(blocker["key"] == "supabase_credentials" and blocker["category"] == "configuration" for blocker in response["rollout_blockers"]))
        self.assertFalse(response["capabilities"]["can_sync_requirements_and_events"])
        self.assertTrue(response["capabilities"]["has_critical_readiness_failures"])
        self.assertTrue(response["rollout_blockers"])
        self.assertEqual(response["rollout_assessment"]["pilot"]["status"], "blocked")
        self.assertEqual(response["rollout_assessment"]["launch"]["status"], "blocked")
        self.assertTrue(response["rollout_assessment"]["pilot"]["next_actions"])

    def test_health_reports_invalid_origin_entries_as_degraded(self) -> None:
        with (
            patch("main.SUPABASE_URL", "https://example.supabase.co"),
            patch("main.SUPABASE_API_KEY", "test-key"),
            patch("main.os.getenv", side_effect=lambda key, default=None: {
                "FRONTEND_URL": "localhost:5173",
                "ALLOWED_ORIGINS": "http://localhost:5173,not-a-url",
            }.get(key, default)),
            patch("main.supabase_feedback_available", return_value=True),
            patch("main.supabase_project_intake_available", return_value=True),
            patch("main.analytics_snapshots_available", return_value=True),
        ):
            response = health()
        self.assertEqual(response["status"], "degraded")
        self.assertIn("invalid_allowed_origins", response["degraded_reasons"])
        self.assertTrue(response["configuration"]["invalid_origin_entries"])
        self.assertEqual(response["configuration_audit"]["cors"]["status"], "invalid")
        self.assertEqual(len(response["configuration_audit"]["cors"]["invalid_origins"]), 2)
        self.assertTrue(any(check["key"] == "allowed_origins" and check["status"] == "degraded" for check in response["readiness_checks"]))

    def test_health_reports_invalid_supabase_url_as_degraded(self) -> None:
        with (
            patch("main.SUPABASE_URL", "example.supabase.co"),
            patch("main.SUPABASE_API_KEY", "test-key"),
            patch("main.supabase_feedback_available", return_value=True),
            patch("main.supabase_project_intake_available", return_value=True),
            patch("main.analytics_snapshots_available", return_value=True),
        ):
            response = health()
        self.assertEqual(response["status"], "degraded")
        self.assertIn("invalid_supabase_url", response["degraded_reasons"])
        self.assertTrue(response["configuration"]["invalid_supabase_url"])
        self.assertEqual(response["configuration_audit"]["required_env"][0]["status"], "invalid")
        self.assertTrue(any(check["key"] == "supabase_endpoint" and check["status"] == "degraded" for check in response["readiness_checks"]))
        self.assertEqual(response["rollout_assessment"]["pilot"]["status"], "blocked")

    def test_health_reports_invalid_numeric_env_warnings(self) -> None:
        with (
            patch("main.SUPABASE_URL", "https://example.supabase.co"),
            patch("main.SUPABASE_API_KEY", "test-key"),
            patch("main.ENV_CONFIG_WARNINGS", ["REQ_MATCH_THRESHOLD must be numeric. Falling back to 0.45."]),
            patch("main.supabase_feedback_available", return_value=True),
            patch("main.supabase_project_intake_available", return_value=True),
            patch("main.analytics_snapshots_available", return_value=True),
        ):
            response = health()
        self.assertIn("REQ_MATCH_THRESHOLD must be numeric. Falling back to 0.45.", response["warnings"])
        self.assertIn(
            "Fix invalid numeric environment values so runtime behavior matches deployment intent.",
            response["recommendations"],
        )
        self.assertEqual(response["configuration"]["match_threshold"], main_module.MATCH_THRESHOLD)

    def test_health_reports_optional_module_details_when_missing(self) -> None:
        with (
            patch("main.delivery_timeline_service", None),
            patch("main.DELIVERY_TIMELINE_IMPORT_ERROR", "delivery_timeline module not installed"),
            patch("main.analytics_service.showcase_summaries_available", return_value=False),
            patch("main.analytics_service.showcase_summaries_import_error", return_value="showcase_summaries module missing"),
        ):
            response = health()
        self.assertFalse(response["optional_modules"]["delivery_timeline"])
        self.assertEqual(response["optional_module_details"]["delivery_timeline"]["status"], "missing")
        self.assertIn("install", response["optional_module_details"]["delivery_timeline"]["action"].lower())
        self.assertFalse(response["optional_module_details"]["showcase_summaries"]["available"])

    def test_health_reports_invalid_snapshot_payloads(self) -> None:
        with (
            patch("main.SUPABASE_URL", "https://example.supabase.co"),
            patch("main.SUPABASE_API_KEY", "test-key"),
            patch("main.supabase_feedback_available", return_value=True),
            patch("main.supabase_project_intake_available", return_value=True),
            patch("main.analytics_snapshots_available", return_value=True),
            patch(
                "main.fetch_analytics_snapshot",
                side_effect=lambda key: {
                    "snapshot_key": key,
                    "generated_at": "2026-04-02T10:00:00+00:00",
                    "payload": {"broken": True},
                },
            ),
            patch("main.snapshot_age_seconds", return_value=5),
        ):
            response = health()
        self.assertEqual(response["snapshot_health"]["dashboard_analytics"]["source"], "invalid-snapshot")
        self.assertFalse(response["snapshot_health"]["dashboard_analytics"]["valid_payload"])
        self.assertFalse(response["snapshot_health"]["dashboard_analytics"]["fresh"])
        self.assertTrue(any("invalid" in warning.lower() for warning in response["warnings"]))

    def test_delivery_timeline_endpoint_falls_back_when_module_is_missing(self) -> None:
        with (
            patch("main.delivery_timeline_service", None),
            patch("main.fetch_issues", return_value=self.issues),
            patch("main.fetch_delivery_timeline_events", return_value=self.events),
            patch("main.fetch_analytics_snapshot", return_value=None),
        ):
            response = main_module.delivery_timeline_endpoint()
        self.assertIn("summary", response)
        self.assertEqual(response["summary"]["requirements_total"], len(self.issues))
        self.assertEqual(response["records"], [])

    def test_delivery_timeline_endpoint_prefers_fresh_snapshot(self) -> None:
        snapshot_payload = {
            "generated_at": "2026-04-02T10:00:00+00:00",
            "summary": {"requirements_total": 7},
            "meta": {"real_data": "cached"},
            "records": [{"issue_id": "KAN-1"}],
        }
        with (
            patch("main.fetch_analytics_snapshot", return_value={"payload": snapshot_payload, "generated_at": "2026-04-02T10:00:00+00:00"}),
            patch("main.snapshot_age_seconds", return_value=5),
            patch("main.fetch_issues") as issues_mock,
        ):
            response = main_module.delivery_timeline_endpoint()
        issues_mock.assert_not_called()
        self.assertEqual(response["summary"]["requirements_total"], 7)
        self.assertEqual(response["meta"]["snapshot_source"], "snapshot")
        self.assertEqual(response["meta"]["snapshot_age_seconds"], 5)

    def test_delivery_timeline_endpoint_recomputes_when_snapshot_payload_is_invalid(self) -> None:
        invalid_snapshot = {
            "payload": {"summary": {"requirements_total": 7}},
            "generated_at": "2026-04-02T10:00:00+00:00",
        }
        live_payload = {
            "generated_at": "2026-04-02T10:05:00+00:00",
            "summary": {"requirements_total": 2},
            "meta": {"real_data": "live"},
            "records": [],
        }
        with (
            patch("main.fetch_analytics_snapshot", return_value=invalid_snapshot),
            patch("main.snapshot_age_seconds", return_value=5),
            patch("main.get_delivery_timeline_payload_live", return_value=live_payload) as live_mock,
            patch("main.persist_analytics_snapshot") as persist_mock,
        ):
            response = main_module.delivery_timeline_endpoint()
        live_mock.assert_called_once()
        persist_mock.assert_called_once()
        self.assertEqual(response["summary"]["requirements_total"], 2)
        self.assertEqual(response["meta"]["snapshot_source"], "live")

    def test_project_intake_list_falls_back_to_manual_issues(self) -> None:
        fallback_issue = {
            "issue_id": "MANUAL-1",
            "title": "Manual intake",
            "description": "Manually added requirement",
            "project_key": "MANUAL",
            "issue_type": "Requirement",
            "priority": "Medium",
            "status": "Draft",
            "assignee_email": "owner@example.com",
            "reporter_email": "reporter@example.com",
            "jira_created_at": "2026-04-01T10:00:00+00:00",
            "jira_updated_at": "2026-04-01T12:00:00+00:00",
            "created_at": "2026-04-01T10:00:00+00:00",
            "updated_at": "2026-04-01T12:00:00+00:00",
            "source": "manual",
            "commits": [],
        }
        with (
            patch("main.supabase_project_intake_available", return_value=False),
            patch("main.fetch_issues", return_value=[fallback_issue]),
        ):
            response = list_project_intake_records()
        self.assertEqual(len(response["records"]), 1)
        self.assertEqual(response["records"][0]["issue_id"], "MANUAL-1")

    def test_feedback_persistence_raises_when_strict_supabase_mode_is_enabled(self) -> None:
        with (
            patch("main.DISABLE_FILE_FALLBACK", True),
            patch("main.post_rows", side_effect=main_module.HTTPException(status_code=503, detail="offline")),
        ):
            with self.assertRaises(Exception) as error:
                persist_feedback_record(
                    {
                        "commit_id": "c1",
                        "feedback_type": "approved",
                        "predicted_issue_id": "KAN-1",
                        "reviewed_by": "tester",
                        "reviewed_at": "2026-04-02T10:00:00+00:00",
                    }
                )
        self.assertEqual(getattr(error.exception, "status_code", None), 503)

    def test_dashboard_prefers_fresh_analytics_snapshot(self) -> None:
        snapshot_payload = {
            "project_intake": {"requirements_ingested": 99},
            "effort_estimates": [],
            "developer_metrics": [],
            "impact_summaries": {},
            "transparency": {},
            "knowledge_risks": [],
            "activity_log": {},
        }
        snapshot_record = {
            "snapshot_key": "dashboard_analytics_v1",
            "payload": snapshot_payload,
            "generated_at": "2026-04-02T10:00:00+00:00",
        }
        with (
            patch("main.fetch_issues", return_value=self.issues),
            patch("main.fetch_events", return_value=self.events),
            patch("main.fetch_analytics_snapshot", return_value=snapshot_record),
            patch("main.snapshot_age_seconds", return_value=10),
            patch("main.build_dashboard_analytics") as build_mock,
        ):
            response = dashboard()
        build_mock.assert_not_called()
        self.assertEqual(response["analytics"], snapshot_payload)
        self.assertEqual(response["meta"]["analytics_source"], "snapshot")
        self.assertEqual(response["meta"]["analytics_snapshot_age_seconds"], 10)

    def test_dashboard_recomputes_and_persists_snapshot_when_missing(self) -> None:
        computed_payload = {"project_intake": {"requirements_ingested": 2}}
        with (
            patch("main.fetch_issues", return_value=self.issues),
            patch("main.fetch_events", return_value=self.events),
            patch("main.fetch_analytics_snapshot", return_value=None),
            patch("main.build_dashboard_analytics", return_value=computed_payload) as build_mock,
            patch("main.persist_analytics_snapshot") as persist_mock,
        ):
            response = dashboard()
        build_mock.assert_called_once()
        persist_mock.assert_called_once()
        self.assertEqual(response["analytics"], computed_payload)
        self.assertEqual(response["meta"]["analytics_source"], "live")
        self.assertEqual(response["meta"]["analytics_snapshot_age_seconds"], 0)

    def test_dashboard_recomputes_when_snapshot_payload_is_invalid(self) -> None:
        invalid_snapshot = {
            "snapshot_key": "dashboard_analytics_v1",
            "payload": {"project_intake": {"requirements_ingested": 99}},
            "generated_at": "2026-04-02T10:00:00+00:00",
        }
        computed_payload = {
            "project_intake": {},
            "effort_estimates": [],
            "developer_metrics": [],
            "impact_summaries": {},
            "transparency": {},
            "knowledge_risks": [],
            "activity_log": {},
        }
        with (
            patch("main.fetch_issues", return_value=self.issues),
            patch("main.fetch_events", return_value=self.events),
            patch("main.fetch_analytics_snapshot", return_value=invalid_snapshot),
            patch("main.snapshot_age_seconds", return_value=5),
            patch("main.build_dashboard_analytics", return_value=computed_payload) as build_mock,
            patch("main.persist_analytics_snapshot") as persist_mock,
        ):
            response = dashboard()
        build_mock.assert_called_once()
        persist_mock.assert_called_once()
        self.assertEqual(response["meta"]["analytics_source"], "live")
        self.assertEqual(response["analytics"], computed_payload)


if __name__ == "__main__":
    unittest.main()
