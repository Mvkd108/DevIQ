"""
Burnout Early Warning System for DevHouse26

Predicts developer burnout 2-4 weeks in advance using multi-factor analysis.
Uses weighted heuristics (no ML required) for explainable predictions.
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Burnout risk levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class TrendDirection(Enum):
    """Trend direction for risk scores."""
    IMPROVING = "improving"
    STABLE = "stable"
    WORSENING = "worsening"


@dataclass
class BurnoutRiskScore:
    """Complete burnout risk assessment for a developer."""
    developer_id: str
    team_id: str
    overall_score: float  # 0-100, higher = more risk
    risk_level: RiskLevel
    trend: TrendDirection
    
    # Component scores (0-100 each)
    work_pattern_score: float
    sustainability_score: float
    activity_score: float
    isolation_score: float
    
    # Detailed contributing factors
    contributing_factors: List[Dict[str, Any]] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    
    # Metadata
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    lookback_days: int = 21
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "developer_id": self.developer_id,
            "team_id": self.team_id,
            "overall_score": round(self.overall_score, 1),
            "risk_level": self.risk_level.value,
            "trend": self.trend.value,
            "component_scores": {
                "work_pattern": round(self.work_pattern_score, 1),
                "sustainability": round(self.sustainability_score, 1),
                "activity": round(self.activity_score, 1),
                "isolation": round(self.isolation_score, 1)
            },
            "contributing_factors": self.contributing_factors,
            "recommended_actions": self.recommended_actions,
            "calculated_at": self.calculated_at.isoformat(),
            "lookback_days": self.lookback_days
        }


class BurnoutDetector:
    """
    Detects developer burnout risk using multi-factor analysis.
    
    Weights:
    - Work Pattern: 30% (after-hours, weekends, focus decline)
    - Sustainability: 25% (overtime trends, consistency)
    - Activity: 25% (engagement, participation)
    - Isolation: 20% (team collaboration, PR participation)
    """
    
    # Weights for overall score calculation
    WEIGHTS = {
        "work_pattern": 0.30,
        "sustainability": 0.25,
        "activity": 0.25,
        "isolation": 0.20
    }
    
    # Thresholds for risk levels
    THRESHOLDS = {
        RiskLevel.LOW: 35,
        RiskLevel.MODERATE: 55,
        RiskLevel.HIGH: 75,
        RiskLevel.CRITICAL: 100
    }
    
    def __init__(self, lookback_days: int = 21):
        """
        Initialize burnout detector.
        
        Args:
            lookback_days: Days of history to analyze (default 21 = 3 weeks)
        """
        self.lookback_days = lookback_days
        logger.info(f"BurnoutDetector initialized with {lookback_days} day lookback")
    
    def calculate_risk(
        self,
        developer_id: str,
        team_id: str,
        activity_data: List[Dict[str, Any]],
        historical_scores: Optional[List[BurnoutRiskScore]] = None
    ) -> BurnoutRiskScore:
        """
        Calculate burnout risk for a developer.
        
        Args:
            developer_id: Developer identifier
            team_id: Team identifier
            activity_data: List of daily activity records from extension_events
            historical_scores: Previous risk scores for trend detection
        
        Returns:
            Complete burnout risk assessment
        """
        logger.debug(f"Calculating burnout risk for {developer_id}")
        
        # Calculate component scores
        work_pattern = self._calculate_work_pattern_score(activity_data)
        sustainability = self._calculate_sustainability_score(activity_data)
        activity = self._calculate_activity_score(activity_data)
        isolation = self._calculate_isolation_score(activity_data)
        
        # Calculate overall score
        overall = (
            work_pattern * self.WEIGHTS["work_pattern"] +
            sustainability * self.WEIGHTS["sustainability"] +
            activity * self.WEIGHTS["activity"] +
            isolation * self.WEIGHTS["isolation"]
        )
        
        # Determine risk level
        risk_level = self._get_risk_level(overall)
        
        # Detect trend
        trend = self._detect_trend(overall, historical_scores)
        
        # Identify contributing factors
        factors = self._identify_contributing_factors(
            work_pattern, sustainability, activity, isolation, activity_data
        )
        
        # Generate recommendations
        actions = self._generate_recommendations(risk_level, factors)
        
        return BurnoutRiskScore(
            developer_id=developer_id,
            team_id=team_id,
            overall_score=overall,
            risk_level=risk_level,
            trend=trend,
            work_pattern_score=work_pattern,
            sustainability_score=sustainability,
            activity_score=activity,
            isolation_score=isolation,
            contributing_factors=factors,
            recommended_actions=actions,
            lookback_days=self.lookback_days
        )
    
    def _calculate_work_pattern_score(self, activity_data: List[Dict[str, Any]]) -> float:
        """
        Calculate work pattern risk score.
        
        Indicators:
        - After-hours work > 40% = elevated risk
        - Weekend streak >= 3 weeks = high risk
        - Focus ratio decline > 15% = warning
        - Idle time increase > 30% = procrastination
        """
        if not activity_data:
            return 0.0
        
        score = 0.0
        
        # After-hours percentage
        after_hours_commits = sum(
            1 for d in activity_data 
            if d.get('is_after_hours', False)
        )
        total_commits = len([d for d in activity_data if d.get('commit_id')])
        
        if total_commits > 0:
            after_hours_pct = after_hours_commits / total_commits
            if after_hours_pct > 0.50:
                score += 25  # Critical
            elif after_hours_pct > 0.40:
                score += 18  # High
            elif after_hours_pct > 0.25:
                score += 10  # Moderate
        
        # Weekend streak detection
        weekend_days = set()
        for d in activity_data:
            ts = d.get('timestamp')
            if ts:
                try:
                    if isinstance(ts, str):
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    else:
                        dt = ts
                    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
                        week_key = dt.isocalendar()[1]  # Week number
                        weekend_days.add(week_key)
                except:
                    pass
        
        if len(weekend_days) >= 4:
            score += 25  # Working most weekends
        elif len(weekend_days) >= 3:
            score += 18  # Frequent weekend work
        elif len(weekend_days) >= 2:
            score += 10  # Some weekend work
        
        # Focus ratio decline
        focus_ratios = [
            d.get('focus_ratio', 0) for d in activity_data 
            if d.get('focus_ratio') is not None
        ]
        
        if len(focus_ratios) >= 7:
            first_week = sum(focus_ratios[:7]) / 7
            last_week = sum(focus_ratios[-7:]) / 7
            decline = first_week - last_week
            
            if decline > 0.20:
                score += 20  # Severe decline
            elif decline > 0.15:
                score += 15  # Significant decline
            elif decline > 0.10:
                score += 8   # Moderate decline
        
        # Idle time increase
        idle_ratios = [
            d.get('idle_minutes', 0) / max(d.get('active_minutes', 1), 1)
            for d in activity_data
            if d.get('active_minutes', 0) > 0
        ]
        
        if len(idle_ratios) >= 7:
            first_week_idle = sum(idle_ratios[:7]) / 7
            last_week_idle = sum(idle_ratios[-7:]) / 7
            increase = last_week_idle - first_week_idle
            
            if increase > 0.50:
                score += 15  # Major increase in idle time
            elif increase > 0.30:
                score += 10  # Moderate increase
        
        return min(100.0, score)
    
    def _calculate_sustainability_score(self, activity_data: List[Dict[str, Any]]) -> float:
        """
        Calculate sustainability risk score.
        
        Indicators:
        - Sustainability score < 40 = high risk
        - Declining for 2+ weeks = warning
        - Overtime penalty spike = overwork
        """
        if not activity_data:
            return 0.0
        
        score = 0.0
        
        # Average sustainability metric (from existing scoring)
        sustainability_values = [
            d.get('sustainability_score', 100) for d in activity_data
            if d.get('sustainability_score') is not None
        ]
        
        if sustainability_values:
            avg_sustainability = sum(sustainability_values) / len(sustainability_values)
            # Lower sustainability = higher risk
            if avg_sustainability < 30:
                score += 30
            elif avg_sustainability < 40:
                score += 25
            elif avg_sustainability < 50:
                score += 15
            elif avg_sustainability < 60:
                score += 8
        
        # Check for declining trend in consistency
        daily_activity = [
            d.get('active_minutes', 0) for d in activity_data
        ]
        
        if len(daily_activity) >= 14:
            first_week = sum(daily_activity[:7])
            second_week = sum(daily_activity[7:14])
            
            if second_week < first_week * 0.6:  # 40%+ drop
                score += 20  # Sharp decline
            elif second_week < first_week * 0.8:  # 20%+ drop
                score += 12  # Moderate decline
        
        # Check overtime patterns
        overtime_indicators = sum(
            1 for d in activity_data
            if d.get('is_after_hours') or d.get('is_weekend')
        )
        
        if overtime_indicators > len(activity_data) * 0.5:
            score += 20  # Majority of activity is overtime
        elif overtime_indicators > len(activity_data) * 0.3:
            score += 12  # Significant overtime
        
        return min(100.0, score)
    
    def _calculate_activity_score(self, activity_data: List[Dict[str, Any]]) -> float:
        """
        Calculate activity/engagement risk score.
        
        Indicators:
        - Activity < 50% baseline = withdrawal
        - Commit consistency < 40% = sporadic
        - Debug sessions decreasing = less deep work
        """
        if not activity_data:
            return 0.0
        
        score = 0.0
        
        # Days with any activity
        active_days = len([d for d in activity_data if d.get('active_minutes', 0) > 30])
        total_days = len(activity_data)
        
        if total_days > 0:
            activity_ratio = active_days / total_days
            if activity_ratio < 0.30:
                score += 25  # Very sporadic
            elif activity_ratio < 0.40:
                score += 18  # Inconsistent
            elif activity_ratio < 0.50:
                score += 10  # Below normal
        
        # Debug session engagement
        debug_sessions = [
            d.get('debug_session_count', 0) for d in activity_data
        ]
        
        if len(debug_sessions) >= 14:
            first_week_debug = sum(debug_sessions[:7])
            last_week_debug = sum(debug_sessions[-7:])
            
            if first_week_debug > 0 and last_week_debug == 0:
                score += 20  # Stopped debugging entirely
            elif first_week_debug > 0:
                decline_ratio = 1 - (last_week_debug / first_week_debug)
                if decline_ratio > 0.7:
                    score += 15  # Major decline in deep work
        
        # Total activity decline
        total_activity = [d.get('total_changes', 0) for d in activity_data]
        if len(total_activity) >= 14:
            first_week = sum(total_activity[:7])
            last_week = sum(total_activity[-7:])
            
            if first_week > 100 and last_week < first_week * 0.3:
                score += 18  # Major activity drop
        
        return min(100.0, score)
    
    def _calculate_isolation_score(self, activity_data: List[Dict[str, Any]]) -> float:
        """
        Calculate team isolation risk score.
        
        Indicators:
        - PR participation < 20% = team isolation
        - Solo commits > 70% = lack of collaboration
        - Team linkage < 30% = misalignment
        """
        if not activity_data:
            return 0.0
        
        score = 0.0
        
        # Solo vs collaborative work
        solo_commits = sum(
            1 for d in activity_data
            if d.get('is_solo_commit', True)
        )
        total_commits = len([d for d in activity_data if d.get('commit_id')])
        
        if total_commits > 0:
            solo_ratio = solo_commits / total_commits
            if solo_ratio > 0.85:
                score += 25  # Very isolated
            elif solo_ratio > 0.70:
                score += 18  # Mostly solo work
            elif solo_ratio > 0.55:
                score += 10  # Above average solo work
        
        # PR review participation
        pr_reviews = sum(
            1 for d in activity_data
            if d.get('pr_review_count', 0) > 0
        )
        active_days = len([d for d in activity_data if d.get('active_minutes', 0) > 0])
        
        if active_days > 0:
            review_ratio = pr_reviews / active_days
            if review_ratio < 0.10:
                score += 20  # Rarely reviewing others' code
            elif review_ratio < 0.20:
                score += 12  # Low review participation
        
        # Team requirement linkage
        linked_commits = sum(
            1 for d in activity_data
            if d.get('issue_id') or d.get('linked_issue')
        )
        
        if total_commits > 0:
            linkage_ratio = linked_commits / total_commits
            if linkage_ratio < 0.25:
                score += 18  # Low alignment with team priorities
            elif linkage_ratio < 0.40:
                score += 10  # Below average linkage
        
        return min(100.0, score)
    
    def _get_risk_level(self, score: float) -> RiskLevel:
        """Convert score to risk level."""
        if score >= self.THRESHOLDS[RiskLevel.HIGH]:
            return RiskLevel.CRITICAL
        elif score >= self.THRESHOLDS[RiskLevel.MODERATE]:
            return RiskLevel.HIGH
        elif score >= self.THRESHOLDS[RiskLevel.LOW]:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
    
    def _detect_trend(
        self,
        current_score: float,
        historical_scores: Optional[List[BurnoutRiskScore]]
    ) -> TrendDirection:
        """Detect trend direction from historical scores."""
        if not historical_scores or len(historical_scores) < 2:
            return TrendDirection.STABLE
        
        # Compare with previous score
        previous = historical_scores[-1].overall_score
        delta = current_score - previous
        
        if delta > 10:
            return TrendDirection.WORSENING
        elif delta < -10:
            return TrendDirection.IMPROVING
        else:
            return TrendDirection.STABLE
    
    def _identify_contributing_factors(
        self,
        work_pattern: float,
        sustainability: float,
        activity: float,
        isolation: float,
        activity_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify specific factors contributing to risk."""
        factors = []
        
        # Work pattern factors
        if work_pattern >= 20:
            factors.append({
                "category": "work_pattern",
                "severity": "high" if work_pattern > 40 else "moderate",
                "description": "Significant after-hours or weekend work detected",
                "metric": f"{work_pattern:.0f}/100"
            })
        
        if sustainability >= 20:
            factors.append({
                "category": "sustainability",
                "severity": "high" if sustainability > 40 else "moderate",
                "description": "Declining work sustainability and consistency",
                "metric": f"{sustainability:.0f}/100"
            })
        
        if activity >= 20:
            factors.append({
                "category": "activity",
                "severity": "high" if activity > 40 else "moderate",
                "description": "Decreased engagement and activity levels",
                "metric": f"{activity:.0f}/100"
            })
        
        if isolation >= 20:
            factors.append({
                "category": "isolation",
                "severity": "high" if isolation > 40 else "moderate",
                "description": "Reduced team collaboration and PR participation",
                "metric": f"{isolation:.0f}/100"
            })
        
        # Add specific behavioral flags
        after_hours = sum(1 for d in activity_data if d.get('is_after_hours'))
        total = len([d for d in activity_data if d.get('commit_id')])
        
        if total > 0 and after_hours / total > 0.4:
            factors.append({
                "category": "overtime",
                "severity": "high",
                "description": f"{after_hours}/{total} commits during after-hours",
                "metric": f"{(after_hours/total)*100:.0f}%"
            })
        
        return factors
    
    def _generate_recommendations(
        self,
        risk_level: RiskLevel,
        factors: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations based on risk level."""
        actions = []
        
        if risk_level == RiskLevel.CRITICAL:
            actions.extend([
                "Schedule immediate 1-on-1 conversation",
                "Consider workload reduction or PTO",
                "Review recent deadline pressures",
                "Check for personal circumstances affecting work"
            ])
        elif risk_level == RiskLevel.HIGH:
            actions.extend([
                "Schedule 1-on-1 this week",
                "Assess current workload and deadlines",
                "Consider redistributing tasks",
                "Encourage time off or wellness days"
            ])
        elif risk_level == RiskLevel.MODERATE:
            actions.extend([
                "Include check-in during next 1-on-1",
                "Monitor workload distribution",
                "Encourage sustainable work patterns",
                "Discuss any blockers or concerns"
            ])
        else:
            actions.extend([
                "Continue regular 1-on-1s",
                "Maintain healthy work patterns",
                "Recognize good sustainability practices"
            ])
        
        # Add specific recommendations based on factors
        factor_categories = {f["category"] for f in factors}
        
        if "work_pattern" in factor_categories:
            actions.append("Address after-hours work expectations")
        
        if "sustainability" in factor_categories:
            actions.append("Review sprint planning and commitments")
        
        if "activity" in factor_categories:
            actions.append("Check for disengagement or unclear priorities")
        
        if "isolation" in factor_categories:
            actions.append("Encourage pair programming or team collaboration")
        
        return actions


class BurnoutAlertManager:
    """Manages alerts for high burnout risk."""
    
    def __init__(self, cooldown_hours: int = 24):
        """
        Initialize alert manager.
        
        Args:
            cooldown_hours: Hours between duplicate alerts for same developer
        """
        self.cooldown_hours = cooldown_hours
        self._alert_history: Dict[str, datetime] = {}
    
    def should_alert(self, developer_id: str, risk_level: RiskLevel) -> bool:
        """Check if alert should be sent (respects cooldown)."""
        if risk_level not in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return False
        
        last_alert = self._alert_history.get(developer_id)
        if last_alert:
            hours_since = (datetime.utcnow() - last_alert).total_seconds() / 3600
            if hours_since < self.cooldown_hours:
                return False
        
        return True
    
    def record_alert(self, developer_id: str) -> None:
        """Record that alert was sent."""
        self._alert_history[developer_id] = datetime.utcnow()
    
    def send_alert(
        self,
        risk_score: BurnoutRiskScore,
        slack_webhook: Optional[str] = None,
        email: Optional[str] = None
    ) -> bool:
        """Send alert via configured channels."""
        if not self.should_alert(risk_score.developer_id, risk_score.risk_level):
            return False
        
        logger.warning(
            f"BURNOUT ALERT: {risk_score.developer_id} - "
            f"{risk_score.risk_level.value.upper()} ({risk_score.overall_score:.1f})"
        )
        
        # TODO: Implement actual Slack/Email sending
        # For now, just log the alert
        
        self.record_alert(risk_score.developer_id)
        return True


def run_burnout_detection_job(
    storage_provider,
    alert_manager: Optional[BurnoutAlertManager] = None,
    team_ids: Optional[List[str]] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Background job to run burnout detection for all developers.
    
    Args:
        storage_provider: Storage provider for fetching data and saving results
        alert_manager: Optional alert manager for notifications
        team_ids: Optional list of teams to process (None = all teams)
        dry_run: If True, don't save results or send alerts
    
    Returns:
        Job statistics
    """
    logger.info("Starting burnout detection job")
    
    detector = BurnoutDetector()
    results = {
        "processed": 0,
        "alerts_sent": 0,
        "by_risk_level": {level.value: 0 for level in RiskLevel},
        "errors": 0
    }
    
    # TODO: Fetch developers from storage
    # For now, return template
    
    logger.info(f"Burnout detection job completed: {results}")
    return results
