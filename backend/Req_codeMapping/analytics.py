from __future__ import annotations

import re
from typing import Any, Optional

try:
    from showcase_summaries import build_showcase_summaries as build_showcase_summaries_impl
    SHOWCASE_SUMMARIES_IMPORT_ERROR = ""
except ModuleNotFoundError as exc:
    build_showcase_summaries_impl = None
    SHOWCASE_SUMMARIES_IMPORT_ERROR = str(exc)


def showcase_summaries_import_error() -> str:
    return SHOWCASE_SUMMARIES_IMPORT_ERROR


def showcase_summaries_available() -> bool:
    return build_showcase_summaries_impl is not None


STOP_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "into", "your", "when",
    "were", "been", "have", "has", "had", "about", "after", "before", "there",
    "their", "them", "then", "than", "also", "only", "each", "able", "using",
    "used", "will", "would", "could", "should", "into", "over", "under", "main",
    "feat", "fix", "task", "jira", "issue", "commit", "code", "test", "tests",
}


def human_list(items: list[str]) -> str:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def build_dashboard_analytics(
    issues: list[dict[str, Any]],
    events: list[dict[str, Any]],
    sync_result: Optional[dict[str, Any]] = None,
    feedback_count: int = 0,
) -> dict[str, Any]:
    event_map = {str(event.get("commit_id") or ""): event for event in events if str(event.get("commit_id") or "").strip()}
    linked_commit_ids = {
        str(commit_id)
        for issue in issues
        for commit_id in (issue.get("commits") or [])
        if str(commit_id or "").strip()
    }
    intake_profiles = build_project_intake_profiles(issues, event_map)
    effort_estimates = build_effort_estimates(issues, event_map)
    developer_metrics = build_developer_metrics(events, issues, linked_commit_ids)
    issue_impact_summaries = build_issue_impact_summaries(intake_profiles, effort_estimates)
    developer_impact_summaries = build_developer_impact_summaries(developer_metrics)
    knowledge_risks = build_knowledge_risks(events)
    knowledge_risk_summary = build_knowledge_risk_summary(knowledge_risks)
    elevated_knowledge_risks = [risk for risk in knowledge_risks if risk.get("severity") in {"high", "medium"}]
    if build_showcase_summaries_impl is None:
        showcase_summaries = {
            "meta": {
                "generated_at": None,
                "generated_from": ["core analytics only"],
                "inference_level": "high",
                "evidence_count": len(events),
                "section_labels": {
                    "observed": "Observed in data",
                    "inferred": "Deterministic reading",
                },
                "section_descriptions": {
                    "observed": "Facts are pulled directly from linked issues, commits, telemetry, and delivery-stage records.",
                    "inferred": "Judgments are deterministic interpretations of workload, freshness, continuity risk, and delivery readiness.",
                },
            },
            "portfolio_overview": {
                "headline": "Showcase summaries unavailable in this deployment.",
                "executive_summary": "Weekly narrative summaries are unavailable because the optional summary module is not installed in this deployment.",
                "summary": "The weekly readable review is unavailable because the optional summary module is not installed in this deployment.",
                "manager_summary": "The summary module is not installed, so only core analytics are available.",
                "developer_summary": "Developer-facing readable summaries are temporarily unavailable.",
                "risk_summary": "Risk and effort tables still remain available in the baseline analytics section.",
                "confidence": "low",
                "confidence_reason": "Low confidence because the optional summary module is unavailable in this environment.",
                "confidence_detail": {
                    "level": "low",
                    "reason": "Low confidence because the optional summary module is unavailable in this environment.",
                    "score": 0.0,
                    "supporting_evidence": [],
                    "missing_evidence": ["summary module not installed"],
                    "improve_confidence": "To improve confidence, install the optional summary module.",
                },
                "evidence_count": len(events),
                "generated_from": ["core analytics only"],
                "inference_level": "high",
                "risk_level": "low",
                "freshness_note": "Freshness is unclear because the readable summary module is unavailable.",
                "freshness_level": "stale",
                "uncertainty_note": "Uncertainty is high because the readable summary module is unavailable in this environment.",
                "traceability_note": "Traceability can still be reviewed from the baseline analytics sections, but not through the narrative summary surface.",
                "follow_up": "Install the optional summary module to enable weekly readable review cards.",
                "why_it_matters": "This matters because weekly operating review is unavailable until the optional summary module is installed.",
                "review_focus": "Review focus should stay on baseline analytics until the readable summary module is available.",
                "top_risk_driver": "The top risk driver is missing narrative intelligence coverage in this deployment.",
                "recommended_follow_up": "Install the optional summary module to enable weekly readable review cards.",
                "summary_confidence_band": "Operationally weak",
                "action_priority": "watch",
                "review_window": "Review within this sprint",
                "review_owner": "engineering manager",
                "weekly_review": {
                    "scope": "portfolio",
                    "observed_snapshot": [],
                    "inferred_signal": [
                        "Narrative output is unavailable because the optional summary module is not installed."
                    ],
                    "decision_basis": "Confidence is low until the summary module is installed.",
                    "next_action": "Install the optional summary module to enable weekly readable review cards.",
                    "action_priority": "watch",
                    "review_window": "Review within this sprint",
                },
                "stats": [],
            },
            "coverage": {
                "delivery": {"stage_coverage_pct": 0.0, "connector_stage_coverage_pct": 0.0, "inferred_stage_coverage_pct": 0.0, "stale_requirements": 0},
                "telemetry": {"field_coverage_pct": 0.0, "tracked_events": len(events), "tracked_contributors": len({event_actor(event) for event in events})},
            },
            "developer_weekly": [],
            "manager_contributions": [],
            "issue_impacts": [],
            "logic_notes": ["Optional showcase summary module is unavailable in this environment."],
        }
    else:
        showcase_summaries = build_showcase_summaries_impl(
            issues=issues,
            events=events,
            intake_profiles=intake_profiles,
            effort_estimates=effort_estimates,
            developer_metrics=developer_metrics,
            knowledge_risks=elevated_knowledge_risks,
        )

    total_requirements = len(issues)
    ownership_coverage = percent(
        len([issue for issue in issues if issue.get("assignee_email") or issue.get("reporter_email")]),
        total_requirements,
    )
    timeline_coverage = percent(
        len([issue for issue in issues if issue.get("jira_created_at") or issue.get("jira_updated_at")]),
        total_requirements,
    )
    linked_requirements = len([issue for issue in issues if issue.get("commits")])
    estimated_requirements = len([estimate for estimate in effort_estimates if estimate["observed_effort_points"] > 0])

    return {
        "project_intake": {
            "requirements_ingested": total_requirements,
            "linked_requirements": linked_requirements,
            "ownership_coverage_pct": ownership_coverage,
            "timeline_coverage_pct": timeline_coverage,
            "estimated_requirements": estimated_requirements,
            "profiles": intake_profiles[:8],
        },
        "effort_estimates": effort_estimates[:10],
        "developer_metrics": developer_metrics[:10],
        "impact_summaries": {
            "issues": issue_impact_summaries[:6],
            "developers": developer_impact_summaries[:6],
        },
        "transparency": {
            "scoring_model": [
                {"component": "Delivery", "weight": 35, "description": "Requirement-linked commits and fulfilled issues."},
                {"component": "Execution", "weight": 25, "description": "Observed engineering effort from active minutes and code change volume."},
                {"component": "Ownership", "weight": 20, "description": "Breadth across modules and repositories."},
                {"component": "Sustainability", "weight": 20, "description": "Penalizes heavy overtime concentration."},
            ],
            "knowledge_risk_model": build_knowledge_risk_model(),
            "top_scorecards": [
                {
                    "developer": metric["developer"],
                    "impact_score": metric["impact_score"],
                    "delivery_score": metric["delivery_score"],
                    "execution_score": metric["execution_score"],
                    "ownership_score": metric["ownership_score"],
                    "sustainability_score": metric["sustainability_score"],
                    "reasons": metric["reasons"],
                }
                for metric in developer_metrics[:5]
            ],
            "mapping_explainability": {
                "high_confidence_links": len([match for update in (sync_result or {}).get("updates", []) for match in update.get("matches", []) if match.get("confidence") == "high"]),
                "medium_confidence_links": len([match for update in (sync_result or {}).get("updates", []) for match in update.get("matches", []) if match.get("confidence") == "medium"]),
                "review_overrides": feedback_count,
            },
        },
        "showcase_summaries": showcase_summaries,
        "knowledge_risk_summary": knowledge_risk_summary,
        "knowledge_risks": knowledge_risks[:8],
        "activity_log": build_activity_log(events),
    }


