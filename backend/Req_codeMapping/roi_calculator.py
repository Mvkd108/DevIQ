"""
Dollar ROI Calculator for DevHouse26.

This module calculates the financial return on investment for using DevHouse26,
including savings from burnout prevention, productivity improvements, and
delivery optimization.

Key ROI Streams:
1. Burnout Prevention (reduced turnover costs)
2. Delivery Prediction (prevented missed launches)
3. Productivity Gains (improved velocity)
4. Time Savings (automated insights vs manual tracking)

Cost Benchmarks (Industry Data):
- Developer replacement cost: 50-150% of annual salary
- Cost of missed product launch: $500K-$2M (typical)
- Meeting/tracking overhead: 5-10 hours/week per manager
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class ROICategory(Enum):
    """Categories of ROI calculation."""

    BURNOUT_PREVENTION = "burnout_prevention"
    DELIVERY_PREDICTION = "delivery_prediction"
    PRODUCTIVITY_GAIN = "productivity_gain"
    TIME_SAVINGS = "time_savings"
    QUALITY_IMPROVEMENT = "quality_improvement"


@dataclass
class ROIDetail:
    """Detailed breakdown of a single ROI component."""

    category: ROICategory
    annual_value: float  # Dollar amount per year
    assumptions: Dict[str, Any]
    calculation_notes: str
    confidence_level: str  # "low", "medium", "high"


@dataclass
class ROICalculation:
    """Complete ROI calculation results."""

    team_id: str
    calculated_at: datetime
    team_size: int
    avg_developer_salary: float
    total_annual_roi: float
    monthly_roi: float
    cost_per_developer_month: float  # DevHouse26 cost
    roi_components: List[ROIDetail] = field(default_factory=list)
    break_even_months: float = 0.0
    three_year_value: float = 0.0
    risk_adjusted_value: float = 0.0
    recommendations: List[str] = field(default_factory=list)

    def roi_ratio(self) -> float:
        """Calculate ROI ratio (return / investment)."""
        annual_cost = self.team_size * self.cost_per_developer_month * 12
        if annual_cost == 0:
            return 0.0
        return self.total_annual_roi / annual_cost

    def percentage_gain(self) -> float:
        """Calculate percentage gain."""
        annual_cost = self.team_size * self.cost_per_developer_month * 12
        if annual_cost == 0:
            return 0.0
        return ((self.total_annual_roi - annual_cost) / annual_cost) * 100


class ROICalculator:
    """
    Calculate dollar-value ROI for DevHouse26 implementation.

    This calculator uses industry benchmarks and customer-specific data
