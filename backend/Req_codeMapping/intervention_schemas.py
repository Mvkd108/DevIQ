"""
Intervention & Simulation System Schemas

Data models for the predictive intervention and simulation capabilities.
Defines structures for interventions, recommendations, scenarios, and simulation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class InterventionType(str, Enum):
    """Types of interventions that can be recommended."""
    DEVELOPER_PAIRING = "developer_pairing"
    SCOPE_REDUCTION = "scope_reduction"
    WORKLOAD_REBALANCE = "workload_rebalance"
    DEADLINE_EXTENSION = "deadline_extension"
    KNOWLEDGE_TRANSFER = "knowledge_transfer"
    ADD_RESOURCES = "add_resources"
    SIMPLIFY_REQUIREMENT = "simplify_requirement"
    RISK_ACCEPTANCE = "risk_acceptance"


class InterventionPriority(str, Enum):
    """Priority levels for interventions."""
    CRITICAL = "critical"  # Must apply immediately
    HIGH = "high"          # Apply within 24 hours
    MEDIUM = "medium"      # Apply within 1 week
    LOW = "low"            # Apply when convenient


class InterventionStatus(str, Enum):
    """Lifecycle status of an intervention."""
    SUGGESTED = "suggested"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    VERIFIED = "verified"  # Outcome confirmed
    FAILED = "failed"


class RiskLevel(str, Enum):
    """Risk assessment levels."""
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    CRITICAL = "critical"
    DELAYED = "delayed"


class ShockType(str, Enum):
    """Types of shock scenarios for simulation."""
    DEVELOPER_DEPARTURE = "developer_departure"
    SCOPE_INCREASE = "scope_increase"
    DEADLINE_CHANGE = "deadline_change"
    TEAM_RESTRUCTURE = "team_restructure"
    REQUIREMENT_EMERGENCY = "requirement_emergency"
    RESOURCE_CUT = "resource_cut"
    TECH_DEBT_CRISIS = "tech_debt_crisis"


@dataclass
class DeveloperPairing:
    """Recommended developer pairing for knowledge transfer."""
    primary_developer_id: str
    secondary_developer_id: str
    reason: str
    expected_duration_days: int
    knowledge_areas: list[str]
    confidence_score: float  # 0-1 likelihood of success


@dataclass
class ScopeReduction:
    """Recommended scope reduction to preserve critical path."""
    requirement_id: str
    original_scope_description: str
    proposed_reduction: str
    business_impact: str  # "low", "medium", "high"
    effort_saved_days: float
    critical_path_preserved: bool
    stakeholder_approval_required: list[str]


@dataclass
class WorkloadRebalance:
    """Recommended workload redistribution."""
    overloaded_developer_id: str
    target_developer_id: str
    requirements_to_transfer: list[str]
    transfer_reason: str
    capacity_after_transfer: dict[str, float]  # developer_id -> capacity
    risk_mitigation: str


@dataclass
class Recommendation:
    """A specific recommendation for addressing a risk."""
    id: str
    type: InterventionType
    title: str
    description: str
    priority: InterventionPriority
    
    # Target information
    target_requirement_id: Optional[str] = None
    target_developer_id: Optional[str] = None
    target_team_id: Optional[str] = None
    
    # Recommendation details
    developer_pairing: Optional[DeveloperPairing] = None
    scope_reduction: Optional[ScopeReduction] = None
    workload_rebalance: Optional[WorkloadRebalance] = None
    
    # Impact prediction
    predicted_success_probability: float = 0.0  # 0-1
    predicted_risk_reduction: float = 0.0  # Percentage points
    predicted_delivery_improvement_days: float = 0.0
    
    # Evidence
    supporting_factors: list[str] = field(default_factory=list)
    contraindications: list[str] = field(default_factory=list)
    similar_past_outcomes: list[dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    generated_by: str = "system"  # or specific engine name


@dataclass
class Intervention:
    """An intervention that has been or will be applied."""
    id: str
    recommendation_id: str
    
    # Type and status
    type: InterventionType
    status: InterventionStatus
    priority: InterventionPriority
    
    # Content
    title: str
    description: str
    recommendation: Recommendation
    
    # Assignment
    requested_by: str
    approved_by: Optional[str] = None
    assigned_to: Optional[str] = None
    
    # Timeline
    suggested_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    expected_resolution_at: Optional[datetime] = None
    actual_resolution_at: Optional[datetime] = None
    
    # Outcome tracking
    outcome_description: Optional[str] = None
    outcome_verified: bool = False
    risk_before: Optional[RiskLevel] = None
    risk_after: Optional[RiskLevel] = None
    delivery_impact_days: Optional[float] = None
    
    # Feedback
    effectiveness_score: Optional[float] = None  # 0-1
    stakeholder_feedback: list[dict[str, Any]] = field(default_factory=list)
    lessons_learned: list[str] = field(default_factory=list)


@dataclass
class ShockScenario:
    """A crisis/shock scenario for simulation."""
    id: str
    name: str
    description: str
    type: ShockType
    
    # Impact parameters
    affected_developer_ids: list[str] = field(default_factory=list)
    affected_requirement_ids: list[str] = field(default_factory=list)
    affected_team_ids: list[str] = field(default_factory=list)
    
    # Scenario details
    scope_increase_percent: float = 0.0
    deadline_change_days: int = 0  # negative = sooner
    resource_reduction_percent: float = 0.0
    
    # Simulation settings
    probability_of_occurrence: float = 0.0  # 0-1
    typical_duration_days: int = 0
    recovery_difficulty: str = "medium"  # "easy", "medium", "hard"


@dataclass
class SimulationResult:
    """Result of running a simulation scenario."""
    id: str
    scenario_id: str
    scenario_name: str
    
    # Baseline (before shock)
    baseline_risk_level: RiskLevel
    baseline_delivery_probability: float
    baseline_predicted_completion: datetime
    
    # After shock (without intervention)
    shocked_risk_level: RiskLevel
    shocked_delivery_probability: float
    shocked_predicted_completion: datetime
    shocked_delay_days: float
    
    # Run metadata
    run_at: datetime = field(default_factory=datetime.utcnow)
    
    # After intervention (if applied)
    mitigated_risk_level: Optional[RiskLevel] = None
    mitigated_delivery_probability: Optional[float] = None
    mitigated_predicted_completion: Optional[datetime] = None
    mitigation_effectiveness: float = 0.0  # 0-1
    
    # Recommended response
    recommended_interventions: list[Recommendation] = field(default_factory=list)
    optimal_resource_allocation: dict[str, Any] = field(default_factory=dict)
    
    # Impact metrics
    financial_impact_estimate: Optional[float] = None
    team_morale_impact: Optional[str] = None  # "low", "medium", "high"
    customer_impact: Optional[str] = None
    
    # Comparison data
    alternative_scenarios_tested: list[dict[str, Any]] = field(default_factory=list)
    best_case_outcome: Optional[dict[str, Any]] = None
    worst_case_outcome: Optional[dict[str, Any]] = None


@dataclass
class InterventionDashboard:
    """Aggregated view for the intervention dashboard."""
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Active features status
    active_features: list[dict[str, Any]] = field(default_factory=list)
    # Each feature: {id, name, risk_status, progress_pct, expected_delivery, risk_factors}
    
    # Interventions
    pending_interventions: list[Intervention] = field(default_factory=list)
    active_interventions: list[Intervention] = field(default_factory=list)
    completed_interventions: list[Intervention] = field(default_factory=list)
    
    # Risk summary
    total_on_track: int = 0
    total_at_risk: int = 0
    total_critical: int = 0
    
    # Recommendations awaiting action
    top_recommendations: list[Recommendation] = field(default_factory=list)
    
    # System status
    simulation_engine_ready: bool = False
    last_simulation_run: Optional[datetime] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "risk_summary": {
                "on_track": self.total_on_track,
                "at_risk": self.total_at_risk,
                "critical": self.total_critical,
                "total": self.total_on_track + self.total_at_risk + self.total_critical
            },
            "active_features": self.active_features,
            "interventions": {
                "pending": len(self.pending_interventions),
                "active": len(self.active_interventions),
                "completed": len(self.completed_interventions),
                "top_pending": [
                    {
                        "id": i.id,
                        "type": i.type.value,
                        "priority": i.priority.value,
                        "title": i.title,
                        "predicted_success": i.recommendation.predicted_success_probability
                    }
                    for i in self.pending_interventions[:5]
                ]
            },
            "top_recommendations": [
                {
                    "id": r.id,
                    "type": r.type.value,
                    "priority": r.priority.value,
                    "title": r.title,
                    "predicted_risk_reduction": r.predicted_risk_reduction
                }
                for r in self.top_recommendations[:5]
            ],
            "system_status": {
                "simulation_ready": self.simulation_engine_ready,
                "last_simulation": self.last_simulation_run.isoformat() if self.last_simulation_run else None
            }
        }


# Export all classes
__all__ = [
    "InterventionType",
    "InterventionPriority", 
    "InterventionStatus",
    "RiskLevel",
    "ShockType",
    "DeveloperPairing",
    "ScopeReduction",
    "WorkloadRebalance",
    "Recommendation",
    "Intervention",
    "ShockScenario",
    "SimulationResult",
    "InterventionDashboard",
]