def build_project_intake_profiles(
    issues: list[dict[str, Any]],
    event_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for issue in issues:
        commit_ids = [str(commit_id) for commit_id in (issue.get("commits") or []) if str(commit_id or "").strip()]
        linked_events = [event_map[commit_id] for commit_id in commit_ids if commit_id in event_map]
        owners = dedupe_preserve_order(
            [
                normalize_spaces(str(issue.get("assignee_email") or "")),
                normalize_spaces(str(issue.get("reporter_email") or "")),
            ]
            + [event_actor(event) for event in linked_events]
        )
        commit_times = [parse_datetime(event.get("timestamp")) for event in linked_events]
        commit_times = [value for value in commit_times if value is not None]
        profiles.append(
            {
                "issue_id": issue.get("issue_id"),
                "title": issue.get("title"),
                "owners": owners,
                "roles_identified": len(owners),
                "contributors": len({event_actor(event) for event in linked_events}),
                "linked_commits": len(commit_ids),
                "timeline_start": issue.get("jira_created_at") or issue.get("created_at"),
                "timeline_end": issue.get("jira_updated_at") or issue.get("updated_at"),
                "first_commit_at": min(commit_times).isoformat() if commit_times else None,
                "last_commit_at": max(commit_times).isoformat() if commit_times else None,
                "intake_source": profile_source(issue),
            }
        )
    profiles.sort(key=lambda item: (item["linked_commits"], item["roles_identified"]), reverse=True)
    return profiles


def build_effort_estimates(
    issues: list[dict[str, Any]],
    event_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    estimates: list[dict[str, Any]] = []
    for issue in issues:
        issue_text = build_requirement_text(issue)
        complexity_tokens = tokenize(issue_text)
        commit_ids = [str(commit_id) for commit_id in (issue.get("commits") or []) if str(commit_id or "").strip()]
        linked_events = [event_map[commit_id] for commit_id in commit_ids if commit_id in event_map]
        linked_commit_count = len(commit_ids)
        active_minutes = sum(to_number(event.get("active_minutes")) for event in linked_events)
        total_changes = sum(to_number(event.get("total_changes")) for event in linked_events)
        debug_sessions = sum(to_number(event.get("debug_session_count")) for event in linked_events)
        module_count = len({module for event in linked_events for module in (event.get("modules_touched") or []) if module})
        priority_boost = {"highest": 2.4, "high": 1.8, "medium": 1.1, "low": 0.6, "lowest": 0.3}.get(str(issue.get("priority") or "").lower(), 0.9)
        issue_type_boost = {"epic": 2.0, "story": 1.4, "task": 1.0, "bug": 0.8}.get(str(issue.get("issue_type") or "").lower(), 1.0)

        planned_effort = round(min(13.0, 1.0 + len(complexity_tokens) / 12 + priority_boost + issue_type_boost), 1)
        observed_effort = round(
            min(
                13.0,
                (linked_commit_count * 0.9)
                + (active_minutes / 45)
                + (total_changes / 220)
                + (debug_sessions * 0.35)
                + (module_count * 0.25),
            ),
            1,
        )
        progress_pct = min(100, int(round((observed_effort / max(planned_effort, 1.0)) * 100))) if observed_effort else 0
        variance_ratio = observed_effort / max(planned_effort, 1.0)
        if observed_effort == 0:
            variance = "not started"
        elif variance_ratio >= 1.2:
            variance = "above plan"
        elif variance_ratio <= 0.8:
            variance = "below plan"
        else:
            variance = "on plan"

        drivers = [
            f"{len(complexity_tokens)} requirement terms",
            f"{linked_commit_count} linked commits",
            f"{active_minutes:.0f} active minutes",
        ]
        if module_count:
            drivers.append(f"{module_count} modules touched")

        estimates.append(
            {
                "issue_id": issue.get("issue_id"),
                "title": issue.get("title"),
                "planned_effort_points": planned_effort,
                "observed_effort_points": observed_effort,
                "variance": variance,
                "progress_pct": progress_pct,
                "drivers": drivers,
            }
        )
    estimates.sort(key=lambda item: (item["observed_effort_points"], item["planned_effort_points"]), reverse=True)
    return estimates


def build_developer_metrics(
    events: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    linked_commit_ids: set[str],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    event_timestamps = [parse_datetime(event.get("timestamp")) for event in events]
    event_timestamps = [timestamp for timestamp in event_timestamps if timestamp is not None]
    latest_timestamp = max(event_timestamps, default=None)
    issue_commit_lookup = {
        str(commit_id): str(issue.get("issue_id"))
        for issue in issues
        for commit_id in (issue.get("commits") or [])
        if str(commit_id or "").strip()
    }

    for event in events:
        actor = event_actor(event)
        grouped.setdefault(actor, []).append(event)

    total_active_minutes = sum(to_number(event.get("active_minutes")) for event in events) or 1.0
    metrics: list[dict[str, Any]] = []

    for actor, actor_events in grouped.items():
        commit_ids = [str(event.get("commit_id") or "") for event in actor_events]
        linked_commits = [commit_id for commit_id in commit_ids if commit_id in linked_commit_ids]
        linked_issues = {issue_commit_lookup[commit_id] for commit_id in linked_commits if commit_id in issue_commit_lookup}
        active_minutes = sum(to_number(event.get("active_minutes")) for event in actor_events)
        idle_minutes = sum(to_number(event.get("idle_minutes")) for event in actor_events)
        total_changes = sum(to_number(event.get("total_changes")) for event in actor_events)
        avg_focus = average([to_number(event.get("focus_ratio")) for event in actor_events])
        avg_attendance = average([to_number(event.get("attendance_pct")) for event in actor_events if event.get("attendance_pct") is not None])
        module_breadth = len({module for event in actor_events for module in (event.get("modules_touched") or []) if module})
        repo_breadth = len({str(event.get("repository_name") or "") for event in actor_events if str(event.get("repository_name") or "").strip()})
        overtime_commits = len([event for event in actor_events if is_overtime_event(event)])
        workload_share_pct = percent(active_minutes, total_active_minutes)

        delivery_score = min(35.0, len(linked_commits) * 4.5 + len(linked_issues) * 2.5)
        execution_score = min(25.0, active_minutes / 8 + total_changes / 90)
        ownership_score = min(20.0, module_breadth * 2.8 + repo_breadth * 2.2)
        sustainability_score = max(0.0, min(20.0, 20.0 - (overtime_commits * 1.8)))
        impact_score = round(delivery_score + execution_score + ownership_score + sustainability_score, 1)

        reasons = [
            f"{len(linked_commits)} requirement-linked commits",
            f"{module_breadth} modules touched",
            f"{active_minutes:.0f} active minutes observed",
        ]
        if overtime_commits:
            reasons.append(f"{overtime_commits} overtime commits")

        metrics.append(
            {
                "developer": actor,
                "commit_count": len(actor_events),
                "linked_commits": len(linked_commits),
                "linked_issues": len(linked_issues),
                "active_minutes": round(active_minutes, 1),
                "idle_minutes": round(idle_minutes, 1),
                "focus_ratio": round(avg_focus, 3),
                "attendance_pct": round(avg_attendance, 1),
                "workload_share_pct": workload_share_pct,
                "overtime_commits": overtime_commits,
                "performance_trend": performance_trend(actor_events, latest_timestamp),
                "impact_score": impact_score,
                "delivery_score": round(delivery_score, 1),
                "execution_score": round(execution_score, 1),
                "ownership_score": round(ownership_score, 1),
                "sustainability_score": round(sustainability_score, 1),
                "reasons": reasons,
            }
        )

    metrics.sort(key=lambda item: item["impact_score"], reverse=True)
    return metrics


def build_issue_impact_summaries(
    intake_profiles: list[dict[str, Any]],
    effort_estimates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    estimates_by_issue = {item["issue_id"]: item for item in effort_estimates}
    summaries: list[dict[str, Any]] = []
    for profile in intake_profiles:
        estimate = estimates_by_issue.get(profile["issue_id"], {})
        summaries.append(
            {
                "scope": "issue",
                "id": profile["issue_id"],
                "title": profile["title"],
                "summary": (
                    f"{profile['issue_id']} currently has {profile['linked_commits']} linked commits across "
                    f"{profile['contributors']} contributors. Observed effort is {estimate.get('observed_effort_points', 0)} "
                    f"points versus {estimate.get('planned_effort_points', 0)} planned, which is {estimate.get('variance', 'untracked')}."
                ),
            }
        )
    return summaries


def build_developer_impact_summaries(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for metric in metrics:
        summaries.append(
            {
                "scope": "developer",
                "id": metric["developer"],
                "title": metric["developer"],
                "summary": (
                    f"{metric['developer']} contributed {metric['linked_commits']} requirement-linked commits, "
                    f"owns {metric['workload_share_pct']}% of observed active workload, and has an explainable impact "
                    f"score of {metric['impact_score']} driven by delivery, execution, ownership, and sustainability."
                ),
            }
        )
    return summaries


def build_knowledge_risks(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    module_profiles: dict[str, dict[str, Any]] = {}
    event_timestamps = [parse_datetime(event.get("timestamp")) for event in events]
    event_timestamps = [timestamp for timestamp in event_timestamps if timestamp is not None]
    latest_timestamp = max(event_timestamps, default=None)

    for event in events:
        actor = event_actor(event)
        contribution = knowledge_contribution_weight(event)
        event_timestamp = parse_datetime(event.get("timestamp"))
        linked_requirement = linked_requirement_id(event)
        repository_name = normalize_spaces(str(event.get("repository_name") or ""))

        for module in (event.get("modules_touched") or []):
            normalized_module = normalize_spaces(str(module))
            if not normalized_module:
                continue
            profile = module_profiles.setdefault(
                normalized_module,
                {
                    "contributors": {},
                    "linked_requirements": set(),
                    "repositories": set(),
                    "activity_events": 0,
                    "linked_commit_count": 0,
                    "recent_activity_at": None,
                },
            )
            contributor_profile = profile["contributors"].setdefault(
                actor,
                {
                    "contribution_units": 0.0,
                    "commit_count": 0,
                    "linked_commit_count": 0,
                    "linked_requirements": set(),
                    "recent_activity_at": None,
                },
            )
            contributor_profile["contribution_units"] += contribution
            contributor_profile["commit_count"] += 1
            if linked_requirement:
                contributor_profile["linked_commit_count"] += 1
                contributor_profile["linked_requirements"].add(linked_requirement)
                profile["linked_commit_count"] += 1
                profile["linked_requirements"].add(linked_requirement)
            if repository_name:
                profile["repositories"].add(repository_name)
            profile["activity_events"] += 1
            if event_timestamp and (
                profile["recent_activity_at"] is None or event_timestamp > profile["recent_activity_at"]
            ):
                profile["recent_activity_at"] = event_timestamp
            if event_timestamp and (
                contributor_profile["recent_activity_at"] is None or event_timestamp > contributor_profile["recent_activity_at"]
            ):
                contributor_profile["recent_activity_at"] = event_timestamp

    risks: list[dict[str, Any]] = []
    for module, profile in module_profiles.items():
        contributors = profile["contributors"]
        total = sum(details["contribution_units"] for details in contributors.values()) or 1.0
        sorted_contributors = sorted(
            contributors.items(),
            key=lambda item: (item[1]["contribution_units"], item[1]["commit_count"]),
            reverse=True,
        )
        primary_owner, primary_details = sorted_contributors[0]
        primary_value = primary_details["contribution_units"]
        ownership_share_pct = percent(primary_value, total)
        contributor_count = len(sorted_contributors)
        linked_requirement_count = len(profile["linked_requirements"])
        repository_count = len(profile["repositories"])
        linked_commit_count = int(profile["linked_commit_count"])
        activity_events = int(profile["activity_events"])
        recent_activity_at = profile["recent_activity_at"]
        recency_days = (
            max(0, (latest_timestamp - recent_activity_at).days)
            if latest_timestamp is not None and recent_activity_at is not None
            else 0
        )
        freshness = module_freshness_label(recency_days)
        secondary_owner = sorted_contributors[1][0] if contributor_count > 1 else None
        secondary_share_pct = (
            percent(sorted_contributors[1][1]["contribution_units"], total)
            if contributor_count > 1
            else 0.0
        )
        backup_gap_pct = round(max(0.0, ownership_share_pct - secondary_share_pct), 1)
        coverage_index = contributor_coverage_index(
            [percent(details["contribution_units"], total) for _, details in sorted_contributors]
        )
        bus_factor = contributor_bus_factor(sorted_contributors, total)
        recency_band = module_recency_band(recency_days)

        concentration_score = round(min(40.0, max(0.0, ownership_share_pct - 45.0)), 1)
        contributor_score = {1: 20.0, 2: 14.0, 3: 8.0, 4: 4.0}.get(contributor_count, 1.0)
        recency_score = module_recency_score(recency_days)
        linkage_score = round(min(15.0, linked_commit_count * 2.5), 1)
        breadth_score = round(
            min(
                10.0,
                (linked_requirement_count * 2.0)
                + (repository_count * 1.5)
                + (1.0 if activity_events >= 5 else 0.0),
            ),
            1,
        )
        risk_score = round(
            concentration_score + contributor_score + recency_score + linkage_score + breadth_score,
            1,
        )
        severity = knowledge_risk_severity(
            risk_score=risk_score,
            ownership_share_pct=ownership_share_pct,
            recency_days=recency_days,
            contributor_count=contributor_count,
            bus_factor=bus_factor,
        )
        recency_phrase = describe_module_recency(recency_days)
        continuity_profile = classify_module_continuity_profile(
            severity=severity,
            freshness=freshness,
            ownership_share_pct=ownership_share_pct,
            linked_requirement_count=linked_requirement_count,
            bus_factor=bus_factor,
            recency_band=recency_band,
        )
        ownership_stability = classify_ownership_stability(
            severity=severity,
            ownership_share_pct=ownership_share_pct,
            bus_factor=bus_factor,
            coverage_index=coverage_index,
            continuity_profile=continuity_profile["code"],
        )
        review_urgency = classify_review_urgency(
            severity=severity,
            continuity_profile=continuity_profile["code"],
            freshness=freshness,
            linked_requirement_count=linked_requirement_count,
        )
        mitigation_priority = classify_mitigation_priority(
            severity=severity,
            review_urgency=review_urgency,
            continuity_profile=continuity_profile["code"],
            ownership_stability=ownership_stability,
        )
        continuity_confidence = classify_continuity_confidence(
            activity_events=activity_events,
            linked_requirement_count=linked_requirement_count,
            linked_commit_count=linked_commit_count,
            repository_count=repository_count,
            recent_activity_at=recent_activity_at,
        )

        top_contributors = []
        for contributor, details in sorted_contributors[:3]:
            top_contributors.append(
                {
                    "contributor": contributor,
                    "ownership_share_pct": percent(details["contribution_units"], total),
                    "contribution_units": round(details["contribution_units"], 1),
                    "commit_count": int(details["commit_count"]),
                    "linked_commit_count": int(details["linked_commit_count"]),
                    "linked_requirement_count": len(details["linked_requirements"]),
                    "recent_activity_at": (
                        details["recent_activity_at"].isoformat()
                        if details["recent_activity_at"] is not None
                        else None
                    ),
                }
            )

        continuity_guidance = build_module_continuity_guidance(
            severity=severity,
            primary_owner=primary_owner,
            secondary_owner=secondary_owner,
            freshness=freshness,
            linked_requirement_count=linked_requirement_count,
            continuity_profile=continuity_profile["code"],
        )
        recommended_backup_action = build_recommended_backup_action(
            module=module,
            primary_owner=primary_owner,
            secondary_owner=secondary_owner,
            continuity_profile=continuity_profile["code"],
            review_urgency=review_urgency,
            linked_requirement_count=linked_requirement_count,
        )
        recent_activity_summary = (
            f"Latest visible activity in {module} landed {recency_phrase} ({recency_band})."
            if recent_activity_at is not None
            else f"No recent activity timestamp is available for {module}."
        )
        why_risk = (
            f"Tacit knowledge appears to sit mostly with {primary_owner} because they drive {ownership_share_pct}% "
            f"of observed module contribution, the backup bench is {contributor_count} contributor(s) with a bus factor of {bus_factor}, and {module} "
            f"supports {linked_requirement_count} linked requirement(s) across {repository_count} tracked repos."
        )
        summary = (
            f"{module} is a {severity} continuity risk with a {continuity_profile['label']}. {primary_owner} appears "
            f"to hold the most tacit knowledge with {ownership_share_pct}% of observed contribution. The module was last "
            f"active {recency_phrase} and is tied to {linked_requirement_count} linked requirement(s) across "
            f"{linked_commit_count} linked commit(s)."
        )
        manager_summary = (
            f"{module} is currently a {continuity_profile['label']} for managers: {continuity_profile['manager_signal']} "
            f"Review urgency is {review_urgency.replace('_', ' ')}, mitigation priority is {mitigation_priority}, and {recent_activity_summary}"
        )
        explanation_points = [
            f"{primary_owner} is the top contributor with {ownership_share_pct}% of observed work.",
            f"{module} has {contributor_count} contributor(s), bus factor {bus_factor}, and {linked_requirement_count} linked requirement(s).",
            recent_activity_summary,
            continuity_profile["why_it_matters"],
            f"Ownership stability is {ownership_stability} and continuity confidence is {continuity_confidence}.",
        ]

        dominant_risk_drivers = sorted(
            [
                {"label": "Contribution concentration", "score": concentration_score},
                {"label": "Contributor coverage", "score": contributor_score},
                {"label": "Recency", "score": recency_score},
                {"label": "Commit linkage volume", "score": linkage_score},
                {"label": "Module activity breadth", "score": breadth_score},
            ],
            key=lambda item: item["score"],
            reverse=True,
        )[:2]

        risks.append(
            {
                "module": module,
                "severity": severity,
                "primary_owner": primary_owner,
                "top_contributor": primary_owner,
                "ownership_share_pct": ownership_share_pct,
                "contributor_concentration_pct": ownership_share_pct,
                "contributors": contributor_count,
                "contributor_count": contributor_count,
                "secondary_owner": secondary_owner,
                "secondary_share_pct": secondary_share_pct,
                "backup_gap_pct": backup_gap_pct,
                "bus_factor": bus_factor,
                "coverage_index": coverage_index,
                "risk_score": risk_score,
                "recent_activity_at": recent_activity_at.isoformat() if recent_activity_at is not None else None,
                "recency_days": recency_days,
                "recency_band": recency_band,
                "freshness": freshness,
                "linked_requirement_count": linked_requirement_count,
                "linked_commit_count": linked_commit_count,
                "activity_event_count": activity_events,
                "repository_count": repository_count,
                "continuity_profile": continuity_profile["code"],
                "continuity_label": continuity_profile["label"],
                "manager_signal": continuity_profile["manager_signal"],
                "why_it_matters": continuity_profile["why_it_matters"],
                "mitigation_priority": mitigation_priority,
                "recommended_backup_action": recommended_backup_action,
                "ownership_stability": ownership_stability,
                "review_urgency": review_urgency,
                "continuity_confidence": continuity_confidence,
                "recent_activity_summary": recent_activity_summary,
                "manager_summary": manager_summary,
                "explanation_points": explanation_points,
                "why_risk": why_risk,
                "continuity_guidance": continuity_guidance,
                "summary": summary,
                "dominant_risk_drivers": dominant_risk_drivers,
                "risk_breakdown": [
                    {
                        "label": "Contribution concentration",
                        "score": concentration_score,
                        "max_score": 40,
                        "detail": f"{primary_owner} carries {ownership_share_pct}% of observed module contribution.",
                    },
                    {
                        "label": "Contributor coverage",
                        "score": contributor_score,
                        "max_score": 20,
                        "detail": f"{contributor_count} contributor(s) have touched {module}.",
                    },
                    {
                        "label": "Recency",
                        "score": recency_score,
                        "max_score": 15,
                        "detail": f"Latest module activity was {recency_phrase}.",
                    },
                    {
                        "label": "Commit linkage volume",
                        "score": linkage_score,
                        "max_score": 15,
                        "detail": f"{linked_commit_count} linked commit(s) reference the module.",
                    },
                    {
                        "label": "Module activity breadth",
                        "score": breadth_score,
                        "max_score": 10,
                        "detail": f"{linked_requirement_count} linked requirement(s) span {repository_count} repo(s).",
                    },
                ],
                "top_contributors": top_contributors,
            }
        )
    risks.sort(
        key=lambda item: (
            mitigation_priority_rank(item.get("mitigation_priority")),
            review_urgency_rank(item.get("review_urgency")),
            severity_rank(item["severity"]),
            item["risk_score"],
            item["ownership_share_pct"],
            item["linked_requirement_count"],
        ),
        reverse=True,
    )
    return risks


def build_knowledge_risk_model() -> list[dict[str, Any]]:
    return [
        {
            "component": "Contribution concentration",
            "weight": 40,
            "description": "Higher top-contributor share and larger backup gaps raise ownership concentration risk.",
        },
        {
            "component": "Contributor coverage",
            "weight": 20,
            "description": "Fewer contributors and lower bus factor mean less backup depth if the primary owner is unavailable.",
        },
        {
            "component": "Recency",
            "weight": 15,
            "description": "Staler modules are riskier because tacit context decays before the next change window.",
        },
        {
            "component": "Commit linkage volume",
            "weight": 15,
            "description": "More linked commits increase the amount of module context a manager would want covered.",
        },
        {
            "component": "Module activity breadth",
            "weight": 10,
            "description": "Modules linked to more requirements and repositories create broader continuity impact.",
        },
    ]


def build_knowledge_risk_summary(risks: list[dict[str, Any]]) -> dict[str, Any]:
    ranked_risks = list(risks)
    elevated = [risk for risk in ranked_risks if risk.get("severity") in {"high", "medium"}]
    highest_priority = elevated[0] if elevated else (ranked_risks[0] if ranked_risks else None)
    urgent_gap = next(
        (
            risk for risk in elevated
            if risk.get("review_urgency") in {"immediate", "this_week"}
        ),
        highest_priority,
    )
    backup_needed = [
        risk
        for risk in ranked_risks
        if risk.get("ownership_stability") in {"dangerous", "fragile", "watch"}
    ]
    stale_critical = [
        risk
        for risk in ranked_risks
        if risk.get("continuity_profile") in {"stale_dependency", "aging_bottleneck"}
    ]
    active_now = [
        risk
        for risk in ranked_risks
        if risk.get("continuity_profile") == "active_hotspot"
    ]
    acceptable = [
        risk
        for risk in ranked_risks
        if risk.get("ownership_stability") in {"acceptable", "shared"}
    ]
    return {
        "headline": (
            f"Highest priority continuity action is {highest_priority['module']}."
            if highest_priority
            else "No continuity action is currently required."
        ),
        "highest_priority_subsystem": summarize_risk_action(highest_priority),
        "most_urgent_continuity_gap": summarize_risk_action(urgent_gap),
        "modules_needing_backup_ownership": [summarize_risk_action(risk) for risk in backup_needed[:6]],
        "stale_but_critical_areas": [summarize_risk_action(risk) for risk in stale_critical[:6]],
        "active_right_now_risks": [summarize_risk_action(risk) for risk in active_now[:6]],
        "acceptable_concentration_areas": [summarize_risk_action(risk) for risk in acceptable[:6]],
        "counts": {
            "urgent_reviews": len([risk for risk in ranked_risks if risk.get("review_urgency") == "immediate"]),
            "backup_needed": len(backup_needed),
            "stale_critical": len(stale_critical),
            "active_right_now": len(active_now),
            "acceptable": len(acceptable),
        },
        "manager_readout": build_knowledge_risk_manager_readout(
            highest_priority=highest_priority,
            urgent_gap=urgent_gap,
            stale_critical=stale_critical,
            active_now=active_now,
        ),
    }


def summarize_risk_action(risk: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not risk:
        return None
    return {
        "module": risk.get("module"),
        "mitigation_priority": risk.get("mitigation_priority"),
        "review_urgency": risk.get("review_urgency"),
        "ownership_stability": risk.get("ownership_stability"),
        "continuity_confidence": risk.get("continuity_confidence"),
        "recommended_backup_action": risk.get("recommended_backup_action"),
        "manager_signal": risk.get("manager_signal"),
    }


def build_knowledge_risk_manager_readout(
    *,
    highest_priority: Optional[dict[str, Any]],
    urgent_gap: Optional[dict[str, Any]],
    stale_critical: list[str],
    active_now: list[str],
) -> str:
    if not highest_priority:
        return "Ownership coverage currently looks stable enough that no immediate continuity intervention stands out."
    readout = [
        f"Start with {highest_priority.get('module')} because it has {highest_priority.get('mitigation_priority')} mitigation priority."
    ]
    if urgent_gap and urgent_gap.get("module") != highest_priority.get("module"):
        readout.append(
            f"The most urgent review gap is {urgent_gap.get('module')} with review urgency set to {str(urgent_gap.get('review_urgency') or '').replace('_', ' ')}."
        )
    if stale_critical:
        readout.append(f"Stale-but-critical areas include {human_list(stale_critical[:2])}.")
    if active_now:
        readout.append(f"Active continuity hotspots include {human_list(active_now[:2])}.")
    return " ".join(readout)


def build_activity_log(events: list[dict[str, Any]]) -> dict[str, Any]:
    timestamps = [parse_datetime(event.get("timestamp")) for event in events]
    timestamps = [value for value in timestamps if value is not None]
    repositories = len({str(event.get("repository_name") or "") for event in events if str(event.get("repository_name") or "").strip()})
    developers = len({event_actor(event) for event in events})
    return {
        "event_count": len(events),
        "repository_count": repositories,
        "developer_count": developers,
        "time_window_start": min(timestamps).isoformat() if timestamps else None,
        "time_window_end": max(timestamps).isoformat() if timestamps else None,
    }


def build_requirement_text(issue: dict[str, Any]) -> str:
    parts = [
        str(issue.get("issue_id") or ""),
        str(issue.get("title") or ""),
        str(issue.get("description") or ""),
    ]
    return normalize_spaces(" ".join(parts))


def event_actor(event: dict[str, Any]) -> str:
    return normalize_spaces(
        str(event.get("author") or event.get("developer_id") or event.get("author_email") or "Unknown contributor")
    ) or "Unknown contributor"


def linked_requirement_id(event: dict[str, Any]) -> str:
    return normalize_spaces(str(event.get("issue_id") or event.get("linked_issue") or ""))


def knowledge_contribution_weight(event: dict[str, Any]) -> float:
    active_minutes = to_number(event.get("active_minutes"))
    total_changes = to_number(event.get("total_changes"))
    debug_sessions = to_number(event.get("debug_session_count"))
    linked_bonus = 0.4 if linked_requirement_id(event) else 0.0
    return round(max(1.0, (active_minutes / 60) + (total_changes / 140) + (debug_sessions * 0.35) + linked_bonus), 2)


def module_recency_score(recency_days: int) -> float:
    if recency_days <= 3:
        return 1.0
    if recency_days <= 7:
        return 3.0
    if recency_days <= 14:
        return 7.0
    if recency_days <= 21:
        return 10.0
    if recency_days <= 30:
        return 13.0
    return 15.0


def module_recency_band(recency_days: int) -> str:
    if recency_days <= 3:
        return "active"
    if recency_days <= 14:
        return "cooling"
    if recency_days <= 30:
        return "aging"
    return "dormant"


def module_freshness_label(recency_days: int) -> str:
    if recency_days <= 7:
        return "fresh"
    if recency_days <= 21:
        return "watch"
    return "stale"


def describe_module_recency(recency_days: int) -> str:
    if recency_days <= 0:
        return "in the latest observed activity window"
    if recency_days == 1:
        return "1 day before the latest observed activity"
    return f"{recency_days} days before the latest observed activity"


def knowledge_risk_severity(
    *,
    risk_score: float,
    ownership_share_pct: float,
    recency_days: int,
    contributor_count: int,
    bus_factor: int,
) -> str:
    adjusted_score = risk_score
    if ownership_share_pct >= 75 and bus_factor <= 1:
        adjusted_score += 4
    if recency_days >= 45 and ownership_share_pct >= 70:
        adjusted_score += 3
    if contributor_count >= 4 and ownership_share_pct < 50:
        adjusted_score -= 2

    if adjusted_score >= 60:
        return "high"
    if adjusted_score >= 45:
        return "medium"
    return "low"


def classify_module_continuity_profile(
    *,
    severity: str,
    freshness: str,
    ownership_share_pct: float,
    linked_requirement_count: int,
    bus_factor: int,
    recency_band: str,
) -> dict[str, str]:
    if severity == "high" and freshness == "fresh":
        return {
            "code": "active_hotspot",
            "label": "active hotspot",
            "manager_signal": (
                f"Recent work is still concentrated and {linked_requirement_count or 1} linked requirement(s) may depend on one person staying available."
            ),
            "why_it_matters": "If the top owner becomes unavailable, active delivery can slow immediately because current context is still concentrated.",
        }
    if severity == "high" and freshness == "stale":
        return {
            "code": "stale_dependency",
            "label": "stale dependency",
            "manager_signal": "The subsystem is quiet now, but the next change will likely depend on older tacit context that is still single-threaded.",
            "why_it_matters": "Stale single-owner knowledge is hard to recover under time pressure, so the next change can carry ramp-up and handoff risk.",
        }
    if severity == "medium" and recency_band in {"aging", "dormant"} and bus_factor <= 1:
        return {
            "code": "aging_bottleneck",
            "label": "aging bottleneck",
            "manager_signal": "Contribution concentration is moderate, and context is aging enough that the next change can bottleneck on one person.",
            "why_it_matters": "Aging single-owner modules are often underestimated until rework or incident pressure exposes fragile continuity.",
        }
    if severity == "medium" and ownership_share_pct >= 55:
        return {
            "code": "watchlist_concentration",
            "label": "watchlist concentration",
            "manager_signal": "Ownership is not fully single-threaded yet, but contribution spread is narrow enough to justify planned backup coverage.",
            "why_it_matters": "Without deliberate review rotation, medium concentration can become a high-risk ownership pocket as scope grows.",
        }
    if freshness == "stale":
        return {
            "code": "dormant_concentration",
            "label": "dormant concentration",
            "manager_signal": "The subsystem is not changing often, but coverage remains thin and stale context could be expensive to reload later.",
            "why_it_matters": "Dormant modules often look safe until a late requirement or incident forces a single contributor to reconstruct old decisions.",
        }
    return {
        "code": "shared_coverage",
        "label": "shared coverage",
        "manager_signal": "Knowledge appears comparatively healthier because recent contribution is spread across multiple contributors.",
        "why_it_matters": "Shared coverage lowers the chance that one person becomes the delivery bottleneck for the subsystem.",
    }


def classify_ownership_stability(
    *,
    severity: str,
    ownership_share_pct: float,
    bus_factor: int,
    coverage_index: float,
    continuity_profile: str,
) -> str:
    if continuity_profile in {"active_hotspot", "stale_dependency"} or (severity == "high" and bus_factor <= 1):
        return "dangerous"
    if continuity_profile in {"aging_bottleneck", "watchlist_concentration"} or ownership_share_pct >= 60:
        return "fragile"
    if coverage_index >= 0.6 and ownership_share_pct < 55 and bus_factor >= 2:
        return "shared"
    if coverage_index >= 0.45 and ownership_share_pct < 60 and bus_factor >= 2:
        return "acceptable"
    if continuity_profile in {"dormant_concentration"}:
        return "watch"
    return "watch"


def classify_review_urgency(
    *,
    severity: str,
    continuity_profile: str,
    freshness: str,
    linked_requirement_count: int,
) -> str:
    if continuity_profile == "active_hotspot":
        return "immediate"
    if continuity_profile == "stale_dependency":
        return "this_week"
    if severity == "high" or linked_requirement_count >= 4:
        return "this_week"
    if freshness == "stale" and linked_requirement_count:
        return "this_sprint"
    return "routine"


def classify_mitigation_priority(
    *,
    severity: str,
    review_urgency: str,
    continuity_profile: str,
    ownership_stability: str,
) -> str:
    if continuity_profile == "active_hotspot" or review_urgency == "immediate":
        return "urgent"
    if continuity_profile == "stale_dependency" or severity == "high":
        return "high"
    if review_urgency == "this_sprint" or continuity_profile in {"aging_bottleneck", "watchlist_concentration"} or ownership_stability in {"fragile", "watch"}:
        return "planned"
    return "monitor"


def classify_continuity_confidence(
    *,
    activity_events: int,
    linked_requirement_count: int,
    linked_commit_count: int,
    repository_count: int,
    recent_activity_at: Optional[Any],
) -> str:
    score = 0
    if activity_events >= 4:
        score += 2
    elif activity_events >= 2:
        score += 1
    if linked_requirement_count >= 2:
        score += 1
    if linked_commit_count >= 2:
        score += 1
    if repository_count >= 1:
        score += 1
    if recent_activity_at is not None:
        score += 1
    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def build_recommended_backup_action(
    *,
    module: str,
    primary_owner: str,
    secondary_owner: Optional[str],
    continuity_profile: str,
    review_urgency: str,
    linked_requirement_count: int,
) -> str:
    if continuity_profile == "active_hotspot":
        if secondary_owner:
            return f"Make {secondary_owner} the named backup on the next {linked_requirement_count or 1} active {module} change and require shared review before merge."
        return f"Assign a backup owner to shadow {primary_owner} on the next active {module} change before more delivery accumulates."
    if continuity_profile == "stale_dependency":
        return f"Ask {primary_owner} to refresh {module} context into a short handoff note and assign a backup reviewer before the next change window this {review_urgency.replace('_', ' ')}."
    if continuity_profile == "aging_bottleneck":
        return f"Schedule a walkthrough of {module} with {primary_owner} and add a secondary reviewer so aging context does not bottleneck the next requirement."
    if continuity_profile == "watchlist_concentration":
        return f"Rotate a second contributor into {module} review during this sprint so backup ownership grows before concentration becomes dangerous."
    return f"Keep review coverage shared on {module} and confirm backup ownership stays visible in normal delivery review."


def mitigation_priority_rank(value: Any) -> int:
    return {"urgent": 4, "high": 3, "planned": 2, "monitor": 1}.get(str(value or "").lower(), 0)


def review_urgency_rank(value: Any) -> int:
    return {
        "immediate": 4,
        "this_week": 3,
        "this_sprint": 2,
        "routine": 1,
    }.get(str(value or "").lower(), 0)


def severity_rank(value: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(str(value or "").lower(), 0)


def build_module_continuity_guidance(
    *,
    severity: str,
    primary_owner: str,
    secondary_owner: Optional[str],
    freshness: str,
    linked_requirement_count: int,
    continuity_profile: str,
) -> str:
    if continuity_profile == "active_hotspot":
        if secondary_owner:
            return (
                f"Pair {primary_owner} with {secondary_owner} on the next active {linked_requirement_count or 1} requirement change, "
                "make the reviewer capture decisions in writing, and treat backup ownership as part of delivery readiness."
            )
        return (
            f"Add a backup owner alongside {primary_owner} before the next release-critical change, require a short walkthrough, "
            "and track whether the next change lands with shared review coverage."
        )
    if continuity_profile == "stale_dependency":
        return (
            f"Before the next change, ask {primary_owner} to refresh module context into a note or runbook, then assign a second reviewer "
            "so dormant tacit knowledge is not reloaded by one person under deadline."
        )
    if continuity_profile == "aging_bottleneck":
        return (
            f"Plan the next change with {primary_owner} plus a backup reviewer, and capture a concise module context note so aging knowledge does not create a one-person bottleneck."
        )
    if severity == "high":
        if secondary_owner:
            return (
                f"Pair {primary_owner} with {secondary_owner} on the next {linked_requirement_count or 1} requirement change, "
                "capture the decision trail, and make handoff notes part of the next delivery review."
            )
        return (
            f"Add a backup owner alongside {primary_owner}, review the module walkthrough in the next manager checkpoint, "
            "and require basic runbook coverage before more work lands."
        )
    if freshness == "stale":
        return (
            f"Before the next change, refresh {primary_owner}'s module context with a short design note and assign a second reviewer "
            "so stale tacit knowledge does not stay single-threaded."
        )
    return (
        f"Keep {primary_owner} as the anchor contributor, but rotate review or pairing so module knowledge stays shared as work continues."
    )


def contributor_coverage_index(shares: list[float]) -> float:
    if not shares:
        return 0.0
    normalized = [max(0.0, float(share)) / 100.0 for share in shares]
    concentration = sum(value * value for value in normalized)
    return round(max(0.0, min(1.0, 1.0 - concentration)), 3)


def contributor_bus_factor(sorted_contributors: list[tuple[str, dict[str, Any]]], total_contribution: float) -> int:
    if not sorted_contributors:
        return 0
    cumulative = 0.0
    target = max(total_contribution * 0.7, 0.0001)
    for index, (_, details) in enumerate(sorted_contributors, start=1):
        cumulative += float(details.get("contribution_units") or 0.0)
        if cumulative >= target:
            return index
    return len(sorted_contributors)


def performance_trend(events: list[dict[str, Any]], latest_timestamp: Optional[Any]) -> str:
    if not latest_timestamp:
        return "stable"

    latest_dt = parse_datetime(latest_timestamp)
    if not latest_dt:
        return "stable"

    current_score = 0.0
    previous_score = 0.0
    for event in events:
        event_dt = parse_datetime(event.get("timestamp"))
        if not event_dt:
            continue
        contribution = to_number(event.get("active_minutes")) + (to_number(event.get("total_changes")) / 20)
        if (latest_dt - event_dt).days <= 14:
            current_score += contribution
        elif (latest_dt - event_dt).days <= 28:
            previous_score += contribution

    if previous_score == 0 and current_score == 0:
        return "stable"
    if previous_score == 0:
        return "rising"
    ratio = current_score / previous_score
    if ratio >= 1.2:
        return "rising"
    if ratio <= 0.8:
        return "slowing"
    return "stable"


def is_overtime_event(event: dict[str, Any]) -> bool:
    event_dt = parse_datetime(event.get("timestamp"))
    if not event_dt:
        return False
    return event_dt.weekday() >= 5 or event_dt.hour < 7 or event_dt.hour >= 20


def parse_datetime(value: Any):
    from datetime import datetime

    if value is None:
        return None
    if hasattr(value, "isoformat") and hasattr(value, "year"):
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


def average(values: list[float]) -> float:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return 0.0
    return sum(filtered) / len(filtered)


def to_number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def percent(part: float, whole: float) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100, 1)


def normalize_spaces(text: str) -> str:
    return " ".join(str(text or "").split())


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9_]+", str(text or "").lower())
    return [token for token in tokens if len(token) > 2 and token not in STOP_WORDS]


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def profile_source(issue: dict[str, Any]) -> str:
    source = normalize_spaces(str(issue.get("source") or "")).lower()
    return source or "jira"
