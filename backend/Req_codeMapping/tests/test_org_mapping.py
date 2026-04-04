"""
Tests for org_mapping.py and manager_rollups.py.

Tests cover:
- Developer-to-team mapping with confidence
- Team-to-manager resolution
- Time-aware membership (historical queries)
- Manager rollup calculation
- Shared repo scenario: two managers, same repo, correct rollup separation
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from org_mapping import OrgMapper, create_org_mapper
from org_mapping import (
    CONFIDENCE_EMPLOYEE_DIRECTORY,
    CONFIDENCE_GIT_JIRA_CONSISTENT,
    CONFIDENCE_INFERRED_PATTERN,
)
from manager_rollups import ManagerRollupEngine, create_manager_rollup_engine
from schemas import TeamMembership, ManagerMapping, AttributionDecision, DependencyEdge


class TestOrgMapperBasics:
    """Basic OrgMapper functionality tests."""

    def test_create_org_mapper(self):
        """Test factory function creates OrgMapper."""
        mapper = create_org_mapper()
        assert mapper is not None
        assert isinstance(mapper, OrgMapper)

    def test_add_team_membership(self):
        """Test adding a team membership."""
        mapper = OrgMapper()
        
        membership = mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-alpha",
            role="developer",
            confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
            provenance="hr_system",
            evidence=["Employee directory entry for team-alpha"],
        )
        
        assert membership.canonical_id == "dev-001"
        assert membership.team_id == "team-alpha"
        assert membership.role == "developer"
        assert membership.confidence_score == CONFIDENCE_EMPLOYEE_DIRECTORY
        assert membership.confidence_label == "high"
        assert not membership.ambiguity_flag
        assert membership.provenance == "hr_system"

    def test_add_manager_mapping(self):
        """Test adding a manager mapping."""
        mapper = OrgMapper()
        
        mapping = mapper.add_manager_mapping(
            team_id="team-alpha",
            manager_canonical_id="mgr-001",
            manager_role="engineering_manager",
        )
        
        assert mapping.team_id == "team-alpha"
        assert mapping.manager_canonical_id == "mgr-001"
        assert mapping.manager_role == "engineering_manager"
        assert mapping.is_primary is True
        assert mapping.confidence_score == CONFIDENCE_EMPLOYEE_DIRECTORY


class TestDeveloperToTeamMapping:
    """Test developer-to-team mapping with confidence levels."""

    def test_map_developer_to_teams_empty(self):
        """Test mapping returns empty list for unknown developer."""
        mapper = OrgMapper()
        result = mapper.map_developer_to_teams("unknown-dev")
        assert result == []

    def test_map_developer_to_teams_single(self):
        """Test getting single team membership."""
        mapper = OrgMapper()
        mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-alpha",
            confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
        )
        
        result = mapper.map_developer_to_teams("dev-001")
        
        assert len(result) == 1
        assert result[0].team_id == "team-alpha"
        assert result[0].confidence_score == CONFIDENCE_EMPLOYEE_DIRECTORY

    def test_map_developer_to_teams_multiple(self):
        """Test getting multiple team memberships."""
        mapper = OrgMapper()
        
        # High confidence primary team
        mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-alpha",
            allocation_percent=80,
            confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
        )
        
        # Lower confidence secondary team
        mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-beta",
            allocation_percent=20,
            confidence_score=CONFIDENCE_GIT_JIRA_CONSISTENT,
        )
        
        result = mapper.map_developer_to_teams("dev-001")
        
        assert len(result) == 2
        # Should be sorted by confidence (high first)
        assert result[0].team_id == "team-alpha"
        assert result[0].confidence_score == CONFIDENCE_EMPLOYEE_DIRECTORY
        assert result[1].team_id == "team-beta"
        assert result[1].confidence_score == CONFIDENCE_GIT_JIRA_CONSISTENT

    def test_confidence_levels(self):
        """Test different confidence levels are handled correctly."""
        mapper = OrgMapper()
        
        # High confidence (employee directory)
        high = mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-high",
            confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
        )
        assert high.confidence_label == "high"
        assert not high.ambiguity_flag
        
        # Medium confidence (git/jira consistent)
        medium = mapper.add_team_membership(
            canonical_id="dev-002",
            team_id="team-medium",
            confidence_score=CONFIDENCE_GIT_JIRA_CONSISTENT,
        )
        assert medium.confidence_label == "medium"
        assert not medium.ambiguity_flag
        
        # Low confidence (inferred pattern) - should be flagged
        low = mapper.add_team_membership(
            canonical_id="dev-003",
            team_id="team-low",
            confidence_score=CONFIDENCE_INFERRED_PATTERN,
        )
        assert low.confidence_label == "low"
        assert low.ambiguity_flag is True
        assert low.manual_review_required is True


class TestTeamToManagerResolution:
    """Test team-to-manager resolution."""

    def test_map_team_to_manager_not_found(self):
        """Test mapping returns None for unknown team."""
        mapper = OrgMapper()
        result = mapper.map_team_to_manager("unknown-team")
        assert result is None

    def test_map_team_to_manager_single(self):
        """Test getting manager for a team."""
        mapper = OrgMapper()
        mapper.add_manager_mapping(
            team_id="team-alpha",
            manager_canonical_id="mgr-001",
            manager_role="engineering_manager",
        )
        
        result = mapper.map_team_to_manager("team-alpha")
        
        assert result is not None
        assert result.manager_canonical_id == "mgr-001"
        assert result.team_id == "team-alpha"

    def test_map_team_to_manager_multiple_primary(self):
        """Test that primary manager is returned when multiple exist."""
        mapper = OrgMapper()
        
        # Primary manager
        mapper.add_manager_mapping(
            team_id="team-alpha",
            manager_canonical_id="mgr-001",
            is_primary=True,
            confidence_score=0.95,
        )
        
        # Secondary manager
        mapper.add_manager_mapping(
            team_id="team-alpha",
            manager_canonical_id="mgr-002",
            is_primary=False,
            confidence_score=0.90,
        )
        
        result = mapper.map_team_to_manager("team-alpha", primary_only=True)
        
        assert result is not None
        assert result.manager_canonical_id == "mgr-001"

    def test_get_developer_manager(self):
        """Test getting manager for a developer."""
        mapper = OrgMapper()
        
        # Setup team and manager
        mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-alpha",
            confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
        )
        mapper.add_manager_mapping(
            team_id="team-alpha",
            manager_canonical_id="mgr-001",
        )
        
        result = mapper.get_developer_manager("dev-001")
        
        assert result is not None
        assert result.manager_canonical_id == "mgr-001"

    def test_get_developer_manager_no_team(self):
        """Test getting manager for developer with no team."""
        mapper = OrgMapper()
        
        result = mapper.get_developer_manager("dev-orphan")
        
        assert result is None


class TestTimeAwareMembership:
    """Test time-aware membership queries."""

    def test_current_membership_vs_historical(self):
        """Test current vs historical membership queries."""
        mapper = OrgMapper()
        
        now = datetime.now(timezone.utc)
        past = (now - timedelta(days=90)).isoformat()
        future = (now + timedelta(days=1)).isoformat()
        
        # Add a membership that ended in the past
        mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-old",
            effective_from=past,
            effective_to=(now - timedelta(days=30)).isoformat(),
        )
        
        # Add current membership
        mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-current",
        )
        
        # Query current - should only see current team
        current = mapper.map_developer_to_teams("dev-001", active_only=True)
        assert len(current) == 1
        assert current[0].team_id == "team-current"
        
        # Query with as_of in the past - should see old team
        historical = mapper.map_developer_to_teams(
            "dev-001",
            as_of=(now - timedelta(days=60)).isoformat(),
            active_only=False,
        )
        assert len(historical) == 1
        assert historical[0].team_id == "team-old"

    def test_is_team_member_current(self):
        """Test is_team_member for current membership."""
        mapper = OrgMapper()
        
        mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-alpha",
        )
        
        result = mapper.is_team_member("dev-001", "team-alpha")
        
        assert result["is_member"] is True
        assert result["membership"] is not None
        assert result["membership"].team_id == "team-alpha"

    def test_is_team_member_historical(self):
        """Test is_team_member for historical query."""
        mapper = OrgMapper()
        
        now = datetime.now(timezone.utc)
        past = (now - timedelta(days=90)).isoformat()
        
        # Add membership that is now ended
        membership = mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-alpha",
            effective_from=past,
            effective_to=(now - timedelta(days=30)).isoformat(),
        )
        
        # Current query - should not be member
        current_result = mapper.is_team_member("dev-001", "team-alpha")
        assert current_result["is_member"] is False
        
        # Historical query (during membership) - should be member
        historical_result = mapper.is_team_member(
            "dev-001",
            "team-alpha",
            as_of=(now - timedelta(days=60)).isoformat(),
        )
        assert historical_result["is_member"] is True

    def test_manager_changes_over_time(self):
        """Test manager changes with effective dates."""
        mapper = OrgMapper()
        
        now = datetime.now(timezone.utc)
        past = (now - timedelta(days=90)).isoformat()
        middle = (now - timedelta(days=45)).isoformat()
        
        # Old manager (ended 45 days ago)
        mapper.add_manager_mapping(
            team_id="team-alpha",
            manager_canonical_id="mgr-old",
            effective_from=past,
            effective_to=middle,
        )
        
        # Current manager (started 45 days ago)
        mapper.add_manager_mapping(
            team_id="team-alpha",
            manager_canonical_id="mgr-new",
            effective_from=middle,
        )
        
        # Query current - should see new manager
        current_mgr = mapper.map_team_to_manager("team-alpha")
        assert current_mgr is not None
        assert current_mgr.manager_canonical_id == "mgr-new"
        
        # Query past - should see old manager
        past_mgr = mapper.map_team_to_manager("team-alpha", as_of=(now - timedelta(days=60)).isoformat())
        assert past_mgr is not None
        assert past_mgr.manager_canonical_id == "mgr-old"

    def test_end_membership(self):
        """Test ending a team membership."""
        mapper = OrgMapper()
        
        now = datetime.now(timezone.utc)
        past_start = (now - timedelta(days=30)).isoformat()
        query_time = (now - timedelta(days=15)).isoformat()
        
        # Add membership that started 30 days ago
        mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-alpha",
            effective_from=past_start,
        )
        
        # Verify active at current time
        assert len(mapper.map_developer_to_teams("dev-001")) == 1
        
        # Verify active at query time (before ending)
        assert len(mapper.map_developer_to_teams("dev-001", as_of=query_time)) == 1
        
        # End membership
        result = mapper.end_membership("dev-001", "team-alpha")
        assert result is True
        
        # Verify inactive at current time
        assert len(mapper.map_developer_to_teams("dev-001", active_only=True)) == 0
        # Verify still visible when querying time before it ended
        assert len(mapper.map_developer_to_teams("dev-001", as_of=query_time, active_only=False)) == 1


class TestGetTeamMembers:
    """Test getting team members."""

    def test_get_team_members_empty(self):
        """Test getting members of empty team."""
        mapper = OrgMapper()
        result = mapper.get_team_members("empty-team")
        assert result == []

    def test_get_team_members_multiple(self):
        """Test getting multiple team members."""
        mapper = OrgMapper()
        
        mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-alpha",
            role="tech_lead",
            confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
        )
        mapper.add_team_membership(
            canonical_id="dev-002",
            team_id="team-alpha",
            role="developer",
            confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
        )
        mapper.add_team_membership(
            canonical_id="dev-003",
            team_id="team-alpha",
            role="developer",
            confidence_score=CONFIDENCE_GIT_JIRA_CONSISTENT,
        )
        
        result = mapper.get_team_members("team-alpha")
        
        assert len(result) == 3
        # Should be sorted by confidence
        assert result[0]["canonical_id"] == "dev-001"
        assert result[0]["role"] == "tech_lead"
        assert result[1]["canonical_id"] == "dev-002"
        assert result[2]["canonical_id"] == "dev-003"


class TestManagerRollups:
    """Test manager rollup calculations."""

    def test_create_manager_rollup_engine(self):
        """Test factory function creates engine."""
        mapper = OrgMapper()
        engine = create_manager_rollup_engine(mapper)
        assert engine is not None
        assert isinstance(engine, ManagerRollupEngine)

    def test_rollup_attribution_basic(self):
        """Test basic attribution rollup."""
        mapper = OrgMapper()
        engine = ManagerRollupEngine(mapper)
        
        # Setup team with manager
        mapper.add_team_membership(
            canonical_id="dev-001",
            team_id="team-alpha",
        )
        mapper.add_manager_mapping(
            team_id="team-alpha",
            manager_canonical_id="mgr-001",
        )
        
        # Add some work items
        now = datetime.now(timezone.utc).isoformat()
        engine.add_attribution_decision(
            AttributionDecision(
                decision_id="dec-001",
                work_item_id="issue-123",
                work_item_type="issue",
                canonical_id="dev-001",
                effective_from=now,
                confidence_score=0.9,
                confidence_label="high",
                provenance="jira_api",
            )
        )
        
        # Rollup
        summary = engine.rollup_attribution("mgr-001", time_range="30d")
        
        assert summary.manager_id == "mgr-001"
        assert summary.team_ids == ["team-alpha"]
        assert summary.developer_count == 1
        assert summary.total_work_items == 1
        assert summary.confidence_distribution.high == 1

    def test_rollup_attribution_multiple_devs(self):
        """Test attribution rollup with multiple developers."""
        mapper = OrgMapper()
        engine = ManagerRollupEngine(mapper)
        
        # Setup team with 2 developers
        mapper.add_team_membership("dev-001", "team-alpha")
        mapper.add_team_membership("dev-002", "team-alpha")
        mapper.add_manager_mapping("team-alpha", "mgr-001")
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Add work items
        engine.add_attribution_decision(
            AttributionDecision(
                decision_id="dec-001",
                work_item_id="issue-123",
                work_item_type="issue",
                canonical_id="dev-001",
                effective_from=now,
                confidence_score=0.9,
                confidence_label="high",
                provenance="jira_api",
            )
        )
        engine.add_attribution_decision(
            AttributionDecision(
                decision_id="dec-002",
                work_item_id="pr-456",
                work_item_type="pull_request",
                canonical_id="dev-002",
                effective_from=now,
                confidence_score=0.6,
                confidence_label="medium",
                provenance="github_api",
            )
        )
        
        summary = engine.rollup_attribution("mgr-001")
        
        assert summary.developer_count == 2
        assert summary.total_work_items == 2
        assert summary.work_items_by_type["issue"] == 1
        assert summary.work_items_by_type["pull_request"] == 1
        assert summary.confidence_distribution.high == 1
        assert summary.confidence_distribution.medium == 1

    def test_rollup_dependency_pressure(self):
        """Test dependency pressure rollup."""
        mapper = OrgMapper()
        engine = ManagerRollupEngine(mapper)
        
        # Setup two teams
        mapper.add_team_membership("dev-001", "team-a")
        mapper.add_team_membership("dev-002", "team-b")
        mapper.add_manager_mapping("team-a", "mgr-a")
        mapper.add_manager_mapping("team-b", "mgr-b")
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Add cross-team dependency: team-a depends on team-b
        engine.add_dependency_edge(
            DependencyEdge(
                edge_id="edge-001",
                source_work_item_id="issue-a-1",
                source_work_item_type="issue",
                source_team_id="team-a",
                target_work_item_id="issue-b-1",
                target_work_item_type="issue",
                target_team_id="team-b",
                is_cross_team=True,
                detected_at=now,
                effective_from=now,
                confidence_score=0.85,
                confidence_label="high",
                provenance="jira_link",
                dependency_type="depends_on",
                detection_method="jira_link",
            )
        )
        
        # Rollup for mgr-a (outgoing dependency)
        pressure_a = engine.rollup_dependency_pressure("mgr-a")
        assert len(pressure_a.outgoing_dependencies) == 1
        assert len(pressure_a.incoming_dependencies) == 0
        assert pressure_a.cross_team_strength["outgoing_count"] == 1
        
        # Rollup for mgr-b (incoming dependency)
        pressure_b = engine.rollup_dependency_pressure("mgr-b")
        assert len(pressure_b.incoming_dependencies) == 1
        assert len(pressure_b.outgoing_dependencies) == 0
        assert pressure_b.cross_team_strength["incoming_count"] == 1

    def test_rollup_risk_exposure(self):
        """Test risk exposure rollup."""
        mapper = OrgMapper()
        engine = ManagerRollupEngine(mapper)
        
        # Setup team
        mapper.add_team_membership("dev-001", "team-alpha")
        mapper.add_manager_mapping("team-alpha", "mgr-001")
        
        # Mock knowledge risks
        knowledge_risks = [
            {
                "module": "auth-service",
                "severity": "high",
                "primary_owner": "dev-001",
                "ownership_share_pct": 85.0,
                "contributor_count": 1,
                "bus_factor": 1,
                "secondary_owner": None,
            },
            {
                "module": "api-gateway",
                "severity": "medium",
                "primary_owner": "dev-001",
                "ownership_share_pct": 60.0,
                "contributor_count": 2,
                "bus_factor": 2,
                "secondary_owner": "dev-002",
            },
        ]
        
        risk = engine.rollup_risk_exposure("mgr-001", knowledge_risks=knowledge_risks)
        
        assert risk.manager_id == "mgr-001"
        assert len(risk.high_risk_modules) == 1
        assert len(risk.medium_risk_modules) == 1
        assert risk.high_risk_modules[0]["module"] == "auth-service"
        assert len(risk.shared_modules) == 1  # api-gateway has 2 contributors

    def test_compare_team_capacity(self):
        """Test team capacity comparison."""
        mapper = OrgMapper()
        engine = ManagerRollupEngine(mapper)
        
        # Setup teams
        mapper.add_team_membership("dev-001", "team-a", role="tech_lead")
        mapper.add_team_membership("dev-002", "team-a", role="developer")
        mapper.add_team_membership("dev-003", "team-b", role="developer")
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Add work items
        engine.add_attribution_decision(
            AttributionDecision(
                decision_id="dec-001",
                work_item_id="issue-1",
                work_item_type="issue",
                canonical_id="dev-001",
                effective_from=now,
                confidence_score=0.9,
                confidence_label="high",
                provenance="jira_api",
            )
        )
        engine.add_attribution_decision(
            AttributionDecision(
                decision_id="dec-002",
                work_item_id="issue-2",
                work_item_type="issue",
                canonical_id="dev-002",
                effective_from=now,
                confidence_score=0.8,
                confidence_label="high",
                provenance="jira_api",
            )
        )
        engine.add_attribution_decision(
            AttributionDecision(
                decision_id="dec-003",
                work_item_id="issue-3",
                work_item_type="issue",
                canonical_id="dev-003",
                effective_from=now,
                confidence_score=0.9,
                confidence_label="high",
                provenance="jira_api",
            )
        )
        
        comparison = engine.compare_team_capacity("team-a", "team-b")
        
        assert comparison.team_a_id == "team-a"
        assert comparison.team_b_id == "team-b"
        assert comparison.team_a_size == 2
        assert comparison.team_b_size == 1
        assert comparison.capacity_metrics["team_a"]["total_work_items"] == 2
        assert comparison.capacity_metrics["team_b"]["total_work_items"] == 1


class TestMonorepoSafety:
    """
    Critical test: Shared repo scenario - two managers, same repo, correct rollup separation.
    
    Manager A has 10 employees working in shared repo X
    Manager B has another team also in shared repo X
    System must correctly rollup ONLY their respective team's work
    Must NOT derive manager from repository alone
    """

    def test_monorepo_rollup_separation(self):
        """
        Core monorepo safety test: Multiple teams in same repo must have separate rollups.
        """
        mapper = OrgMapper()
        engine = ManagerRollupEngine(mapper)
        
        # Setup: Manager A with 10 developers on team-alpha
        for i in range(10):
            mapper.add_team_membership(
                canonical_id=f"mgr-a-dev-{i:02d}",
                team_id="team-alpha",
                confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
            )
        mapper.add_manager_mapping(
            team_id="team-alpha",
            manager_canonical_id="mgr-a",
            confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
        )
        
        # Setup: Manager B with 5 developers on team-beta
        for i in range(5):
            mapper.add_team_membership(
                canonical_id=f"mgr-b-dev-{i:02d}",
                team_id="team-beta",
                confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
            )
        mapper.add_manager_mapping(
            team_id="team-beta",
            manager_canonical_id="mgr-b",
            confidence_score=CONFIDENCE_EMPLOYEE_DIRECTORY,
        )
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Both teams work in repo "shared-monorepo"
        # Manager A's team does work
        for i in range(10):
            engine.add_attribution_decision(
                AttributionDecision(
                    decision_id=f"mgr-a-dec-{i:02d}",
                    work_item_id=f"commit-a-{i:02d}",
                    work_item_type="commit",
                    canonical_id=f"mgr-a-dev-{i:02d}",
                    effective_from=now,
                    confidence_score=0.9,
                    confidence_label="high",
                    provenance="git",
                )
            )
        
        # Manager B's team does work (same repo!)
        for i in range(5):
            engine.add_attribution_decision(
                AttributionDecision(
                    decision_id=f"mgr-b-dec-{i:02d}",
                    work_item_id=f"commit-b-{i:02d}",
                    work_item_type="commit",
                    canonical_id=f"mgr-b-dev-{i:02d}",
                    effective_from=now,
                    confidence_score=0.9,
                    confidence_label="high",
                    provenance="git",
                )
            )
        
        # Rollup for Manager A - should only see their 10 developers' work
        rollup_a = engine.rollup_attribution("mgr-a")
        assert rollup_a.manager_id == "mgr-a"
        assert rollup_a.developer_count == 10
        assert rollup_a.total_work_items == 10  # Only their team's work
        
        # Rollup for Manager B - should only see their 5 developers' work
        rollup_b = engine.rollup_attribution("mgr-b")
        assert rollup_b.manager_id == "mgr-b"
        assert rollup_b.developer_count == 5
        assert rollup_b.total_work_items == 5  # Only their team's work
        
        # Verify no cross-contamination
        a_dev_ids = {d["developer_id"] for d in rollup_a.developers_summary}
        b_dev_ids = {d["developer_id"] for d in rollup_b.developers_summary}
        
        # No overlap in developers
        assert len(a_dev_ids & b_dev_ids) == 0
        
        # All of A's developers are mgr-a-dev-*
        for dev_id in a_dev_ids:
            assert dev_id.startswith("mgr-a-dev-")
        
        # All of B's developers are mgr-b-dev-*
        for dev_id in b_dev_ids:
            assert dev_id.startswith("mgr-b-dev-")

    def test_monorepo_safety_diagnostic(self):
        """Test the monorepo safety diagnostic method."""
        mapper = OrgMapper()
        engine = ManagerRollupEngine(mapper)
        
        # Setup two teams in same repo
        mapper.add_team_membership("dev-001", "team-alpha")
        mapper.add_team_membership("dev-002", "team-beta")
        mapper.add_manager_mapping("team-alpha", "mgr-a")
        mapper.add_manager_mapping("team-beta", "mgr-b")
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Add work items in shared repo
        engine.add_attribution_decision(
            AttributionDecision(
                decision_id="dec-001",
                work_item_id="commit-1",
                work_item_type="commit",
                canonical_id="dev-001",
                effective_from=now,
                confidence_score=0.9,
                confidence_label="high",
                provenance="git",
            )
        )
        engine.add_attribution_decision(
            AttributionDecision(
                decision_id="dec-002",
                work_item_id="commit-2",
                work_item_type="commit",
                canonical_id="dev-002",
                effective_from=now,
                confidence_score=0.9,
                confidence_label="high",
                provenance="git",
            )
        )
        
        # Run safety check
        check = engine.get_monorepo_rollup_safety_check("mgr-a", "shared-monorepo")
        
        assert check["separation_verified"] is True
        assert check["manager_developer_count"] == 1  # Only dev-001
        assert check["manager_work_items_in_repo"] == 1  # Only commit-1
        assert check["other_manager_work_items_in_repo"] == 1  # commit-2 belongs to mgr-b

    def test_manager_not_derived_from_repo(self):
        """
        Verify that manager is NEVER derived from repository alone.
        
        This test ensures that even if we have work items in a repo,
        we don't assign them to a manager unless we know the developer's
        team membership.
        """
        mapper = OrgMapper()
        engine = ManagerRollupEngine(mapper)
        
        # Setup: Manager with team
        mapper.add_team_membership("dev-known", "team-alpha")
        mapper.add_manager_mapping("team-alpha", "mgr-a")
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Work item from known developer (will be attributed)
        engine.add_attribution_decision(
            AttributionDecision(
                decision_id="dec-known",
                work_item_id="commit-known",
                work_item_type="commit",
                canonical_id="dev-known",
                effective_from=now,
                confidence_score=0.9,
                confidence_label="high",
                provenance="git",
            )
        )
        
        # Work item from unknown developer (orphan, no team/manager)
        engine.add_attribution_decision(
            AttributionDecision(
                decision_id="dec-unknown",
                work_item_id="commit-unknown",
                work_item_type="commit",
                canonical_id="dev-unknown",
                effective_from=now,
                confidence_score=0.5,
                confidence_label="medium",
                provenance="git",
            )
        )
        
        # Rollup should only include work from dev-known
        rollup = engine.rollup_attribution("mgr-a")
        
        assert rollup.total_work_items == 1
        assert rollup.developers_summary[0]["developer_id"] == "dev-known"
        
        # Unknown developer's work is NOT attributed to mgr-a
        assert len(rollup.developers_summary) == 1
        assert "dev-unknown" not in {d["developer_id"] for d in rollup.developers_summary}


class TestAllTeamsForManager:
    """Test getting all teams managed by a manager."""

    def test_get_all_teams_for_manager_single(self):
        """Test getting single team for manager."""
        mapper = OrgMapper()
        
        mapper.add_manager_mapping("team-alpha", "mgr-001")
        
        teams = mapper.get_all_teams_for_manager("mgr-001")
        
        assert len(teams) == 1
        assert teams[0]["team_id"] == "team-alpha"
        assert teams[0]["is_primary"] is True

    def test_get_all_teams_for_manager_multiple(self):
        """Test getting multiple teams for manager."""
        mapper = OrgMapper()
        
        mapper.add_manager_mapping("team-alpha", "mgr-001", is_primary=True)
        mapper.add_manager_mapping("team-beta", "mgr-001", is_primary=False)
        
        teams = mapper.get_all_teams_for_manager("mgr-001")
        
        assert len(teams) == 2
        # Primary first
        assert teams[0]["team_id"] == "team-alpha"
        assert teams[0]["is_primary"] is True
        assert teams[1]["team_id"] == "team-beta"
        assert teams[1]["is_primary"] is False


class TestOrgMapperStats:
    """Test OrgMapper statistics."""

    def test_get_stats(self):
        """Test statistics collection."""
        mapper = OrgMapper()
        
        # Add some data
        mapper.add_team_membership("dev-001", "team-alpha")
        mapper.add_team_membership("dev-002", "team-alpha")
        mapper.add_team_membership("dev-002", "team-beta")
        mapper.add_manager_mapping("team-alpha", "mgr-001")
        mapper.add_manager_mapping("team-beta", "mgr-002")
        
        stats = mapper.get_stats()
        
        assert stats["total_developers"] == 2
        assert stats["total_teams"] == 2
        assert stats["total_memberships"] == 3
        assert stats["active_memberships"] == 3
        assert stats["teams_with_managers"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
