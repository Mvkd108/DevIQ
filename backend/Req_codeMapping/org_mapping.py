"""
Developer-to-Team and Manager Organization Mapping System.

This module provides hierarchical organization mapping, linking developers to teams
and teams to managers with time-aware support for historical queries.

Key principles:
- Confidence-based resolution with clear evidence
- Time-aware membership queries (historical vs current)
- Manager rollups based on developer membership, NOT repository membership
- Monorepo safety: multiple teams can work in the same repository without incorrect rollup attribution

Example usage:
    mapper = OrgMapper()
    
    # Map a developer to their current teams
    memberships = mapper.map_developer_to_teams("dev-123")
    
    # Get manager for a team
    manager = mapper.map_team_to_manager("team-alpha")
    
    # Find who manages a developer
    manager = mapper.get_developer_manager("dev-123")
    
    # Check membership at a specific time
    was_member = mapper.is_team_member("dev-123", "team-alpha", as_of="2024-01-15")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from schemas import TeamMembership, ManagerMapping


# Confidence score constants
CONFIDENCE_EMPLOYEE_DIRECTORY = 0.90  # High: Official HR/employee directory match
CONFIDENCE_GIT_JIRA_CONSISTENT = 0.65  # Medium: Git/Jira consistent team mention
CONFIDENCE_INFERRED_PATTERN = 0.40  # Low: Inferred from commit patterns


@dataclass
class MembershipEvidence:
    """Evidence for a team membership decision."""

    evidence_type: str
    source_system: str
    source_reference: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: dict[str, Any] = field(default_factory=dict)


class OrgMapper:
    """
    Maps developers to teams and managers with confidence scoring.
    
    Time-aware support:
    - effective_from / effective_to dates for historical tracking
    - Current membership vs historical query support
    - Manager changes over time
    
    Confidence rules:
    - Employee directory match = 0.90 (high)
    - Git/Jira consistent team mention = 0.65 (medium)
    - Inferred from commit patterns = 0.40 (low, flagged as ambiguous)
    """

    def __init__(self, storage_provider: Any = None):
        """Initialize the organization mapper.
        
        Args:
            storage_provider: Optional storage backend for persisting mappings.
                             If None, mappings are stored in memory only.
        """
        self._memberships: dict[str, list[TeamMembership]] = {}  # canonical_id -> list
        self._team_members: dict[str, list[str]] = {}  # team_id -> list of canonical_ids
        self._manager_mappings: dict[str, list[ManagerMapping]] = {}  # team_id -> list
        self._storage = storage_provider
        self._next_membership_id = 1
        self._next_mapping_id = 1

    def _generate_membership_id(self) -> str:
        """Generate a unique membership ID."""
        id_val = f"membership-{self._next_membership_id:06d}"
        self._next_membership_id += 1
        return id_val

    def _generate_mapping_id(self) -> str:
        """Generate a unique manager mapping ID."""
        id_val = f"mapping-{self._next_mapping_id:06d}"
        self._next_mapping_id += 1
        return id_val

    def _now_iso(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def _is_effective_at(
        self,
        membership: TeamMembership | ManagerMapping,
        as_of: Optional[str] = None,
    ) -> bool:
        """Check if a membership/mapping is effective at a given time.
        
        Args:
            membership: The membership or mapping to check
            as_of: ISO timestamp to check at (None = current time)
            
        Returns:
            True if the membership is effective at the given time
        """
        check_time = as_of or self._now_iso()
        
        # Check effective_from
        if membership.effective_from and check_time < membership.effective_from:
            return False
            
        # Check effective_to (None means currently active)
        if membership.effective_to and check_time >= membership.effective_to:
            return False
            
        return True

    def add_team_membership(
        self,
        canonical_id: str,
        team_id: str,
        role: str = "developer",
        allocation_percent: int = 100,
        effective_from: Optional[str] = None,
        effective_to: Optional[str] = None,
        confidence_score: float = CONFIDENCE_EMPLOYEE_DIRECTORY,
        provenance: str = "hr_system",
        evidence: Optional[list[str]] = None,
    ) -> TeamMembership:
        """Add a team membership for a developer.
        
        Args:
            canonical_id: The canonical developer ID
            team_id: The team identifier
            role: Role within the team (developer, senior_developer, tech_lead, etc.)
            allocation_percent: Percentage of time allocated (0-100)
            effective_from: When membership becomes effective (default: now)
            effective_to: When membership ends (None = currently active)
            confidence_score: Confidence in this mapping (0.0-1.0)
            provenance: Source system (hr_system, manual, jira, etc.)
            evidence: List of evidence strings
            
        Returns:
            The created TeamMembership record
        """
        now = self._now_iso()
        
        # Determine confidence label based on score
        if confidence_score >= 0.8:
            confidence_label = "high"
        elif confidence_score >= 0.5:
            confidence_label = "medium"
        else:
            confidence_label = "low"
        
        # Flag as ambiguous if low confidence
        ambiguity_flag = confidence_score < 0.5
        
        membership = TeamMembership(
            membership_id=self._generate_membership_id(),
            canonical_id=canonical_id,
            team_id=team_id,
            role=role,
            allocation_percent=allocation_percent,
            status="active" if not effective_to else "inactive",
            effective_from=effective_from or now,
            effective_to=effective_to,
            created_at=now,
            updated_at=now,
            confidence_score=confidence_score,
            confidence_label=confidence_label,  # type: ignore[arg-type]
            evidence=evidence or [],
            provenance=provenance,
            ambiguity_flag=ambiguity_flag,
            ambiguity_reasons=["Low confidence membership"] if ambiguity_flag else [],
            manual_review_required=ambiguity_flag,
        )
        
        # Store in developer's memberships
        if canonical_id not in self._memberships:
            self._memberships[canonical_id] = []
        self._memberships[canonical_id].append(membership)
        
        # Store in team's member list
        if team_id not in self._team_members:
            self._team_members[team_id] = []
        if canonical_id not in self._team_members[team_id]:
            self._team_members[team_id].append(canonical_id)
        
        return membership

    def add_manager_mapping(
        self,
        team_id: str,
        manager_canonical_id: str,
        manager_role: str = "engineering_manager",
        is_primary: bool = True,
        effective_from: Optional[str] = None,
        effective_to: Optional[str] = None,
        confidence_score: float = CONFIDENCE_EMPLOYEE_DIRECTORY,
        provenance: str = "hr_system",
        evidence: Optional[list[str]] = None,
    ) -> ManagerMapping:
        """Add a manager mapping for a team.
        
        Args:
            team_id: The team identifier
            manager_canonical_id: The canonical ID of the manager
            manager_role: Type of management role
            is_primary: Whether this is the primary manager
            effective_from: When mapping becomes effective (default: now)
            effective_to: When mapping ends (None = currently active)
            confidence_score: Confidence in this mapping (0.0-1.0)
            provenance: Source system
            evidence: List of evidence strings
            
        Returns:
            The created ManagerMapping record
        """
        now = self._now_iso()
        
        # Determine confidence label
        if confidence_score >= 0.8:
            confidence_label = "high"
        elif confidence_score >= 0.5:
            confidence_label = "medium"
        else:
            confidence_label = "low"
        
        mapping = ManagerMapping(
            mapping_id=self._generate_mapping_id(),
            team_id=team_id,
            manager_canonical_id=manager_canonical_id,
            manager_role=manager_role,  # type: ignore[arg-type]
            is_primary=is_primary,
            effective_from=effective_from or now,
            effective_to=effective_to,
            created_at=now,
            updated_at=now,
            confidence_score=confidence_score,
            confidence_label=confidence_label,  # type: ignore[arg-type]
            evidence=evidence or [],
            provenance=provenance,
            ambiguity_flag=False,
            ambiguity_reasons=[],
            manual_review_required=False,
        )
        
        # Store in team's manager mappings
        if team_id not in self._manager_mappings:
            self._manager_mappings[team_id] = []
        self._manager_mappings[team_id].append(mapping)
        
        return mapping

    def map_developer_to_teams(
        self,
        canonical_id: str,
        as_of: Optional[str] = None,
        active_only: bool = True,
    ) -> list[TeamMembership]:
        """Get all team memberships for a developer.
        
        Args:
            canonical_id: The canonical developer ID
            as_of: ISO timestamp for historical query (None = current time)
            active_only: If True, only return memberships with status="active"
            
        Returns:
            List of TeamMembership records, sorted by confidence (highest first)
        """
        if canonical_id not in self._memberships:
            return []
        
        memberships = self._memberships[canonical_id]
        
        # Filter by effectiveness at the given time
        effective_memberships = [
            m for m in memberships
            if self._is_effective_at(m, as_of)
        ]
        
        # Filter by status if requested
        if active_only:
            effective_memberships = [
                m for m in effective_memberships
                if m.status == "active"
            ]
        
        # Sort by confidence (highest first), then by effective_from (most recent first)
        return sorted(
            effective_memberships,
            key=lambda m: (-m.confidence_score, m.effective_from or "",),
        )

    def map_team_to_manager(
        self,
        team_id: str,
        as_of: Optional[str] = None,
        primary_only: bool = True,
    ) -> Optional[ManagerMapping]:
        """Get the manager for a team.
        
        Args:
            team_id: The team identifier
            as_of: ISO timestamp for historical query (None = current time)
            primary_only: If True, only consider primary managers
            
        Returns:
            The ManagerMapping with highest confidence, or None if no mapping found
        """
        if team_id not in self._manager_mappings:
            return None
        
        mappings = self._manager_mappings[team_id]
        
        # Filter by effectiveness
        effective_mappings = [
            m for m in mappings
            if self._is_effective_at(m, as_of)
        ]
        
        # Filter by primary flag if requested
        if primary_only:
            effective_mappings = [
                m for m in effective_mappings
                if m.is_primary
            ]
        
        if not effective_mappings:
            return None
        
        # Return the one with highest confidence
        return max(effective_mappings, key=lambda m: m.confidence_score)

    def get_developer_manager(
        self,
        canonical_id: str,
        as_of: Optional[str] = None,
    ) -> Optional[ManagerMapping]:
        """Get the manager for a developer through their team membership.
        
        This follows the chain: developer -> team -> manager
        
        Args:
            canonical_id: The canonical developer ID
            as_of: ISO timestamp for historical query (None = current time)
            
        Returns:
            ManagerMapping with confidence, or None if no manager found
        """
        # Get current team memberships
        memberships = self.map_developer_to_teams(canonical_id, as_of=as_of, active_only=True)
        
        if not memberships:
            return None
        
        # Get the primary team (highest confidence, highest allocation)
        primary_membership = max(
            memberships,
            key=lambda m: (m.confidence_score, m.allocation_percent),
        )
        
        # Get manager for that team
        manager = self.map_team_to_manager(
            primary_membership.team_id,
            as_of=as_of,
            primary_only=True,
        )
        
        return manager

    def is_team_member(
        self,
        canonical_id: str,
        team_id: str,
        as_of: Optional[str] = None,
    ) -> dict[str, Any]:
        """Check if a developer is a member of a specific team.
        
        Args:
            canonical_id: The canonical developer ID
            team_id: The team identifier
            as_of: ISO timestamp for historical query (None = current time)
            
        Returns:
            Dict with:
                - is_member: bool
                - membership: TeamMembership if found, None otherwise
                - evidence: list of evidence strings
        """
        memberships = self.map_developer_to_teams(canonical_id, as_of=as_of, active_only=False)
        
        for membership in memberships:
            if membership.team_id == team_id:
                return {
                    "is_member": True,
                    "membership": membership,
                    "evidence": membership.evidence,
                }
        
        return {
            "is_member": False,
            "membership": None,
            "evidence": [],
        }

    def get_team_members(
        self,
        team_id: str,
        active_only: bool = True,
        as_of: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get all members of a team.
        
        Args:
            team_id: The team identifier
            active_only: If True, only return active members
            as_of: ISO timestamp for historical query (None = current time)
            
        Returns:
            List of dicts with developer info and membership details:
                - canonical_id: str
                - membership: TeamMembership
                - role: str
                - confidence_score: float
        """
        members: list[dict[str, Any]] = []
        
        # Get all canonical IDs associated with this team
        candidate_ids = self._team_members.get(team_id, [])
        
        for canonical_id in candidate_ids:
            # Get effective memberships for this developer
            dev_memberships = self.map_developer_to_teams(
                canonical_id,
                as_of=as_of,
                active_only=False,  # We'll filter manually for this specific team
            )
            
            # Find membership for this specific team
            for membership in dev_memberships:
                if membership.team_id == team_id:
                    if active_only and membership.status != "active":
                        continue
                        
                    members.append({
                        "canonical_id": canonical_id,
                        "membership": membership,
                        "role": membership.role,
                        "confidence_score": membership.confidence_score,
                    })
                    break
        
        # Sort by confidence (highest first)
        return sorted(members, key=lambda m: -m["confidence_score"])

    def get_all_teams_for_manager(
        self,
        manager_canonical_id: str,
        as_of: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get all teams managed by a specific manager.
        
        Args:
            manager_canonical_id: The canonical ID of the manager
            as_of: ISO timestamp for historical query (None = current time)
            
        Returns:
            List of dicts with team_id and mapping details
        """
        teams: list[dict[str, Any]] = []
        
        for team_id, mappings in self._manager_mappings.items():
            # Find effective mappings for this manager
            effective_mappings = [
                m for m in mappings
                if m.manager_canonical_id == manager_canonical_id
                and self._is_effective_at(m, as_of)
            ]
            
            for mapping in effective_mappings:
                teams.append({
                    "team_id": team_id,
                    "mapping": mapping,
                    "is_primary": mapping.is_primary,
                    "confidence_score": mapping.confidence_score,
                })
        
        # Sort by primary first, then confidence
        return sorted(
            teams,
            key=lambda t: (-int(t["is_primary"]), -t["confidence_score"]),
        )

    def end_membership(
        self,
        canonical_id: str,
        team_id: str,
        effective_to: Optional[str] = None,
    ) -> bool:
        """End a team membership.
        
        Args:
            canonical_id: The canonical developer ID
            team_id: The team identifier
            effective_to: When membership ends (default: now)
            
        Returns:
            True if a membership was ended, False otherwise
        """
        now = self._now_iso()
        end_time = effective_to or now
        
        if canonical_id not in self._memberships:
            return False
        
        found = False
        for membership in self._memberships[canonical_id]:
            if (membership.team_id == team_id and 
                not membership.effective_to):  # Only end if currently active
                membership.effective_to = end_time
                membership.status = "inactive"
                membership.updated_at = now
                found = True
        
        return found

    def end_manager_mapping(
        self,
        team_id: str,
        manager_canonical_id: str,
        effective_to: Optional[str] = None,
    ) -> bool:
        """End a manager mapping.
        
        Args:
            team_id: The team identifier
            manager_canonical_id: The canonical ID of the manager
            effective_to: When mapping ends (default: now)
            
        Returns:
            True if a mapping was ended, False otherwise
        """
        now = self._now_iso()
        end_time = effective_to or now
        
        if team_id not in self._manager_mappings:
            return False
        
        found = False
        for mapping in self._manager_mappings[team_id]:
            if (mapping.manager_canonical_id == manager_canonical_id and
                not mapping.effective_to):  # Only end if currently active
                mapping.effective_to = end_time
                mapping.updated_at = now
                found = True
        
        return found

    def get_stats(self) -> dict[str, Any]:
        """Get mapper statistics."""
        total_memberships = sum(len(m) for m in self._memberships.values())
        total_mappings = sum(len(m) for m in self._manager_mappings.values())
        
        # Count active vs historical
        active_memberships = sum(
            1 for memberships in self._memberships.values()
            for m in memberships if not m.effective_to
        )
        
        return {
            "total_developers": len(self._memberships),
            "total_teams": len(self._team_members),
            "total_memberships": total_memberships,
            "active_memberships": active_memberships,
            "historical_memberships": total_memberships - active_memberships,
            "total_manager_mappings": total_mappings,
            "teams_with_managers": len(self._manager_mappings),
        }

    def get_org_stats(self) -> dict[str, Any]:
        """Alias for get_stats() - provides org-level statistics.
        
        Returns:
            Dictionary with organization mapping statistics
        """
        return self.get_stats()


def create_org_mapper(storage_provider: Any = None) -> OrgMapper:
    """Factory function to create an OrgMapper instance.
    
    Args:
        storage_provider: Optional storage backend for persistence
        
    Returns:
        Configured OrgMapper instance
    """
    return OrgMapper(storage_provider)
