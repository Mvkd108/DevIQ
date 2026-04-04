"""
Tests for Ownership Graph and Dependency Graph modules.

Tests cover:
- Weighted ownership calculation
- Primary vs secondary owner detection
- Cross-team overlap detection
- Handoff chain detection
- Bottleneck identification with bus factor
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ownership_graph import (
    OwnershipGraph,
    calculate_recency_weight,
    calculate_gini_coefficient,
    calculate_bus_factor,
    parse_datetime,
)
from dependency_graph import DependencyGraph
from schemas import OwnershipEvidence, CanonicalDeveloper, DependencyEdge


class TestOwnershipGraphWeightedCalculation(unittest.TestCase):
    """Test weighted ownership calculation with recency, volume, and review factors."""
    
    def make_event(
        self,
        commit_id: str,
        author: str,
        timestamp: str,
        module: str = "auth",
        total_changes: int = 50,
        files_changed: list | None = None,
    ) -> dict[str, Any]:
        """Create a test event."""
        return {
            "commit_id": commit_id,
            "message": f"Work on {module}",
            "timestamp": timestamp,
            "repository_name": "platform",
            "modules_touched": [module],
            "files_changed": files_changed or [{"path": f"src/{module}/file.py", "changes": total_changes}],
            "total_changes": total_changes,
            "author": author,
            "author_email": f"{author.lower()}@example.com",
            "developer_id": author.lower(),
            "active_minutes": 60,
        }
    
    def test_recency_weight_decay(self) -> None:
        """Test that recency weights decay exponentially over time."""
        reference_time = parse_datetime("2026-04-04T10:00:00+00:00")
        
        # Recent commit (today)
        recent_weight = calculate_recency_weight("2026-04-04T09:00:00+00:00", reference_time, half_life_days=30)
        # Old commit (30 days ago, one half-life)
        old_weight = calculate_recency_weight("2026-03-05T09:00:00+00:00", reference_time, half_life_days=30)
        # Very old commit (60 days ago, two half-lives)
        very_old_weight = calculate_recency_weight("2026-02-03T09:00:00+00:00", reference_time, half_life_days=30)
        
        # Recent should be near 1.0
        self.assertGreater(recent_weight, 0.95)
        # One half-life should be near 0.5
        self.assertAlmostEqual(old_weight, 0.5, delta=0.1)
        # Two half-lives should be near 0.25
        self.assertAlmostEqual(very_old_weight, 0.25, delta=0.1)
        
        # Ordering should be preserved
        self.assertGreater(recent_weight, old_weight)
        self.assertGreater(old_weight, very_old_weight)
    
    def test_gini_coefficient_perfect_equality(self) -> None:
        """Test Gini coefficient with equal contributions (should be 0)."""
        values = [0.33, 0.33, 0.34]  # Roughly equal
        gini = calculate_gini_coefficient(values)
        self.assertLess(gini, 0.1)  # Close to perfect equality
    
    def test_gini_coefficient_perfect_inequality(self) -> None:
        """Test Gini coefficient with one owner doing everything (should be high)."""
        values = [1.0, 0.0, 0.0]  # One person does all
        gini = calculate_gini_coefficient(values)
        self.assertGreater(gini, 0.5)  # High inequality
    
    def test_bus_factor_calculation(self) -> None:
        """Test bus factor calculation for various scenarios."""
        # Single owner - bus factor 1
        single = [("alice", 100.0)]
        self.assertEqual(calculate_bus_factor(single), 1)
        
        # Two equal owners - bus factor 1 (either covers 50%, need both for 70%)
        equal_two = [("alice", 50.0), ("bob", 50.0)]
        self.assertEqual(calculate_bus_factor(equal_two), 2)
        
        # 70/30 split - bus factor 1 (alice covers 70% alone)
        split_70_30 = [("alice", 70.0), ("bob", 30.0)]
        self.assertEqual(calculate_bus_factor(split_70_30), 1)
        
        # Three with 40/35/25 - bus factor 2
        three = [("alice", 40.0), ("bob", 35.0), ("carol", 25.0)]
        self.assertEqual(calculate_bus_factor(three), 2)
    
    def test_compute_ownership_weights(self) -> None:
        """Test the ownership weights computation."""
        graph = OwnershipGraph()
        
        # High values in all categories
        weights = graph.compute_ownership_weights(
            recency=1.0,
            commit_count=10,
            churn=500,
            review_participation=5,
        )
        
        # All components should be at or near max
        self.assertAlmostEqual(weights["recency"], 0.30, delta=0.01)
        self.assertAlmostEqual(weights["volume_commits"], 0.25, delta=0.01)
        self.assertAlmostEqual(weights["volume_churn"], 0.25, delta=0.01)
        self.assertAlmostEqual(weights["review_participation"], 0.20, delta=0.01)
        self.assertAlmostEqual(weights["total"], 1.0, delta=0.1)
        
        # Low values
        low_weights = graph.compute_ownership_weights(
            recency=0.1,
            commit_count=1,
            churn=50,
            review_participation=0,
        )
        self.assertLess(low_weights["total"], 0.3)
    
    def test_weighted_ownership_with_recency(self) -> None:
        """Test that recent contributions are weighted higher."""
        events = [
            # Alice has older commits
            self.make_event("c1", "Alice", "2026-03-01T10:00:00+00:00", total_changes=100),
            self.make_event("c2", "Alice", "2026-03-02T10:00:00+00:00", total_changes=100),
            # Bob has recent commits (more recent = higher weight)
            self.make_event("c3", "Bob", "2026-04-03T10:00:00+00:00", total_changes=60),
            self.make_event("c4", "Bob", "2026-04-04T10:00:00+00:00", total_changes=60),
        ]
        
        graph = OwnershipGraph(events)
        owners = graph.get_all_owners("auth")
        
        # Both should be present
        self.assertEqual(len(owners), 2)
        
        # Bob should have significant share due to recency
        bob_share = next(o["ownership_share_pct"] for o in owners if o["developer_id"] == "Bob")
        # Bob's recency should give him a boost despite fewer total changes
        self.assertGreater(bob_share, 20.0)  # Should have at least 20% share


class TestPrimarySecondaryOwnerDetection(unittest.TestCase):
    """Test primary and secondary owner detection."""
    
    def make_event(self, commit_id: str, author: str, timestamp: str, module: str = "payments") -> dict[str, Any]:
        return {
            "commit_id": commit_id,
            "message": f"Work on {module}",
            "timestamp": timestamp,
            "repository_name": "platform",
            "modules_touched": [module],
            "files_changed": [{"path": f"src/{module}/file.py", "changes": 50}],
            "total_changes": 50,
            "author": author,
            "author_email": f"{author.lower()}@example.com",
            "developer_id": author.lower(),
            "active_minutes": 60,
        }
    
    def test_get_primary_owner_clear_primary(self) -> None:
        """Test primary owner detection when one developer dominates."""
        events = [
            self.make_event("c1", "Alice", "2026-04-01T10:00:00+00:00"),
            self.make_event("c2", "Alice", "2026-04-02T10:00:00+00:00"),
            self.make_event("c3", "Alice", "2026-04-03T10:00:00+00:00"),
            self.make_event("c4", "Bob", "2026-04-02T10:00:00+00:00"),  # Minor contribution
        ]
        
        graph = OwnershipGraph(events)
        primary, confidence = graph.get_primary_owner("payments")
        
        self.assertEqual(primary.canonical_id, "Alice")
        self.assertGreater(confidence, 0.5)
    
    def test_get_all_owners_with_shares(self) -> None:
        """Test getting all owners with ownership shares."""
        events = [
            # Alice has more commits = higher ownership share
            self.make_event("c1", "Alice", "2026-04-03T10:00:00+00:00"),  # Most recent
            self.make_event("c2", "Alice", "2026-04-02T10:00:00+00:00"),
            self.make_event("c3", "Alice", "2026-04-01T10:00:00+00:00"),
            # Bob has fewer commits
            self.make_event("c4", "Bob", "2026-04-02T11:00:00+00:00"),
            self.make_event("c5", "Bob", "2026-04-01T11:00:00+00:00"),
            # Carol has fewest
            self.make_event("c6", "Carol", "2026-04-03T10:00:00+00:00"),
        ]
        
        graph = OwnershipGraph(events)
        owners = graph.get_all_owners("payments")
        
        # Should have 3 owners
        self.assertEqual(len(owners), 3)
        
        # Shares should sum to 100
        total_share = sum(o["ownership_share_pct"] for o in owners)
        self.assertAlmostEqual(total_share, 100.0, delta=5.0)  # Allow rounding error
        
        # Alice should be primary (most commits), Bob secondary
        self.assertEqual(owners[0]["developer_id"], "Alice")
        self.assertEqual(owners[1]["developer_id"], "Bob")
        
        # Alice should have highest share
        self.assertGreater(owners[0]["ownership_share_pct"], owners[1]["ownership_share_pct"])
    
    def test_get_all_owners_respects_min_confidence(self) -> None:
        """Test that min_confidence filter works."""
        events = [
            self.make_event("c1", "Alice", "2026-04-01T10:00:00+00:00"),
            self.make_event("c2", "Alice", "2026-04-02T10:00:00+00:00"),
            self.make_event("c3", "Bob", "2026-04-01T10:00:00+00:00"),  # Single contribution
        ]
        
        graph = OwnershipGraph(events)
        
        # High confidence threshold - only primary
        high_conf = graph.get_all_owners("payments", min_confidence=0.8)
        # Low confidence threshold - should include both
        low_conf = graph.get_all_owners("payments", min_confidence=0.2)
        
        self.assertLessEqual(len(high_conf), len(low_conf))


class TestCrossTeamOverlapDetection(unittest.TestCase):
    """Test cross-team overlap detection for monorepo scenarios."""
    
    def make_event(
        self,
        commit_id: str,
        author: str,
        team: str,
        timestamp: str,
        module: str = "auth",
    ) -> dict[str, Any]:
        return {
            "commit_id": commit_id,
            "message": f"Work on {module}",
            "timestamp": timestamp,
            "repository_name": "platform",
            "modules_touched": [module],
            "files_changed": [{"path": f"src/{module}/file.py", "changes": 50}],
            "total_changes": 50,
            "author": author,
            "author_email": f"{author.lower()}@example.com",
            "developer_id": author.lower(),
            "active_minutes": 60,
        }
    
    def test_detect_cross_team_overlap_single_module(self) -> None:
        """Test detecting when two teams touch the same module."""
        events = [
            # Team A touches auth
            self.make_event("c1", "Alice", "team-a", "2026-04-01T10:00:00+00:00", "auth"),
            self.make_event("c2", "Alan", "team-a", "2026-04-02T10:00:00+00:00", "auth"),
            # Team B also touches auth (same repo)
            self.make_event("c3", "Bob", "team-b", "2026-04-03T10:00:00+00:00", "auth"),
            self.make_event("c4", "Ben", "team-b", "2026-04-04T10:00:00+00:00", "auth"),
        ]
        
        team_assignments = {
            "Alice": "team-a", "Alan": "team-a",
            "Bob": "team-b", "Ben": "team-b",
        }
        
        graph = DependencyGraph(events, team_assignments)
        edges = graph.detect_cross_team_overlap("/repo", events, team_assignments)
        
        # Should detect cross-team dependency
        self.assertGreater(len(edges), 0)
        
        # Edge should be marked as cross-team
        edge = edges[0]
        self.assertTrue(edge.is_cross_team)
        self.assertEqual(edge.source_team_id, "team-a")
        self.assertEqual(edge.target_team_id, "team-b")
    
    def test_shared_ownership_report(self) -> None:
        """Test shared ownership report for monorepo."""
        events = [
            # Team A owns auth primarily
            self.make_event("c1", "Alice", "team-a", "2026-04-01T10:00:00+00:00", "auth"),
            self.make_event("c2", "Alice", "team-a", "2026-04-02T10:00:00+00:00", "auth"),
            # Team B touches payments primarily
            self.make_event("c3", "Bob", "team-b", "2026-04-01T10:00:00+00:00", "payments"),
            self.make_event("c4", "Bob", "team-b", "2026-04-02T10:00:00+00:00", "payments"),
            # BUT both teams touch shared-module (the critical scenario)
            self.make_event("c5", "Alice", "team-a", "2026-04-03T10:00:00+00:00", "shared-module"),
            self.make_event("c6", "Bob", "team-b", "2026-04-04T10:00:00+00:00", "shared-module"),
        ]
        
        team_assignments = {
            "Alice": "team-a",
            "Bob": "team-b",
        }
        
        graph = DependencyGraph(events, team_assignments)
        report = graph.identify_shared_modules("/repo")
        
        # Should identify shared-module as shared
        shared_module_names = [m["module"] for m in report["shared_modules"]]
        self.assertIn("shared-module", shared_module_names)
        
        # shared-module should have both teams
        shared_module = next(m for m in report["shared_modules"] if m["module"] == "shared-module")
        self.assertEqual(shared_module["team_count"], 2)
        self.assertIn("team-a", shared_module["teams"])
        self.assertIn("team-b", shared_module["teams"])
    
    def test_no_cross_team_for_single_team(self) -> None:
        """Test that single-team modules don't create cross-team edges."""
        events = [
            self.make_event("c1", "Alice", "team-a", "2026-04-01T10:00:00+00:00", "team-a-module"),
            self.make_event("c2", "Alan", "team-a", "2026-04-02T10:00:00+00:00", "team-a-module"),
        ]
        
        team_assignments = {"Alice": "team-a", "Alan": "team-a"}
        
        graph = DependencyGraph(events, team_assignments)
        edges = graph.detect_cross_team_overlap("/repo", events, team_assignments)
        
        # No cross-team edges should be created
        self.assertEqual(len(edges), 0)


