"""
Work Item Resolution Engine.

Maps commits, pull requests, and issues to developers using multiple
signals with confidence scoring and ambiguity tracking.

This module provides the AttributionEngine class which consolidates
ownership evidence from multiple sources to make attribution decisions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from identity_resolution import IdentityResolver, SourceType


@dataclass
class OwnershipEvidence:
    """A single piece of evidence for ownership attribution."""

    evidence_type: str  # commit_author, pr_reviewer, jira_assignee, etc.
    source_system: str  # git, github, jira, etc.
    source_identifier: str  # email, username, etc.
    canonical_id: Optional[str] = None  # Resolved developer ID
    source_reference: str = ""  # commit SHA, PR number, etc.
    source_timestamp: Optional[str] = None
    weight: float = 0.5  # 0.0 to 1.0
    confidence: float = 0.8
    evidence_details: list[str] = field(default_factory=list)


@dataclass
class AttributionDecision:
    """A decision about which developer owns/is responsible for a work item."""

    decision_id: str
    work_item_id: str
    work_item_type: str  # commit, pull_request, issue, etc.
    canonical_id: str
    ownership_factors: list[str] = field(default_factory=list)
    ownership_score: float = 0.5
    decision_type: str = "automatic"  # automatic, manual, hybrid, inferred
    confidence_score: float = 0.5
    confidence_label: str = "medium"  # high, medium, low
    evidence: list[OwnershipEvidence] = field(default_factory=list)
    effective_from: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    effective_to: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: str = "attribution_engine"
    ambiguity_flag: bool = False
    ambiguity_reasons: list[str] = field(default_factory=list)
    manual_review_required: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None


@dataclass
class AmbiguityRecord:
    """Tracks unresolved ambiguous mappings."""

    ambiguity_id: str
    work_item_id: str
    work_item_type: str
    ambiguity_type: str  # multiple_contributors, unknown_author, etc.
    possible_canonical_ids: list[str] = field(default_factory=list)
    source_identifiers: list[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_review, resolved, escalated, deferred
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence_score: float = 0.3
    confidence_label: str = "low"
    evidence: list[str] = field(default_factory=list)
    provenance: str = "attribution_engine"
    ambiguity_reasons: list[str] = field(default_factory=list)
    manual_review_required: bool = True
    assigned_reviewer: Optional[str] = None
    priority: str = "medium"  # low, medium, high, critical


class AttributionEngine:
    """Main engine for attributing work items to developers.

    Uses multiple signals with weighted scoring:
    - Commit authorship (highest weight: 1.0)
    - PR authorship (high weight: 0.9)
    - Code review activity (medium weight: 0.6)
    - Jira assignment (medium weight: 0.7)
    - Merge activity (medium weight: 0.5)

    Conflict resolution:
    - Disagreement between sources lowers confidence
    - Cross-source agreement boosts confidence
    - Ambiguous cases are flagged for manual review
    """

    # Weight constants for different evidence types
    WEIGHTS = {
        "commit_author": 1.0,
        "commit_committer": 0.8,
        "pr_author": 0.9,
        "pr_merger": 0.5,
        "pr_reviewer": 0.6,
        "pr_approver": 0.7,
        "jira_assignee": 0.7,
        "jira_reporter": 0.5,
        "jira_commenter": 0.4,
        "issue_assignee": 0.7,
        "code_owner": 0.85,
        "file_path_pattern": 0.3,
        "review_approval": 0.7,
        "time_correlation": 0.4,
        "manual_assignment": 1.0,
        "inferred_from_team": 0.2,
    }

    def __init__(self, identity_resolver: Optional[IdentityResolver] = None):
        """Initialize the attribution engine.

        Args:
            identity_resolver: Optional identity resolver for mapping
                              source identifiers to canonical IDs.
        """
        self._resolver = identity_resolver or IdentityResolver()
        self._decisions: dict[str, AttributionDecision] = {}
        self._ambiguities: dict[str, AmbiguityRecord] = {}
        self._next_decision_id = 1
        self._next_ambiguity_id = 1

    def _generate_decision_id(self) -> str:
        """Generate a unique decision ID."""
        id_val = f"decision-{self._next_decision_id:06d}"
        self._next_decision_id += 1
        return id_val

    def _generate_ambiguity_id(self) -> str:
        """Generate a unique ambiguity ID."""
        id_val = f"ambiguity-{self._next_ambiguity_id:06d}"
        self._next_ambiguity_id += 1
        return id_val

    def attribute_work_item(
        self,
        work_item_id: str,
        work_item_type: str,
        commit_data: Optional[dict[str, Any]] = None,
        pr_data: Optional[dict[str, Any]] = None,
        issue_data: Optional[dict[str, Any]] = None,
    ) -> AttributionDecision:
        """Attribute a work item to a developer.

        Args:
            work_item_id: Unique identifier for the work item
            work_item_type: Type of work item (commit, pull_request, issue, etc.)
            commit_data: Optional commit metadata with author/committer info
            pr_data: Optional PR metadata with author/reviewer info
            issue_data: Optional issue metadata with assignee/reporter info

        Returns:
            AttributionDecision with resolved developer and confidence scores
        """
        evidence_list: list[OwnershipEvidence] = []

        # Extract evidence from commit data
        if commit_data:
            commit_evidence = self._extract_commit_evidence(commit_data)
            evidence_list.extend(commit_evidence)

        # Extract evidence from PR data
        if pr_data:
            pr_evidence = self._extract_pr_evidence(pr_data)
            evidence_list.extend(pr_evidence)

        # Extract evidence from issue data
        if issue_data:
            issue_evidence = self._extract_issue_evidence(issue_data)
            evidence_list.extend(issue_evidence)

        # Resolve canonical IDs for all evidence
        for evidence in evidence_list:
            if evidence.source_identifier:
                # Try to resolve to canonical ID
                dev = self._resolver.get_developer_by_email(evidence.source_identifier)
                if not dev:
                    # Try alias lookup
                    for src_type in [SourceType.GIT, SourceType.GITHUB, SourceType.JIRA]:
                        dev = self._resolver.get_developer_by_alias(src_type, evidence.source_identifier)
                        if dev:
                            break
                if dev:
                    evidence.canonical_id = dev.id

        # Calculate weighted ownership scores
        canonical_scores: dict[str, float] = {}
        canonical_evidence: dict[str, list[OwnershipEvidence]] = {}

        for evidence in evidence_list:
            if not evidence.canonical_id:
                continue

            cid = evidence.canonical_id
            weight = evidence.weight

            if cid not in canonical_scores:
                canonical_scores[cid] = 0.0
                canonical_evidence[cid] = []

            canonical_scores[cid] += weight
            canonical_evidence[cid].append(evidence)

        # Make attribution decision
        if not canonical_scores:
            # No valid attribution - create ambiguity record
            return self._create_ambiguous_decision(
                work_item_id, work_item_type, evidence_list, "unknown_author"
            )

        # Sort by score
        sorted_canonical = sorted(canonical_scores.items(), key=lambda x: x[1], reverse=True)

        if len(sorted_canonical) == 1:
            # Single clear owner
            canonical_id = sorted_canonical[0][0]
            score = sorted_canonical[0][1]
            confidence = self._calculate_confidence(score, canonical_evidence[canonical_id])

            decision = AttributionDecision(
                decision_id=self._generate_decision_id(),
                work_item_id=work_item_id,
                work_item_type=work_item_type,
                canonical_id=canonical_id,
                ownership_factors=[e.evidence_type for e in canonical_evidence[canonical_id]],
                ownership_score=min(1.0, score),
                confidence_score=confidence,
                confidence_label=self._confidence_label(confidence),
                evidence=canonical_evidence[canonical_id],
            )
            self._decisions[decision.decision_id] = decision
            return decision

        # Multiple candidates - check for conflicts
        top_candidate = sorted_canonical[0]
        second_candidate = sorted_canonical[1] if len(sorted_canonical) > 1 else None

        # If top candidate is significantly ahead, attribute to them
        if second_candidate is None or top_candidate[1] > second_candidate[1] * 1.5:
            canonical_id = top_candidate[0]
            score = top_candidate[1]
            confidence = self._calculate_confidence(score, canonical_evidence[canonical_id])

            decision = AttributionDecision(
                decision_id=self._generate_decision_id(),
                work_item_id=work_item_id,
                work_item_type=work_item_type,
                canonical_id=canonical_id,
                ownership_factors=[e.evidence_type for e in canonical_evidence[canonical_id]],
                ownership_score=min(1.0, score),
                confidence_score=confidence,
                confidence_label=self._confidence_label(confidence),
                evidence=canonical_evidence[canonical_id],
            )
            self._decisions[decision.decision_id] = decision
            return decision

        # Multiple strong candidates - ambiguous case
        possible_ids = [cid for cid, _ in sorted_canonical]
        return self._create_ambiguous_decision(
            work_item_id,
            work_item_type,
            evidence_list,
            "multiple_contributors",
            possible_ids,
        )

    def _extract_commit_evidence(self, commit_data: dict[str, Any]) -> list[OwnershipEvidence]:
        """Extract ownership evidence from commit metadata."""
        evidence = []

        # Author evidence (highest weight)
        author_email = commit_data.get("author_email") or commit_data.get("author", {}).get("email")
        if author_email:
            evidence.append(
                OwnershipEvidence(
                    evidence_type="commit_author",
                    source_system="git",
                    source_identifier=author_email,
                    source_reference=commit_data.get("commit_id", commit_data.get("sha", "")),
                    source_timestamp=commit_data.get("timestamp") or commit_data.get("date"),
                    weight=self.WEIGHTS["commit_author"],
                    confidence=0.95,
                    evidence_details=[f"Commit authored by {author_email}"],
                )
            )

        # Committer evidence
        committer_email = commit_data.get("committer_email") or commit_data.get("committer", {}).get("email")
        if committer_email and committer_email != author_email:
            evidence.append(
                OwnershipEvidence(
                    evidence_type="commit_committer",
                    source_system="git",
                    source_identifier=committer_email,
                    source_reference=commit_data.get("commit_id", commit_data.get("sha", "")),
                    source_timestamp=commit_data.get("timestamp") or commit_data.get("date"),
                    weight=self.WEIGHTS["commit_committer"],
                    confidence=0.85,
                    evidence_details=[f"Commit committed by {committer_email}"],
                )
            )

        return evidence

    def _extract_pr_evidence(self, pr_data: dict[str, Any]) -> list[OwnershipEvidence]:
        """Extract ownership evidence from PR metadata."""
        evidence = []

        # PR author
        pr_author = pr_data.get("author") or pr_data.get("user", {}).get("login")
        if pr_author:
            evidence.append(
                OwnershipEvidence(
                    evidence_type="pr_author",
                    source_system="github",
                    source_identifier=pr_author,
                    source_reference=str(pr_data.get("pr_number", pr_data.get("number", ""))),
                    source_timestamp=pr_data.get("created_at"),
                    weight=self.WEIGHTS["pr_author"],
                    confidence=0.9,
                    evidence_details=[f"PR authored by {pr_author}"],
                )
            )

        # PR merger
        merger = pr_data.get("merged_by") or pr_data.get("merger")
        if merger:
            evidence.append(
                OwnershipEvidence(
                    evidence_type="pr_merger",
                    source_system="github",
                    source_identifier=merger,
                    source_reference=str(pr_data.get("pr_number", pr_data.get("number", ""))),
                    source_timestamp=pr_data.get("merged_at"),
                    weight=self.WEIGHTS["pr_merger"],
                    confidence=0.7,
                    evidence_details=[f"PR merged by {merger}"],
                )
            )

        # PR reviewers
        reviewers = pr_data.get("reviewers", [])
        if isinstance(reviewers, list):
            for reviewer in reviewers:
                reviewer_id = reviewer if isinstance(reviewer, str) else reviewer.get("login")
                if reviewer_id:
                    evidence.append(
                        OwnershipEvidence(
                            evidence_type="pr_reviewer",
                            source_system="github",
                            source_identifier=reviewer_id,
                            source_reference=str(pr_data.get("pr_number", pr_data.get("number", ""))),
                            weight=self.WEIGHTS["pr_reviewer"],
                            confidence=0.6,
                            evidence_details=[f"PR reviewed by {reviewer_id}"],
                        )
                    )

        # Approvers
        approvers = pr_data.get("approvers", [])
        if isinstance(approvers, list):
            for approver in approvers:
                approver_id = approver if isinstance(approver, str) else approver.get("login")
                if approver_id:
                    evidence.append(
                        OwnershipEvidence(
                            evidence_type="pr_approver",
                            source_system="github",
                            source_identifier=approver_id,
                            source_reference=str(pr_data.get("pr_number", pr_data.get("number", ""))),
                            weight=self.WEIGHTS["pr_approver"],
                            confidence=0.7,
                            evidence_details=[f"PR approved by {approver_id}"],
                        )
                    )

        return evidence

    def _extract_issue_evidence(self, issue_data: dict[str, Any]) -> list[OwnershipEvidence]:
        """Extract ownership evidence from issue metadata."""
        evidence = []

        # Assignee
        assignee = issue_data.get("assignee_email") or issue_data.get("assignee")
        if assignee:
            evidence.append(
                OwnershipEvidence(
                    evidence_type="jira_assignee",
                    source_system="jira",
                    source_identifier=assignee,
                    source_reference=issue_data.get("issue_id", issue_data.get("key", "")),
                    weight=self.WEIGHTS["jira_assignee"],
                    confidence=0.7,
                    evidence_details=[f"Issue assigned to {assignee}"],
                )
            )

        # Reporter
        reporter = issue_data.get("reporter_email") or issue_data.get("reporter")
        if reporter:
            evidence.append(
                OwnershipEvidence(
                    evidence_type="jira_reporter",
                    source_system="jira",
                    source_identifier=reporter,
                    source_reference=issue_data.get("issue_id", issue_data.get("key", "")),
                    weight=self.WEIGHTS["jira_reporter"],
                    confidence=0.5,
                    evidence_details=[f"Issue reported by {reporter}"],
                )
            )

        return evidence

    def _calculate_confidence(self, score: float, evidence: list[OwnershipEvidence]) -> float:
        """Calculate confidence score based on evidence."""
        base_confidence = min(1.0, score * 0.8)  # Scale down a bit

        # Boost for multiple corroborating sources
        source_types = set(e.source_system for e in evidence)
        if len(source_types) > 1:
            base_confidence = min(1.0, base_confidence * 1.1)

        # Boost for high-confidence evidence
        high_confidence_count = sum(1 for e in evidence if e.confidence >= 0.9)
        if high_confidence_count >= 2:
            base_confidence = min(1.0, base_confidence * 1.05)

        return round(base_confidence, 2)

    def _confidence_label(self, score: float) -> str:
        """Convert score to human-readable label."""
        if score >= 0.8:
            return "high"
        elif score >= 0.5:
            return "medium"
        return "low"

    def _create_ambiguous_decision(
        self,
        work_item_id: str,
        work_item_type: str,
        evidence: list[OwnershipEvidence],
        ambiguity_type: str,
        possible_ids: Optional[list[str]] = None,
    ) -> AttributionDecision:
        """Create an ambiguous attribution decision."""
        ambiguity_id = self._generate_ambiguity_id()

        # Extract source identifiers from evidence
        source_ids = [e.source_identifier for e in evidence if e.source_identifier]

        # Get unique possible canonical IDs
        possible = possible_ids or []
        if not possible:
            possible = list(set(e.canonical_id for e in evidence if e.canonical_id))

        ambiguity = AmbiguityRecord(
            ambiguity_id=ambiguity_id,
            work_item_id=work_item_id,
            work_item_type=work_item_type,
            ambiguity_type=ambiguity_type,
            possible_canonical_ids=possible,
            source_identifiers=source_ids,
            ambiguity_reasons=[f"Ambiguous attribution: {ambiguity_type}"],
        )
        self._ambiguities[ambiguity_id] = ambiguity

        # Create a low-confidence decision pointing to first possible or unknown
        canonical_id = possible[0] if possible else "unknown"

        return AttributionDecision(
            decision_id=self._generate_decision_id(),
            work_item_id=work_item_id,
            work_item_type=work_item_type,
            canonical_id=canonical_id,
            ownership_factors=[],
            ownership_score=0.3,
            confidence_score=0.3,
            confidence_label="low",
            evidence=evidence,
            ambiguity_flag=True,
            ambiguity_reasons=ambiguity.ambiguity_reasons,
            manual_review_required=True,
        )

    def get_attribution_trace(self, work_item_id: str) -> Optional[dict[str, Any]]:
        """Get the full attribution trace for a work item."""
        # Find decision for this work item
        for decision in self._decisions.values():
            if decision.work_item_id == work_item_id:
                return {
                    "work_item_id": work_item_id,
                    "work_item_type": decision.work_item_type,
                    "attributed_to": decision.canonical_id,
                    "confidence": decision.confidence_score,
                    "confidence_label": decision.confidence_label,
                    "decision_type": decision.decision_type,
                    "ownership_score": decision.ownership_score,
                    "ownership_factors": decision.ownership_factors,
                    "ambiguity_flag": decision.ambiguity_flag,
                    "ambiguity_reasons": decision.ambiguity_reasons,
                    "evidence": [
                        {
                            "type": e.evidence_type,
                            "source_system": e.source_system,
                            "source_identifier": e.source_identifier,
                            "canonical_id": e.canonical_id,
                            "source_reference": e.source_reference,
                            "weight": e.weight,
                            "confidence": e.confidence,
                            "details": e.evidence_details,
                        }
                        for e in decision.evidence
                    ],
                    "created_at": decision.created_at,
                    "manual_review_required": decision.manual_review_required,
                }
        return None

    def get_ambiguity_queue(self, status: Optional[str] = None) -> list[AmbiguityRecord]:
        """Get ambiguity records, optionally filtered by status."""
        records = list(self._ambiguities.values())
        if status:
            records = [r for r in records if r.status == status]
        return records

    def resolve_ambiguity(
        self,
        ambiguity_id: str,
        canonical_id: str,
        resolved_by: str,
        resolution_notes: Optional[str] = None,
    ) -> bool:
        """Manually resolve an ambiguous attribution."""
        if ambiguity_id not in self._ambiguities:
            return False

        ambiguity = self._ambiguities[ambiguity_id]
        ambiguity.status = "resolved"
        ambiguity.resolved_by = resolved_by
        ambiguity.resolved_at = datetime.now(timezone.utc).isoformat()
        ambiguity.resolution = resolution_notes or f"Resolved to {canonical_id}"

        # Create a new manual decision
        decision = AttributionDecision(
            decision_id=self._generate_decision_id(),
            work_item_id=ambiguity.work_item_id,
            work_item_type=ambiguity.work_item_type,
            canonical_id=canonical_id,
            decision_type="manual",
            confidence_score=0.95,
            confidence_label="high",
            manual_review_required=False,
            reviewed_by=resolved_by,
            reviewed_at=ambiguity.resolved_at,
        )
        self._decisions[decision.decision_id] = decision

        return True

    def get_attribution_history(self, canonical_id: str) -> list[AttributionDecision]:
        """Get all work items attributed to a developer."""
        return [d for d in self._decisions.values() if d.canonical_id == canonical_id]

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_decisions": len(self._decisions),
            "ambiguous_decisions": sum(1 for d in self._decisions.values() if d.ambiguity_flag),
            "pending_ambiguities": sum(1 for a in self._ambiguities.values() if a.status == "pending"),
            "resolved_ambiguities": sum(1 for a in self._ambiguities.values() if a.status == "resolved"),
        }


def create_attribution_engine(identity_resolver: Optional[IdentityResolver] = None) -> AttributionEngine:
    """Factory function to create an AttributionEngine instance."""
    return AttributionEngine(identity_resolver)