to quantify the financial value of using the platform.

    Industry Benchmarks Used:
    - Developer turnover cost: 100% of annual salary (recruitment + onboarding)
    - Missed launch cost: $500K (conservative estimate)
    - Productivity gain from insights: 15-30%
    - Manager time on status updates: 6 hours/week

    Example:
        >>> calculator = ROICalculator(
        ...     avg_salary=150000,
        ...     devhouse26_cost_per_dev_month=15
        ... )
        >>> roi = calculator.calculate_for_team(
        ...     team_id="team-456",
        ...     team_size=50,
        ...     burnout_risk_snapshot=burnout_data,
        ...     delivery_data=delivery_predictions
        ... )
        >>> print(f"Annual ROI: ${roi.total_annual_roi:,.0f}")
        >>> print(f"ROI Ratio: {roi.roi_ratio():.1f}x")
    """

    # Industry benchmark values
    DEFAULT_TURNOVER_COST_PERCENT = 1.0  # 100% of salary
    DEFAULT_MISSED_LAUNCH_COST = 500000  # $500K
    DEFAULT_PRODUCTIVITY_GAIN_PERCENT = 0.20  # 20%
    DEFAULT_MANAGER_HOURS_WEEKLY = 6  # 6 hours/week
    DEFAULT_MANAGER_HOURLY_RATE = 100  # $100/hour

    def __init__(
        self,
        avg_developer_salary: float = 150000,
        devhouse26_cost_per_dev_month: float = 15,
        manager_hourly_rate: float = 100,
        custom_benchmarks: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize ROI calculator.

        Args:
            avg_developer_salary: Average annual developer salary
            devhouse26_cost_per_dev_month: Monthly cost per developer
            manager_hourly_rate: Hourly rate for engineering managers
            custom_benchmarks: Optional overrides for industry benchmarks
        """
        self.avg_salary = avg_developer_salary
        self.monthly_cost = devhouse26_cost_per_dev_month
        self.manager_hourly = manager_hourly_rate

        benchmarks = custom_benchmarks or {}
        self.turnover_cost_pct = benchmarks.get(
            "turnover_cost_percent", self.DEFAULT_TURNOVER_COST_PERCENT
        )
        self.missed_launch_cost = benchmarks.get(
            "missed_launch_cost", self.DEFAULT_MISSED_LAUNCH_COST
        )
        self.productivity_gain_pct = benchmarks.get(
            "productivity_gain_percent", self.DEFAULT_PRODUCTIVITY_GAIN_PERCENT
        )
        self.manager_hours_weekly = benchmarks.get(
            "manager_hours_weekly", self.DEFAULT_MANAGER_HOURS_WEEKLY
        )

    def calculate_for_team(
        self,
        team_id: str,
        team_size: int,
        burnout_risk_snapshot: Optional[Dict[str, Any]] = None,
        delivery_predictions: Optional[List[Dict[str, Any]]] = None,
        historical_turnover: Optional[float] = None,
        manager_count: int = 2,
    ) -> ROICalculation:
        """
        Calculate ROI for a specific team.

        Args:
            team_id: Team identifier
            team_size: Number of developers
            burnout_risk_snapshot: Current burnout risk data by developer
            delivery_predictions: Delivery prediction data
            historical_turnover: Annual turnover rate (0.0-1.0)
            manager_count: Number of managers on the team

        Returns:
            ROICalculation with detailed breakdown
        """
        now = datetime.utcnow()
        components: List[ROIDetail] = []

        # 1. Burnout Prevention ROI
        burnout_roi = self._calculate_burnout_roi(
            team_size, burnout_risk_snapshot, historical_turnover
        )
        components.append(burnout_roi)

        # 2. Delivery Prediction ROI
        delivery_roi = self._calculate_delivery_roi(delivery_predictions)
        components.append(delivery_roi)

        # 3. Productivity Gain ROI
        productivity_roi = self._calculate_productivity_roi(team_size)
        components.append(productivity_roi)

        # 4. Time Savings ROI
        time_savings_roi = self._calculate_time_savings_roi(manager_count)
        components.append(time_savings_roi)

        # Calculate totals
        total_annual = sum(c.annual_value for c in components)
        monthly_roi = total_annual / 12
        monthly_cost = team_size * self.monthly_cost

        # Break-even calculation
        if monthly_roi > monthly_cost:
            break_even = monthly_cost / (monthly_roi - monthly_cost)
        else:
            break_even = float('inf')

        # 3-year projection (with 10% annual growth in value)
        three_year = total_annual * 3 * 1.15  # 15% growth over 3 years

        # Risk adjustment (reduce by 20% for uncertainty)
        risk_adjusted = total_annual * 0.8

        # Generate recommendations
        recommendations = self._generate_recommendations(components, team_size)

        return ROICalculation(
            team_id=team_id,
            calculated_at=now,
            team_size=team_size,
            avg_developer_salary=self.avg_salary,
            total_annual_roi=total_annual,
            monthly_roi=monthly_roi,
            cost_per_developer_month=self.monthly_cost,
            roi_components=components,
            break_even_months=break_even if break_even != float('inf') else 999,
            three_year_value=three_year,
            risk_adjusted_value=risk_adjusted,
            recommendations=recommendations,
        )

    def _calculate_burnout_roi(
        self,
        team_size: int,
        burnout_snapshot: Optional[Dict[str, Any]],
        historical_turnover: Optional[float],
    ) -> ROIDetail:
        """Calculate ROI from burnout prevention."""
        # Default: industry average 20% annual turnover
        baseline_turnover = historical_turnover or 0.20

        # Calculate at-risk developers
        high_risk_count = 0
        moderate_risk_count = 0

        if burnout_snapshot:
            for dev_id, risk_data in burnout_snapshot.items():
                risk_level = risk_data.get("risk_level", "low")
                if risk_level == "high":
                    high_risk_count += 1
                elif risk_level == "moderate":
                    moderate_risk_count += 1

        # If no data, estimate: 10% high risk, 20% moderate risk
        if high_risk_count == 0 and moderate_risk_count == 0:
            high_risk_count = max(1, int(team_size * 0.10))
            moderate_risk_count = max(1, int(team_size * 0.20))

        # Expected turnover from high-risk: 60%, moderate: 30%
        expected_turnover = (
            high_risk_count * 0.60 +
            moderate_risk_count * 0.30 +
            (team_size - high_risk_count - moderate_risk_count) * baseline_turnover * 0.5
        )

        # With DevHouse26 intervention, reduce by 50%
        prevented_turnover = expected_turnover * 0.50

        # Cost per turnover = 100% of salary
        turnover_cost = self.avg_salary * self.turnover_cost_pct
        annual_savings = prevented_turnover * turnover_cost

        return ROIDetail(
            category=ROICategory.BURNOUT_PREVENTION,
            annual_value=annual_savings,
            assumptions={
                "baseline_turnover_rate": baseline_turnover,
                "high_risk_developers": high_risk_count,
                "moderate_risk_developers": moderate_risk_count,
                "turnover_cost_percent": self.turnover_cost_pct * 100,
                "intervention_success_rate": 0.50,
                "high_risk_turnover_rate": 0.60,
                "moderate_risk_turnover_rate": 0.30,
            },
            calculation_notes=f"""
                Expected turnover without intervention: {expected_turnover:.1f} developers/year
                Prevented through early warning: {prevented_turnover:.1f} developers/year
                Cost per replacement: ${turnover_cost:,.0f}
                Annual savings: ${annual_savings:,.0f}
            """.strip(),
            confidence_level="high" if burnout_snapshot else "medium",
        )

    def _calculate_delivery_roi(
        self,
        delivery_predictions: Optional[List[Dict[str, Any]]],
    ) -> ROIDetail:
        """Calculate ROI from delivery prediction and prevented delays."""
        # Assume 2 major launches per year for a typical team
        launches_per_year = 2

        # Without prediction, 30% chance of missing launch
        baseline_miss_rate = 0.30

        # With prediction, reduce miss rate to 10%
        improved_miss_rate = 0.10

        # Prevented misses per year
        prevented_misses = launches_per_year * (baseline_miss_rate - improved_miss_rate)

        # Value per prevented miss
        annual_savings = prevented_misses * self.missed_launch_cost

        # Add value from early warning (allowing re-scoping vs. missed deadline)
        early_warning_value = launches_per_year * self.missed_launch_cost * 0.20

        total_value = annual_savings + early_warning_value

        return ROIDetail(
            category=ROICategory.DELIVERY_PREDICTION,
            annual_value=total_value,
            assumptions={
                "launches_per_year": launches_per_year,
                "baseline_miss_rate": baseline_miss_rate,
                "improved_miss_rate": improved_miss_rate,
                "missed_launch_cost": self.missed_launch_cost,
                "early_warning_value": self.missed_launch_cost * 0.20,
            },
            calculation_notes=f"""
                Major launches per year: {launches_per_year}
                Baseline miss rate: {baseline_miss_rate:.0%}
                Improved miss rate: {improved_miss_rate:.0%}
                Prevented misses: {prevented_misses:.1f}/year
                Missed launch cost: ${self.missed_launch_cost:,.0f}
                Early warning value: ${early_warning_value:,.0f}
            """.strip(),
            confidence_level="medium",
        )

    def _calculate_productivity_roi(self, team_size: int) -> ROIDetail:
        """Calculate ROI from productivity improvements."""
        # Baseline: 20% productivity gain from data-driven insights
        productivity_gain = self.productivity_gain_pct

        # Conservative: only 50% of gains are attributable to the tool
        attributable_gain = productivity_gain * 0.50

        # Value = additional effective capacity
        # A 10% gain on 50 developers = 5 additional devs worth of output
        effective_additional_devs = team_size * attributable_gain

        # Value at loaded cost (salary + 30% overhead)
        loaded_cost = self.avg_salary * 1.30
        annual_value = effective_additional_devs * loaded_cost

        return ROIDetail(
            category=ROICategory.PRODUCTIVITY_GAIN,
            annual_value=annual_value,
            assumptions={
                "productivity_gain_percent": productivity_gain * 100,
                "attributable_percent": 50,
                "effective_additional_capacity": effective_additional_devs,
                "loaded_cost_per_dev": loaded_cost,
            },
            calculation_notes=f"""
                Baseline productivity gain: {productivity_gain:.0%}
                Attributable to DevHouse26: {attributable_gain:.0%}
                Effective additional capacity: {effective_additional_devs:.1f} devs
                Loaded cost per dev: ${loaded_cost:,.0f}
                Annual value: ${annual_value:,.0f}
            """.strip(),
            confidence_level="medium",
        )

    def _calculate_time_savings_roi(self, manager_count: int) -> ROIDetail:
        """Calculate ROI from automated insights and time savings."""
        # Managers save time on:
        # - Manual status collection: 2 hours/week
        # - 1-on-1 prep with data: 1 hour/week
        # - Reporting: 2 hours/week
        # - Blocker identification: 1 hour/week

        hours_saved_per_manager_weekly = self.manager_hours_weekly
        weeks_per_year = 48  # Account for PTO/holidays

        total_hours_saved = hours_saved_per_manager_weekly * weeks_per_year * manager_count

        annual_value = total_hours_saved * self.manager_hourly

        return ROIDetail(
            category=ROICategory.TIME_SAVINGS,
            annual_value=annual_value,
            assumptions={
                "hours_saved_per_manager_weekly": hours_saved_per_manager_weekly,
                "manager_count": manager_count,
                "working_weeks_per_year": weeks_per_year,
                "manager_hourly_rate": self.manager_hourly,
                "total_hours_saved_annually": total_hours_saved,
            },
            calculation_notes=f"""
                Hours saved per manager per week: {hours_saved_per_manager_weekly}
                Manager count: {manager_count}
                Total hours saved annually: {total_hours_saved:,.0f}
                Hourly rate: ${self.manager_hourly}
                Annual value: ${annual_value:,.0f}
            """.strip(),
            confidence_level="high",
        )

    def _generate_recommendations(
        self, components: List[ROIDetail], team_size: int
    ) -> List[str]:
        """Generate ROI-based recommendations."""
        recommendations = []

        # Find highest value component
        sorted_components = sorted(components, key=lambda c: c.annual_value, reverse=True)
        top_component = sorted_components[0]

        recommendations.append(
            f"Focus on {top_component.category.value.replace('_', ' ')}: "
            f"represents ${top_component.annual_value:,.0f} annual value"
        )

        # Team size specific recommendations
        if team_size < 20:
            recommendations.append(
                "Small team benefit: High visibility per developer, "
                "personalized burnout alerts more actionable"
            )
        elif team_size > 100:
            recommendations.append(
                "Enterprise benefit: At scale, productivity gains compound. "
                "Consider custom integrations for maximum ROI."
            )

        # Check confidence levels
        low_confidence = [c for c in components if c.confidence_level == "low"]
        if low_confidence:
            recommendations.append(
                f"Improve data collection for: {', '.join(c.category.value for c in low_confidence)} "
                f"to increase ROI confidence"
            )

        return recommendations

    def calculate_tco_comparison(
        self,
        team_size: int,
        competitor_cost_per_dev_month: float = 30,  # GitPrime/Linear
    ) -> Dict[str, Any]:
        """
        Calculate Total Cost of Ownership comparison with competitors.

        Args:
            team_size: Number of developers
            competitor_cost_per_dev_month: Competitor price per dev/month

        Returns:
            Dictionary with TCO comparison data
        """
        devhouse26_annual = team_size * self.monthly_cost * 12
        competitor_annual = team_size * competitor_cost_per_dev_month * 12
        savings = competitor_annual - devhouse26_annual

        return {
            "team_size": team_size,
            "devhouse26_annual_cost": devhouse26_annual,
            "competitor_annual_cost": competitor_annual,
            "annual_savings": savings,
            "savings_percent": (savings / competitor_annual) * 100,
            "three_year_savings": savings * 3,
        }