class TestHandoffChainDetection(unittest.TestCase):
    """Test handoff chain detection when primary owner changes over time."""
    
    def make_event(self, commit_id: str, author: str, timestamp: str, module: str = "legacy") -> dict[str, Any]:
        return {
            "commit_id": commit_id,
            "message": f"Work on {module}",
            "timestamp": timestamp,
            "repository_name": "platform",
            "modules_touched": [module],
            "files_changed": [{"path": f"src/{module}/file.py", "changes": 50}],
            "total_changes": 50,
            "author": author,
            "author_email": f"{author.lower()}@example.com",
            "developer_id": author.lower(),
            "active_minutes": 60,
        }
    
    def test_detect_handoff_chain(self) -> None:
        """Test detection of ownership handoff over time."""
        events = [
            # Phase 1: Alice is primary owner (March)
            self.make_event("c1", "Alice", "2026-03-01T10:00:00+00:00", "legacy"),
            self.make_event("c2", "Alice", "2026-03-15T10:00:00+00:00", "legacy"),
            # Phase 2: Bob takes over (April)
            self.make_event("c3", "Bob", "2026-04-01T10:00:00+00:00", "legacy"),
            self.make_event("c4", "Bob", "2026-04-15T10:00:00+00:00", "legacy"),
            self.make_event("c5", "Bob", "2026-04-20T10:00:00+00:00", "legacy"),
        ]
        
        graph = DependencyGraph(events)
        handoff = graph.detect_handoff_risk("legacy", time_window_days=90)
        
        # Should detect handoff
        self.assertTrue(handoff["handoff_detected"])
        self.assertEqual(handoff["handoff_count"], 1)
        
        # Chain should show Alice then Bob
        chain = handoff["handoff_chain"]
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0]["owner"], "Alice")
        self.assertEqual(chain[1]["owner"], "Bob")
    
    def test_no_handoff_for_stable_ownership(self) -> None:
        """Test that stable ownership doesn't trigger false handoff detection."""
        events = [
            # Alice consistently owns the module
            self.make_event("c1", "Alice", "2026-04-01T10:00:00+00:00", "stable"),
            self.make_event("c2", "Alice", "2026-04-05T10:00:00+00:00", "stable"),
            self.make_event("c3", "Alice", "2026-04-10T10:00:00+00:00", "stable"),
            self.make_event("c4", "Alice", "2026-04-15T10:00:00+00:00", "stable"),
        ]
        
        graph = DependencyGraph(events)
        handoff = graph.detect_handoff_risk("stable", time_window_days=90)
        
        # No handoff should be detected
        self.assertFalse(handoff["handoff_detected"])
        self.assertEqual(handoff["handoff_count"], 0)
    
    def test_multiple_handoffs_high_risk(self) -> None:
        """Test that multiple handoffs are flagged as high risk."""
        events = [
            # Alice -> Bob -> Carol (multiple handoffs)
            self.make_event("c1", "Alice", "2026-01-01T10:00:00+00:00", "volatile"),
            self.make_event("c2", "Bob", "2026-02-01T10:00:00+00:00", "volatile"),
            self.make_event("c3", "Bob", "2026-02-15T10:00:00+00:00", "volatile"),
            self.make_event("c4", "Carol", "2026-03-01T10:00:00+00:00", "volatile"),
            self.make_event("c5", "Carol", "2026-03-15T10:00:00+00:00", "volatile"),
        ]
        
        graph = DependencyGraph(events)
        handoff = graph.detect_handoff_risk("volatile", time_window_days=120)
        
        # Multiple handoffs should be detected
        self.assertTrue(handoff["handoff_detected"])
        self.assertGreaterEqual(handoff["handoff_count"], 2)
        self.assertEqual(handoff["risk_level"], "high")


