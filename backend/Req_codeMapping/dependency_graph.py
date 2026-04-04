"""
Dependency Graph Module

Implements cross-team dependency detection and analysis.
Identifies shared modules, handoff risks, bottlenecks, and manager-to-manager dependencies.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from schemas import DependencyEdge, CanonicalDeveloper
from ownership_graph import OwnershipGraph, calculate_bus_factor, parse_datetime


def normalize_spaces(text: str) -> str:
    """Normalize whitespace in text."""
    return " ".join(str(text or "").split())


def event_actor(event: dict[str, Any]) -> str:
    """Extract the actor/developer from an event."""
    return normalize_spaces(
        str(event.get("author") or event.get("developer_id") or event.get("author_email") or "Unknown contributor")
    ) or "Unknown contributor"


class DependencyGraph:
    """
    Detects and analyzes cross-team dependencies.
    
    Identifies:
    - Cross-team overlaps (multiple teams touching same file/module)
    - Manager-to-manager dependency edges
    - Handoff chains when primary owner changes
    - Bottlenecks (high cross-team dependency + low bus factor)
    """
    
    def __init__(self, events: list[dict[str, Any]] = None, team_assignments: dict[str, str] = None):
        """
        Initialize the dependency graph.
        
        Args:
            events: Optional list of events to process
            team_assignments: Mapping of developer_id -> team_id
        """
        self.events = events or []
        self.team_assignments = team_assignments or {}
        self._ownership_graph: Optional[OwnershipGraph] = None
        self._module_teams: dict[str, set[str]] = defaultdict(set)
        self._module_managers: dict[str, set[str]] = defaultdict(set)
        self._team_modules: dict[str, set[str]] = defaultdict(set)
        self._developer_timeline: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._processed = False
    
    def process_events(self, events: Optional[list[dict[str, Any]]] = None) -> None:
        """
        Process events to build dependency data structures.
        
        Args:
            events: List of events to process
        """
        if events is not None:
            self.events = events
        
        if not self.events:
            return
        
        # Build ownership graph
        self._ownership_graph = OwnershipGraph(self.events)
        self._ownership_graph.process_events()
        
        # Process events for team-module mappings
        for event in self.events:
            actor = event_actor(event)
            team_id = self.team_assignments.get(actor, "unassigned")
            timestamp = event.get("timestamp")
            
            modules = event.get("modules_touched", []) or []
            for module in modules:
                if module:
                    self._module_teams[module].add(team_id)
                    self._team_modules[team_id].add(module)
                    
                    # Track developer timeline for this module
                    self._developer_timeline[module].append({
                        "developer": actor,
                        "team": team_id,
                        "timestamp": timestamp,
                        "event": event,
                    })
        
        self._processed = True
    
    def set_manager_mappings(self, manager_mappings: dict[str, str]) -> None:
        """
        Set manager mappings for teams.
        
        Args:
            manager_mappings: Mapping of team_id -> manager_id
        """
        self._manager_mappings = manager_mappings
        
        # Rebuild module_managers based on new mappings
        self._module_managers = defaultdict(set)
        for module, teams in self._module_teams.items():
            for team in teams:
                manager = manager_mappings.get(team)
                if manager:
                    self._module_managers[module].add(manager)
    
    def detect_cross_team_overlap(
        self,
        repo_path: str,
        events: Optional[list[dict[str, Any]]] = None,
        team_assignments: Optional[dict[str, str]] = None,
    ) -> list[DependencyEdge]:
        """
        Detect cross-team overlaps where multiple teams touch the same file/module.
        
        Args:
            repo_path: Repository path (for context)
            events: Optional events to process
            team_assignments: Optional team assignments to use
        
        Returns:
            List of DependencyEdge objects representing cross-team dependencies
        """
        if team_assignments is not None:
            self.team_assignments = team_assignments
        
        if events is not None:
            self.process_events(events)
        elif not self._processed:
            self.process_events()
        
        edges: list[DependencyEdge] = []
        edge_id = 0
        
        # Find modules touched by multiple teams
        for module in sorted(self._module_teams.keys()):
            teams = self._module_teams[module]
            if len(teams) <= 1:
                continue  # Not cross-team
            
            teams_list = sorted(teams)  # Sort for consistent ordering
            
            # Create edges between all team pairs
            for i, source_team in enumerate(teams_list):
                for target_team in teams_list[i + 1:]:
                    if source_team == target_team:
                        continue
                    
                    edge_id += 1
                    
                    # Get evidence for this dependency
                    events_in_module = self._developer_timeline.get(module, [])
                    source_events = [e for e in events_in_module if e["team"] == source_team]
                    target_events = [e for e in events_in_module if e["team"] == target_team]
                    
                    # Calculate dependency strength
                    if len(source_events) > 5 and len(target_events) > 5:
                        strength = "strong"
                    elif len(source_events) > 2 and len(target_events) > 2:
                        strength = "moderate"
                    else:
                        strength = "weak"
                    
                    # Build evidence
                    evidence = [
                        f"Module '{module}' touched by {len(teams)} teams",
                        f"{source_team}: {len(source_events)} events",
                        f"{target_team}: {len(target_events)} events",
                    ]
                    
                    # Find overlap timeframe
                    if events_in_module:
                        timestamps = [parse_datetime(e["timestamp"]) for e in events_in_module]
                        timestamps = [t for t in timestamps if t is not None]
                        if timestamps:
                            earliest = min(timestamps)
                            latest = max(timestamps)
                            evidence.append(f"Overlap period: {earliest.date()} to {latest.date()}")
                    
                    edge = DependencyEdge(
                        edge_id=f"cross-team-{edge_id:04d}",
                        source_work_item_id=f"team-{source_team}-work",
                        source_work_item_type="requirement",
                        source_team_id=source_team,
                        target_work_item_id=f"team-{target_team}-work",
                        target_work_item_type="requirement",
                        target_team_id=target_team,
                        dependency_type="depends_on",
                        strength=strength,
                        is_cross_team=True,
                        detected_at=datetime.now(timezone.utc).isoformat(),
                        effective_from=datetime.now(timezone.utc).isoformat(),
                        confidence_score=0.7 if strength == "strong" else 0.5 if strength == "moderate" else 0.3,
                        confidence_label="high" if strength == "strong" else "medium" if strength == "moderate" else "low",
                        evidence=evidence,
                        provenance="inferred_from_timing",
                        detection_method="inferred_from_timing",
                    )
                    edges.append(edge)
        
        return edges
    
    def identify_shared_modules(
        self,
        repo_path: str,
        module_profiles: Optional[dict[str, dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Identify and report on shared ownership across modules.
        
        Args:
            repo_path: Repository path
            module_profiles: Optional pre-computed module profiles
        
        Returns:
            Shared ownership report dictionary
        """
        if not self._processed:
            self.process_events()
        
        shared_modules = []
        
        for module, teams in self._module_teams.items():
            if len(teams) <= 1:
                continue
            
            # Get bus factor for this module
            bus_factor = self._ownership_graph.get_module_bus_factor(module) if self._ownership_graph else 1
            
            # Get team shares
            events_in_module = self._developer_timeline.get(module, [])
            team_event_counts: dict[str, int] = defaultdict(int)
            for event in events_in_module:
                team_event_counts[event["team"]] += 1
            
            total_events = sum(team_event_counts.values())
            team_shares = {
                team: round(count / total_events * 100, 1)
                for team, count in team_event_counts.items()
            } if total_events > 0 else {}
            
            module_report = {
                "module": module,
                "team_count": len(teams),
                "teams": list(teams),
                "team_shares_pct": team_shares,
                "bus_factor": bus_factor,
                "total_events": total_events,
                "risk_level": "high" if len(teams) > 2 and bus_factor <= 2 else "medium" if bus_factor <= 2 else "low",
                "recommendation": self._build_shared_module_recommendation(len(teams), bus_factor, list(teams)),
            }
            
            shared_modules.append(module_report)
        
        # Sort by risk (team count desc, then bus factor asc)
        shared_modules.sort(key=lambda x: (-x["team_count"], x["bus_factor"]))
        
        return {
            "repo_path": repo_path,
            "shared_module_count": len(shared_modules),
            "shared_modules": shared_modules,
            "high_risk_shared": [m for m in shared_modules if m["risk_level"] == "high"],
            "manager_attention_required": [m for m in shared_modules if m["bus_factor"] <= 1],
        }
    
    def _build_shared_module_recommendation(self, team_count: int, bus_factor: int, teams: list[str]) -> str:
        """Build a recommendation for shared module management."""
        if team_count > 2 and bus_factor <= 2:
            return f"CRITICAL: {team_count} teams depend on module with bus factor {bus_factor}. Establish cross-team ownership protocol immediately."
        elif bus_factor <= 1:
            return f"WARNING: Single point of failure with {team_count} dependent teams. Assign backup owners from {' or '.join(teams[:2])}."
        elif team_count > 2:
            return f"ATTENTION: {team_count} teams share this module. Consider splitting or establishing clear ownership boundaries."
        else:
            return f"OK: Shared between {teams[0]} and {teams[1]}. Monitor for ownership drift."
    
    def detect_handoff_risk(
        self,
        module: str,
        time_window_days: int = 90,
    ) -> dict[str, Any]:
        """
        Detect handoff chain analysis for a module.
        
        Identifies when primary owner changes over time, indicating knowledge handoffs.
        
        Args:
            module: Module name to analyze
            time_window_days: Time window for handoff detection
        
        Returns:
            Handoff chain analysis dictionary
        """
        if not self._processed:
            self.process_events()
        
        events_in_module = self._developer_timeline.get(module, [])
        
        if not events_in_module:
            return {
                "module": module,
                "handoff_detected": False,
                "handoff_chain": [],
                "risk_assessment": "No activity data available",
            }
        
        # Sort by timestamp
        sorted_events = sorted(
            events_in_module,
            key=lambda x: parse_datetime(x["timestamp"]) or datetime.min.replace(tzinfo=timezone.utc)
        )
        
        # Identify ownership periods (developer with most activity in time window)
        handoff_chain: list[dict[str, Any]] = []
        current_owner: Optional[str] = None
        current_period_start: Optional[datetime] = None
        period_events: list[dict[str, Any]] = []
        
        window_delta = timedelta(days=time_window_days // 3)  # Divide into 3 periods
        
        for event in sorted_events:
            event_time = parse_datetime(event["timestamp"])
            if event_time is None:
                continue
            
            developer = event["developer"]
            
            if current_owner is None:
                current_owner = developer
                current_period_start = event_time
                period_events = [event]
            elif developer != current_owner:
                # Potential handoff
                # Check if new developer has sustained activity
                recent_events = [e for e in sorted_events if e["developer"] == developer]
                if len(recent_events) >= 2:
                    # Record the period
                    handoff_chain.append({
                        "owner": current_owner,
                        "team": self.team_assignments.get(current_owner, "unknown"),
                        "period_start": current_period_start.isoformat() if current_period_start else None,
                        "period_end": event_time.isoformat(),
                        "event_count": len(period_events),
                    })
                    current_owner = developer
                    current_period_start = event_time
                    period_events = [event]
            else:
                period_events.append(event)
        
        # Add final period
        if current_owner and period_events:
            last_time = parse_datetime(period_events[-1]["timestamp"]) if period_events else None
            handoff_chain.append({
                "owner": current_owner,
                "team": self.team_assignments.get(current_owner, "unknown"),
                "period_start": current_period_start.isoformat() if current_period_start else None,
                "period_end": last_time.isoformat() if last_time else None,
                "event_count": len(period_events),
            })
        
        # Assess handoff risk
        handoff_count = len(handoff_chain) - 1 if len(handoff_chain) > 1 else 0
        
        if handoff_count == 0:
            risk_level = "low"
            risk_assessment = f"Stable ownership by {handoff_chain[0]['owner'] if handoff_chain else 'unknown'}"
        elif handoff_count == 1:
            risk_level = "medium"
            risk_assessment = f"One handoff detected. Monitor knowledge transfer."
        else:
            risk_level = "high"
            risk_assessment = f"Multiple handoffs ({handoff_count}) detected. Risk of knowledge loss."
        
        return {
            "module": module,
            "handoff_detected": handoff_count > 0,
            "handoff_count": handoff_count,
            "handoff_chain": handoff_chain,
            "time_window_days": time_window_days,
            "risk_level": risk_level,
            "risk_assessment": risk_assessment,
            "recommendation": self._build_handoff_recommendation(handoff_count, handoff_chain),
        }
    
    def _build_handoff_recommendation(self, handoff_count: int, handoff_chain: list[dict[str, Any]]) -> str:
        """Build a recommendation for handoff management."""
        if handoff_count == 0:
            return "No action needed - ownership is stable."
        elif handoff_count == 1:
            return "Document knowledge transfer and ensure new owner has full context."
        else:
            current = handoff_chain[-1]["owner"] if handoff_chain else "unknown"
            previous = handoff_chain[-2]["owner"] if len(handoff_chain) > 1 else "unknown"
            return f"CRITICAL: Multiple handoffs. Ensure {current} has knowledge from {previous} and earlier owners."
    
    def find_bottlenecks(self) -> list[dict[str, Any]]:
        """
        Find modules with high cross-team dependency and low bus factor.
        
        Bottleneck score = (cross_team_count * 10) / (bus_factor + 1)
        
        Returns:
            List of bottleneck modules sorted by score
        """
        if not self._processed:
            self.process_events()
        
        bottlenecks = []
        
        for module, teams in self._module_teams.items():
            cross_team_count = len(teams)
            
            if cross_team_count <= 1:
                continue  # Not cross-team, not a bottleneck
            
            # Get bus factor
            bus_factor = self._ownership_graph.get_module_bus_factor(module) if self._ownership_graph else 1
            
            # Calculate bottleneck score
            # Higher cross-team count = higher score
            # Lower bus factor = higher score
            bottleneck_score = (cross_team_count * 10) / (bus_factor + 1)
            
            # Get teams involved
            events_in_module = self._developer_timeline.get(module, [])
            team_event_counts: dict[str, int] = defaultdict(int)
            for event in events_in_module:
                team_event_counts[event["team"]] += 1
            
            # Sort teams by activity
            sorted_teams = sorted(team_event_counts.items(), key=lambda x: x[1], reverse=True)
            
            bottleneck = {
                "module": module,
                "bottleneck_score": round(bottleneck_score, 2),
                "cross_team_count": cross_team_count,
                "teams": [t[0] for t in sorted_teams],
                "bus_factor": bus_factor,
                "risk_level": "critical" if bottleneck_score >= 25 else "high" if bottleneck_score >= 15 else "medium" if bottleneck_score >= 10 else "low",
                "severity": "critical" if bus_factor <= 1 and cross_team_count >= 3 else "high" if bus_factor <= 2 else "medium",
                "recommendation": self._build_bottleneck_recommendation(cross_team_count, bus_factor, [t[0] for t in sorted_teams]),
            }
            
            bottlenecks.append(bottleneck)
        
        # Sort by bottleneck score descending
        bottlenecks.sort(key=lambda x: x["bottleneck_score"], reverse=True)
        
        return bottlenecks
    
    def _build_bottleneck_recommendation(self, cross_team_count: int, bus_factor: int, teams: list[str]) -> str:
        """Build a recommendation for bottleneck modules."""
        if bus_factor <= 1 and cross_team_count >= 3:
            return f"CRITICAL BOTTLENECK: {cross_team_count} teams depend on single owner. Immediate action required."
        elif bus_factor <= 1:
            return f"HIGH RISK: Single owner for cross-team module. Add backup from {' or '.join(teams[:2])}."
        elif bus_factor <= 2 and cross_team_count >= 3:
            return f"ELEVATED: Thin coverage across {cross_team_count} teams. Expand ownership."
        else:
            return f"MONITOR: Cross-team usage with bus factor {bus_factor}. Track ownership health."
    
    def get_manager_dependency_edges(self) -> list[DependencyEdge]:
        """
        Get manager-to-manager dependency edges when their teams share modules.
        
        Returns:
            List of DependencyEdge objects for manager dependencies
        """
        if not self._processed:
            self.process_events()
        
        if not hasattr(self, '_manager_mappings') or not self._manager_mappings:
            # No manager mappings available
            return []
        
        edges = []
        edge_id = 0
        
        # Find all manager pairs that share modules
        manager_pairs: dict[tuple[str, str], list[str]] = defaultdict(list)
        
        for module, teams in self._module_teams.items():
            if len(teams) <= 1:
                continue
            
            # Get managers for this module
            managers = set()
            for team in teams:
                manager = self._manager_mappings.get(team)
                if manager:
                    managers.add(manager)
            
            # Create pairs
            managers_list = list(managers)
            for i, manager_a in enumerate(managers_list):
                for manager_b in managers_list[i + 1:]:
                    if manager_a != manager_b:
                        pair = tuple(sorted([manager_a, manager_b]))
                        manager_pairs[pair].append(module)
        
        # Create edges
        for (manager_a, manager_b), shared_modules in manager_pairs.items():
            edge_id += 1
            
            # Get teams for each manager
            teams_a = [t for t, m in self._manager_mappings.items() if m == manager_a]
            teams_b = [t for t, m in self._manager_mappings.items() if m == manager_b]
            
            # Calculate strength
            if len(shared_modules) >= 5:
                strength = "strong"
            elif len(shared_modules) >= 2:
                strength = "moderate"
            else:
                strength = "weak"
            
            edge = DependencyEdge(
                edge_id=f"mgr-{edge_id:04d}",
                source_work_item_id=f"manager-{manager_a}",
                source_work_item_type="requirement",
                source_team_id=teams_a[0] if teams_a else "unknown",
                target_work_item_id=f"manager-{manager_b}",
                target_work_item_type="requirement",
                target_team_id=teams_b[0] if teams_b else "unknown",
                dependency_type="relates_to",
                strength=strength,
                is_cross_team=True,
                detected_at=datetime.now(timezone.utc).isoformat(),
                effective_from=datetime.now(timezone.utc).isoformat(),
                confidence_score=0.8 if strength == "strong" else 0.6 if strength == "moderate" else 0.4,
                confidence_label="high" if strength == "strong" else "medium" if strength == "moderate" else "low",
                evidence=[
                    f"Managers {manager_a} and {manager_b} have teams sharing modules",
                    f"Shared modules: {', '.join(shared_modules[:5])}" + (f" and {len(shared_modules) - 5} more" if len(shared_modules) > 5 else ""),
                    f"Manager {manager_a} teams: {', '.join(teams_a)}",
                    f"Manager {manager_b} teams: {', '.join(teams_b)}",
                ],
                provenance="inferred_from_timing",
                detection_method="inferred_from_timing",
            )
            edges.append(edge)
        
        return edges
    
    def get_dependency_summary(self) -> dict[str, Any]:
        """
        Get a summary of all dependencies and risks.
        
        Returns:
            Summary dictionary
        """
        if not self._processed:
            self.process_events()
        
        cross_team_edges = self.detect_cross_team_overlap("")
        bottlenecks = self.find_bottlenecks()
        manager_edges = self.get_manager_dependency_edges()
        
        # Calculate metrics
        total_shared_modules = len([m for m, teams in self._module_teams.items() if len(teams) > 1])
        critical_bottlenecks = [b for b in bottlenecks if b["risk_level"] == "critical"]
        high_bottlenecks = [b for b in bottlenecks if b["risk_level"] == "high"]
        
        return {
            "cross_team_dependencies": len(cross_team_edges),
            "shared_modules": total_shared_modules,
            "manager_dependencies": len(manager_edges),
            "bottlenecks_total": len(bottlenecks),
            "bottlenecks_critical": len(critical_bottlenecks),
            "bottlenecks_high": len(high_bottlenecks),
            "requires_manager_attention": len(critical_bottlenecks) + len(high_bottlenecks),
            "top_bottlenecks": bottlenecks[:5],
            "manager_edges": [{"from": e.source_team_id, "to": e.target_team_id, "strength": e.strength} for e in manager_edges[:5]],
            "assessment": self._build_summary_assessment(total_shared_modules, len(critical_bottlenecks), len(high_bottlenecks)),
        }
    
    def get_cross_team_dependencies(self) -> list[DependencyEdge]:
        """
        Get all cross-team dependencies.
        
        Returns:
            List of DependencyEdge objects representing cross-team dependencies
        """
        if not self._processed:
            self.process_events()
        
        return self.detect_cross_team_overlap("")
    
    def _build_summary_assessment(self, shared_modules: int, critical: int, high: int) -> str:
        """Build a summary assessment string."""
        if critical > 0:
            return f"CRITICAL: {critical} critical bottlenecks require immediate manager attention across {shared_modules} shared modules."
        elif high > 0:
            return f"WARNING: {high} high-risk dependencies need attention in {shared_modules} shared modules."
        elif shared_modules > 0:
            return f"OK: {shared_modules} shared modules with manageable risk levels."
        else:
            return "No cross-team dependencies detected."


def create_dependency_graph(
    events: Optional[list[dict[str, Any]]] = None,
    team_assignments: Optional[dict[str, str]] = None,
) -> DependencyGraph:
    """Factory function to create a DependencyGraph instance.
    
    Args:
        events: Optional list of events to process
        team_assignments: Optional mapping of developer_id -> team_id
        
    Returns:
        Configured DependencyGraph instance
    """
    graph = DependencyGraph(events=events, team_assignments=team_assignments)
    return graph
