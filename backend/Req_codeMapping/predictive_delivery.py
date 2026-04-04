"""
Predictive Delivery Intelligence for DevHouse26

Predicts whether requirements will be delivered on time using
multi-factor analysis including per-developer velocity and risk profiles.
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class DeliveryProbability(Enum):
    """Delivery probability categories."""
    VERY_LIKELY = "very_likely"      # > 80%
    LIKELY = "likely"                # 60-80%
    UNCERTAIN = "uncertain"          # 40-60%
    UNLIKELY = "unlikely"            # 20-40%
    VERY_UNLIKELY = "very_unlikely"  # < 20%


class RiskSeverity(Enum):
    """Risk factor severity."""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


@dataclass
class DeveloperVelocity:
    """Per-developer velocity metrics."""
    developer_id: str
    developer_name: str
    
    # Historical performance
    avg_days_per_requirement: float
    completion_rate: float  # 0-1
    
    # Current state
    current_workload: int  # Number of active requirements
    burnout_risk_score: float  # 0-100 from burnout detector
    
    # Knowledge
    module_familiarity: Dict[str, float]  # module -> familiarity score (0-1)
    
    # Availability
    availability_score: float  # 0-1 (1.0 = fully available)
    
    def calculate_capacity_factor(self) -> float:
        """Calculate developer's current capacity (0-1)."""
        # Base capacity
        capacity = 1.0
        
        # Reduce for workload (more work = slower per item)
        if self.current_workload > 3:
            capacity *= 0.6
        elif self.current_workload > 2:
            capacity *= 0.8
        elif self.current_workload > 1:
            capacity *= 0.9
        
        # Reduce for burnout risk
        if self.burnout_risk_score > 75:
            capacity *= 0.5  # Critical burnout = half speed
        elif self.burnout_risk_score > 55:
            capacity *= 0.7
        elif self.burnout_risk_score > 35:
            capacity *= 0.85
        
        # Reduce for availability
        capacity *= self.availability_score
        
        return capacity


@dataclass
class DeliveryRiskFactor:
    """Individual risk factor."""
    type: str
    severity: RiskSeverity
    description: str
    mitigation: str
    related_developer_id: Optional[str] = None


@dataclass
class DeliveryPrediction:
    """Complete delivery prediction for a requirement."""
    # Identification
    requirement_id: str
    requirement_title: str
    project_id: str
    
    # Prediction
    delivery_probability: float  # 0-100
    probability_category: DeliveryProbability
    predicted_completion_date: datetime
    predicted_days_remaining: float
    
    # Timeline
    target_date: Optional[datetime]
    days_until_deadline: Optional[int]
    expected_delay_days: Optional[float]
    
    # Analysis
    risk_factors: List[DeliveryRiskFactor]
    contributing_developers: List[DeveloperVelocity]
    confidence_level: str  # high, medium, low
    
    # Explanation
    primary_risk_driver: str
    recommendation: str
    
    # Metadata
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    model_version: str = "heuristic-v1"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "requirement_id": self.requirement_id,
            "requirement_title": self.requirement_title,
            "project_id": self.project_id,
            "prediction": {
                "delivery_probability": round(self.delivery_probability, 1),
                "probability_category": self.probability_category.value,
                "predicted_completion_date": self.predicted_completion_date.isoformat(),
                "predicted_days_remaining": round(self.predicted_days_remaining, 1),
                "confidence_level": self.confidence_level
            },
            "timeline": {
                "target_date": self.target_date.isoformat() if self.target_date else None,
                "days_until_deadline": self.days_until_deadline,
                "expected_delay_days": round(self.expected_delay_days, 1) if self.expected_delay_days else None
            },
            "risk_analysis": {
                "risk_factors": [
                    {
                        "type": f.type,
                        "severity": f.severity.value,
                        "description": f.description,
                        "mitigation": f.mitigation,
                        "related_developer": f.related_developer_id
                    }
                    for f in self.risk_factors
                ],
                "risk_count": len(self.risk_factors),
                "critical_risks": sum(1 for f in self.risk_factors if f.severity == RiskSeverity.CRITICAL),
                "high_risks": sum(1 for f in self.risk_factors if f.severity == RiskSeverity.HIGH)
            },
            "developers": [
                {
                    "id": d.developer_id,
                    "name": d.developer_name,
                    "workload": d.current_workload,
                    "burnout_risk": round(d.burnout_risk_score, 1),
                    "capacity_factor": round(d.calculate_capacity_factor(), 2),
                    "familiarity_with_module": d.module_familiarity
                }
                for d in self.contributing_developers
            ],
            "explanation": {
                "primary_risk_driver": self.primary_risk_driver,
                "recommendation": self.recommendation
            },
            "metadata": {
                "calculated_at": self.calculated_at.isoformat(),
                "model_version": self.model_version
            }
        }