class TestBottleneckIdentification(unittest.TestCase):
    """Test bottleneck identification with bus factor."""
    
    def make_event(
        self,
        commit_id: str,
        author: str,
        team: str,
        timestamp: str,
        module: str,
    ) -> dict[str, Any]:
        return {
            "commit_id": commit_id,
            "message": f"Work on {module}",
            "timestamp": timestamp,
            "repository_name": "platform",
            "modules_touched": [module],
            "files_changed": [{"path": f"src/{module}/file.py", "changes": 50}],
            "total_changes": 50,
            "author": author,
            "author_email": f"{author.lower()}@example.com",
            "developer_id": author.lower(),
            "active_minutes": 60,
        }
    
    def test_bottleneck_score_calculation(self) -> None:
        """Test bottleneck score = (cross_team_count * 10) / (bus_factor + 1)."""
        # Scenario: 3 teams, bus factor 1
        # Score = (3 * 10) / (1 + 1) = 30 / 2 = 15
        
        events = [
            # 3 teams touching same module, but only 1 developer (Alice) does most work (70%+)
            self.make_event("c1", "Alice", "team-a", "2026-04-01T10:00:00+00:00", "critical"),
            self.make_event("c2", "Alice", "team-a", "2026-04-02T10:00:00+00:00", "critical"),
            self.make_event("c3", "Alice", "team-a", "2026-04-03T10:00:00+00:00", "critical"),
            self.make_event("c4", "Alice", "team-a", "2026-04-04T10:00:00+00:00", "critical"),
            self.make_event("c5", "Alice", "team-a", "2026-04-05T10:00:00+00:00", "critical"),
            self.make_event("c6", "Alice", "team-a", "2026-04-06T10:00:00+00:00", "critical"),
            self.make_event("c7", "Alice", "team-a", "2026-04-07T10:00:00+00:00", "critical"),  # Alice has 7
            self.make_event("c8", "Bob", "team-b", "2026-04-04T10:00:00+00:00", "critical"),  # Small contribution
            self.make_event("c9", "Carol", "team-c", "2026-04-05T10:00:00+00:00", "critical"),  # Small contribution
        ]
        
        team_assignments = {
            "Alice": "team-a",
            "Bob": "team-b",
            "Carol": "team-c",
        }
        
        graph = DependencyGraph(events, team_assignments)
        bottlenecks = graph.find_bottlenecks()
        
        # Should find the critical module as bottleneck
        self.assertGreater(len(bottlenecks), 0)
        
        # Find critical module in bottlenecks
        critical_bottleneck = next((b for b in bottlenecks if b["module"] == "critical"), None)
        self.assertIsNotNone(critical_bottleneck)
        
        # Verify calculations
        self.assertEqual(critical_bottleneck["cross_team_count"], 3)
        # Alice has 7/9 = 77% coverage, so bus factor is 1
        self.assertEqual(critical_bottleneck["bus_factor"], 1)  # Only Alice covers 70%
        
        # Score should be high: (3 * 10) / (1 + 1) = 15
        expected_score = (3 * 10) / (1 + 1)
        self.assertAlmostEqual(critical_bottleneck["bottleneck_score"], expected_score, delta=1.0)
        
        # Should be high/critical risk
        self.assertIn(critical_bottleneck["risk_level"], ["high", "critical"])
    
    def test_bottleneck_not_created_for_shared_ownership(self) -> None:
        """Test that well-distributed ownership reduces bottleneck score."""
        events = [
            # 2 teams, but distributed ownership (high bus factor)
            self.make_event("c1", "Alice", "team-a", "2026-04-01T10:00:00+00:00", "healthy"),
            self.make_event("c2", "Alan", "team-a", "2026-04-02T10:00:00+00:00", "healthy"),
            self.make_event("c3", "Bob", "team-b", "2026-04-01T10:00:00+00:00", "healthy"),
            self.make_event("c4", "Ben", "team-b", "2026-04-02T10:00:00+00:00", "healthy"),
        ]
        
        team_assignments = {
            "Alice": "team-a", "Alan": "team-a",
            "Bob": "team-b", "Ben": "team-b",
        }
        
        graph = DependencyGraph(events, team_assignments)
        bottlenecks = graph.find_bottlenecks()
        
        # Should still be a bottleneck but lower score
        healthy = next((b for b in bottlenecks if b["module"] == "healthy"), None)
        if healthy:
            # Bus factor should be higher due to distributed ownership
            self.assertGreater(healthy["bus_factor"], 1)
            # Score should be lower due to higher bus factor
            # (2 * 10) / (2 + 1) = 6.67
            self.assertLess(healthy["bottleneck_score"], 10)
    
    def test_manager_dependency_edges(self) -> None:
        """Test manager-to-manager dependency edges when teams share modules."""
        events = [
            # Manager A's team (team-a) and Manager B's team (team-b) share auth module
            self.make_event("c1", "Alice", "team-a", "2026-04-01T10:00:00+00:00", "auth"),
            self.make_event("c2", "Bob", "team-b", "2026-04-02T10:00:00+00:00", "auth"),
            # Both teams also share payments module
            self.make_event("c3", "Alice", "team-a", "2026-04-03T10:00:00+00:00", "payments"),
            self.make_event("c4", "Bob", "team-b", "2026-04-04T10:00:00+00:00", "payments"),
        ]
        
        team_assignments = {
            "Alice": "team-a",
            "Bob": "team-b",
        }
        
        graph = DependencyGraph(events, team_assignments)
        
        # Set manager mappings
        manager_mappings = {
            "team-a": "manager-a",
            "team-b": "manager-b",
        }
        graph.set_manager_mappings(manager_mappings)
        
        edges = graph.get_manager_dependency_edges()
        
        # Should create manager-to-manager edge
        self.assertGreater(len(edges), 0)
        
        # Verify edge properties
        edge = edges[0]
        self.assertIn("manager", edge.source_work_item_id)
        self.assertIn("manager", edge.target_work_item_id)
        self.assertTrue(edge.is_cross_team)
        
        # Evidence should mention shared modules
        self.assertTrue(any("auth" in e or "payments" in e for e in edge.evidence))


