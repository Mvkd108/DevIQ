"""
Ownership Graph Module

Implements ownership calculation and analysis for files, modules, and components.
Provides weighted ownership factors including recency, volume, concentration,
review participation, and continuity analysis.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from schemas import OwnershipEvidence, CanonicalDeveloper


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO timestamp string into a datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def normalize_spaces(text: str) -> str:
    """Normalize whitespace in text."""
    return " ".join(str(text or "").split())


def event_actor(event: dict[str, Any]) -> str:
    """Extract the actor/developer from an event."""
    return normalize_spaces(
        str(event.get("author") or event.get("developer_id") or event.get("author_email") or "Unknown contributor")
    ) or "Unknown contributor"


def calculate_gini_coefficient(values: list[float]) -> float:
    """
    Calculate the Gini coefficient for measuring contribution concentration.
    0 = perfect equality (equal contributions), 1 = perfect inequality (one person does everything).
    """
    if not values or len(values) == 0:
        return 0.0
    
    n = len(values)
    if n == 1:
        return 0.0
    
    sorted_values = sorted(values)
    mean_value = sum(sorted_values) / n
    
    if mean_value == 0:
        return 0.0
    
    # Gini coefficient formula: (2 * sum(i * y_i)) / (n * sum(y_i)) - (n + 1) / n
    cumsum = sum((i + 1) * y for i, y in enumerate(sorted_values))
    gini = (2 * cumsum) / (n * sum(sorted_values)) - (n + 1) / n
    
    return round(gini, 3)


def calculate_recency_weight(timestamp: Optional[str], reference_time: Optional[datetime] = None, half_life_days: float = 30.0) -> float:
    """
    Calculate exponential decay weight based on recency.
    More recent commits get higher weights.
    
    Args:
        timestamp: ISO timestamp string
        reference_time: Reference time for recency calculation (defaults to now)
        half_life_days: Number of days for weight to decay to 50%
    
    Returns:
        Weight value between 0 and 1
    """
    event_time = parse_datetime(timestamp)
    if event_time is None:
        return 0.5  # Neutral weight for unknown timestamps
    
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    
    # Handle naive vs aware datetime comparison
    if event_time.tzinfo is None and reference_time.tzinfo is not None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    elif event_time.tzinfo is not None and reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    
    days_diff = (reference_time - event_time).total_seconds() / (24 * 3600)
    
    if days_diff < 0:
        days_diff = 0  # Future events treated as present
    
    # Exponential decay: weight = 0.5 ^ (days / half_life)
    weight = math.pow(0.5, days_diff / half_life_days)
    return round(weight, 3)


def calculate_bus_factor(sorted_contributors: list[tuple[str, float]], threshold: float = 0.7) -> int:
    """
    Calculate the bus factor - minimum number of people needed to cover threshold % of work.
    
    Args:
        sorted_contributors: List of (developer_id, contribution) sorted by contribution desc
        threshold: Coverage threshold (default 70%)
    
    Returns:
        Bus factor (minimum contributors needed for threshold coverage)
    """
    if not sorted_contributors:
        return 0
    
    total_contribution = sum(c[1] for c in sorted_contributors)
    if total_contribution == 0:
        return 0
    
    target = total_contribution * threshold
    cumulative = 0.0
    
    for i, (_, contribution) in enumerate(sorted_contributors, start=1):
        cumulative += contribution
        if cumulative >= target:
            return i
    
    return len(sorted_contributors)


class OwnershipGraph:
    """
    Calculates and tracks ownership for files, modules, and components.
    
    Provides weighted ownership analysis including:
    - Recency-weighted contributions
    - Code churn volume
    - Contribution concentration (Gini coefficient)
    - Review participation
    - Continuity/bus factor analysis
    """
    
    def __init__(
        self,
        events: Optional[list[dict[str, Any]]] = None,
        identity_resolver: Any = None,
        attribution_engine: Any = None,
    ):
        """
        Initialize the ownership graph.
        
        Args:
            events: Optional list of events to process (primary input)
            identity_resolver: Optional identity resolver for developer lookup
            attribution_engine: Optional attribution engine for work item resolution
        """
        self.events = events or []
        self._identity_resolver = identity_resolver
        self._attribution_engine = attribution_engine
        self._file_contributions: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        self._module_contributions: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        self._developer_profiles: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "commits": [],
            "reviews_given": [],
            "reviews_received": [],
            "modules_touched": set(),
            "files_touched": set(),
        })
        self._processed = False
    
    def process_events(self, events: Optional[list[dict[str, Any]]] = None) -> None:
        """
        Process events to build ownership data structures.
        
        Args:
            events: List of events to process (uses events from constructor if not provided)
        """
        if events is not None:
            self.events = events
        
        if not self.events:
            return
        
        # Find reference time (latest event timestamp)
        timestamps = [parse_datetime(e.get("timestamp")) for e in self.events]
        timestamps = [t for t in timestamps if t is not None]
        self._reference_time = max(timestamps) if timestamps else datetime.now(timezone.utc)
        
        for event in self.events:
            actor = event_actor(event)
            timestamp = event.get("timestamp")
            
            # Process file-level contributions
            files = event.get("files_changed", []) or []
            if isinstance(files, list):
                for file_info in files:
                    if isinstance(file_info, dict):
                        file_path = file_info.get("path") or file_info.get("filename")
                    else:
                        file_path = str(file_info)
                    
                    if file_path:
                        self._file_contributions[file_path][actor].append({
                            "timestamp": timestamp,
                            "changes": file_info.get("changes", 0) if isinstance(file_info, dict) else 0,
                            "event": event,
                        })
                        self._developer_profiles[actor]["files_touched"].add(file_path)
            
            # Process module-level contributions
            modules = event.get("modules_touched", []) or []
            for module in modules:
                if module:
                    self._module_contributions[module][actor].append({
                        "timestamp": timestamp,
                        "event": event,
                    })
                    self._developer_profiles[actor]["modules_touched"].add(module)
            
            # Track commits
            if event.get("commit_id"):
                self._developer_profiles[actor]["commits"].append({
                    "commit_id": event.get("commit_id"),
                    "timestamp": timestamp,
                    "message": event.get("message", ""),
                })
            
            # Track reviews
            if event.get("review_given_to"):
                for reviewed_dev in event.get("review_given_to", []):
                    self._developer_profiles[actor]["reviews_given"].append({
                        "to": reviewed_dev,
                        "timestamp": timestamp,
                    })
                    self._developer_profiles[reviewed_dev]["reviews_received"].append({
                        "from": actor,
                        "timestamp": timestamp,
                    })
        
        self._processed = True
    
    def calculate_file_ownership(self, file_path: str, events: Optional[list[dict[str, Any]]] = None) -> OwnershipEvidence:
        """
        Calculate ownership evidence for a specific file.
        
        Args:
            file_path: Path to the file
            events: Optional events to process (uses processed events if not provided)
        
        Returns:
            OwnershipEvidence for the file
        """
        if events is not None:
            self.process_events(events)
        elif not self._processed:
            self.process_events()
        
        contributions = self._file_contributions.get(file_path, {})
        
        if not contributions:
            return OwnershipEvidence(
                evidence_id=f"file-{file_path}-no-evidence",
                decision_id=f"file-{file_path}",
                evidence_type="file_path_pattern",
                source_identifier="unknown",
                canonical_id="unknown",
                weight=0.0,
                source_system="ownership_graph",
                source_reference=file_path,
                confidence_score=0.1,
                confidence_label="low",
                evidence=["No contribution data available for this file"],
                provenance="inferred",
                ambiguity_flag=True,
                ambiguity_reasons=["No events found touching this file"],
            )
        
        # Calculate weighted contributions
        weighted_scores: dict[str, float] = {}
        for developer, dev_contributions in contributions.items():
            total_weight = 0.0
            for contrib in dev_contributions:
                recency = calculate_recency_weight(contrib["timestamp"], self._reference_time)
                volume = max(1.0, contrib["changes"] / 10)  # Normalize changes
                total_weight += recency * volume
            weighted_scores[developer] = total_weight
        
        # Sort by weighted score
        sorted_contributors = sorted(weighted_scores.items(), key=lambda x: x[1], reverse=True)
        primary_owner = sorted_contributors[0][0] if sorted_contributors else "unknown"
        primary_score = sorted_contributors[0][1] if sorted_contributors else 0.0
        
        total_score = sum(weighted_scores.values())
        ownership_share = (primary_score / total_score * 100) if total_score > 0 else 0.0
        
        # Calculate concentration
        shares = [score / total_score * 100 for score in weighted_scores.values()] if total_score > 0 else []
        gini = calculate_gini_coefficient([s / 100 for s in shares])
        
        # Calculate bus factor
        bus_factor = calculate_bus_factor(sorted_contributors)
        
        # Determine confidence
        confidence = 0.7 if len(contributions) >= 2 else 0.5
        if ownership_share > 70:
            confidence -= 0.1  # Lower confidence for highly concentrated ownership
        
        return OwnershipEvidence(
            evidence_id=f"file-{file_path}-ownership",
            decision_id=f"file-{file_path}",
            evidence_type="commit_author",
            source_identifier=primary_owner,
            canonical_id=primary_owner,
            weight=min(1.0, ownership_share / 100),
            source_system="git",
            source_reference=file_path,
            source_timestamp=None,
            confidence_score=round(confidence, 2),
            confidence_label="high" if confidence >= 0.8 else "medium" if confidence >= 0.5 else "low",
            evidence=[
                f"{len(contributions)} contributors to this file",
                f"Primary owner: {primary_owner} with {ownership_share:.1f}% ownership",
                f"Ownership concentration (Gini): {gini:.3f}",
                f"Bus factor: {bus_factor}",
            ],
            provenance="git",
            ambiguity_flag=len(contributions) > 3 and ownership_share < 40,
            ambiguity_reasons=["Shared ownership across multiple contributors"] if len(contributions) > 3 and ownership_share < 40 else [],
        )
    
    def calculate_module_ownership(self, module_name: str, events: Optional[list[dict[str, Any]]] = None) -> list[OwnershipEvidence]:
        """
        Calculate ownership evidence for a module.
        
        Args:
            module_name: Name of the module
            events: Optional events to process
        
        Returns:
            List of OwnershipEvidence (one per significant contributor)
        """
        if events is not None:
            self.process_events(events)
        elif not self._processed:
            self.process_events()
        
        contributions = self._module_contributions.get(module_name, {})
        
        if not contributions:
            return []
        
        # Calculate weighted scores
        weighted_scores: dict[str, dict[str, Any]] = {}
        for developer, dev_contributions in contributions.items():
            recency_sum = 0.0
            commit_count = len(dev_contributions)
            
            for contrib in dev_contributions:
                recency = calculate_recency_weight(contrib["timestamp"], self._reference_time)
                recency_sum += recency
            
            # Get churn from events
            total_churn = 0
            for contrib in dev_contributions:
                event = contrib["event"]
                total_churn += event.get("total_changes", 0)
            
            weighted_scores[developer] = {
                "recency_score": recency_sum,
                "commit_count": commit_count,
                "churn": total_churn,
            }
        
        # Calculate final ownership weights
        total_recency = sum(s["recency_score"] for s in weighted_scores.values())
        total_churn = sum(s["churn"] for s in weighted_scores.values())
        
        results: list[OwnershipEvidence] = []
        for developer, scores in weighted_scores.items():
            recency_share = (scores["recency_score"] / total_recency * 100) if total_recency > 0 else 0
            churn_share = (scores["churn"] / total_churn * 100) if total_churn > 0 else 0
            
            # Combined weight: 60% recency, 40% volume
            combined_weight = (recency_share * 0.6 + churn_share * 0.4) / 100
            
            evidence = OwnershipEvidence(
                evidence_id=f"module-{module_name}-{developer}",
                decision_id=f"module-{module_name}",
                evidence_type="commit_author",
                source_identifier=developer,
                canonical_id=developer,
                weight=round(min(1.0, combined_weight), 3),
                source_system="git",
                source_reference=module_name,
                confidence_score=0.7 if scores["commit_count"] >= 3 else 0.5,
                confidence_label="high" if scores["commit_count"] >= 5 else "medium" if scores["commit_count"] >= 2 else "low",
                evidence=[
                    f"{scores['commit_count']} commits to {module_name}",
                    f"{scores['churn']} lines changed",
                    f"Recency-weighted share: {recency_share:.1f}%",
                ],
                provenance="git",
            )
            results.append(evidence)
        
        # Sort by weight descending
        results.sort(key=lambda x: x.weight, reverse=True)
        return results
    
    def compute_ownership_weights(
        self,
        recency: float,
        commit_count: int,
        churn: int,
        review_participation: int,
    ) -> dict[str, float]:
        """
        Compute weighted ownership factors.
        
        Args:
            recency: Recency score (0-1, higher = more recent)
            commit_count: Number of commits
            churn: Lines of code changed
            review_participation: Number of reviews given to others in this area
        
        Returns:
            Dictionary of weighted factors
        """
        # Normalize inputs
        normalized_recency = min(1.0, recency)
        normalized_commits = min(1.0, commit_count / 10)  # Cap at 10 commits
        normalized_churn = min(1.0, churn / 500)  # Cap at 500 lines
        normalized_reviews = min(1.0, review_participation / 5)  # Cap at 5 reviews
        
        # Apply weights
        weights = {
            "recency": round(normalized_recency * 0.30, 3),
            "volume_commits": round(normalized_commits * 0.25, 3),
            "volume_churn": round(normalized_churn * 0.25, 3),
            "review_participation": round(normalized_reviews * 0.20, 3),
        }
        
        weights["total"] = round(sum(weights.values()), 3)
        
        return weights
    
    def get_primary_owner(self, target_path: str) -> tuple[CanonicalDeveloper, float]:
        """
        Get the primary owner of a file or module with confidence score.
        
        Args:
            target_path: File path or module name
        
        Returns:
            Tuple of (CanonicalDeveloper, confidence_score)
        """
        if not self._processed:
            self.process_events()
        
        # Determine if it's a file or module
        is_file = "." in target_path or "/" in target_path
        
        if is_file:
            evidence = self.calculate_file_ownership(target_path)
        else:
            module_evidence = self.calculate_module_ownership(target_path)
            evidence = module_evidence[0] if module_evidence else None
        
        if evidence is None or evidence.canonical_id == "unknown":
            return (
                CanonicalDeveloper(
                    canonical_id="unknown",
                    display_name="Unknown Owner",
                    status="inactive",
                ),
                0.0,
            )
        
        developer = CanonicalDeveloper(
            canonical_id=evidence.canonical_id,
            display_name=evidence.canonical_id,  # Use ID as display name for now
            primary_email=f"{evidence.canonical_id.lower().replace(' ', '.')}@example.com",
            status="active",
        )
        
        return developer, evidence.confidence_score
    
    def get_all_owners(self, target_path: str, min_confidence: float = 0.3) -> list[dict[str, Any]]:
        """
        Get all owners of a file or module with their ownership shares.
        
        Args:
            target_path: File path or module name
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of owner dictionaries with shares
        """
        if not self._processed:
            self.process_events()
        
        is_file = "." in target_path or "/" in target_path
        
        if is_file:
            evidence = self.calculate_file_ownership(target_path)
            # For files, we need to get all contributors from internal data
            contributions = self._file_contributions.get(target_path, {})
        else:
            contributions = self._module_contributions.get(target_path, {})
        
        if not contributions:
            return []
        
        # Calculate weighted scores for all contributors
        weighted_scores: dict[str, float] = {}
        for developer, dev_contributions in contributions.items():
            total_weight = 0.0
            for contrib in dev_contributions:
                recency = calculate_recency_weight(contrib.get("timestamp"), self._reference_time)
                total_weight += recency
            weighted_scores[developer] = total_weight
        
        total_score = sum(weighted_scores.values())
        
        # Build owner list
        owners = []
        for developer, score in sorted(weighted_scores.items(), key=lambda x: (x[1], x[0]), reverse=True):
            share = (score / total_score * 100) if total_score > 0 else 0
            confidence = min(1.0, score / (total_score / len(weighted_scores))) if total_score > 0 else 0
            
            if confidence >= min_confidence:
                owners.append({
                    "developer_id": developer,
                    "display_name": developer,
                    "ownership_share_pct": round(share, 1),
                    "confidence": round(confidence, 2),
                    "contributions": len(contributions[developer]),
                })
        
        return owners
    
    def detect_ownership_risk(self, target_path: str) -> dict[str, Any]:
        """
        Detect ownership risk for a file or module.
        
        Args:
            target_path: File path or module name
        
        Returns:
            Risk assessment dictionary with backup gap and recommendations
        """
        if not self._processed:
            self.process_events()
        
        owners = self.get_all_owners(target_path)
        
        if not owners:
            return {
                "target": target_path,
                "risk_level": "high",
                "risk_score": 100,
                "primary_owner": None,
                "backup_gap_pct": 100,
                "bus_factor": 0,
                "recommendation": "No ownership data available - immediate attention required",
            }
        
        primary = owners[0]
        secondary = owners[1] if len(owners) > 1 else None
        
        primary_share = primary["ownership_share_pct"]
        secondary_share = secondary["ownership_share_pct"] if secondary else 0.0
        backup_gap = primary_share - secondary_share
        
        # Calculate bus factor
        is_file = "." in target_path or "/" in target_path
        contributions = self._file_contributions.get(target_path, {}) if is_file else self._module_contributions.get(target_path, {})
        
        sorted_contributors = sorted(
            [(dev, len(contribs)) for dev, contribs in contributions.items()],
            key=lambda x: x[1],
            reverse=True
        )
        bus_factor = calculate_bus_factor([(c[0], float(c[1])) for c in sorted_contributors])
        
        # Determine risk level
        if primary_share >= 80 and bus_factor <= 1:
            risk_level = "high"
            risk_score = 85
        elif primary_share >= 60 or bus_factor <= 1:
            risk_level = "medium"
            risk_score = 60
        elif primary_share >= 40 and bus_factor >= 2:
            risk_level = "low"
            risk_score = 30
        else:
            risk_level = "low"
            risk_score = 20
        
        return {
            "target": target_path,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "primary_owner": primary["developer_id"],
            "primary_share_pct": primary_share,
            "secondary_owner": secondary["developer_id"] if secondary else None,
            "secondary_share_pct": secondary_share,
            "backup_gap_pct": round(backup_gap, 1),
            "bus_factor": bus_factor,
            "contributor_count": len(owners),
            "concentration_gini": calculate_gini_coefficient([o["ownership_share_pct"] / 100 for o in owners]),
            "recommendation": self._build_risk_recommendation(risk_level, primary["developer_id"], secondary["developer_id"] if secondary else None, bus_factor),
        }
    
    def _build_risk_recommendation(self, risk_level: str, primary: str, secondary: Optional[str], bus_factor: int) -> str:
        """Build a risk recommendation string."""
        if risk_level == "high":
            if secondary:
                return f"CRITICAL: {primary} owns {80}%+. Pair with {secondary} immediately and document knowledge."
            return f"CRITICAL: {primary} is single owner. Add backup owner and require pair programming."
        elif risk_level == "medium":
            if secondary:
                return f"WARNING: Ownership concentrated with {primary}. Rotate {secondary} into more changes."
            return f"WARNING: Limited backup for {primary}. Assign shadow developer."
        else:
            return f"OK: Ownership is well distributed. Monitor for changes."
    
    def get_module_bus_factor(self, module_name: str) -> int:
        """
        Get the bus factor for a specific module.
        
        Args:
            module_name: Name of the module
        
        Returns:
            Bus factor (number of developers covering 70% of work)
        """
        if not self._processed:
            self.process_events()
        
        contributions = self._module_contributions.get(module_name, {})
        
        sorted_contributors = sorted(
            [(dev, float(len(contribs))) for dev, contribs in contributions.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return calculate_bus_factor(sorted_contributors)

    def get_stats(self) -> dict[str, Any]:
        """Get ownership graph statistics.
        
        Returns:
            Dictionary with graph statistics
        """
        if not self._processed:
            self.process_events()
        
        total_files = len(self._file_contributions)
        total_modules = len(self._module_contributions)
        
        # Count unique developers
        all_developers: set[str] = set()
        for file_contribs in self._file_contributions.values():
            all_developers.update(file_contribs.keys())
        for module_contribs in self._module_contributions.values():
            all_developers.update(module_contribs.keys())
        
        # Calculate total events processed
        total_events = len(self.events)
        
        # Calculate ownership concentration stats
        high_concentration_count = 0
        for file_path in self._file_contributions:
            owners = self.get_all_owners(file_path)
            if owners and owners[0].get("ownership_share_pct", 0) >= 70:
                high_concentration_count += 1
        
        return {
            "total_files_tracked": total_files,
            "total_modules_tracked": total_modules,
            "total_developers": len(all_developers),
            "total_events_processed": total_events,
            "high_concentration_files": high_concentration_count,
            "processed": self._processed,
        }


def create_ownership_graph(
    identity_resolver: Any = None,
    attribution_engine: Any = None,
    events: Optional[list[dict[str, Any]]] = None,
) -> OwnershipGraph:
    """Factory function to create an OwnershipGraph instance.
    
    Args:
        identity_resolver: Optional identity resolver for developer lookup
        attribution_engine: Optional attribution engine for work item resolution
        events: Optional initial list of events to process
        
    Returns:
        Configured OwnershipGraph instance
    """
    graph = OwnershipGraph(events=events if events is not None else None)
    if events:
        graph.process_events()
    return graph