class PredictiveDeliveryEngine:
    """
    Predicts requirement delivery using multi-factor analysis.
    
    Considers per-developer factors:
    - Historical velocity (how fast they typically work)
    - Current workload (how much they have now)
    - Burnout risk (are they slowing down)
    - Module familiarity (have they worked here before)
    - Availability (are they on PTO or part-time)
    """
    
    def __init__(self):
        """Initialize prediction engine."""
        logger.info("PredictiveDeliveryEngine initialized")
    
    def predict_delivery(
        self,
        requirement_id: str,
        requirement_title: str,
        requirement_description: str,
        requirement_complexity: int,  # 1-5 scale
        target_date: Optional[datetime],
        assigned_developers: List[DeveloperVelocity],
        similar_requirements_history: List[Dict[str, Any]],
        team_velocity_trend: float = 0.0  # -1 to 1, negative = slowing
    ) -> DeliveryPrediction:
        """
        Predict delivery for a requirement.
        
        Args:
            requirement_id: Requirement identifier
            requirement_title: Short title
            requirement_description: Full description
            requirement_complexity: 1-5 (1=simple, 5=very complex)
            target_date: Deadline (optional)
            assigned_developers: List of developers with their velocity profiles
            similar_requirements_history: Past similar requirements and actual delivery times
            team_velocity_trend: Team velocity trend (-1 to 1)
        
        Returns:
            Complete delivery prediction
        """
        logger.debug(f"Predicting delivery for requirement: {requirement_id}")
        
        # Calculate base delivery time
        base_days = self._calculate_base_delivery_time(
            requirement_complexity,
            requirement_description,
            similar_requirements_history
        )
        
        # Adjust for developer factors
        adjusted_days = self._adjust_for_developers(base_days, assigned_developers)
        
        # Adjust for team velocity trend
        adjusted_days = self._adjust_for_team_trend(adjusted_days, team_velocity_trend)
        
        # Calculate predicted completion date
        predicted_completion = datetime.utcnow() + timedelta(days=adjusted_days)
        
        # Calculate probability
        probability = self._calculate_probability(
            adjusted_days,
            target_date,
            assigned_developers
        )
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(
            requirement_complexity,
            adjusted_days,
            target_date,
            assigned_developers,
            requirement_description
        )
        
        # Determine expected delay
        expected_delay = None
        if target_date and predicted_completion > target_date:
            expected_delay = (predicted_completion - target_date).days
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            probability,
            risk_factors,
            assigned_developers
        )
        
        return DeliveryPrediction(
            requirement_id=requirement_id,
            requirement_title=requirement_title,
            project_id="",  # Set by caller
            delivery_probability=probability,
            probability_category=self._categorize_probability(probability),
            predicted_completion_date=predicted_completion,
            predicted_days_remaining=adjusted_days,
            target_date=target_date,
            days_until_deadline=(target_date - datetime.utcnow()).days if target_date else None,
            expected_delay_days=expected_delay,
            risk_factors=risk_factors,
            contributing_developers=assigned_developers,
            confidence_level=self._calculate_confidence(similar_requirements_history),
            primary_risk_driver=self._get_primary_risk_driver(risk_factors),
            recommendation=recommendation
        )
    
    def _calculate_base_delivery_time(
        self,
        complexity: int,
        description: str,
        similar_history: List[Dict[str, Any]]
    ) -> float:
        """Calculate base delivery time from complexity and history."""
        # Base days by complexity
        complexity_days = {
            1: 2.0,   # Simple
            2: 4.0,   # Easy
            3: 8.0,   # Medium
            4: 15.0,  # Complex
            5: 25.0   # Very complex
        }
        
        base = complexity_days.get(complexity, 8.0)
        
        # Adjust for description length (vague = more time)
        word_count = len(description.split())
        if word_count < 20:
            base *= 1.3  # Vague requirement = 30% more time
        elif word_count > 200:
            base *= 1.1  # Very detailed = slightly more complex
        
        # Adjust based on similar requirements history
        if similar_history:
            avg_days = sum(r.get('actual_days', base) for r in similar_history) / len(similar_history)
            # Blend historical average with complexity estimate (70% history, 30% complexity)
            base = (avg_days * 0.7) + (base * 0.3)
        
        return base
    
    def _adjust_for_developers(
        self,
        base_days: float,
        developers: List[DeveloperVelocity]
    ) -> float:
        """Adjust delivery time based on developer factors."""
        if not developers:
            return base_days * 1.5  # No developers = risk and delay
        
        # Calculate weighted capacity
        total_capacity = sum(d.calculate_capacity_factor() for d in developers)
        avg_capacity = total_capacity / len(developers)
        
        # More developers = faster (but with diminishing returns)
        if len(developers) == 1:
            parallel_factor = 1.0
        elif len(developers) == 2:
            parallel_factor = 0.75  # 2 devs = 25% faster
        elif len(developers) == 3:
            parallel_factor = 0.60  # 3 devs = 40% faster
        else:
            parallel_factor = 0.55  # 4+ devs = 45% faster (coordination overhead)
        
        # Combine capacity and parallelism
        adjusted = base_days * parallel_factor / avg_capacity
        
        return adjusted
    
    def _adjust_for_team_trend(self, days: float, trend: float) -> float:
        """Adjust for team velocity trend."""
        # trend is -1 to 1, negative = slowing down
        if trend < -0.5:
            return days * 1.3  # Significantly slowing = 30% more time
        elif trend < -0.2:
            return days * 1.15  # Moderately slowing = 15% more time
        elif trend > 0.3:
            return days * 0.90  # Improving = 10% faster
        return days
    
    def _calculate_probability(
        self,
        predicted_days: float,
        target_date: Optional[datetime],
        developers: List[DeveloperVelocity]
    ) -> float:
        """Calculate delivery probability (0-100)."""
        if not target_date:
            return 50.0  # No deadline = unknown
        
        days_available = (target_date - datetime.utcnow()).days
        
        if days_available <= 0:
            return 0.0  # Already overdue
        
        # Base probability on days ratio
        ratio = days_available / predicted_days
        
        if ratio >= 2.0:
            base_prob = 95.0
        elif ratio >= 1.5:
            base_prob = 85.0
        elif ratio >= 1.2:
            base_prob = 70.0
        elif ratio >= 1.0:
            base_prob = 55.0
        elif ratio >= 0.8:
            base_prob = 35.0
        elif ratio >= 0.6:
            base_prob = 20.0
        else:
            base_prob = 10.0
        
        # Adjust for developer burnout risk
        max_burnout = max((d.burnout_risk_score for d in developers), default=0)
        if max_burnout > 75:
            base_prob *= 0.6  # Critical burnout = 40% reduction
        elif max_burnout > 55:
            base_prob *= 0.75  # High burnout = 25% reduction
        elif max_burnout > 35:
            base_prob *= 0.90  # Moderate burnout = 10% reduction
        
        return min(100.0, max(0.0, base_prob))
    
    def _identify_risk_factors(
        self,
        complexity: int,
        predicted_days: float,
        target_date: Optional[datetime],
        developers: List[DeveloperVelocity],
        description: str
    ) -> List[DeliveryRiskFactor]:
        """Identify specific risk factors."""
        risks = []
        
        # Timeline risks
        if target_date:
            days_available = (target_date - datetime.utcnow()).days
            
            if days_available < predicted_days * 0.8:
                risks.append(DeliveryRiskFactor(
                    type="timeline",
                    severity=RiskSeverity.CRITICAL if days_available < predicted_days * 0.5 else RiskSeverity.HIGH,
                    description=f"Only {days_available} days available but {predicted_days:.1f} days predicted",
                    mitigation="Extend deadline or reduce scope",
                    related_developer_id=None
                ))
            elif days_available < predicted_days:
                risks.append(DeliveryRiskFactor(
                    type="timeline",
                    severity=RiskSeverity.MODERATE,
                    description=f"Tight timeline: {days_available} days for {predicted_days:.1f} days of work",
                    mitigation="Monitor closely, have backup plan",
                    related_developer_id=None
                ))
        
        # Developer-specific risks
        for dev in developers:
            if dev.burnout_risk_score > 75:
                risks.append(DeliveryRiskFactor(
                    type="developer",
                    severity=RiskSeverity.CRITICAL,
                    description=f"{dev.developer_name} showing critical burnout signs (score: {dev.burnout_risk_score:.0f})",
                    mitigation=f"Immediately reduce {dev.developer_name}'s workload or provide support",
                    related_developer_id=dev.developer_id
                ))
            elif dev.burnout_risk_score > 55:
                risks.append(DeliveryRiskFactor(
                    type="developer",
                    severity=RiskSeverity.HIGH,
                    description=f"{dev.developer_name} showing high burnout risk (score: {dev.burnout_risk_score:.0f})",
                    mitigation=f"Check in with {dev.developer_name} and assess workload",
                    related_developer_id=dev.developer_id
                ))
            
            if dev.current_workload > 3:
                risks.append(DeliveryRiskFactor(
                    type="workload",
                    severity=RiskSeverity.HIGH,
                    description=f"{dev.developer_name} has {dev.current_workload} active requirements",
                    mitigation=f"Redistribute {dev.developer_name}'s workload",
                    related_developer_id=dev.developer_id
                ))
        
        # Complexity risk
        if complexity >= 4:
            risks.append(DeliveryRiskFactor(
                type="complexity",
                severity=RiskSeverity.HIGH if complexity == 5 else RiskSeverity.MODERATE,
                description=f"High complexity requirement (level {complexity}/5)",
                mitigation="Break into smaller tasks or add senior reviewer",
                related_developer_id=None
            ))
        
        # Vague requirement risk
        if len(description.split()) < 30:
            risks.append(DeliveryRiskFactor(
                type="clarity",
                severity=RiskSeverity.MODERATE,
                description="Requirement description is vague (less than 30 words)",
                mitigation="Clarify requirements with PM/stakeholder",
                related_developer_id=None
            ))
        
        return risks
    
    def _categorize_probability(self, probability: float) -> DeliveryProbability:
        """Categorize probability score."""
        if probability >= 80:
            return DeliveryProbability.VERY_LIKELY
        elif probability >= 60:
            return DeliveryProbability.LIKELY
        elif probability >= 40:
            return DeliveryProbability.UNCERTAIN
        elif probability >= 20:
            return DeliveryProbability.UNLIKELY
        else:
            return DeliveryProbability.VERY_UNLIKELY
    
    def _calculate_confidence(self, similar_history: List[Dict[str, Any]]) -> str:
        """Calculate prediction confidence."""
        if len(similar_history) >= 5:
            return "high"
        elif len(similar_history) >= 2:
            return "medium"
        return "low"
    
    def _get_primary_risk_driver(self, risks: List[DeliveryRiskFactor]) -> str:
        """Identify primary risk driver."""
        if not risks:
            return "No significant risks identified"
        
        # Priority: timeline > developer > workload > complexity > clarity
        critical_timeline = next((r for r in risks if r.type == "timeline" and r.severity == RiskSeverity.CRITICAL), None)
        if critical_timeline:
            return "Critical timeline pressure"
        
        critical_dev = next((r for r in risks if r.type == "developer" and r.severity == RiskSeverity.CRITICAL), None)
        if critical_dev:
            return f"Developer burnout risk ({critical_dev.related_developer_id})"
        
        high_dev = next((r for r in risks if r.type == "developer" and r.severity == RiskSeverity.HIGH), None)
        if high_dev:
            return f"Developer showing burnout signs ({high_dev.related_developer_id})"
        
        timeline = next((r for r in risks if r.type == "timeline"), None)
        if timeline:
            return "Tight timeline"
        
        return risks[0].description
    
    def _generate_recommendation(
        self,
        probability: float,
        risks: List[DeliveryRiskFactor],
        developers: List[DeveloperVelocity]
    ) -> str:
        """Generate actionable recommendation."""
        if probability >= 80:
            return "Requirement is on track. Continue monitoring."
        
        if probability >= 60:
            return "Requirement is likely to be delivered on time, but monitor identified risks closely."
        
        # Below 60% - need action
        actions = []
        
        # Check for burnout
        burnout_devs = [d for d in developers if d.burnout_risk_score > 55]
        if burnout_devs:
            actions.append(f"Address burnout risk for {', '.join(d.developer_name for d in burnout_devs)}")
        
        # Check for overload
        overloaded = [d for d in developers if d.current_workload > 3]
        if overloaded:
            actions.append(f"Redistribute workload from {', '.join(d.developer_name for d in overloaded)}")
        
        # Check for timeline
        timeline_risks = [r for r in risks if r.type == "timeline"]
        if timeline_risks:
            actions.append("Consider deadline extension or scope reduction")
        
        if not actions:
            actions.append("Review requirement clarity and complexity")
        
        return "; ".join(actions)