class TestMonorepoScenarios(unittest.TestCase):
    """Test critical monorepo scenarios from requirements."""
    
    def make_event(
        self,
        commit_id: str,
        author: str,
        team: str,
        timestamp: str,
        module: str,
    ) -> dict[str, Any]:
        return {
            "commit_id": commit_id,
            "message": f"Work on {module}",
            "timestamp": timestamp,
            "repository_name": "monorepo",
            "modules_touched": [module],
            "files_changed": [{"path": f"src/{module}/file.py", "changes": 50}],
            "total_changes": 50,
            "author": author,
            "author_email": f"{author.lower()}@example.com",
            "developer_id": author.lower(),
            "active_minutes": 60,
        }
    
    def test_scenario_same_repo_manager_a_auth_module(self) -> None:
        """
        Scenario: Same repo, Manager A's team touches auth module.
        System should correctly attribute to Manager A's team.
        """
        events = [
            self.make_event("c1", "Alice", "team-a", "2026-04-01T10:00:00+00:00", "auth"),
            self.make_event("c2", "Alan", "team-a", "2026-04-02T10:00:00+00:00", "auth"),
        ]
        
        team_assignments = {"Alice": "team-a", "Alan": "team-a"}
        manager_mappings = {"team-a": "manager-a"}
        
        graph = DependencyGraph(events, team_assignments)
        graph.set_manager_mappings(manager_mappings)
        
        report = graph.identify_shared_modules("/monorepo")
        
        # auth should be in the report
        auth_module = next((m for m in report["shared_modules"] if m["module"] == "auth"), None)
        if auth_module:
            # Should be attributed to team-a (Manager A), not wrong manager
            self.assertIn("team-a", auth_module["teams"])
            self.assertNotIn("team-b", auth_module["teams"])
    
    def test_scenario_same_repo_manager_b_auth_module_shared_ownership(self) -> None:
        """
        Scenario: Same repo, Manager B's team also touches auth module (shared ownership).
        System should surface shared ownership.
        """
        events = [
            # Manager A's team
            self.make_event("c1", "Alice", "team-a", "2026-04-01T10:00:00+00:00", "auth"),
            # Manager B's team
            self.make_event("c2", "Bob", "team-b", "2026-04-02T10:00:00+00:00", "auth"),
        ]
        
        team_assignments = {"Alice": "team-a", "Bob": "team-b"}
        manager_mappings = {"team-a": "manager-a", "team-b": "manager-b"}
        
        graph = DependencyGraph(events, team_assignments)
        graph.set_manager_mappings(manager_mappings)
        
        report = graph.identify_shared_modules("/monorepo")
        
        # Should identify auth as shared
        auth_module = next(m for m in report["shared_modules"] if m["module"] == "auth")
        self.assertEqual(auth_module["team_count"], 2)
        self.assertIn("team-a", auth_module["teams"])
        self.assertIn("team-b", auth_module["teams"])
        
        # Should have both managers
        manager_edges = graph.get_manager_dependency_edges()
        self.assertGreater(len(manager_edges), 0)
    
    def test_scenario_both_teams_payments_cross_team_dependency(self) -> None:
        """
        Scenario: Same repo, both teams touch payments module (cross-team dependency).
        System should expose dependency edges.
        """
        events = [
            # Team A's contributions to payments
            self.make_event("c1", "Alice", "team-a", "2026-04-01T10:00:00+00:00", "payments"),
            self.make_event("c2", "Alan", "team-a", "2026-04-02T10:00:00+00:00", "payments"),
            # Team B's contributions to payments
            self.make_event("c3", "Bob", "team-b", "2026-04-03T10:00:00+00:00", "payments"),
            self.make_event("c4", "Ben", "team-b", "2026-04-04T10:00:00+00:00", "payments"),
        ]
        
        team_assignments = {
            "Alice": "team-a", "Alan": "team-a",
            "Bob": "team-b", "Ben": "team-b",
        }
        
        graph = DependencyGraph(events, team_assignments)
        edges = graph.detect_cross_team_overlap("/monorepo", events, team_assignments)
        
        # Should expose dependency edges
        self.assertGreater(len(edges), 0)
        
        # Edge should show dependency between teams
        edge = edges[0]
        self.assertTrue(edge.is_cross_team)
        self.assertEqual(edge.dependency_type, "depends_on")
        
        # Evidence should mention payments
        self.assertTrue(any("payments" in str(e) or "2 teams" in str(e) for e in edge.evidence))


