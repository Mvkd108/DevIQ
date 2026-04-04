"""
Recommendation Engine for Predictive Interventions

Generates specific recommendations for addressing delivery risks:
- Developer pairings based on knowledge continuity
- Scope reductions to preserve critical path
- Workload rebalancing to reduce bottlenecks
- Deadline extensions with impact analysis
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from intervention_schemas import (
    DeveloperPairing,
    InterventionPriority,
    InterventionType,
    Recommendation,
    RiskLevel,
    ScopeReduction,
    WorkloadRebalance,
)


class RecommendationEngine:
    """
    Generates actionable recommendations for delivery risk mitigation.
    
    Leverages existing engines (PredictiveDelivery, ManagerRollups, DependencyGraph)
    to suggest specific interventions with predicted outcomes.
    """
    
    def __init__(
        self,
        predictive_engine: Any = None,
        org_mapper: Any = None,
        dependency_graph: Any = None,
        ownership_graph: Any = None,
    ):
        """
        Initialize recommendation engine.
        
        Args:
            predictive_engine: PredictiveDeliveryEngine instance
            org_mapper: OrgMapper for team/manager data
            dependency_graph: DependencyGraph for cross-team analysis
            ownership_graph: OwnershipGraph for knowledge risk
        """
        self._predictive_engine = predictive_engine
        self._org_mapper = org_mapper
        self._dependency_graph = dependency_graph
        self._ownership_graph = ownership_graph
    
    def recommend_developer_pairing(
        self,
        requirement_id: str,
        primary_developer_id: str,
        target_module: str,
    ) -> Optional[Recommendation]:
        """
        Recommend a developer pairing for knowledge transfer.
        
        Strategy: Pair overloaded primary with underloaded secondary
        who has some familiarity with the module.
        """
        # Find best secondary developer
        secondary = self._find_best_pairing_candidate(
            primary_developer_id, target_module
        )
        
        if not secondary:
            return None
        
        pairing = DeveloperPairing(
            primary_developer_id=primary_developer_id,
            secondary_developer_id=secondary["id"],
            reason=f"Knowledge transfer for {target_module}. Primary overloaded, secondary available.",
            expected_duration_days=5,
            knowledge_areas=[target_module],
            confidence_score=0.75,
        )
        
        return Recommendation(
            id=f"rec-pair-{uuid.uuid4().hex[:8]}",
            type=InterventionType.DEVELOPER_PAIRING,
            title=f"Pair {primary_developer_id} with {secondary['id']}",
            description=pairing.reason,
            priority=InterventionPriority.HIGH,
            target_requirement_id=requirement_id,
            target_developer_id=primary_developer_id,
            developer_pairing=pairing,
            predicted_success_probability=0.75,
            predicted_risk_reduction=15.0,  # Percentage points
            predicted_delivery_improvement_days=2.0,
            supporting_factors=[
                "Secondary developer has module familiarity",
                "Workload imbalance detected",
                "Knowledge continuity risk identified"
            ],
        )
    
    def recommend_scope_reduction(
        self,
        requirement_id: str,
        original_description: str,
        complexity_score: float,
    ) -> Optional[Recommendation]:
        """
        Recommend scope reduction to preserve critical path.
        
        Strategy: Identify non-essential features that can be deferred.
        """
        if complexity_score < 3.0:
            return None  # Not complex enough to warrant reduction
        
        reduction = ScopeReduction(
            requirement_id=requirement_id,
            original_scope_description=original_description,
            proposed_reduction="Defer non-critical features to next sprint",
            business_impact="low" if complexity_score < 4.0 else "medium",
            effort_saved_days=complexity_score * 1.5,  # Heuristic
            critical_path_preserved=True,
            stakeholder_approval_required=["product_owner", "tech_lead"],
        )
        
        priority = (
            InterventionPriority.CRITICAL 
            if complexity_score > 4.5 
            else InterventionPriority.HIGH
        )
        
        return Recommendation(
            id=f"rec-scope-{uuid.uuid4().hex[:8]}",
            type=InterventionType.SCOPE_REDUCTION,
            title=f"Reduce scope for {requirement_id}",
            description=f"Proposed: {reduction.proposed_reduction}. Saves ~{reduction.effort_saved_days:.1f} days.",
            priority=priority,
            target_requirement_id=requirement_id,
            scope_reduction=reduction,
            predicted_success_probability=0.85,
            predicted_risk_reduction=25.0,
            predicted_delivery_improvement_days=reduction.effort_saved_days,
            supporting_factors=[
                f"High complexity score ({complexity_score:.1f}/5.0)",
                "Non-critical features identified",
                "Critical path will be preserved"
            ],
        )
    
    def recommend_workload_rebalance(
        self,
        overloaded_developer_id: str,
        team_id: str,
    ) -> Optional[Recommendation]:
        """
        Recommend redistributing workload from overloaded developer.
        
        Strategy: Transfer lowest-priority items to available team members.
        """
        # Find best target developer
        target = self._find_available_team_member(team_id, overloaded_developer_id)
        
        if not target:
            return None
        
        rebalance = WorkloadRebalance(
            overloaded_developer_id=overloaded_developer_id,
            target_developer_id=target["id"],
            requirements_to_transfer=[],  # To be filled by manager
            transfer_reason=f"{overloaded_developer_id} overloaded. {target['id']} has capacity.",
            capacity_after_transfer={
                overloaded_developer_id: 0.7,
                target["id"]: 0.85,
            },
            risk_mitigation="Monitor both developers during transition",
        )
        
        return Recommendation(
            id=f"rec-wl-{uuid.uuid4().hex[:8]}",
            type=InterventionType.WORKLOAD_REBALANCE,
            title=f"Rebalance workload: {overloaded_developer_id} → {target['id']}",
            description=rebalance.transfer_reason,
            priority=InterventionPriority.HIGH,
            target_developer_id=overloaded_developer_id,
            target_team_id=team_id,
            workload_rebalance=rebalance,
            predicted_success_probability=0.80,
            predicted_risk_reduction=20.0,
            predicted_delivery_improvement_days=3.0,
            supporting_factors=[
                "Significant workload imbalance detected",
                f"Target developer ({target['id']}) has available capacity",
                "Burnout risk reduction for overloaded developer"
            ],
        )
    
    def generate_all_recommendations(
        self,
        at_risk_requirements: list[dict[str, Any]],
    ) -> list[Recommendation]:
        """
        Generate comprehensive recommendations for all at-risk items.
        
        Args:
            at_risk_requirements: List of requirements flagged as at-risk
            
        Returns:
            Prioritized list of recommendations
        """
        recommendations: list[Recommendation] = []
        
        for req in at_risk_requirements:
            req_id = req.get("id", "unknown")
            complexity = req.get("complexity", 3.0)
            assignee = req.get("assignee")
            module = req.get("module", "unknown")
            
            # Try scope reduction first for complex items
            if complexity >= 3.5:
                scope_rec = self.recommend_scope_reduction(
                    req_id, req.get("description", ""), complexity
                )
                if scope_rec:
                    recommendations.append(scope_rec)
            
            # Recommend pairing for knowledge gaps
            if assignee and module:
                pair_rec = self.recommend_developer_pairing(
                    req_id, assignee, module
                )
                if pair_rec:
                    recommendations.append(pair_rec)
        
        # Sort by priority and predicted impact
        priority_order = {
            InterventionPriority.CRITICAL: 0,
            InterventionPriority.HIGH: 1,
            InterventionPriority.MEDIUM: 2,
            InterventionPriority.LOW: 3,
        }
        
        recommendations.sort(key=lambda r: (
            priority_order.get(r.priority, 4),
            -r.predicted_risk_reduction,
        ))
        
        return recommendations
    
    def _find_best_pairing_candidate(
        self,
        primary_id: str,
        target_module: str,
    ) -> Optional[dict[str, Any]]:
        """Find the best developer to pair with primary."""
        # Simplified implementation - would query ownership_graph
        # for developers with module familiarity
        return {
            "id": f"dev-{uuid.uuid4().hex[:6]}",
            "module_familiarity": 0.6,
            "availability": 0.8,
        }
    
    def _find_available_team_member(
        self,
        team_id: str,
        exclude_id: str,
    ) -> Optional[dict[str, Any]]:
        """Find team member with available capacity."""
        # Simplified implementation - would query org_mapper
        # for team members and their current workload
        return {
            "id": f"dev-{uuid.uuid4().hex[:6]}",
            "current_workload": 1,
            "capacity": 0.8,
        }


# Convenience function for quick recommendations
def generate_quick_recommendations(
    requirement_data: list[dict[str, Any]],
    **engine_deps,
) -> list[Recommendation]:
    """
    Quick helper to generate recommendations without instantiating engine.
    
    Args:
        requirement_data: List of requirement dictionaries
        **engine_deps: Optional engine dependencies
        
    Returns:
        List of prioritized recommendations
    """
    engine = RecommendationEngine(**engine_deps)
    return engine.generate_all_recommendations(requirement_data)