# Helper function to create DeveloperVelocity from existing data
def create_developer_velocity(
    developer_id: str,
    developer_name: str,
    activity_data: List[Dict[str, Any]],
    burnout_risk_score: float,
    current_workload: int,
    module_commits: Dict[str, int],
    availability: float = 1.0
) -> DeveloperVelocity:
    """
    Create DeveloperVelocity from raw activity data.
    
    Args:
        developer_id: Developer ID
        developer_name: Developer name
        activity_data: Historical activity from extension_events
        burnout_risk_score: From BurnoutDetector
        current_workload: Number of active requirements assigned
        module_commits: Dict of module_name -> commit_count
        availability: 0-1 availability factor (1.0 = full time)
    
    Returns:
        DeveloperVelocity object ready for prediction
    """
    # Calculate average days per requirement
    completed_reqs = len([d for d in activity_data if d.get('issue_id') and d.get('completed_at')])
    total_days = len(set(d.get('date') for d in activity_data if d.get('date')))
    
    avg_days = total_days / max(completed_reqs, 1) if completed_reqs > 0 else 5.0
    
    # Calculate completion rate
    started = len([d for d in activity_data if d.get('issue_id')])
    completed = len([d for d in activity_data if d.get('completed_at')])
    completion_rate = completed / max(started, 1) if started > 0 else 0.8
    
    # Calculate module familiarity (normalize commit counts to 0-1)
    max_commits = max(module_commits.values()) if module_commits else 1
    familiarity = {
        module: min(1.0, count / max_commits * 2)  # Scale so top contributor = ~1.0
        for module, count in module_commits.items()
    }
    
    return DeveloperVelocity(
        developer_id=developer_id,
        developer_name=developer_name,
        avg_days_per_requirement=avg_days,
        completion_rate=completion_rate,
        current_workload=current_workload,
        burnout_risk_score=burnout_risk_score,
        module_familiarity=familiarity,
        availability_score=availability
    )