class TestOwnershipRiskDetection(unittest.TestCase):
    """Test ownership risk detection including backup gaps."""
    
    def make_event(self, commit_id: str, author: str, timestamp: str, module: str = "risky") -> dict[str, Any]:
        return {
            "commit_id": commit_id,
            "message": f"Work on {module}",
            "timestamp": timestamp,
            "repository_name": "platform",
            "modules_touched": [module],
            "files_changed": [{"path": f"src/{module}/file.py", "changes": 50}],
            "total_changes": 50,
            "author": author,
            "author_email": f"{author.lower()}@example.com",
            "developer_id": author.lower(),
            "active_minutes": 60,
        }
    
    def test_detect_ownership_risk_single_owner(self) -> None:
        """Test high risk detection for single owner with no backup."""
        events = [
            self.make_event("c1", "Alice", "2026-04-01T10:00:00+00:00", "critical"),
            self.make_event("c2", "Alice", "2026-04-02T10:00:00+00:00", "critical"),
            self.make_event("c3", "Alice", "2026-04-03T10:00:00+00:00", "critical"),
        ]
        
        graph = OwnershipGraph(events)
        risk = graph.detect_ownership_risk("critical")
        
        # Should be high risk
        self.assertEqual(risk["risk_level"], "high")
        self.assertEqual(risk["bus_factor"], 1)
        self.assertEqual(risk["primary_owner"], "Alice")
        self.assertIsNone(risk["secondary_owner"])
        self.assertEqual(risk["backup_gap_pct"], 100.0)  # No backup = full gap
        self.assertIn("CRITICAL", risk["recommendation"])
    
    def test_detect_ownership_risk_with_backup(self) -> None:
        """Test lower risk when backup owner exists."""
        events = [
            # Alice is primary (more commits)
            self.make_event("c1", "Alice", "2026-04-01T10:00:00+00:00", "healthy"),
            self.make_event("c2", "Alice", "2026-04-02T10:00:00+00:00", "healthy"),
            self.make_event("c3", "Alice", "2026-04-03T10:00:00+00:00", "healthy"),
            # Bob is secondary (fewer commits)
            self.make_event("c4", "Bob", "2026-04-01T11:00:00+00:00", "healthy"),
            self.make_event("c5", "Bob", "2026-04-02T11:00:00+00:00", "healthy"),
        ]
        
        graph = OwnershipGraph(events)
        risk = graph.detect_ownership_risk("healthy")
        
        # Should have backup
        self.assertIsNotNone(risk["secondary_owner"])
        self.assertEqual(risk["secondary_owner"], "Bob")
        
        # Backup gap should be smaller
        self.assertLess(risk["backup_gap_pct"], 40.0)
        
        # Should be medium or low risk
        self.assertIn(risk["risk_level"], ["low", "medium"])
    
    def test_detect_ownership_risk_no_data(self) -> None:
        """Test risk detection with no data."""
        graph = OwnershipGraph([])
        risk = graph.detect_ownership_risk("unknown-module")
        
        # Should handle gracefully
        self.assertEqual(risk["risk_level"], "high")
        self.assertEqual(risk["bus_factor"], 0)
        self.assertIsNone(risk["primary_owner"])


if __name__ == "__main__":
    unittest.main()
