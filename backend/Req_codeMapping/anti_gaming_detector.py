"""
Anti-Gaming Scoring Engine for DevHouse26.

This module detects fake productivity patterns and attempts to game the system.
It uses behavioral analysis to identify suspicious activity patterns that don't
represent real engineering work.

Key Indicators:
- Burst commits (many commits in short time)
- Copy-paste coding (large additions with low keystrokes)
- Repetitive keystrokes (fake activity simulation)
- Time-of-day anomalies (automated/scripted commits)
- Low-value commits (whitespace, formatting only)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class GamingPatternType(Enum):
    """Types of gaming patterns detected."""

    BURST_COMMITS = "burst_commits"
    COPY_PASTE_CODING = "copy_paste_coding"
    REPETITIVE_KEYSTROKES = "repetitive_keystrokes"
    TIME_ANOMALY = "time_anomaly"
    LOW_VALUE_COMMITS = "low_value_commits"
    AUTO_FORMATTED_COMMITS = "auto_formatted_commits"
    COMMIT_MESSAGE_SPAM = "commit_message_spam"
    FAKE_REVIEW_ACTIVITY = "fake_review_activity"


@dataclass
class GamingIndicator:
    """A detected gaming indicator."""

    pattern_type: GamingPatternType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    evidence: Dict[str, Any]
    timestamp: datetime
    confidence_score: float  # 0.0 - 1.0


@dataclass
class AntiGamingScore:
    """Overall anti-gaming assessment for a developer."""

    developer_id: str
    calculated_at: datetime
    overall_score: float  # 0-100, higher = more suspicious
    risk_level: str  # "low", "medium", "high", "critical"
    indicators: List[GamingIndicator] = field(default_factory=list)
    pattern_counts: Dict[GamingPatternType, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Ensure pattern_counts includes all types."""
        for pattern_type in GamingPatternType:
            if pattern_type not in self.pattern_counts:
                self.pattern_counts[pattern_type] = 0