def generate_roi_report(
    calculator: ROICalculator,
    team_id: str,
    team_size: int,
    output_format: str = "text",
) -> str:
    """
    Generate a formatted ROI report.

    Args:
        calculator: Configured ROICalculator instance
        team_id: Team identifier
        team_size: Number of developers
        output_format: "text", "markdown", or "json"

    Returns:
        Formatted ROI report string
    """
    roi = calculator.calculate_for_team(team_id=team_id, team_size=team_size)

    if output_format == "text":
        lines = [
            "=" * 60,
            "DevHouse26 ROI Analysis",
            "=" * 60,
            f"Team: {team_id}",
            f"Team Size: {team_size} developers",
            f"Average Salary: ${calculator.avg_salary:,.0f}",
            "",
            "ANNUAL ROI BREAKDOWN",
            "-" * 40,
        ]

        for component in roi.roi_components:
            lines.append(
                f"{component.category.value.replace('_', ' ').title():<30} "
                f"${component.annual_value:>12,.0f}"
            )

        lines.extend([
            "-" * 40,
            f"{'TOTAL ANNUAL ROI':<30} ${roi.total_annual_roi:>12,.0f}",
            "",
            "COSTS",
            "-" * 40,
            f"{'DevHouse26 Annual Cost':<30} ${roi.team_size * calculator.monthly_cost * 12:>12,.0f}",
            f"{'Monthly per Developer':<30} ${calculator.monthly_cost:>12,.0f}",
            "",
            "METRICS",
            "-" * 40,
            f"{'ROI Ratio':<30} {roi.roi_ratio():>12.1f}x",
            f"{'Net Gain':<30} {roi.percentage_gain():>11.0f}%",
            f"{'Break-even':<30} {roi.break_even_months:>11.1f} months",
            f"{'3-Year Value':<30} ${roi.three_year_value:>12,.0f}",
            "",
            "RECOMMENDATIONS",
            "-" * 40,
        ])

        for rec in roi.recommendations:
            lines.append(f"• {rec}")

        lines.extend(["", "=" * 60])

        return "\n".join(lines)

    elif output_format == "markdown":
        lines = [
            f"# DevHouse26 ROI Analysis: {team_id}",
            "",
            f"**Team Size:** {team_size} developers  ",
            f"**Average Salary:** ${calculator.avg_salary:,.0f}  ",
            f"**Analysis Date:** {roi.calculated_at.strftime('%Y-%m-%d')}  ",
            "",
            "## Annual ROI Breakdown",
            "",
            "| Category | Annual Value | Confidence |",
            "|----------|--------------|------------|",
        ]

        for component in roi.roi_components:
            lines.append(
                f"| {component.category.value.replace('_', ' ').title()} | "
                f"${component.annual_value:,.0f} | {component.confidence_level} |"
            )

        annual_cost = roi.team_size * calculator.monthly_cost * 12

        lines.extend([
            "| **TOTAL** | **" + f"${roi.total_annual_roi:,.0f}" + "** | |",
            "",
            "## Investment",
            "",
            f"- **DevHouse26 Annual Cost:** ${annual_cost:,.0f}",
            f"- **Cost per Developer/Month:** ${calculator.monthly_cost:.0f}",
            "",
            "## Key Metrics",
            "",
            f"- **ROI Ratio:** {roi.roi_ratio():.1f}x",
            f"- **Net Gain:** {roi.percentage_gain():.0f}%",
            f"- **Break-even:** {roi.break_even_months:.1f} months",
            f"- **3-Year Value:** ${roi.three_year_value:,.0f}",
            f"- **Risk-Adjusted Value:** ${roi.risk_adjusted_value:,.0f}",
            "",
            "## Recommendations",
            "",
        ])

        for rec in roi.recommendations:
            lines.append(f"- {rec}")

        return "\n".join(lines)

    else:
        import json
        return json.dumps({
            "team_id": roi.team_id,
            "calculated_at": roi.calculated_at.isoformat(),
            "team_size": roi.team_size,
            "total_annual_roi": roi.total_annual_roi,
            "roi_ratio": roi.roi_ratio(),
            "break_even_months": roi.break_even_months,
            "three_year_value": roi.three_year_value,
            "components": [
                {
                    "category": c.category.value,
                    "annual_value": c.annual_value,
                    "confidence": c.confidence_level,
                }
                for c in roi.roi_components
            ],
        }, indent=2)
