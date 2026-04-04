from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics import build_dashboard_analytics, build_knowledge_risks  # noqa: E402


class KnowledgeRiskModelTests(unittest.TestCase):
    def make_event(
        self,
        *,
        commit_id: str,
        module: str,
        author: str,
        timestamp: str,
        active_minutes: int,
        total_changes: int,
        issue_id: str,
        repository_name: str = "platform",
    ) -> dict[str, object]:
        return {
            "commit_id": commit_id,
            "message": f"Work on {module}",
            "timestamp": timestamp,
            "repository_name": repository_name,
            "issue_id": issue_id,
            "linked_issue": issue_id,
            "modules_touched": [module],
            "developer_id": author.lower(),
            "author": author,
            "author_email": f"{author.lower()}@example.com",
            "total_changes": total_changes,
            "active_minutes": active_minutes,
            "idle_minutes": 5,
            "focus_ratio": 0.9,
            "debug_session_count": 1,
        }

    def find_risk(self, risks: list[dict[str, object]], module: str) -> dict[str, object]:
        return next(risk for risk in risks if risk["module"] == module)

    def test_high_concentration_module_scores_high(self) -> None:
        events = [
            self.make_event(commit_id="c1", module="auth", author="Alice", timestamp="2026-03-31T10:00:00+00:00", active_minutes=120, total_changes=80, issue_id="REQ-1"),
            self.make_event(commit_id="c2", module="auth", author="Alice", timestamp="2026-04-01T10:00:00+00:00", active_minutes=100, total_changes=70, issue_id="REQ-2"),
            self.make_event(commit_id="c3", module="auth", author="Alice", timestamp="2026-04-02T09:00:00+00:00", active_minutes=90, total_changes=60, issue_id="REQ-2"),
            self.make_event(commit_id="c4", module="auth", author="Bob", timestamp="2026-04-01T09:30:00+00:00", active_minutes=10, total_changes=10, issue_id="REQ-1"),
        ]

        risks = build_knowledge_risks(events)
        auth_risk = self.find_risk(risks, "auth")

        self.assertEqual(auth_risk["severity"], "high")
        self.assertEqual(auth_risk["top_contributor"], "Alice")
        self.assertGreater(auth_risk["ownership_share_pct"], 80.0)
        self.assertEqual(auth_risk["linked_requirement_count"], 2)
        self.assertEqual(auth_risk["freshness"], "fresh")
        self.assertEqual(auth_risk["continuity_profile"], "active_hotspot")
        self.assertEqual(auth_risk["mitigation_priority"], "urgent")
        self.assertEqual(auth_risk["review_urgency"], "immediate")
        self.assertEqual(auth_risk["ownership_stability"], "dangerous")
        self.assertIn("Recent work is still concentrated", auth_risk["manager_signal"])
        self.assertGreater(auth_risk["risk_score"], 60.0)
        self.assertTrue(any(item["label"] == "Contribution concentration" for item in auth_risk["risk_breakdown"]))

    def test_low_concentration_module_stays_low(self) -> None:
        events = [
            self.make_event(commit_id="c1", module="payments", author="Alice", timestamp="2026-04-01T10:00:00+00:00", active_minutes=60, total_changes=45, issue_id="REQ-1"),
            self.make_event(commit_id="c2", module="payments", author="Bob", timestamp="2026-04-01T11:00:00+00:00", active_minutes=55, total_changes=40, issue_id="REQ-2"),
            self.make_event(commit_id="c3", module="payments", author="Cara", timestamp="2026-04-02T12:00:00+00:00", active_minutes=50, total_changes=35, issue_id="REQ-3"),
        ]

        risks = build_knowledge_risks(events)
        payments_risk = self.find_risk(risks, "payments")

        self.assertEqual(payments_risk["severity"], "low")
        self.assertLess(payments_risk["ownership_share_pct"], 45.0)
        self.assertEqual(payments_risk["contributor_count"], 3)
        self.assertEqual(payments_risk["linked_requirement_count"], 3)
        self.assertLess(payments_risk["risk_score"], 45.0)
        self.assertEqual(payments_risk["continuity_profile"], "shared_coverage")
        self.assertIn(payments_risk["ownership_stability"], {"acceptable", "shared"})
        self.assertEqual(payments_risk["mitigation_priority"], "monitor")

    def test_stale_concentrated_module_surfaces_staleness(self) -> None:
        events = [
            self.make_event(commit_id="c1", module="search", author="Alice", timestamp="2026-03-01T10:00:00+00:00", active_minutes=120, total_changes=85, issue_id="REQ-1"),
            self.make_event(commit_id="c2", module="search", author="Alice", timestamp="2026-03-02T10:00:00+00:00", active_minutes=90, total_changes=60, issue_id="REQ-2"),
            self.make_event(commit_id="c3", module="search", author="Bob", timestamp="2026-03-03T10:00:00+00:00", active_minutes=15, total_changes=10, issue_id="REQ-1"),
            self.make_event(commit_id="c4", module="billing", author="Cara", timestamp="2026-04-02T10:00:00+00:00", active_minutes=45, total_changes=30, issue_id="REQ-9"),
        ]

        risks = build_knowledge_risks(events)
        search_risk = self.find_risk(risks, "search")
        recency_component = next(item for item in search_risk["risk_breakdown"] if item["label"] == "Recency")

        self.assertEqual(search_risk["severity"], "high")
        self.assertEqual(search_risk["freshness"], "stale")
        self.assertEqual(search_risk["continuity_profile"], "stale_dependency")
        self.assertEqual(search_risk["mitigation_priority"], "high")
        self.assertEqual(search_risk["review_urgency"], "this_week")
        self.assertIn("next change", search_risk["manager_signal"])
        self.assertGreaterEqual(search_risk["recency_days"], 30)
        self.assertGreaterEqual(recency_component["score"], 13.0)
        self.assertIn("latest observed activity", search_risk["summary"])

    def test_shared_ownership_keeps_primary_and_backup_visible(self) -> None:
        events = [
            self.make_event(commit_id="c1", module="onboarding", author="Dana", timestamp="2026-04-01T10:00:00+00:00", active_minutes=100, total_changes=70, issue_id="REQ-1"),
            self.make_event(commit_id="c2", module="onboarding", author="Dana", timestamp="2026-04-02T10:00:00+00:00", active_minutes=80, total_changes=60, issue_id="REQ-2"),
            self.make_event(commit_id="c3", module="onboarding", author="Eli", timestamp="2026-04-01T12:00:00+00:00", active_minutes=55, total_changes=40, issue_id="REQ-2"),
            self.make_event(commit_id="c4", module="onboarding", author="Eli", timestamp="2026-04-02T11:00:00+00:00", active_minutes=50, total_changes=35, issue_id="REQ-3"),
        ]

        risks = build_knowledge_risks(events)
        onboarding_risk = self.find_risk(risks, "onboarding")

        self.assertEqual(onboarding_risk["severity"], "medium")
        self.assertEqual(onboarding_risk["top_contributor"], "Dana")
        self.assertEqual(onboarding_risk["secondary_owner"], "Eli")
        self.assertGreater(onboarding_risk["secondary_share_pct"], 35.0)
        self.assertEqual(len(onboarding_risk["top_contributors"]), 2)
        self.assertEqual(onboarding_risk["continuity_profile"], "watchlist_concentration")
        self.assertEqual(onboarding_risk["mitigation_priority"], "planned")
        self.assertEqual(onboarding_risk["review_urgency"], "routine")
        self.assertIn("rotate review or pairing", onboarding_risk["continuity_guidance"])

    def test_severity_transitions_from_low_to_medium_to_high(self) -> None:
        low_events = [
            self.make_event(commit_id="c1", module="infra", author="Alice", timestamp="2026-04-01T10:00:00+00:00", active_minutes=60, total_changes=40, issue_id="REQ-1"),
            self.make_event(commit_id="c2", module="infra", author="Bob", timestamp="2026-04-01T11:00:00+00:00", active_minutes=55, total_changes=38, issue_id="REQ-2"),
            self.make_event(commit_id="c3", module="infra", author="Cara", timestamp="2026-04-02T09:00:00+00:00", active_minutes=50, total_changes=34, issue_id="REQ-3"),
        ]
        medium_events = [
            self.make_event(commit_id="c4", module="infra", author="Alice", timestamp="2026-04-01T10:00:00+00:00", active_minutes=100, total_changes=70, issue_id="REQ-1"),
            self.make_event(commit_id="c5", module="infra", author="Alice", timestamp="2026-04-02T10:00:00+00:00", active_minutes=90, total_changes=65, issue_id="REQ-2"),
            self.make_event(commit_id="c6", module="infra", author="Bob", timestamp="2026-04-02T11:00:00+00:00", active_minutes=55, total_changes=42, issue_id="REQ-3"),
        ]
        high_events = [
            self.make_event(commit_id="c7", module="infra", author="Alice", timestamp="2026-03-30T10:00:00+00:00", active_minutes=120, total_changes=90, issue_id="REQ-1"),
            self.make_event(commit_id="c8", module="infra", author="Alice", timestamp="2026-04-01T10:00:00+00:00", active_minutes=100, total_changes=80, issue_id="REQ-2"),
            self.make_event(commit_id="c9", module="infra", author="Alice", timestamp="2026-04-02T10:00:00+00:00", active_minutes=95, total_changes=70, issue_id="REQ-3"),
            self.make_event(commit_id="c10", module="infra", author="Bob", timestamp="2026-04-02T11:00:00+00:00", active_minutes=10, total_changes=10, issue_id="REQ-2"),
        ]

        low_risk = self.find_risk(build_knowledge_risks(low_events), "infra")
        medium_risk = self.find_risk(build_knowledge_risks(medium_events), "infra")
        high_risk = self.find_risk(build_knowledge_risks(high_events), "infra")

        self.assertEqual(low_risk["severity"], "low")
        self.assertEqual(medium_risk["severity"], "medium")
        self.assertEqual(high_risk["severity"], "high")
        self.assertLess(low_risk["risk_score"], medium_risk["risk_score"])
        self.assertLess(medium_risk["risk_score"], high_risk["risk_score"])

    def test_explanation_output_calls_out_owner_recency_and_impact(self) -> None:
        events = [
            self.make_event(commit_id="c1", module="checkout", author="Alice", timestamp="2026-03-15T10:00:00+00:00", active_minutes=120, total_changes=90, issue_id="REQ-1"),
            self.make_event(commit_id="c2", module="checkout", author="Alice", timestamp="2026-03-16T10:00:00+00:00", active_minutes=95, total_changes=70, issue_id="REQ-2"),
            self.make_event(commit_id="c3", module="checkout", author="Bob", timestamp="2026-03-17T10:00:00+00:00", active_minutes=15, total_changes=12, issue_id="REQ-1"),
            self.make_event(commit_id="c4", module="profile", author="Cara", timestamp="2026-04-25T10:00:00+00:00", active_minutes=30, total_changes=22, issue_id="REQ-9"),
        ]

        checkout_risk = self.find_risk(build_knowledge_risks(events), "checkout")

        self.assertIn("Alice is the top contributor", checkout_risk["explanation_points"][0])
        self.assertIn("Latest visible activity", checkout_risk["recent_activity_summary"])
        self.assertIn("stale single-owner knowledge", checkout_risk["why_it_matters"].lower())
        self.assertIn("checkout is currently a stale dependency", checkout_risk["manager_summary"])

    def test_continuity_confidence_distinguishes_sparse_and_rich_evidence(self) -> None:
        sparse_events = [
            self.make_event(commit_id="c1", module="search", author="Alice", timestamp="2026-04-02T10:00:00+00:00", active_minutes=30, total_changes=12, issue_id="REQ-1"),
        ]
        rich_events = [
            self.make_event(commit_id="c2", module="search", author="Alice", timestamp="2026-03-30T10:00:00+00:00", active_minutes=90, total_changes=60, issue_id="REQ-1"),
            self.make_event(commit_id="c3", module="search", author="Alice", timestamp="2026-04-01T10:00:00+00:00", active_minutes=110, total_changes=80, issue_id="REQ-2"),
            self.make_event(commit_id="c4", module="search", author="Bob", timestamp="2026-04-02T10:00:00+00:00", active_minutes=35, total_changes=20, issue_id="REQ-2"),
        ]

        sparse_risk = self.find_risk(build_knowledge_risks(sparse_events), "search")
        rich_risk = self.find_risk(build_knowledge_risks(rich_events), "search")

        self.assertEqual(sparse_risk["continuity_confidence"], "low")
        self.assertEqual(rich_risk["continuity_confidence"], "high")

    def test_dashboard_summary_rolls_up_priority_backup_and_stale_areas(self) -> None:
        issues = [
            {"issue_id": "REQ-1", "title": "Auth", "description": "Auth work", "commits": ["c1", "c2"]},
            {"issue_id": "REQ-2", "title": "Search", "description": "Search work", "commits": ["c3", "c4"]},
        ]
        events = [
            self.make_event(commit_id="c1", module="auth", author="Alice", timestamp="2026-04-01T10:00:00+00:00", active_minutes=120, total_changes=80, issue_id="REQ-1"),
            self.make_event(commit_id="c2", module="auth", author="Alice", timestamp="2026-04-02T10:00:00+00:00", active_minutes=90, total_changes=60, issue_id="REQ-1"),
            self.make_event(commit_id="c3", module="search", author="Dana", timestamp="2026-03-01T10:00:00+00:00", active_minutes=100, total_changes=70, issue_id="REQ-2"),
            self.make_event(commit_id="c4", module="search", author="Eli", timestamp="2026-03-02T10:00:00+00:00", active_minutes=20, total_changes=12, issue_id="REQ-2"),
            self.make_event(commit_id="c5", module="profile", author="Mina", timestamp="2026-04-02T11:00:00+00:00", active_minutes=25, total_changes=16, issue_id="REQ-9"),
        ]

        analytics = build_dashboard_analytics(issues, events, {"updates": []})
        summary = analytics["knowledge_risk_summary"]

        self.assertIn("highest_priority_subsystem", summary)
        self.assertEqual(summary["highest_priority_subsystem"]["module"], "auth")
        self.assertTrue(any(item["module"] == "auth" for item in summary["active_right_now_risks"]))
        self.assertTrue(any(item["module"] == "search" for item in summary["stale_but_critical_areas"]))
        self.assertTrue(isinstance(summary["modules_needing_backup_ownership"], list))
        self.assertTrue(summary["modules_needing_backup_ownership"][0]["module"])
        self.assertIn("Start with auth", summary["manager_readout"])

    def test_bus_factor_backup_gap_and_coverage_index_are_exposed(self) -> None:
        events = [
            self.make_event(commit_id="c1", module="catalog", author="Alice", timestamp="2026-04-01T10:00:00+00:00", active_minutes=110, total_changes=80, issue_id="REQ-1"),
            self.make_event(commit_id="c2", module="catalog", author="Alice", timestamp="2026-04-02T10:00:00+00:00", active_minutes=95, total_changes=70, issue_id="REQ-2"),
            self.make_event(commit_id="c3", module="catalog", author="Bob", timestamp="2026-04-02T12:00:00+00:00", active_minutes=35, total_changes=25, issue_id="REQ-2"),
            self.make_event(commit_id="c4", module="catalog", author="Cara", timestamp="2026-04-02T13:00:00+00:00", active_minutes=20, total_changes=18, issue_id="REQ-3"),
        ]

        catalog_risk = self.find_risk(build_knowledge_risks(events), "catalog")

        self.assertIn("bus_factor", catalog_risk)
        self.assertIn("backup_gap_pct", catalog_risk)
        self.assertIn("coverage_index", catalog_risk)
        self.assertGreaterEqual(catalog_risk["bus_factor"], 1)
        self.assertGreaterEqual(catalog_risk["backup_gap_pct"], 0.0)
        self.assertGreater(catalog_risk["coverage_index"], 0.0)
        self.assertLessEqual(catalog_risk["coverage_index"], 1.0)
        self.assertIn(catalog_risk["ownership_stability"], {"dangerous", "fragile", "watch", "acceptable", "shared"})
        self.assertTrue(catalog_risk.get("dominant_risk_drivers"))

    def test_aging_bottleneck_profile_for_aging_single_owner_modules(self) -> None:
        events = [
            self.make_event(commit_id="c1", module="ledger", author="Alice", timestamp="2026-03-08T10:00:00+00:00", active_minutes=95, total_changes=70, issue_id="REQ-1"),
            self.make_event(commit_id="c2", module="ledger", author="Alice", timestamp="2026-03-09T10:00:00+00:00", active_minutes=85, total_changes=65, issue_id="REQ-2"),
            self.make_event(commit_id="c3", module="ledger", author="Bob", timestamp="2026-03-10T10:00:00+00:00", active_minutes=15, total_changes=10, issue_id="REQ-2"),
            self.make_event(commit_id="c4", module="active-ref", author="Cara", timestamp="2026-04-02T10:00:00+00:00", active_minutes=55, total_changes=40, issue_id="REQ-9"),
        ]

        ledger_risk = self.find_risk(build_knowledge_risks(events), "ledger")

        self.assertIn(ledger_risk["recency_band"], {"aging", "dormant"})
        self.assertIn(ledger_risk["continuity_profile"], {"aging_bottleneck", "stale_dependency"})
        self.assertIn("next change", ledger_risk["manager_summary"])

    def test_dashboard_exposes_knowledge_risk_model_transparency(self) -> None:
        issues = [
            {
                "issue_id": "REQ-1",
                "title": "Strengthen auth",
                "description": "Add recovery controls",
                "assignee_email": "alice@example.com",
                "reporter_email": "lead@example.com",
                "jira_created_at": "2026-03-28T09:00:00+00:00",
                "jira_updated_at": "2026-04-02T09:00:00+00:00",
                "commits": ["c1", "c2"],
            }
        ]
        events = [
            self.make_event(commit_id="c1", module="auth", author="Alice", timestamp="2026-04-01T10:00:00+00:00", active_minutes=120, total_changes=80, issue_id="REQ-1"),
            self.make_event(commit_id="c2", module="auth", author="Alice", timestamp="2026-04-02T10:00:00+00:00", active_minutes=90, total_changes=55, issue_id="REQ-1"),
        ]

        analytics = build_dashboard_analytics(issues, events, {"updates": []})

        self.assertIn("knowledge_risk_model", analytics["transparency"])
        self.assertEqual(len(analytics["transparency"]["knowledge_risk_model"]), 5)
        auth_risk = self.find_risk(analytics["knowledge_risks"], "auth")
        self.assertEqual(len(auth_risk["risk_breakdown"]), 5)
        self.assertIn("Tacit knowledge appears", auth_risk["why_risk"])
        self.assertIn("manager_summary", auth_risk)


if __name__ == "__main__":
    unittest.main()