class AntiGamingDetector:
    """
    Detects fake productivity patterns and gaming attempts.

    This engine analyzes commit patterns, keystroke data, and activity metrics
to identify suspicious behaviors that don't represent genuine engineering work.

    Example:
        >>> detector = AntiGamingDetector()
        >>> score = detector.analyze_developer(
        ...     developer_id="dev-123",
        ...     commits=commits,
        ...     keystroke_data=keystrokes,
        ...     daily_activity=activity
        ... )
        >>> print(f"Gaming Score: {score.overall_score}")
        >>> for indicator in score.indicators:
        ...     print(f"Detected: {indicator.description}")
    """

    # Thresholds for detection
    BURST_COMMIT_THRESHOLD = 5  # commits in BURST_TIME_WINDOW
    BURST_TIME_WINDOW_MINUTES = 10

    COPY_PASTE_LINES_THRESHOLD = 100  # lines added per keystroke session
    COPY_PASTE_KEYSTROKE_RATIO = 10  # lines per keystroke (high = copy-paste)

    REPETITIVE_KEYSTROKE_THRESHOLD = 0.7  # 70% same keystroke pattern

    AUTO_COMMIT_HOURS = {2, 3, 4}  # Commits at 2-4 AM are suspicious

    LOW_VALUE_PATTERNS = [
        r"^\s*$",  # Whitespace only
        r"^[\s]*[//\#].*",  # Comment only changes
        r"format|lint|style|whitespace|trailing",
    ]

    def __init__(self, custom_thresholds: Optional[Dict[str, Any]] = None):
        """
        Initialize the anti-gaming detector.

        Args:
            custom_thresholds: Optional overrides for detection thresholds
        """
        self.thresholds = {
            "burst_commits": self.BURST_COMMIT_THRESHOLD,
            "burst_window_minutes": self.BURST_TIME_WINDOW_MINUTES,
            "copy_paste_lines": self.COPY_PASTE_LINES_THRESHOLD,
            "copy_paste_ratio": self.COPY_PASTE_KEYSTROKE_RATIO,
            "repetitive_keystroke": self.REPETITIVE_KEYSTROKE_THRESHOLD,
            **(custom_thresholds or {}),
        }

    def analyze_developer(
        self,
        developer_id: str,
        commits: List[Dict[str, Any]],
        keystroke_data: Optional[List[Dict[str, Any]]] = None,
        daily_activity: Optional[List[Dict[str, Any]]] = None,
        review_activity: Optional[List[Dict[str, Any]]] = None,
    ) -> AntiGamingScore:
        """
        Analyze a developer's activity for gaming patterns.

        Args:
            developer_id: Unique developer identifier
            commits: List of commit data dictionaries
            keystroke_data: Optional keystroke telemetry data
            daily_activity: Optional daily aggregated activity
            review_activity: Optional code review activity data

        Returns:
            AntiGamingScore with detected indicators and overall assessment
        """
        indicators: List[GamingIndicator] = []
        now = datetime.utcnow()

        # Analyze commit patterns
        indicators.extend(self._detect_burst_commits(commits))
        indicators.extend(self._detect_low_value_commits(commits))
        indicators.extend(self._detect_time_anomalies(commits))
        indicators.extend(self._detect_commit_message_spam(commits))

        # Analyze keystroke patterns (if available)
        if keystroke_data:
            indicators.extend(self._detect_copy_paste(keystroke_data))
            indicators.extend(self._detect_repetitive_keystrokes(keystroke_data))

        # Analyze review patterns (if available)
        if review_activity:
            indicators.extend(self._detect_fake_reviews(review_activity))

        # Calculate overall score
        overall_score = self._calculate_overall_score(indicators)
        risk_level = self._score_to_risk_level(overall_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(indicators, risk_level)

        # Count patterns by type
        pattern_counts: Dict[GamingPatternType, int] = {}
        for indicator in indicators:
            pattern_counts[indicator.pattern_type] = pattern_counts.get(indicator.pattern_type, 0) + 1

        return AntiGamingScore(
            developer_id=developer_id,
            calculated_at=now,
            overall_score=overall_score,
            risk_level=risk_level,
            indicators=indicators,
            pattern_counts=pattern_counts,
            recommendations=recommendations,
        )

    def _detect_burst_commits(
        self, commits: List[Dict[str, Any]]
    ) -> List[GamingIndicator]:
        """Detect rapid-fire commits in short time windows."""
        indicators = []

        if not commits or len(commits) < 2:
            return indicators

        # Sort by timestamp
        sorted_commits = sorted(
            commits, key=lambda c: c.get("committed_at", datetime.min)
        )

        window_minutes = self.thresholds["burst_window_minutes"]
        threshold = self.thresholds["burst_commits"]

        # Sliding window detection
        for i, commit in enumerate(sorted_commits):
            window_start = commit.get("committed_at", datetime.min)
            window_end = window_start + timedelta(minutes=window_minutes)

            commits_in_window = [
                c for c in sorted_commits
                if window_start <= c.get("committed_at", datetime.min) <= window_end
            ]

            if len(commits_in_window) >= threshold:
                # Calculate total lines changed in burst
                total_lines = sum(
                    c.get("lines_added", 0) + c.get("lines_deleted", 0)
                    for c in commits_in_window
                )

                indicators.append(
                    GamingIndicator(
                        pattern_type=GamingPatternType.BURST_COMMITS,
                        severity="medium",
                        description=f"Detected {len(commits_in_window)} commits in {window_minutes} minutes",
                        evidence={
                            "commits_in_window": len(commits_in_window),
                            "window_minutes": window_minutes,
                            "commit_shas": [c.get("sha", "")[:8] for c in commits_in_window],
                            "total_lines_changed": total_lines,
                        },
                        timestamp=window_start,
                        confidence_score=min(0.9, len(commits_in_window) / threshold * 0.5),
                    )
                )
                break  # Only flag once per burst

        return indicators

    def _detect_copy_paste(
        self, keystroke_data: List[Dict[str, Any]]
    ) -> List[GamingIndicator]:
        """Detect copy-paste coding patterns."""
        indicators = []

        for session in keystroke_data:
            lines_added = session.get("lines_added", 0)
            keystrokes = session.get("keystrokes_count", 0)
            duration_minutes = session.get("duration_minutes", 0)

            if keystrokes == 0:
                continue

            # High lines-to-keystrokes ratio suggests copy-paste
            ratio = lines_added / keystrokes
            threshold = self.thresholds["copy_paste_ratio"]

            if ratio > threshold and lines_added > self.thresholds["copy_paste_lines"]:
                indicators.append(
                    GamingIndicator(
                        pattern_type=GamingPatternType.COPY_PASTE_CODING,
                        severity="high" if ratio > threshold * 2 else "medium",
                        description=f"Copy-paste detected: {lines_added} lines with only {keystrokes} keystrokes",
                        evidence={
                            "lines_added": lines_added,
                            "keystrokes": keystrokes,
                            "ratio": round(ratio, 2),
                            "session_duration": duration_minutes,
                            "file_path": session.get("file_path"),
                        },
                        timestamp=session.get("timestamp", datetime.utcnow()),
                        confidence_score=min(0.95, ratio / (threshold * 3)),
                    )
                )

        return indicators

    def _detect_repetitive_keystrokes(
        self, keystroke_data: List[Dict[str, Any]]
    ) -> List[GamingIndicator]:
        """Detect repetitive keystroke patterns (fake activity)."""
        indicators = []

        for session in keystroke_data:
            keystroke_pattern = session.get("keystroke_sequence", "")
            if not keystroke_pattern or len(keystroke_pattern) < 20:
                continue

            # Check for repetitive patterns (e.g., "aaaaaaaa", "abababab")
            pattern_count = self._count_pattern_repetition(keystroke_pattern)
            total_keystrokes = len(keystroke_pattern)

            if total_keystrokes > 0:
                repetition_ratio = pattern_count / total_keystrokes
                threshold = self.thresholds["repetitive_keystroke"]

                if repetition_ratio > threshold:
                    indicators.append(
                        GamingIndicator(
                            pattern_type=GamingPatternType.REPETITIVE_KEYSTROKES,
                            severity="high" if repetition_ratio > 0.9 else "medium",
                            description=f"Repetitive keystroke pattern detected ({repetition_ratio:.0%} repetition)",
                            evidence={
                                "repetition_ratio": round(repetition_ratio, 3),
                                "sample_pattern": keystroke_pattern[:50],
                                "total_keystrokes": total_keystrokes,
                            },
                            timestamp=session.get("timestamp", datetime.utcnow()),
                            confidence_score=repetition_ratio,
                        )
                    )

        return indicators

    def _count_pattern_repetition(self, sequence: str) -> int:
        """Count repetitive characters in keystroke sequence."""
        if len(sequence) < 2:
            return 0

        repetitive = 0
        for i in range(len(sequence) - 1):
            if sequence[i] == sequence[i + 1]:
                repetitive += 1

        return repetitive

    def _detect_time_anomalies(
        self, commits: List[Dict[str, Any]]
    ) -> List[GamingIndicator]:
        """Detect suspicious commit timing patterns."""
        indicators = []
        auto_commit_hours: Set[int] = set()

        for commit in commits:
            commit_time = commit.get("committed_at")
            if not isinstance(commit_time, datetime):
                continue

            hour = commit_time.hour
            if hour in self.AUTO_COMMIT_HOURS:
                auto_commit_hours.add(hour)

        if len(auto_commit_hours) >= 2:
            # Multiple commits during suspicious hours
            indicators.append(
                GamingIndicator(
                    pattern_type=GamingPatternType.TIME_ANOMALY,
                    severity="medium",
                    description=f"Suspicious commit timing detected (multiple commits at {sorted(auto_commit_hours)}:00)",
                    evidence={
                        "suspicious_hours": sorted(auto_commit_hours),
                        "pattern": "commits_during_automation_hours",
                    },
                    timestamp=datetime.utcnow(),
                    confidence_score=0.6,
                )
            )

        return indicators

    def _detect_low_value_commits(
        self, commits: List[Dict[str, Any]]
    ) -> List[GamingIndicator]:
        """Detect low-value commits (whitespace, formatting only)."""
        indicators = []
        low_value_count = 0
        evidence_commits = []

        for commit in commits:
            message = commit.get("message", "").lower()
            lines_added = commit.get("lines_added", 0)
            lines_deleted = commit.get("lines_deleted", 0)

            # Check message patterns
            is_low_value = any(
                re.search(pattern, message) for pattern in self.LOW_VALUE_PATTERNS
            )

            # Check for large whitespace-only changes
            if lines_added > 50 and lines_deleted > 50 and lines_added == lines_deleted:
                is_low_value = True

            if is_low_value:
                low_value_count += 1
                evidence_commits.append({
                    "sha": commit.get("sha", "")[:8],
                    "message": message[:50],
                })

        if low_value_count >= 3:
            indicators.append(
                GamingIndicator(
                    pattern_type=GamingPatternType.LOW_VALUE_COMMITS,
                    severity="low" if low_value_count < 5 else "medium",
                    description=f"Detected {low_value_count} low-value commits (formatting/whitespace)",
                    evidence={
                        "low_value_count": low_value_count,
                        "example_commits": evidence_commits[:3],
                    },
                    timestamp=datetime.utcnow(),
                    confidence_score=min(0.8, low_value_count / 10),
                )
            )

        return indicators

    def _detect_commit_message_spam(
        self, commits: List[Dict[str, Any]]
    ) -> List[GamingIndicator]:
        """Detect repetitive or spam commit messages."""
        indicators = []

        if len(commits) < 3:
            return indicators

        messages = [c.get("message", "").lower().strip() for c in commits]
        unique_messages = set(messages)

        # High repetition of same message
        if len(messages) > 0:
            repetition_ratio = 1 - (len(unique_messages) / len(messages))

            if repetition_ratio > 0.5:
                indicators.append(
                    GamingIndicator(
                        pattern_type=GamingPatternType.COMMIT_MESSAGE_SPAM,
                        severity="medium",
                        description=f"Repetitive commit messages ({repetition_ratio:.0%} are duplicates)",
                        evidence={
                            "total_commits": len(messages),
                            "unique_messages": len(unique_messages),
                            "repetition_ratio": round(repetition_ratio, 3),
                            "common_messages": self._get_most_common(messages, 3),
                        },
                        timestamp=datetime.utcnow(),
                        confidence_score=repetition_ratio,
                    )
                )

        return indicators

    def _detect_fake_reviews(
        self, review_activity: List[Dict[str, Any]]
    ) -> List[GamingIndicator]:
        """Detect fake or superficial code review activity."""
        indicators = []

        super_fast_reviews = []
        for review in review_activity:
            review_time = review.get("time_seconds", 0)
            if review_time < 30:  # Less than 30 seconds
                super_fast_reviews.append({
                    "pr_id": review.get("pr_id"),
                    "time_seconds": review_time,
                })

        if len(super_fast_reviews) >= 3:
            indicators.append(
                GamingIndicator(
                    pattern_type=GamingPatternType.FAKE_REVIEW_ACTIVITY,
                    severity="high",
                    description=f"Detected {len(super_fast_reviews)} super-fast reviews (<30 seconds)",
                    evidence={
                        "super_fast_count": len(super_fast_reviews),
                        "examples": super_fast_reviews[:3],
                    },
                    timestamp=datetime.utcnow(),
                    confidence_score=0.85,
                )
            )

        return indicators

    def _get_most_common(self, items: List[str], n: int) -> List[tuple]:
        """Get the n most common items with their counts."""
        from collections import Counter
        return Counter(items).most_common(n)

    def _calculate_overall_score(self, indicators: List[GamingIndicator]) -> float:
        """Calculate overall gaming score from indicators."""
        if not indicators:
            return 0.0

        severity_weights = {
            "low": 10,
            "medium": 25,
            "high": 50,
            "critical": 100,
        }

        total_score = sum(
            severity_weights.get(ind.severity, 10) * ind.confidence_score
            for ind in indicators
        )

        # Cap at 100
        return min(100.0, total_score)

    def _score_to_risk_level(self, score: float) -> str:
        """Convert numeric score to risk level."""
        if score >= 75:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 25:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self, indicators: List[GamingIndicator], risk_level: str
    ) -> List[str]:
        """Generate recommendations based on detected patterns."""
        recommendations = []

        if risk_level == "low":
            recommendations.append("No significant gaming patterns detected. Continue monitoring.")
            return recommendations

        # Pattern-specific recommendations
        pattern_types = {ind.pattern_type for ind in indicators}

        if GamingPatternType.BURST_COMMITS in pattern_types:
            recommendations.append(
                "Consider implementing commit squashing or encourage atomic commits. "
                "Burst commits may indicate batch processing of work."
            )

        if GamingPatternType.COPY_PASTE_CODING in pattern_types:
            recommendations.append(
                "Review code quality metrics. High copy-paste ratios may indicate "
                "technical debt accumulation or lack of refactoring."
            )

        if GamingPatternType.REPETITIVE_KEYSTROKES in pattern_types:
            recommendations.append(
                "Review telemetry data integrity. Repetitive keystroke patterns "
                "may indicate automation or fake activity."
            )

        if GamingPatternType.TIME_ANOMALY in pattern_types:
            recommendations.append(
                "Verify if commits at unusual hours are automated (CI/CD) or "
                "require work-life balance discussion."
            )

        if GamingPatternType.LOW_VALUE_COMMITS in pattern_types:
            recommendations.append(
                "Consider implementing pre-commit hooks for formatting. "
                "Low-value commits clutter git history."
            )

        if GamingPatternType.FAKE_REVIEW_ACTIVITY in pattern_types:
            recommendations.append(
                "Review code review guidelines. Fast approvals without proper "
                "review may compromise code quality."
            )

        return recommendations


def run_anti_gaming_analysis(
    developer_id: str,
    storage_provider,
    lookback_days: int = 14,
) -> AntiGamingScore:
    """
    Run anti-gaming analysis using stored data.

    Args:
        developer_id: Developer to analyze
        storage_provider: Storage provider for fetching data
        lookback_days: Days of history to analyze

    Returns:
        AntiGamingScore with detected patterns
    """
    # Fetch data from storage
    since = datetime.utcnow() - timedelta(days=lookback_days)

    # This would query actual storage in production
    # For now, return a template
    detector = AntiGamingDetector()

    # Placeholder: In real implementation, fetch from storage
    commits = []  # storage.get_commits(developer_id, since)
    keystrokes = []  # storage.get_keystrokes(developer_id, since)
    activity = []  # storage.get_daily_activity(developer_id, since)

    return detector.analyze_developer(
        developer_id=developer_id,
        commits=commits,
        keystroke_data=keystrokes,
        daily_activity=activity,
    )
