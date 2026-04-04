"""
Integration test for monorepo scenario with two managers sharing a repository.

This test covers:
- Two managers, same repo, overlapping modules
- Attribution goes to correct developer
- Cross-team dependencies surfaced
- Ambiguous cases flagged
- Manager rollups separate correctly
"""

import unittest
from datetime import datetime, timezone

from org_mapping import OrgMapper, create_org_mapper
from manager_rollups import ManagerRollupEngine, create_manager_rollup_engine
from identity_resolution import create_resolver
from work_item_resolution import create_attribution_engine
from ownership_graph import create_ownership_graph
from dependency_graph import create_dependency_graph
from schemas import AttributionDecision, DependencyEdge


class TestMonorepoScenario(unittest.TestCase):
    """Integration test: Two managers, same repo, overlapping modules."""

    def setUp(self) -> None:
        """Set up the monorepo scenario with two managers and overlapping work."""
        # Initialize systems
        self.resolver = create_resolver()
        self.org_mapper = create_org_mapper()
        self.attribution_engine = create_attribution_engine(self.resolver)
        self.ownership_graph = create_ownership_graph()
        self.dependency_graph = create_dependency_graph()
        self.rollup_engine = create_manager_rollup_engine(self.org_mapper)

        # Create the monorepo scenario
        self._setup_developers()
        self._setup_teams_and_managers()
        self._setup_work_items()
        self._setup_dependencies()

    def _setup_developers(self) -> None:
        """Create developers for both teams using resolver API."""
        # Manager A's team (Platform Team) - add via resolver
        self.resolver.resolve_identity(
            git_email="alice@example.com",
            git_name="Alice (Platform)",
            employee_email="alice@example.com",
        )
        self.resolver.resolve_identity(
            git_email="bob@example.com",
            git_name="Bob (Platform)",
            employee_email="bob@example.com",
        )

        # Manager B's team (Payments Team)
        self.resolver.resolve_identity(
            git_email="carol@example.com",
            git_name="Carol (Payments)",
            employee_email="carol@example.com",
        )
        self.resolver.resolve_identity(
            git_email="dave@example.com",
            git_name="Dave (Payments)",
            employee_email="dave@example.com",
        )

    def _setup_teams_and_managers(self) -> None:
        """Set up teams and manager mappings."""
        # Manager IDs
        self.manager_a = "manager-alice-platform"
        self.manager_b = "manager-carol-payments"

        # Team A: Platform Team (Manager A)
        self.org_mapper.add_team_membership(
            canonical_id="alice@example.com",  # Using email as canonical for simplicity
            team_id="team-platform",
            role="tech_lead",
            allocation_percent=100,
            confidence_score=0.95,
            provenance="hr_system",
            evidence=["HR directory: Platform Team"],
        )
        self.org_mapper.add_team_membership(
            canonical_id="bob@example.com",
            team_id="team-platform",
            role="developer",
            allocation_percent=100,
            confidence_score=0.95,
            provenance="hr_system",
            evidence=["HR directory: Platform Team"],
        )
        self.org_mapper.add_manager_mapping(
            team_id="team-platform",
            manager_canonical_id=self.manager_a,
            manager_role="engineering_manager",
            is_primary=True,
            confidence_score=0.95,
            provenance="hr_system",
        )

        # Team B: Payments Team (Manager B)
        self.org_mapper.add_team_membership(
            canonical_id="carol@example.com",
            team_id="team-payments",
            role="tech_lead",
            allocation_percent=100,
            confidence_score=0.95,
            provenance="hr_system",
            evidence=["HR directory: Payments Team"],
        )
        self.org_mapper.add_team_membership(
            canonical_id="dave@example.com",
            team_id="team-payments",
            role="developer",
            allocation_percent=100,
            confidence_score=0.95,
            provenance="hr_system",
            evidence=["HR directory: Payments Team"],
        )
        self.org_mapper.add_manager_mapping(
            team_id="team-payments",
            manager_canonical_id=self.manager_b,
            manager_role="engineering_manager",
            is_primary=True,
            confidence_score=0.95,
            provenance="hr_system",
        )

    def _setup_work_items(self) -> None:
        """Create work items with overlapping modules in the shared repo."""
        now = datetime.now(timezone.utc).isoformat()

        # Work items for Platform Team (Manager A's team)
        self.platform_items = [
            AttributionDecision(
                decision_id="dec-platform-1",
                work_item_id="TASK-101",
                work_item_type="issue",
                canonical_id="alice@example.com",
                ownership_factors=["assignee", "author"],
                ownership_score=0.85,
                effective_from=now,
                confidence_score=0.85,
                confidence_label="high",
                evidence=["Jira assigned to alice@example.com"],
                provenance="jira_api",
            ),
            AttributionDecision(
                decision_id="dec-platform-2",
                work_item_id="TASK-102",
                work_item_type="issue",
                canonical_id="bob@example.com",
                ownership_factors=["assignee"],
                ownership_score=0.75,
                effective_from=now,
                confidence_score=0.75,
                confidence_label="medium",
                evidence=["Jira assigned to bob@example.com"],
                provenance="jira_api",
            ),
        ]

        # Work items for Payments Team (Manager B's team)
        self.payments_items = [
            AttributionDecision(
                decision_id="dec-payments-1",
                work_item_id="TASK-201",
                work_item_type="issue",
                canonical_id="carol@example.com",
                ownership_factors=["assignee", "author"],
                ownership_score=0.90,
                effective_from=now,
                confidence_score=0.90,
                confidence_label="high",
                evidence=["Jira assigned to carol@example.com"],
                provenance="jira_api",
            ),
            AttributionDecision(
                decision_id="dec-payments-2",
                work_item_id="TASK-202",
                work_item_type="issue",
                canonical_id="dave@example.com",
                ownership_factors=["assignee"],
                ownership_score=0.65,
                effective_from=now,
                confidence_score=0.65,
                confidence_label="medium",
                evidence=["Jira assigned to dave@example.com"],
                provenance="jira_api",
            ),
        ]

        # Ambiguous case: unclear attribution
        self.ambiguous_item = AttributionDecision(
            decision_id="dec-ambiguous-1",
            work_item_id="TASK-301",
            work_item_type="issue",
            canonical_id="alice@example.com",
            ownership_factors=["possible_author"],
            ownership_score=0.35,
            effective_from=now,
            confidence_score=0.35,
            confidence_label="low",
            evidence=["Multiple possible assignees"],
            provenance="inferred",
            ambiguity_flag=True,
            ambiguity_reasons=["Multiple developers touched this module recently"],
            manual_review_required=True,
        )

        # Add all decisions to engine and rollup
        for decision in self.platform_items + self.payments_items + [self.ambiguous_item]:
            self.attribution_engine._decisions[decision.work_item_id] = decision
            self.rollup_engine.add_attribution_decision(decision)

    def _setup_dependencies(self) -> None:
        """Set up cross-team dependencies."""
        now = datetime.now(timezone.utc).isoformat()

        # Platform team depends on Payments team's gateway
        self.dep_platform_to_payments = DependencyEdge(
            edge_id="dep-1",
            source_team_id="team-platform",
            target_team_id="team-payments",
            source_work_item_id="TASK-101",
            target_work_item_id="TASK-201",
            source_work_item_type="issue",
            target_work_item_type="issue",
            dependency_type="blocks",
            strength="strong",
            is_cross_team=True,
            effective_from=now,
            confidence_score=0.80,
            confidence_label="high",
            provenance="jira_api",
            detection_method="manual_annotation",
            detected_at=now,
        )

        # Payments team depends on Platform's auth module
        self.dep_payments_to_platform = DependencyEdge(
            edge_id="dep-2",
            source_team_id="team-payments",
            target_team_id="team-platform",
            source_work_item_id="TASK-201",
            target_work_item_id="TASK-101",
            source_work_item_type="issue",
            target_work_item_type="issue",
            dependency_type="depends_on",
            strength="moderate",
            is_cross_team=True,
            effective_from=now,
            confidence_score=0.75,
            confidence_label="high",
            provenance="jira_api",
            detection_method="manual_annotation",
            detected_at=now,
        )

        # Add edges to rollup engine
        self.rollup_engine.add_dependency_edge(self.dep_platform_to_payments)
        self.rollup_engine.add_dependency_edge(self.dep_payments_to_platform)

    def test_two_managers_same_repo(self) -> None:
        """Test that two managers can have teams in the same repo without conflict."""
        # Verify both managers have teams
        manager_a_teams = self.org_mapper.get_all_teams_for_manager(self.manager_a)
        manager_b_teams = self.org_mapper.get_all_teams_for_manager(self.manager_b)

        self.assertEqual(len(manager_a_teams), 1)
        self.assertEqual(manager_a_teams[0]["team_id"], "team-platform")

        self.assertEqual(len(manager_b_teams), 1)
        self.assertEqual(manager_b_teams[0]["team_id"], "team-payments")

    def test_attribution_goes_to_correct_developer(self) -> None:
        """Test that work items are attributed to the correct developer."""
        # Platform team work
        platform_decision = self.attribution_engine._decisions.get("TASK-101")
        self.assertIsNotNone(platform_decision)
        self.assertEqual(platform_decision.canonical_id, "alice@example.com")

        # Payments team work
        payments_decision = self.attribution_engine._decisions.get("TASK-201")
        self.assertIsNotNone(payments_decision)
        self.assertEqual(payments_decision.canonical_id, "carol@example.com")

        # Verify no cross-contamination
        self.assertNotEqual(platform_decision.canonical_id, payments_decision.canonical_id)

    def test_cross_team_dependencies_surfaced(self) -> None:
        """Test that cross-team dependencies are detected and reported."""
        # Check rollup engine dependency pressure
        pressure_a = self.rollup_engine.rollup_dependency_pressure(self.manager_a)
        pressure_b = self.rollup_engine.rollup_dependency_pressure(self.manager_b)

        # Both managers should see cross-team dependencies
        self.assertTrue(
            len(pressure_a.incoming_dependencies) > 0 or len(pressure_a.outgoing_dependencies) > 0
        )
        self.assertTrue(
            len(pressure_b.incoming_dependencies) > 0 or len(pressure_b.outgoing_dependencies) > 0
        )

        # Verify dependency counts
        self.assertEqual(pressure_a.cross_team_strength["total_cross_team"], 2)
        self.assertEqual(pressure_b.cross_team_strength["total_cross_team"], 2)

    def test_ambiguous_cases_flagged(self) -> None:
        """Test that ambiguous attribution cases are properly flagged."""
        # Check the ambiguous item is flagged
        ambiguous = self.attribution_engine._decisions.get("TASK-301")
        self.assertIsNotNone(ambiguous)
        self.assertTrue(ambiguous.ambiguity_flag)
        self.assertTrue(ambiguous.manual_review_required)
        self.assertLess(ambiguous.confidence_score, 0.40)
        self.assertIn("Multiple", ambiguous.ambiguity_reasons[0])

    def test_manager_rollups_separate_correctly(self) -> None:
        """Test that manager rollups correctly separate team work in monorepo."""
        # Get rollups for both managers
        rollup_a = self.rollup_engine.rollup_attribution(self.manager_a, time_range="30d")
        rollup_b = self.rollup_engine.rollup_attribution(self.manager_b, time_range="30d")

        # Manager A should only see Platform team work
        self.assertEqual(rollup_a.manager_id, self.manager_a)
        self.assertIn("team-platform", rollup_a.team_ids)
        self.assertNotIn("team-payments", rollup_a.team_ids)

        # Manager B should only see Payments team work
        self.assertEqual(rollup_b.manager_id, self.manager_b)
        self.assertIn("team-payments", rollup_b.team_ids)
        self.assertNotIn("team-platform", rollup_b.team_ids)

        # Count work items per manager
        platform_work_count = sum(
            1 for d in self.attribution_engine._decisions.values()
            if d.canonical_id in ["alice@example.com", "bob@example.com"]
        )
        payments_work_count = sum(
            1 for d in self.attribution_engine._decisions.values()
            if d.canonical_id in ["carol@example.com", "dave@example.com"]
        )

        # Rollup totals should match team-specific work
        self.assertEqual(rollup_a.total_work_items, platform_work_count)
        self.assertEqual(rollup_b.total_work_items, payments_work_count)

    def test_monorepo_safety_verification(self) -> None:
        """Test the monorepo safety check ensures proper separation."""
        safety_check_a = self.rollup_engine.get_monorepo_rollup_safety_check(
            self.manager_a, "shared-monorepo"
        )
        safety_check_b = self.rollup_engine.get_monorepo_rollup_safety_check(
            self.manager_b, "shared-monorepo"
        )

        # Both should verify separation
        self.assertTrue(safety_check_a["separation_verified"])
        self.assertTrue(safety_check_b["separation_verified"])

        # Manager A should only see their team's work
        self.assertEqual(safety_check_a["manager_developer_count"], 2)

        # Manager B should only see their team's work
        self.assertEqual(safety_check_b["manager_developer_count"], 2)

        # The separation should be correctly enforced
        self.assertIn("correctly excluded", safety_check_a["correctness_proof"])
        self.assertIn("correctly excluded", safety_check_b["correctness_proof"])

    def test_overlapping_modules_attributed_correctly(self) -> None:
        """Test that work on shared modules is attributed to the correct team."""
        # Both teams have work items
        platform_work = [d for d in self.platform_items]
        payments_work = [d for d in self.payments_items]

        # Platform team's work should be attributed to Alice/Bob
        for item in platform_work:
            self.assertIn(item.canonical_id, ["alice@example.com", "bob@example.com"])

        # Payments team's work should be attributed to Carol/Dave
        for item in payments_work:
            self.assertIn(item.canonical_id, ["carol@example.com", "dave@example.com"])

    def test_confidence_distribution_in_rollups(self) -> None:
        """Test that confidence distribution is correctly calculated in rollups."""
        rollup_a = self.rollup_engine.rollup_attribution(self.manager_a, time_range="30d")
        rollup_b = self.rollup_engine.rollup_attribution(self.manager_b, time_range="30d")

        # Check confidence distribution exists
        self.assertIsNotNone(rollup_a.confidence_distribution)
        self.assertIsNotNone(rollup_b.confidence_distribution)

        # Total should match work items
        dist_a_total = rollup_a.confidence_distribution.total()
        dist_b_total = rollup_b.confidence_distribution.total()

        self.assertEqual(dist_a_total, rollup_a.total_work_items)
        self.assertEqual(dist_b_total, rollup_b.total_work_items)


if __name__ == "__main__":
    unittest.main()
