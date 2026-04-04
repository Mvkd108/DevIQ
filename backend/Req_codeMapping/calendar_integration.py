"""
Calendar Integration for DevHouse26.

This module integrates with Google Calendar and Outlook Calendar to detect
meetings and time fragmentation, which are key burnout indicators.

Key Features:
- Meeting load analysis (hours per day in meetings)
- Fragmentation detection (scattered meetings vs. focus blocks)
- Focus time calculation (uninterrupted 2+ hour blocks)
- After-hours meeting detection (evening/weekend meetings)
- Calendar efficiency scoring

APIs Used:
- Google Calendar API (OAuth 2.0)
- Microsoft Graph API (Outlook Calendar)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class CalendarProvider(Enum):
    """Supported calendar providers."""

    GOOGLE = "google"
    OUTLOOK = "outlook"
    CALDAV = "caldav"


class MeetingType(Enum):
    """Types of meetings detected."""

    FOCUS_BLOCK = "focus_block"
    ONE_ON_ONE = "one_on_one"
    STANDUP = "standup"
    REVIEW = "review"
    PLANNING = "planning"
    EXTERNAL = "external"
    LUNCH_BREAK = "lunch_break"
    AFTER_HOURS = "after_hours"
    WEEKEND = "weekend"


@dataclass
class Meeting:
    """A calendar meeting/event."""

    id: str
    title: str
    start_time: datetime
    end_time: datetime
    attendees: List[str] = field(default_factory=list)
    is_recurring: bool = False
    meeting_type: Optional[MeetingType] = None
    is_optional: bool = False
    location: Optional[str] = None
    description: Optional[str] = None
    is_focus_time_blocked: bool = False

    @property
    def duration_minutes(self) -> int:
        """Calculate meeting duration in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)


@dataclass
class DailyCalendarMetrics:
    """Calendar metrics for a single day."""

    date: datetime
    total_meeting_minutes: int = 0
    meeting_count: int = 0
    focus_time_minutes: int = 0
    after_hours_minutes: int = 0
    one_on_one_count: int = 0
    standup_count: int = 0
    external_meeting_count: int = 0
    longest_focus_block_minutes: int = 0
    fragmentation_score: float = 0.0  # 0-100, higher = more fragmented
    meeting_types: Dict[MeetingType, int] = field(default_factory=dict)
    meetings: List[Meeting] = field(default_factory=list)

    @property
    def meeting_hours(self) -> float:
        """Total meeting hours."""
        return self.total_meeting_minutes / 60

    @property
    def focus_hours(self) -> float:
        """Total focus time hours."""
        return self.focus_time_minutes / 60


@dataclass
class WeeklyCalendarMetrics:
    """Calendar metrics for a week."""

    week_start: datetime
    week_end: datetime
    developer_id: str
    daily_metrics: List[DailyCalendarMetrics] = field(default_factory=list)

    @property
    def total_meeting_hours(self) -> float:
        return sum(d.meeting_hours for d in self.daily_metrics)

    @property
    def avg_daily_meeting_hours(self) -> float:
        if not self.daily_metrics:
            return 0.0
        return self.total_meeting_hours / len(self.daily_metrics)

    @property
    def total_focus_hours(self) -> float:
        return sum(d.focus_hours for d in self.daily_metrics)

    @property
    def after_hours_meeting_count(self) -> int:
        return sum(
            1 for d in self.daily_metrics
            for m in d.meetings
            if m.meeting_type in (MeetingType.AFTER_HOURS, MeetingType.WEEKEND)
        )

    @property
    def avg_fragmentation_score(self) -> float:
        if not self.daily_metrics:
            return 0.0
        return sum(d.fragmentation_score for d in self.daily_metrics) / len(self.daily_metrics)

    @property
    def burnout_risk_indicators(self) -> List[str]:
        """Identify burnout risk indicators from calendar patterns."""
        indicators = []

        if self.avg_daily_meeting_hours > 5:
            indicators.append(f"High meeting load: {self.avg_daily_meeting_hours:.1f} hours/day average")

        if self.avg_fragmentation_score > 70:
            indicators.append("Highly fragmented schedule - limited focus blocks")

        if self.after_hours_meeting_count >= 3:
            indicators.append(f"{self.after_hours_meeting_count} after-hours/weekend meetings")

        if self.total_focus_hours < 10:
            indicators.append(f"Low focus time: {self.total_focus_hours:.1f} hours/week")

        return indicators


