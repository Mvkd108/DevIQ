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

from delivery_timeline import build_delivery_timeline_response, classify_requirement_provenance  # noqa: E402
from delivery_timeline_normalization import normalize_environment, normalize_url  # noqa: E402
from main import delivery_timeline_endpoint  # noqa: E402


class DeliveryTimelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.issue = {
            "issue_id": "KAN-77",
            "title": "Add delivery showcase timeline",
            "status": "In Progress",
            "priority": "High",
            "project_key": "KAN",
            "assignee_email": "owner@example.com",
            "reporter_email": "lead@example.com",
            "jira_created_at": "2026-03-29T09:00:00+00:00",
            "jira_updated_at": "2026-04-01T09:00:00+00:00",
            "created_at": "2026-03-29T09:00:00+00:00",
            "updated_at": "2026-04-01T09:00:00+00:00",
            "source": "jira",
            "commits": ["abc1234", "def5678"],
        }
        self.issues = [self.issue]
        self.base_events = [
            {
                "commit_id": "abc1234",
                "message": "Add delivery timeline cards",
                "timestamp": "2026-04-01T10:00:00+00:00",
                "repository_name": "manager-dashboard",
                "branch": "feature/KAN-77-timeline",
                "author": "Alice",
                "developer_id": "alice",
                "files_json": {"files": [{"file_path": "src/components/DeliveryTimeline.jsx"}]},
                "total_changes": 34,
            },
            {
                "commit_id": "def5678",
                "message": "Wire delivery timeline API",
                "timestamp": "2026-04-01T12:30:00+00:00",
                "repository_name": "req-code-mapping",
                "branch": "feature/KAN-77-timeline",
                "author": "Alice",
                "developer_id": "alice",
                "files": [{"file_path": "backend/Req_codeMapping/delivery_timeline.py"}],
                "total_changes": 18,
            },
        ]

    def test_connector_backed_stage_extraction_normalizes_alias_fields(self) -> None:
        connector_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "pull_request_number": "#482",
                "pull_request_url": "https://example.test/pr/482",
                "pr_title": "KAN-77: Add delivery showcase timeline",
                "pr_state": "MERGED",
                "pr_merged_at": "2026-04-01T13:00:00+00:00",
                "requested_reviewers": [{"name": "Priya"}, {"login": "dan-dev"}],
                "workflow_name": "release-smoke",
                "build_status": "success",
                "run_id": "gha-7782",
                "run_started_at": "2026-04-01T12:35:00+00:00",
                "run_completed_at": "2026-04-01T12:44:00+00:00",
                "duration_seconds": 540,
                "workflow_run_url": "https://example.test/runs/7782",
                "deployment_state": "active",
                "environment_url": "https://preview.example.test/kan-77",
                "environment": "prod",
                "deployment_target": "Vercel",
                "release_version": "release-482",
                "released_at": "2026-04-01T13:15:00+00:00",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, connector_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["source"], "connector")
        self.assertEqual(record["pull_request"]["number"], 482)
        self.assertEqual(record["pull_request"]["state"], "merged")
        self.assertEqual(record["pull_request"]["url"], "https://example.test/pr/482")
        self.assertEqual(record["pull_request"]["author"], "Alice")
        self.assertEqual(record["pull_request"]["reviewers"], ["Priya", "dan-dev"])
        self.assertEqual(record["ci"]["source"], "connector")
        self.assertEqual(record["ci"]["status"], "passed")
        self.assertEqual(record["ci"]["workflow"], "release-smoke")
        self.assertEqual(record["ci"]["run_id"], "gha-7782")
        self.assertEqual(record["ci"]["duration_minutes"], 9)
        self.assertEqual(record["deployment"]["source"], "connector")
        self.assertEqual(record["deployment"]["status"], "live")
        self.assertEqual(record["deployment"]["environment"], "production")
        self.assertEqual(record["deployment"]["target"], "Vercel")
        self.assertEqual(record["deployment"]["version"], "release-482")
        self.assertEqual(record["provenance_rollup"], "connector")
        self.assertEqual(record["readiness"]["code"], "fully-traceable")
        self.assertEqual(record["quality"]["downstream_coverage_pct"], 100)
        self.assertEqual(record["quality"]["traceability_strength"], "strong")
        self.assertEqual(record["quality"]["delivery_evidence_strength"], "verified")
        self.assertEqual(record["quality"]["weakest_stage"]["key"], "deployment")
        self.assertEqual(record["pull_request"]["quality"]["confidence"], "high")
        self.assertEqual(record["ci"]["quality"]["confidence"], "high")
        self.assertEqual(record["deployment"]["quality"]["confidence"], "high")
        self.assertEqual(record["quality"]["completeness_label"], "strong")
        self.assertIn("traceability_strength_counts", payload["summary"])
        self.assertEqual(payload["summary"]["traceability_strength_counts"]["strong"], 1)
        self.assertEqual(payload["summary"]["delivery_evidence_strength_counts"]["verified"], 1)
        self.assertEqual(payload["summary"]["downstream_coverage_pct"], 100)

    def test_partial_connector_data_keeps_connector_provenance_and_fills_missing_fields_from_inference(self) -> None:
        partial_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "pull_request_number": 482,
                "pull_request_url": "https://example.test/pr/482",
                "approved_by": "Release captain",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, partial_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["source"], "connector")
        self.assertEqual(record["pull_request"]["number"], 482)
        self.assertEqual(record["pull_request"]["url"], "https://example.test/pr/482")
        self.assertEqual(record["pull_request"]["reviewers"], ["Release captain"])
        self.assertEqual(record["pull_request"]["branch"], "feature/KAN-77-timeline")
        self.assertEqual(record["pull_request"]["title"], "KAN-77: Add delivery showcase timeline")
        self.assertEqual(record["pull_request"]["repository_name"], "req-code-mapping")
        self.assertEqual(record["pull_request"]["status"], "approved")
        self.assertEqual(record["pull_request"]["provenance_detail"], "partial connector")
        self.assertIn("linked commits", " ".join(record["pull_request"]["evidence"]).lower())
        self.assertEqual(record["provenance_rollup"], "mixed")
        self.assertTrue(record["pull_request"]["quality"]["is_partial_connector"])
        self.assertEqual(record["pull_request"]["quality"]["confidence"], "medium")

    def test_boolean_merge_alias_marks_pr_as_merged(self) -> None:
        merged_flag_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "pull_request_number": 482,
                "pr_title": "KAN-77: Add delivery showcase timeline",
                "pull_request_merged": True,
                "pull_request_url": "https://example.test/pr/482",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, merged_flag_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["source"], "connector")
        self.assertEqual(record["pull_request"]["status"], "merged")
        self.assertEqual(record["pull_request"]["state"], "merged")
        self.assertEqual(record["pull_request"]["provenance_detail"], "explicit connector")
        self.assertEqual(record["delivery_stage"], "deploying")

    def test_partial_ci_connector_data_derives_running_status(self) -> None:
        ci_partial_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "workflow_run_url": "https://example.test/runs/7782",
                "workflow_name": "quality-gates",
                "run_id": "gha-7782",
                "started_at": "2026-04-01T12:35:00+00:00",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, ci_partial_events)
        record = payload["records"][0]

        self.assertEqual(record["ci"]["source"], "connector")
        self.assertEqual(record["ci"]["status"], "running")
        self.assertEqual(record["ci"]["workflow"], "quality-gates")
        self.assertEqual(record["ci"]["provenance_detail"], "partial connector")
        self.assertEqual(record["provenance_rollup"], "mixed")
        self.assertEqual(record["ci"]["quality"]["confidence"], "medium")

    def test_partial_deployment_connector_data_derives_pending_status(self) -> None:
        deployment_partial_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "preview_url": "https://preview.example.test/kan-77",
                "deployment_env": "preview",
                "provider": "Render",
                "tag_name": "release-482",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, deployment_partial_events)
        record = payload["records"][0]

        self.assertEqual(record["deployment"]["source"], "connector")
        self.assertEqual(record["deployment"]["status"], "pending")
        self.assertEqual(record["deployment"]["environment"], "preview")
        self.assertEqual(record["deployment"]["target"], "Render")
        self.assertEqual(record["deployment"]["version"], "release-482")
        self.assertEqual(record["deployment"]["provenance_detail"], "partial connector")
        self.assertEqual(record["provenance_rollup"], "mixed")
        self.assertEqual(record["readiness"]["code"], "fully-traceable")
        self.assertEqual(record["deployment"]["quality"]["confidence"], "medium")

    def test_deployment_connector_url_hints_fill_environment_and_target(self) -> None:
        deployment_url_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "production_url": "kan-77.vercel.app",
                "release_tag": "release-482",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, deployment_url_events)
        record = payload["records"][0]

        self.assertEqual(record["deployment"]["source"], "connector")
        self.assertEqual(record["deployment"]["status"], "pending")
        self.assertEqual(record["deployment"]["environment"], "production")
        self.assertEqual(record["deployment"]["target"], "Vercel")
        self.assertEqual(record["deployment"]["url"], "https://kan-77.vercel.app")
        self.assertIn("environment inferred from deployment url", " ".join(record["deployment"]["evidence"]).lower())
        self.assertIn("target inferred from deployment url", " ".join(record["deployment"]["evidence"]).lower())

    def test_nested_connector_payloads_normalize_real_stage_fields(self) -> None:
        nested_connector_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "connector_payload": {
                    "pull_request": {
                        "number": 482,
                        "title": "KAN-77: Add delivery showcase timeline",
                        "state": "MERGED",
                        "author": {"login": "alice-gh"},
                        "reviewers": [{"name": "Priya"}, {"login": "dan-dev"}],
                        "head": {"ref": "feature/KAN-77-real"},
                        "created_at": "2026-04-01T12:20:00+00:00",
                        "updated_at": "2026-04-01T12:55:00+00:00",
                        "merged_at": "2026-04-01T13:00:00+00:00",
                        "html_url": "https://example.test/pr/482",
                        "base": {"repo": {"name": "req-code-mapping"}},
                    },
                    "workflow_run": {
                        "name": "release-smoke",
                        "id": 7782,
                        "status": "completed",
                        "conclusion": "success",
                        "run_started_at": "2026-04-01T12:35:00+00:00",
                        "completed_at": "2026-04-01T12:44:00+00:00",
                        "run_duration_ms": 540000,
                        "html_url": "https://example.test/runs/7782",
                    },
                    "deployment": {
                        "environment": "production",
                        "platform": "Vercel",
                        "state": "active",
                        "release": "release-482",
                        "ready_at": "2026-04-01T13:15:00+00:00",
                        "public_url": "https://kan-77.vercel.app",
                    },
                },
            },
        ]

        payload = build_delivery_timeline_response(self.issues, nested_connector_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["source"], "connector")
        self.assertEqual(record["pull_request"]["number"], 482)
        self.assertEqual(record["pull_request"]["author"], "alice-gh")
        self.assertEqual(record["pull_request"]["reviewers"], ["Priya", "dan-dev"])
        self.assertEqual(record["pull_request"]["branch"], "feature/KAN-77-real")
        self.assertEqual(record["pull_request"]["repository_name"], "req-code-mapping")
        self.assertEqual(record["ci"]["source"], "connector")
        self.assertEqual(record["ci"]["workflow"], "release-smoke")
        self.assertEqual(record["ci"]["run_id"], "7782")
        self.assertEqual(record["ci"]["status"], "passed")
        self.assertEqual(record["ci"]["duration_minutes"], 9)
        self.assertEqual(record["deployment"]["source"], "connector")
        self.assertEqual(record["deployment"]["environment"], "production")
        self.assertEqual(record["deployment"]["target"], "Vercel")
        self.assertEqual(record["deployment"]["version"], "release-482")
        self.assertEqual(record["deployment"]["status"], "live")
        self.assertEqual(record["provenance_rollup"], "connector")

    def test_nested_connector_pull_request_can_mix_with_inferred_downstream_stages(self) -> None:
        nested_mixed_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "connector_payload": {
                    "pull_request": {
                        "number": 482,
                        "title": "KAN-77: Add delivery showcase timeline",
                        "reviewers": [{"login": "release-captain"}],
                        "html_url": "https://example.test/pr/482",
                    }
                },
            },
        ]

        payload = build_delivery_timeline_response(self.issues, nested_mixed_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["source"], "connector")
        self.assertEqual(record["pull_request"]["number"], 482)
        self.assertEqual(record["pull_request"]["reviewers"], ["release-captain"])
        self.assertEqual(record["pull_request"]["provenance_detail"], "partial connector")
        self.assertEqual(record["ci"]["source"], "inferred")
        self.assertEqual(record["deployment"]["source"], "inferred")
        self.assertEqual(record["provenance_rollup"], "mixed")
        self.assertEqual(record["source_breakdown"]["connector"], 1)
        self.assertEqual(record["source_breakdown"]["inferred"], 2)

    def test_inference_is_used_before_mock_when_real_commit_signals_exist(self) -> None:
        payload = build_delivery_timeline_response(self.issues, self.base_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["source"], "inferred")
        self.assertEqual(record["ci"]["source"], "inferred")
        self.assertEqual(record["deployment"]["source"], "inferred")
        self.assertEqual(record["pull_request"]["status"], "open")
        self.assertEqual(record["ci"]["status"], "running")
        self.assertEqual(record["deployment"]["status"], "blocked")
        self.assertEqual(record["source_breakdown"]["inferred"], 3)
        self.assertEqual(payload["summary"]["mocked_stage_count"], 0)
        self.assertEqual(record["provenance_rollup"], "inferred")
        self.assertEqual(record["readiness"]["code"], "code-linked-only")
        self.assertEqual(record["quality"]["downstream_coverage_pct"], 0)
        self.assertEqual(record["quality"]["traceability_strength"], "weak")
        self.assertEqual(record["quality"]["weakest_stage"]["key"], "deployment")
        self.assertEqual(record["quality"]["freshness"], "fresh")
        self.assertTrue(record["quality"]["missing_downstream_evidence"])

    def test_stage_precedence_prefers_connector_for_stage_but_delivery_stage_follows_latest_release_signal(self) -> None:
        conflicting_connector_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "pull_request_number": 482,
                "pr_status": "open",
                "pr_title": "KAN-77: Add delivery showcase timeline",
                "deployment_status": "success",
                "deployment_environment": "production",
                "deployment_target": "Render",
                "deployment_version": "release-482",
                "deployed_at": "2026-04-01T13:15:00+00:00",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, conflicting_connector_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["source"], "connector")
        self.assertEqual(record["pull_request"]["status"], "open")
        self.assertEqual(record["deployment"]["source"], "connector")
        self.assertEqual(record["delivery_stage"], "deployed")

    def test_conflicting_stage_signals_keep_stage_specific_connector_values(self) -> None:
        conflicting_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "pull_request_number": 482,
                "pr_status": "merged",
                "ci_status": "failed",
                "ci_workflow": "quality-gates",
                "deployment_status": "success",
                "deployment_environment": "production",
                "deployed_at": "2026-04-01T13:15:00+00:00",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, conflicting_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["status"], "merged")
        self.assertEqual(record["ci"]["status"], "failed")
        self.assertEqual(record["deployment"]["status"], "success")
        self.assertEqual(record["delivery_stage"], "deployed")

    def test_missing_event_timestamps_can_still_use_stage_specific_times(self) -> None:
        no_timestamp_events = [
            {
                **self.base_events[0],
                "timestamp": None,
            },
            {
                **self.base_events[1],
                "timestamp": None,
                "pull_request_number": 482,
                "pr_status": "closed_merged",
                "pr_merged_at": "2026-04-01T13:00:00+00:00",
                "workflow_name": "release-smoke",
                "check_conclusion": "successful",
                "run_completed_at": "2026-04-01T12:44:00+00:00",
                "deployment_state": "active",
                "released_at": "2026-04-01T13:15:00+00:00",
                "environment": "prod",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, no_timestamp_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["source"], "connector")
        self.assertEqual(record["pull_request"]["status"], "merged")
        self.assertEqual(record["ci"]["status"], "passed")
        self.assertEqual(record["deployment"]["status"], "live")
        self.assertEqual(record["latest_activity_at"], "2026-04-01T13:15:00+00:00")

    def test_mock_fallback_remains_for_requirements_without_delivery_signals(self) -> None:
        issue_without_commits = {**self.issue, "issue_id": "KAN-99", "commits": []}
        payload = build_delivery_timeline_response([issue_without_commits], [])
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["source"], "mock")
        self.assertEqual(record["ci"]["source"], "mock")
        self.assertEqual(record["deployment"]["source"], "mock")
        self.assertEqual(record["readiness"]["code"], "code-linked-only")
        self.assertEqual(record["quality"]["traceability_strength"], "missing")
        self.assertEqual(record["pull_request"]["quality"]["completeness_label"], "missing")
        self.assertEqual(record["ci"]["quality"]["completeness_label"], "missing")
        self.assertEqual(record["deployment"]["quality"]["completeness_label"], "minimal")
        self.assertEqual(payload["summary"]["mocked_stage_count"], 3)
        self.assertEqual(record["provenance_rollup"], "mock")

    def test_url_and_environment_normalization_helpers_cover_connector_aliases(self) -> None:
        self.assertEqual(normalize_url("//example.test/pr/482"), "https://example.test/pr/482")
        self.assertEqual(normalize_url("github.example.test/org/repo/pull/482"), "https://github.example.test/org/repo/pull/482")
        self.assertEqual(normalize_url("'https://example.test/pr/482',"), "https://example.test/pr/482")
        self.assertEqual(normalize_url("URL: https://example.test/pr/482"), "https://example.test/pr/482")
        self.assertEqual(normalize_url("See https://example.test/pr/482 for details"), "https://example.test/pr/482")
        self.assertEqual(normalize_url("https://example.test/pr/482?view=1&amp;tab=files"), "https://example.test/pr/482?view=1&tab=files")
        self.assertEqual(normalize_environment("prod-us-east-1"), "production")
        self.assertEqual(normalize_environment("qa-preview"), "preview")
        self.assertEqual(normalize_environment("test_env"), "development")
        self.assertEqual(normalize_environment("pre-production"), "staging")
        self.assertEqual(normalize_environment("canary-release"), "preview")

    def test_url_and_environment_normalization_flow_through_connector_records(self) -> None:
        connector_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "pull_request_html_url": "//example.test/pr/482",
                "pull_request_subject": "KAN-77: Add delivery showcase timeline",
                "reviewers": [{"display_name": "Priya"}],
                "workflow": "release-smoke",
                "details_url": "ci.example.test/runs/7782",
                "check_run_id": "gha-7782",
                "check_run_status": "completed_successfully",
                "release_state": "released",
                "target_environment": "qa-preview",
                "service": "Render",
                "release_tag": "release-482",
                "release_url": "//deploy.example.test/releases/482",
                "completed_at": "2026-04-01T13:15:00+00:00",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, connector_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["url"], "https://example.test/pr/482")
        self.assertEqual(record["pull_request"]["reviewers"], ["Priya"])
        self.assertEqual(record["ci"]["url"], "https://ci.example.test/runs/7782")
        self.assertEqual(record["ci"]["status"], "passed")
        self.assertEqual(record["deployment"]["environment"], "preview")
        self.assertEqual(record["deployment"]["url"], "https://deploy.example.test/releases/482")
        self.assertEqual(record["deployment"]["target"], "Render")

    def test_alias_variations_fill_stage_fields_without_losing_provenance(self) -> None:
        connector_events = [
            self.base_events[0],
            {
                **self.base_events[1],
                "pr_web_url": "URL: https://example.test/pr/482",
                "pr_subject": "KAN-77: Add delivery showcase timeline",
                "reviewers": ["Priya"],
                "pipeline_url": "ci.example.test/runs/7782",
                "pipeline_display_name": "release-smoke",
                "pipeline_id": "gha-7782",
                "pipeline_status": "completed_successfully",
                "deployment_web_url": "https://deploy.example.test/releases/482",
                "pre-production": "unused",
                "release_env": "pre-production",
                "deployment_provider": "Render",
                "release_id": "release-482",
            },
        ]

        payload = build_delivery_timeline_response(self.issues, connector_events)
        record = payload["records"][0]

        self.assertEqual(record["pull_request"]["source"], "connector")
        self.assertEqual(record["pull_request"]["url"], "https://example.test/pr/482")
        self.assertEqual(record["pull_request"]["title"], "KAN-77: Add delivery showcase timeline")
        self.assertEqual(record["ci"]["source"], "connector")
        self.assertEqual(record["ci"]["url"], "https://ci.example.test/runs/7782")
        self.assertEqual(record["ci"]["run_id"], "gha-7782")
        self.assertEqual(record["deployment"]["source"], "connector")
        self.assertEqual(record["deployment"]["url"], "https://deploy.example.test/releases/482")
        self.assertEqual(record["deployment"]["environment"], "staging")
        self.assertEqual(record["deployment"]["target"], "Render")
        self.assertEqual(record["provenance_rollup"], "connector")

    def test_readiness_labels_progress_with_visible_review_pipeline_and_deployment_evidence(self) -> None:
        review_visible_payload = build_delivery_timeline_response(
            self.issues,
            [
                self.base_events[0],
                {
                    **self.base_events[1],
                    "pull_request_number": 482,
                    "pull_request_url": "https://example.test/pr/482",
                },
            ],
        )
        pipeline_visible_payload = build_delivery_timeline_response(
            self.issues,
            [
                self.base_events[0],
                {
                    **self.base_events[1],
                    "pull_request_number": 482,
                    "pull_request_url": "https://example.test/pr/482",
                    "workflow_run_url": "https://example.test/runs/7782",
                    "run_id": "gha-7782",
                },
            ],
        )
        deployment_visible_payload = build_delivery_timeline_response(
            self.issues,
            [
                self.base_events[0],
                {
                    **self.base_events[1],
                    "production_url": "kan-77.vercel.app",
                },
            ],
        )

        self.assertEqual(review_visible_payload["records"][0]["readiness"]["code"], "review-visible")
        self.assertEqual(pipeline_visible_payload["records"][0]["readiness"]["code"], "pipeline-visible")
        self.assertEqual(deployment_visible_payload["records"][0]["readiness"]["code"], "fully-traceable")

    def test_provenance_rollup_counts_cover_connector_inferred_mock_and_mixed_records(self) -> None:
        connector_issue = self.issue
        inferred_issue = {**self.issue, "issue_id": "KAN-88", "title": "Inferred flow", "commits": ["ghi9012"]}
        mocked_issue = {**self.issue, "issue_id": "KAN-99", "title": "Mocked flow", "commits": []}
        mixed_issue = {**self.issue, "issue_id": "KAN-100", "title": "Mixed flow", "commits": ["jkl3456", "mno7890"]}

        events = [
            {
                **self.base_events[0],
                "commit_id": "def5678",
                "pull_request_number": 482,
                "pr_state": "merged",
                "pull_request_url": "https://example.test/pr/482",
                "workflow_name": "release-smoke",
                "build_status": "success",
                "workflow_run_url": "https://example.test/runs/7782",
                "deployment_state": "active",
                "environment": "prod",
                "environment_url": "https://preview.example.test/kan-77",
                "released_at": "2026-04-01T13:15:00+00:00",
            },
            {
                **self.base_events[0],
                "commit_id": "ghi9012",
                "message": "Add inferred-only timeline instrumentation",
                "branch": "feature/KAN-88-inferred",
            },
            {
                **self.base_events[0],
                "commit_id": "jkl3456",
                "message": "Open mixed-source PR",
                "branch": "feature/KAN-100-mixed",
            },
            {
                **self.base_events[1],
                "commit_id": "mno7890",
                "message": "Leave CI and deploy inferred",
                "branch": "feature/KAN-100-mixed",
                "pull_request_number": 500,
                "pr_url": "https://example.test/pr/500",
            },
        ]

        payload = build_delivery_timeline_response(
            [connector_issue, inferred_issue, mocked_issue, mixed_issue],
            events,
        )
        summary = payload["summary"]
        records = {record["issue_id"]: record for record in payload["records"]}

        self.assertEqual(summary["connector_backed_requirements"], 1)
        self.assertEqual(summary["inferred_only_requirements"], 1)
        self.assertEqual(summary["mostly_inferred_requirements"], 2)
        self.assertEqual(summary["requirements_with_mocked_stages"], 1)
        self.assertEqual(summary["mocked_requirements"], 1)
        self.assertEqual(summary["mixed_source_requirements"], 1)
        self.assertEqual(summary["connector_coverage_pct"], 33)
        self.assertEqual(summary["synthesized_delivery_pct"], 67)
        self.assertEqual(summary["mock_fallback_stage_pct"], 25)
        self.assertEqual(summary["downstream_evidence_coverage_pct"], 50)
        self.assertEqual(summary["missing_downstream_evidence_requirements"], 2)
        self.assertEqual(summary["fully_traceable_requirements"], 1)
        self.assertEqual(summary["requirements_not_visible_beyond_code"], 2)
        self.assertEqual(summary["requirements_missing_review_visibility"], 2)
        self.assertEqual(summary["requirements_missing_pipeline_visibility"], 1)
        self.assertEqual(summary["requirements_missing_deployment_visibility"], 0)
        self.assertEqual(summary["requirements_with_partial_connector_stages"], 1)
        self.assertEqual(summary["requirements_with_weak_connector_confidence"], 2)
        self.assertEqual(summary["weak_traceability_requirements"], 3)
        self.assertEqual(summary["requirements_with_weak_inference"], 0)
        self.assertEqual(summary["complete_stage_pct"], 25)
        self.assertEqual(summary["partial_stage_pct"], 33)
        self.assertEqual(summary["minimal_stage_pct"], 25)
        self.assertEqual(summary["missing_stage_pct"], 17)
        self.assertEqual(
            summary["connector_backed_requirements"]
            + summary["inferred_only_requirements"]
            + summary["mixed_source_requirements"]
            + summary["mocked_requirements"],
            4,
        )
        self.assertEqual(records["KAN-77"]["provenance_rollup"], "connector")
        self.assertEqual(records["KAN-88"]["provenance_rollup"], "inferred")
        self.assertEqual(records["KAN-99"]["provenance_rollup"], "mock")
        self.assertEqual(records["KAN-100"]["provenance_rollup"], "mixed")

    def test_requirement_provenance_rules_are_stable(self) -> None:
        self.assertEqual(classify_requirement_provenance({"connector": 3, "inferred": 0, "mock": 0}), "connector")
        self.assertEqual(classify_requirement_provenance({"connector": 0, "inferred": 3, "mock": 0}), "inferred")
        self.assertEqual(classify_requirement_provenance({"connector": 0, "inferred": 0, "mock": 3}), "mock")
        self.assertEqual(classify_requirement_provenance({"connector": 1, "inferred": 2, "mock": 0}), "mixed")
        self.assertEqual(
            classify_requirement_provenance({"source_breakdown": {"connector": 1, "inferred": 0, "mock": 1}}),
            "mixed",
        )

    def test_response_emits_stable_provenance_metadata(self) -> None:
        payload = build_delivery_timeline_response(self.issues, self.base_events)
        record = payload["records"][0]
        rules = payload["meta"]["provenance_rules"]

        self.assertEqual(record["provenance"]["rollup"], "inferred")
        self.assertEqual(record["provenance"]["label"], "Inferred-only")
        self.assertEqual(record["provenance"]["trust"], "derived")
        self.assertEqual(record["provenance"]["counts"], {"connector": 0, "inferred": 3, "mock": 0})
        self.assertIn("linked activity", record["provenance"]["description"].lower())
        self.assertEqual(record["readiness"]["label"], "Code-linked only")
        self.assertEqual(record["readiness"]["blocking_gap"], "review")
        self.assertEqual(record["pull_request"]["provenance"]["source"], "inferred")
        self.assertEqual(record["pull_request"]["provenance"]["trust"], "medium")
        self.assertEqual(record["pull_request"]["quality"]["completeness_label"], "partial")
        self.assertEqual(record["quality"]["missing_downstream_evidence"], True)
        self.assertEqual(record["quality"]["downstream_evidence_strength"], "weak")
        self.assertEqual(record["quality"]["traceability_strength"], "weak")
        self.assertEqual(record["quality"]["weakest_stage"]["key"], "deployment")
        self.assertEqual(rules["connector"]["label"], "Connector-backed")
        self.assertEqual(rules["mixed"]["trust"], "blended")
        self.assertIn("placeholders", rules["mock"]["description"].lower())
        self.assertEqual(payload["meta"]["completeness_rules"]["missing"]["label"], "Missing")
        self.assertEqual(payload["meta"]["readiness_rules"]["fully-traceable"]["label"], "Fully traceable")

    def test_delivery_timeline_endpoint_returns_aggregated_records(self) -> None:
        with (
            patch("main.fetch_issues", return_value=self.issues),
            patch("main.fetch_delivery_timeline_events", return_value=self.base_events),
        ):
            payload = delivery_timeline_endpoint()

        self.assertEqual(len(payload["records"]), 1)
        self.assertIn("summary", payload)
        self.assertEqual(payload["records"][0]["issue_id"], "KAN-77")


if __name__ == "__main__":
    unittest.main()
