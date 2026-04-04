from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics import (  # noqa: E402
    build_dashboard_analytics,
    build_developer_metrics,
    build_effort_estimates,
    build_knowledge_risks,
    build_project_intake_profiles,
)
from showcase_summaries import build_showcase_summaries  # noqa: E402


class ShowcaseSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.issues = [
            {
                "issue_id": "KAN-7",
                "title": "Ship onboarding analytics",
                "description": "Track onboarding funnel telemetry and expose a manager-friendly status view.",
                "status": "In Progress",
                "issue_type": "Story",
                "priority": "High",
                "project_key": "KAN",
                "assignee_email": "alice@example.com",
                "reporter_email": "manager@example.com",
                "jira_created_at": "2026-03-24T09:00:00+00:00",
                "jira_updated_at": "2026-03-30T18:00:00+00:00",
                "created_at": "2026-03-24T09:00:00+00:00",
                "updated_at": "2026-03-30T18:00:00+00:00",
                "commits": ["c11", "c12"],
            },
            {
                "issue_id": "KAN-8",
                "title": "Stabilize billing retry flow",
                "description": "Reduce failed retries and tighten alerting in billing jobs.",
                "status": "Review",
                "issue_type": "Task",
                "priority": "Medium",
                "project_key": "KAN",
                "assignee_email": "bob@example.com",
                "reporter_email": "manager@example.com",
                "jira_created_at": "2026-03-25T09:00:00+00:00",
                "jira_updated_at": "2026-03-31T18:00:00+00:00",
                "created_at": "2026-03-25T09:00:00+00:00",
                "updated_at": "2026-03-31T18:00:00+00:00",
                "commits": ["c13"],
            },
        ]
        self.events = [
            {
                "commit_id": "c11",
                "message": "Add onboarding telemetry pipeline",
                "timestamp": "2026-03-28T10:30:00+00:00",
                "repository_name": "portal",
                "branch": "feature/KAN-7-onboarding",
                "issue_id": "KAN-7",
                "linked_issue": "KAN-7",
                "modules_touched": ["analytics", "onboarding"],
                "developer_id": "alice",
                "author": "Alice",
                "author_email": "alice@example.com",
                "total_changes": 140,
                "attendance_pct": 100,
                "active_minutes": 150,
                "idle_minutes": 8,
                "focus_ratio": 0.95,
                "debug_session_count": 2,
                "files": [{"file_path": "src/onboarding/analytics.ts"}],
            },
            {
                "commit_id": "c12",
                "message": "Add showcase onboarding manager view",
                "timestamp": "2026-03-29T21:10:00+00:00",
                "repository_name": "portal",
                "branch": "feature/KAN-7-onboarding",
                "issue_id": "KAN-7",
                "linked_issue": "KAN-7",
                "modules_touched": ["analytics", "dashboard"],
                "developer_id": "alice",
                "author": "Alice",
                "author_email": "alice@example.com",
                "total_changes": 95,
                "attendance_pct": 100,
                "active_minutes": 90,
                "idle_minutes": 4,
                "focus_ratio": 0.9,
                "debug_session_count": 1,
                "pr_number": 482,
                "pr_status": "merged",
                "pr_title": "KAN-7: Ship onboarding analytics",
                "ci_status": "passed",
                "ci_workflow": "quality-gates",
                "deployment_status": "success",
                "deployment_environment": "production",
                "deployment_target": "Vercel",
                "deployment_version": "release-482",
                "deployed_at": "2026-03-30T09:30:00+00:00",
                "files": [{"file_path": "dashboard/showcase.tsx"}],
            },
            {
                "commit_id": "c13",
                "message": "Refine billing retry backoff",
                "timestamp": "2026-03-27T11:00:00+00:00",
                "repository_name": "payments",
                "branch": "task/KAN-8-retries",
                "issue_id": "KAN-8",
                "linked_issue": "KAN-8",
                "modules_touched": ["billing"],
                "developer_id": "bob",
                "author": "Bob",
                "author_email": "bob@example.com",
                "total_changes": 110,
                "attendance_pct": 92,
                "active_minutes": 130,
                "idle_minutes": 12,
                "focus_ratio": 0.86,
                "debug_session_count": 3,
                "files_json": {"files": [{"file_path": "billing/retries.ts"}]},
            },
        ]

    def build_summaries(self, issues=None, events=None):
        active_issues = issues or self.issues
        active_events = events or self.events
        event_map = {event["commit_id"]: event for event in active_events}
        profiles = build_project_intake_profiles(active_issues, event_map)
        effort = build_effort_estimates(active_issues, event_map)
        metrics = build_developer_metrics(
            active_events,
            active_issues,
            {event["commit_id"] for event in active_events if event.get("commit_id")},
        )
        risks = build_knowledge_risks(active_events)
        return build_showcase_summaries(active_issues, active_events, profiles, effort, metrics, risks)

    def test_showcase_summary_contract_contains_launch_ready_fields(self) -> None:
        summaries = self.build_summaries()

        self.assertIn("meta", summaries)
        self.assertIn("portfolio_overview", summaries)
        self.assertIn("coverage", summaries)
        self.assertIn("logic_notes", summaries)
        self.assertIn("generated_from", summaries["meta"])
        self.assertIn("inference_level", summaries["meta"])
        self.assertEqual(summaries["meta"]["section_labels"]["observed"], "Observed in data")
        self.assertEqual(summaries["meta"]["section_labels"]["inferred"], "Deterministic reading")
        self.assertIn("section_descriptions", summaries["meta"])
        self.assertIn("executive_summary", summaries["portfolio_overview"])
        self.assertIn("summary", summaries["portfolio_overview"])
        self.assertIn("freshness_note", summaries["portfolio_overview"])
        self.assertIn("freshness_level", summaries["portfolio_overview"])
        self.assertIn("uncertainty_note", summaries["portfolio_overview"])
        self.assertIn("traceability_note", summaries["portfolio_overview"])
        self.assertIn("follow_up", summaries["portfolio_overview"])
        self.assertIn("why_it_matters", summaries["portfolio_overview"])
        self.assertIn("review_focus", summaries["portfolio_overview"])
        self.assertIn("top_risk_driver", summaries["portfolio_overview"])
        self.assertIn("recommended_follow_up", summaries["portfolio_overview"])
        self.assertIn("summary_confidence_band", summaries["portfolio_overview"])
        self.assertIn("weekly_review", summaries["portfolio_overview"])
        self.assertIn("uncertainty_driver", summaries["portfolio_overview"])
        self.assertIn("action_priority", summaries["portfolio_overview"])
        self.assertIn("review_window", summaries["portfolio_overview"])
        self.assertIn("review_owner", summaries["portfolio_overview"])
        self.assertIn("stable_signals", summaries["portfolio_overview"]["weekly_review"])
        self.assertIn("watch_signals", summaries["portfolio_overview"]["weekly_review"])
        self.assertIn("uncertainty_driver", summaries["portfolio_overview"]["weekly_review"])

        developer_summary = summaries["developer_weekly"][0]
        self.assertEqual(developer_summary["scope"], "developer")
        self.assertIn("headline", developer_summary)
        self.assertIn("executive_summary", developer_summary)
        self.assertIn("confidence", developer_summary)
        self.assertIn("confidence_reason", developer_summary)
        self.assertIn("confidence_detail", developer_summary)
        self.assertIn("score", developer_summary["confidence_detail"])
        self.assertIn("evidence_density", developer_summary["confidence_detail"])
        self.assertIn("certainty_bias", developer_summary["confidence_detail"])
        self.assertIsInstance(developer_summary["confidence_detail"]["supporting_evidence"], list)
        self.assertIsInstance(developer_summary["confidence_detail"]["missing_evidence"], list)
        self.assertIn("improve_confidence", developer_summary["confidence_detail"])
        self.assertIn("evidence_count", developer_summary)
        self.assertIn("generated_from", developer_summary)
        self.assertIn("inference_level", developer_summary)
        self.assertIn("risk_level", developer_summary)
        self.assertIn("freshness_note", developer_summary)
        self.assertIn("freshness_level", developer_summary)
        self.assertIn("uncertainty_note", developer_summary)
        self.assertIn("why_it_matters", developer_summary)
        self.assertIn("review_focus", developer_summary)
        self.assertIn("top_risk_driver", developer_summary)
        self.assertIn("recommended_follow_up", developer_summary)
        self.assertIn("summary_confidence_band", developer_summary)
        self.assertIn("weekly_review", developer_summary)
        self.assertIn("uncertainty_driver", developer_summary)
        self.assertIn("action_priority", developer_summary)
        self.assertIn("review_window", developer_summary)
        self.assertIn("review_owner", developer_summary)
        self.assertIn("work_summary", developer_summary)
        self.assertIn("what_changed", developer_summary)
        self.assertIn("effort_concentration", developer_summary)
        self.assertIn("focus_interpretation", developer_summary)
        self.assertIn("follow_up", developer_summary)
        self.assertIn("highlights", developer_summary)
        self.assertIn("top_requirements", developer_summary)
        self.assertIn("top_modules", developer_summary)
        self.assertIn("top_repositories", developer_summary)
        self.assertIn("risk_signal", developer_summary)
        self.assertTrue(developer_summary["observed_facts"])
        self.assertTrue(developer_summary["inferred_judgments"])
        self.assertIn("stage_evidence", developer_summary)

        issue_summary = summaries["issue_impacts"][0]
        self.assertEqual(issue_summary["scope"], "issue")
        self.assertIn("delivery_stage", issue_summary)
        self.assertIn("executive_summary", issue_summary)
        self.assertIn("confidence_reason", issue_summary)
        self.assertIn("confidence_detail", issue_summary)
        self.assertIn("generated_from", issue_summary)
        self.assertIn("inference_level", issue_summary)
        self.assertIn("risk_level", issue_summary)
        self.assertIn("freshness_note", issue_summary)
        self.assertIn("freshness_level", issue_summary)
        self.assertIn("uncertainty_note", issue_summary)
        self.assertIn("why_it_matters", issue_summary)
        self.assertIn("review_focus", issue_summary)
        self.assertIn("top_risk_driver", issue_summary)
        self.assertIn("recommended_follow_up", issue_summary)
        self.assertIn("summary_confidence_band", issue_summary)
        self.assertIn("weekly_review", issue_summary)
        self.assertIn("uncertainty_driver", issue_summary)
        self.assertIn("action_priority", issue_summary)
        self.assertIn("review_window", issue_summary)
        self.assertIn("review_owner", issue_summary)
        self.assertIn("execution_maturity", issue_summary)
        self.assertIn("fulfillment_confidence", issue_summary)
        self.assertIn("downstream_visibility", issue_summary)
        self.assertIn("risk_to_completion", issue_summary)
        self.assertIn("progress_summary", issue_summary)
        self.assertIn("readiness_summary", issue_summary)
        self.assertIn("variance_summary", issue_summary)
        self.assertIn("continuity_summary", issue_summary)
        self.assertIn("freshness_summary", issue_summary)
        self.assertIn("follow_up", issue_summary)
        self.assertIn("highlights", issue_summary)
        self.assertTrue(issue_summary["observed_facts"])
        self.assertTrue(issue_summary["inferred_judgments"])
        self.assertIn("stage_evidence", issue_summary)

    def test_coverage_fields_include_delivery_and_telemetry_breakdown(self) -> None:
        summaries = self.build_summaries()
        coverage = summaries["coverage"]

        self.assertIn("delivery", coverage)
        self.assertIn("telemetry", coverage)
        self.assertIn("connector_stage_coverage_pct", coverage["delivery"])
        self.assertIn("inferred_stage_coverage_pct", coverage["delivery"])
        self.assertIn("launch_signal_coverage_pct", coverage["delivery"])
        self.assertIn("field_breakdown", coverage["telemetry"])
        self.assertEqual(coverage["delivery"]["requirements_with_links_pct"], 100.0)
        self.assertEqual(coverage["telemetry"]["field_breakdown"]["module_pct"], 100.0)
        self.assertGreaterEqual(coverage["delivery"]["connector_stage_coverage_pct"], 0.0)
        self.assertGreaterEqual(coverage["delivery"]["launch_signal_coverage_pct"], 50.0)

    def test_confidence_and_evidence_drop_with_sparse_input(self) -> None:
        sparse_issues = [
            {
                "issue_id": "KAN-9",
                "title": "Sparse summary sample",
                "description": "Minimal telemetry",
                "status": "To Do",
                "issue_type": "Task",
                "priority": "Low",
                "project_key": "KAN",
                "assignee_email": "",
                "reporter_email": "",
                "created_at": "2026-03-30T09:00:00+00:00",
                "updated_at": "2026-03-30T09:00:00+00:00",
                "commits": ["c21"],
            }
        ]
        sparse_events = [
            {
                "commit_id": "c21",
                "message": "Initial stub",
                "timestamp": "2026-03-30T10:00:00+00:00",
                "repository_name": "portal",
                "issue_id": "KAN-9",
                "linked_issue": "KAN-9",
                "developer_id": "zoe",
                "author": "Zoe",
                "active_minutes": 20,
                "total_changes": 8,
            }
        ]

        summaries = self.build_summaries(sparse_issues, sparse_events)
        developer_summary = summaries["developer_weekly"][0]

        self.assertEqual(developer_summary["confidence"], "low")
        self.assertEqual(developer_summary["evidence_count"], 1)
        self.assertEqual(summaries["coverage"]["telemetry"]["field_breakdown"]["module_pct"], 0.0)
        self.assertIn("only one telemetry event", developer_summary["confidence_reason"].lower())
        self.assertTrue(developer_summary["confidence_detail"]["missing_evidence"])
        self.assertIn("only one telemetry event", developer_summary["confidence_detail"]["missing_evidence"])
        self.assertIn("To improve confidence", developer_summary["confidence_detail"]["improve_confidence"])
        self.assertEqual(developer_summary["freshness_level"], "fresh")
        self.assertIn(developer_summary["action_priority"], {"watch", "urgent"})
        self.assertEqual(developer_summary["summary_confidence_band"], "Directional only")
        self.assertTrue(developer_summary["weekly_review"]["watch_signals"])
        self.assertTrue(developer_summary["weekly_review"]["uncertainty_driver"])
        self.assertIn("Personal work centered on", developer_summary["work_summary"])
        self.assertTrue(
            "weak" in developer_summary["stage_evidence"].lower()
            or "mostly inferred" in developer_summary["stage_evidence"].lower()
        )

    def test_summary_generation_keeps_issue_and_developer_narratives_distinct(self) -> None:
        summaries = self.build_summaries()
        developer_summary = summaries["developer_weekly"][0]
        manager_summary = summaries["manager_contributions"][0]
        issue_summary = summaries["issue_impacts"][0]

        self.assertIn("Alice", developer_summary["headline"])
        self.assertIn("requirement streams", manager_summary["headline"])
        self.assertIn("KAN-7", issue_summary["headline"])
        self.assertIn("Observed effort is", " ".join(issue_summary["observed_facts"]))
        self.assertTrue(any("Execution focus" in item for item in developer_summary["inferred_judgments"]))
        self.assertIn("Manager-visible movement", manager_summary["summary"])
        self.assertIn("heuristic effort plan", issue_summary["summary"])
        self.assertIn("what_moved", manager_summary)
        self.assertIn("risk_watch", manager_summary)
        self.assertIn("For managers, this means", manager_summary["so_what"])
        self.assertIn("Next manager check should", manager_summary["follow_up"])
        self.assertIn("Next developer step should", developer_summary["follow_up"])
        self.assertIn(manager_summary["risk_level"], {"high", "medium", "low"})
        self.assertIn(developer_summary["risk_level"], {"high", "medium", "low"})
        self.assertIn("moved", developer_summary["executive_summary"])
        self.assertIn("Manager view:", manager_summary["executive_summary"])
        self.assertIn("represents", issue_summary["executive_summary"])
        self.assertIn("This week's visible work centered on", developer_summary["summary"])
        self.assertIn("next review centered on", manager_summary["summary"])
        self.assertIn("What Was Worked On", developer_summary["highlights"][0]["label"])
        self.assertIn("Effort concentrated in", developer_summary["effort_concentration"])
        self.assertIn("Focus and workload read as", developer_summary["focus_interpretation"])
        self.assertIn("Requirement progress is", issue_summary["progress_summary"])
        self.assertIn("Delivery readiness is", issue_summary["readiness_summary"])
        self.assertIn("Effort variance is", issue_summary["variance_summary"])
        self.assertIn("Continuity risk is", issue_summary["continuity_summary"])
        self.assertIn("Next issue review should", issue_summary["follow_up"])
        self.assertIn("Manager impact:", manager_summary["why_it_matters"])
        self.assertTrue(manager_summary["top_risk_driver"])
        self.assertEqual(manager_summary["recommended_follow_up"], manager_summary["follow_up"])
        self.assertIn(manager_summary["summary_confidence_band"], {"Decision-ready", "Review-ready", "Use with caution", "Directional only"})
        self.assertIn(issue_summary["execution_maturity"], {"Execution maturity is late-stage because the requirement is already deployed.", "Execution maturity is mid-stage because the requirement has moved into in review.", "Execution maturity is mid-stage because the requirement has moved into in ci.", "Execution maturity is late-stage because the requirement is already ready to deploy.", "Execution maturity is late-stage because the requirement is already deploying."})
        self.assertIn("Fulfillment confidence is", issue_summary["fulfillment_confidence"])
        self.assertIn("Downstream visibility is", issue_summary["downstream_visibility"])
        self.assertIn("Risk to completion is", issue_summary["risk_to_completion"])
        self.assertIn(manager_summary["weekly_review"]["scope"], {"manager"})
        self.assertIn(developer_summary["weekly_review"]["scope"], {"developer"})
        self.assertIn(issue_summary["weekly_review"]["scope"], {"issue"})
        self.assertTrue(manager_summary["weekly_review"]["observed_snapshot"])
        self.assertTrue(issue_summary["weekly_review"]["inferred_signal"])
        self.assertTrue(manager_summary["weekly_review"]["stable_signals"])
        self.assertTrue(issue_summary["weekly_review"]["watch_signals"])
        self.assertTrue(issue_summary["weekly_review"]["uncertainty_driver"])
        self.assertIn("What Moved", [item["label"] for item in manager_summary["highlights"]])
        self.assertIn("Where Effort Concentrated", [item["label"] for item in manager_summary["highlights"]])
        self.assertIn("What Was Worked On", [item["label"] for item in developer_summary["highlights"]])
        self.assertTrue(
            "Latest visible movement" in issue_summary["freshness_summary"]
            or "Freshness is healthy" in issue_summary["freshness_summary"]
        )
        self.assertTrue(
            "connector-backed" in issue_summary["stage_evidence"]
            or "mixed" in issue_summary["stage_evidence"]
        )
        self.assertIn(manager_summary["freshness_level"], {"fresh", "watch", "stale"})
        self.assertIn(issue_summary["freshness_level"], {"fresh", "watch", "stale"})

    def test_dashboard_analytics_exposes_updated_showcase_summary_shape(self) -> None:
        analytics = build_dashboard_analytics(self.issues, self.events, {"updates": []})
        showcase = analytics["showcase_summaries"]

        self.assertIn("meta", showcase)
        self.assertIn("logic_notes", showcase)
        self.assertIn("coverage", showcase)
        self.assertIn("generated_from", showcase["meta"])
        self.assertIn("section_labels", showcase["meta"])
        self.assertIn("section_descriptions", showcase["meta"])
        self.assertIn("observed_facts", showcase["portfolio_overview"])
        self.assertIn("confidence_reason", showcase["portfolio_overview"])
        self.assertIn("confidence_detail", showcase["portfolio_overview"])
        self.assertIn("risk_level", showcase["portfolio_overview"])
        self.assertIn("executive_summary", showcase["portfolio_overview"])
        self.assertIn("summary", showcase["portfolio_overview"])
        self.assertIn("summary_confidence_band", showcase["portfolio_overview"])
        self.assertIn("recommended_follow_up", showcase["portfolio_overview"])
        self.assertIn("launch_signal_coverage_pct", showcase["coverage"]["delivery"])
        self.assertGreater(len(showcase["manager_contributions"]), 0)

    def test_stale_issue_activity_updates_freshness_and_priority(self) -> None:
        stale_events = [
            {
                **self.events[0],
                "timestamp": "2026-02-10T10:30:00+00:00",
            }
        ]
        stale_issues = [
            {
                **self.issues[0],
                "commits": ["c11"],
                "jira_updated_at": "2026-02-10T09:00:00+00:00",
                "updated_at": "2026-02-10T09:00:00+00:00",
            }
        ]
        summaries = self.build_summaries(stale_issues, stale_events)
        issue_summary = summaries["issue_impacts"][0]

        self.assertEqual(issue_summary["freshness_level"], "stale")
        self.assertEqual(issue_summary["action_priority"], "urgent")
        self.assertIn("Latest visible movement", issue_summary["freshness_summary"])
        self.assertIn("Review within", issue_summary["review_window"])


if __name__ == "__main__":
    unittest.main()