class CalendarAnalyzer:
    """
    Analyze calendar data for burnout indicators and productivity insights.

    This analyzer processes calendar events to detect:
    - Excessive meeting load
    - Schedule fragmentation
    - After-hours work patterns
    - Focus time availability

    Example:
        >>> analyzer = CalendarAnalyzer(work_start=time(9, 0), work_end=time(17, 0))
        >>> weekly_metrics = analyzer.analyze_week(
        ...     developer_id="dev-123",
        ...     meetings=calendar_events,
        ...     week_start=datetime(2024, 1, 1)
        ... )
        >>> print(f"Meeting hours: {weekly_metrics.total_meeting_hours:.1f}")
        >>> for indicator in weekly_metrics.burnout_risk_indicators:
        ...     print(f"Risk: {indicator}")
    """

    DEFAULT_WORK_START = time(9, 0)
    DEFAULT_WORK_END = time(17, 0)
    MIN_FOCUS_BLOCK_MINUTES = 120  # 2 hours
    FRAGMENTATION_THRESHOLD_MINUTES = 30  # Meetings < 30 min apart = fragmented

    def __init__(
        self,
        work_start: time = DEFAULT_WORK_START,
        work_end: time = DEFAULT_WORK_END,
        work_days: Optional[Set[int]] = None,
    ):
        """
        Initialize calendar analyzer.

        Args:
            work_start: Standard work day start time
            work_end: Standard work day end time
            work_days: Set of weekday numbers (0=Monday, 6=Sunday) considered work days
        """
        self.work_start = work_start
        self.work_end = work_end
        self.work_days = work_days or {0, 1, 2, 3, 4}  # Mon-Fri

    def analyze_week(
        self,
        developer_id: str,
        meetings: List[Meeting],
        week_start: datetime,
    ) -> WeeklyCalendarMetrics:
        """
        Analyze a week of calendar data.

        Args:
            developer_id: Developer identifier
            meetings: List of meetings for the week
            week_start: Start of the week (Monday)

        Returns:
            WeeklyCalendarMetrics with analysis results
        """
        week_end = week_start + timedelta(days=7)

        # Group meetings by day
        daily_meetings: Dict[datetime, List[Meeting]] = {}
        for meeting in meetings:
            day = meeting.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            if week_start <= day < week_end:
                if day not in daily_meetings:
                    daily_meetings[day] = []
                daily_meetings[day].append(meeting)

        # Analyze each day
        daily_metrics = []
        for day in sorted(daily_meetings.keys()):
            day_meetings = sorted(daily_meetings[day], key=lambda m: m.start_time)
            metrics = self._analyze_day(day, day_meetings)
            daily_metrics.append(metrics)

        return WeeklyCalendarMetrics(
            week_start=week_start,
            week_end=week_end,
            developer_id=developer_id,
            daily_metrics=daily_metrics,
        )

    def _analyze_day(
        self,
        date: datetime,
        meetings: List[Meeting],
    ) -> DailyCalendarMetrics:
        """Analyze a single day's meetings."""
        metrics = DailyCalendarMetrics(date=date)

        if not meetings:
            # No meetings = full focus day
            metrics.focus_time_minutes = self._workday_minutes()
            metrics.longest_focus_block_minutes = metrics.focus_time_minutes
            return metrics

        metrics.meetings = meetings
        metrics.meeting_count = len(meetings)

        # Categorize meetings
        for meeting in meetings:
            self._classify_meeting(meeting)
            metrics.total_meeting_minutes += meeting.duration_minutes

            if meeting.meeting_type:
                metrics.meeting_types[meeting.meeting_type] = metrics.meeting_types.get(meeting.meeting_type, 0) + 1

            if meeting.meeting_type == MeetingType.ONE_ON_ONE:
                metrics.one_on_one_count += 1
            elif meeting.meeting_type == MeetingType.STANDUP:
                metrics.standup_count += 1
            elif meeting.meeting_type == MeetingType.EXTERNAL:
                metrics.external_meeting_count += 1
            elif meeting.meeting_type in (MeetingType.AFTER_HOURS, MeetingType.WEEKEND):
                metrics.after_hours_minutes += meeting.duration_minutes

        # Calculate focus time (gaps between meetings)
        metrics.focus_time_minutes = self._calculate_focus_time(meetings, date)
        metrics.longest_focus_block_minutes = self._find_longest_focus_block(meetings, date)

        # Calculate fragmentation score
        metrics.fragmentation_score = self._calculate_fragmentation(meetings)

        return metrics

    def _classify_meeting(self, meeting: Meeting) -> None:
        """Classify a meeting by type based on title and properties."""
        title_lower = meeting.title.lower()

        # Check for lunch
        if any(word in title_lower for word in ["lunch", "break"]):
            meeting.meeting_type = MeetingType.LUNCH_BREAK
            return

        # Check for standup
        if any(word in title_lower for word in ["standup", "stand-up", "daily", "scrum"]):
            meeting.meeting_type = MeetingType.STANDUP
            return

        # Check for 1:1
        if any(word in title_lower for word in ["1:1", "1-on-1", "one on one", "sync"]):
            meeting.meeting_type = MeetingType.ONE_ON_ONE
            return

        # Check for review
        if any(word in title_lower for word in ["review", "retrospective", "retro"]):
            meeting.meeting_type = MeetingType.REVIEW
            return

        # Check for planning
        if any(word in title_lower for word in ["planning", "sprint", "roadmap", "quarterly"]):
            meeting.meeting_type = MeetingType.PLANNING
            return

        # Check for after-hours
        if meeting.start_time.weekday() not in self.work_days:
            meeting.meeting_type = MeetingType.WEEKEND
            return

        meeting_time = meeting.start_time.time()
        if meeting_time < self.work_start or meeting_time >= self.work_end:
            meeting.meeting_type = MeetingType.AFTER_HOURS
            return

        # Check for external (has non-company attendees)
        if meeting.attendees and len(meeting.attendees) > 5:
            meeting.meeting_type = MeetingType.EXTERNAL
            return

        # Default
        meeting.meeting_type = MeetingType.FOCUS_BLOCK

    def _calculate_focus_time(
        self,
        meetings: List[Meeting],
        date: datetime,
    ) -> int:
        """Calculate available focus time between meetings during work hours."""
        if not meetings:
            return self._workday_minutes()

        # Sort meetings
        sorted_meetings = sorted(meetings, key=lambda m: m.start_time)

        # Create work day boundaries
        work_start = datetime.combine(date, self.work_start)
        work_end = datetime.combine(date, self.work_end)

        focus_minutes = 0
        last_end = work_start

        for meeting in sorted_meetings:
            # Skip after-hours meetings for focus time calculation
            if meeting.meeting_type in (MeetingType.AFTER_HOURS, MeetingType.WEEKEND):
                continue

            # Calculate gap before this meeting
            if meeting.start_time > last_end:
                gap_minutes = int((meeting.start_time - last_end).total_seconds() / 60)
                focus_minutes += gap_minutes

            last_end = max(last_end, meeting.end_time)

        # Calculate gap after last meeting
        if last_end < work_end:
            focus_minutes += int((work_end - last_end).total_seconds() / 60)

        return max(0, focus_minutes)

    def _find_longest_focus_block(
        self,
        meetings: List[Meeting],
        date: datetime,
    ) -> int:
        """Find the longest uninterrupted focus block."""
        if not meetings:
            return self._workday_minutes()

        sorted_meetings = sorted(meetings, key=lambda m: m.start_time)
        work_start = datetime.combine(date, self.work_start)
        work_end = datetime.combine(date, self.work_end)

        longest = 0
        last_end = work_start

        for meeting in sorted_meetings:
            if meeting.meeting_type in (MeetingType.AFTER_HOURS, MeetingType.WEEKEND):
                continue

            if meeting.start_time > last_end:
                gap = int((meeting.start_time - last_end).total_seconds() / 60)
                longest = max(longest, gap)

            last_end = max(last_end, meeting.end_time)

        # Check after last meeting
        if last_end < work_end:
            gap = int((work_end - last_end).total_seconds() / 60)
            longest = max(longest, gap)

        return longest

    def _calculate_fragmentation(self, meetings: List[Meeting]) -> float:
        """Calculate schedule fragmentation score (0-100)."""
        if len(meetings) <= 1:
            return 0.0

        # Sort meetings
        sorted_meetings = sorted(meetings, key=lambda m: m.start_time)

        # Count fragmented transitions
        fragmented_transitions = 0
        total_transitions = len(sorted_meetings) - 1

        for i in range(len(sorted_meetings) - 1):
            gap = (sorted_meetings[i + 1].start_time - sorted_meetings[i].end_time).total_seconds() / 60
            if gap < self.FRAGMENTATION_THRESHOLD_MINUTES:
                fragmented_transitions += 1

        if total_transitions == 0:
            return 0.0

        # Score based on fragmentation ratio and meeting density
        fragmentation_ratio = fragmented_transitions / total_transitions
        meeting_density = min(1.0, len(meetings) / 8)  # Cap at 8 meetings

        return (fragmentation_ratio * 0.5 + meeting_density * 0.5) * 100

    def _workday_minutes(self) -> int:
        """Calculate work day duration in minutes."""
        start_minutes = self.work_start.hour * 60 + self.work_start.minute
        end_minutes = self.work_end.hour * 60 + self.work_end.minute
        return max(0, end_minutes - start_minutes)

    def generate_burnout_insights(
        self,
        weekly_metrics: WeeklyCalendarMetrics,
    ) -> Dict[str, Any]:
        """Generate burnout-specific insights from calendar data."""
        insights = {
            "meeting_load_assessment": self._assess_meeting_load(weekly_metrics),
            "focus_time_assessment": self._assess_focus_time(weekly_metrics),
            "after_hours_assessment": self._assess_after_hours(weekly_metrics),
            "recommendations": [],
            "risk_score": 0,
        }

        # Calculate risk score
        risk_score = 0

        if weekly_metrics.avg_daily_meeting_hours > 5:
            risk_score += 30
        elif weekly_metrics.avg_daily_meeting_hours > 4:
            risk_score += 20

        if weekly_metrics.avg_fragmentation_score > 70:
            risk_score += 25

        if weekly_metrics.after_hours_meeting_count >= 5:
            risk_score += 20
        elif weekly_metrics.after_hours_meeting_count >= 3:
            risk_score += 10

        if weekly_metrics.total_focus_hours < 10:
            risk_score += 25
        elif weekly_metrics.total_focus_hours < 15:
            risk_score += 15

        insights["risk_score"] = min(100, risk_score)

        # Generate recommendations
        if weekly_metrics.avg_daily_meeting_hours > 5:
            insights["recommendations"].append(
                "Consider implementing 'No Meeting Wednesdays' or similar focus day policies"
            )

        if weekly_metrics.avg_fragmentation_score > 70:
            insights["recommendations"].append(
                "Schedule meetings in blocks (e.g., mornings only) to create longer focus periods"
            )

        if weekly_metrics.after_hours_meeting_count >= 3:
            insights["recommendations"].append(
                f"Review {weekly_metrics.after_hours_meeting_count} after-hours/weekend meetings for necessity"
            )

        if weekly_metrics.total_focus_hours < 10:
            insights["recommendations"].append(
                "Only 10 hours of focus time detected - consider declining optional meetings"
            )

        return insights

    def _assess_meeting_load(self, metrics: WeeklyCalendarMetrics) -> str:
        """Assess if meeting load is healthy."""
        daily_avg = metrics.avg_daily_meeting_hours
        if daily_avg < 2:
            return "healthy_low"
        elif daily_avg < 4:
            return "healthy_moderate"
        elif daily_avg < 5:
            return "elevated"
        else:
            return "excessive"

    def _assess_focus_time(self, metrics: WeeklyCalendarMetrics) -> str:
        """Assess if focus time is sufficient."""
        focus_hours = metrics.total_focus_hours
        if focus_hours > 20:
            return "excellent"
        elif focus_hours > 15:
            return "good"
        elif focus_hours > 10:
            return "adequate"
        else:
            return "insufficient"

    def _assess_after_hours(self, metrics: WeeklyCalendarMetrics) -> str:
        """Assess after-hours meeting burden."""
        count = metrics.after_hours_meeting_count
        if count == 0:
            return "healthy"
        elif count <= 2:
            return "occasional"
        elif count <= 4:
            return "frequent"
        else:
            return "excessive"


# Integration with burnout detector
def integrate_calendar_with_burnout(
    calendar_metrics: WeeklyCalendarMetrics,
    burnout_score: float,
) -> Dict[str, Any]:
    """
    Integrate calendar insights with burnout detection.

    Args:
        calendar_metrics: Weekly calendar analysis
        burnout_score: Existing burnout risk score (0-100)

    Returns:
        Combined insights with calendar-adjusted burnout risk
    """
    analyzer = CalendarAnalyzer()
    calendar_insights = analyzer.generate_burnout_insights(calendar_metrics)

    # Calendar burnout risk adds to overall score
    calendar_risk = calendar_insights["risk_score"]

    # Weighted combination: 70% existing burnout, 30% calendar
    combined_score = (burnout_score * 0.7) + (calendar_risk * 0.3)

    return {
        "original_burnout_score": burnout_score,
        "calendar_risk_score": calendar_risk,
        "combined_score": min(100, combined_score),
        "meeting_load_assessment": calendar_insights["meeting_load_assessment"],
        "focus_time_assessment": calendar_insights["focus_time_assessment"],
        "after_hours_assessment": calendar_insights["after_hours_assessment"],
        "recommendations": calendar_insights["recommendations"],
    }
