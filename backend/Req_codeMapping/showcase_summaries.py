from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Optional

try:
    from delivery_timeline import build_delivery_timeline_response as external_build_delivery_timeline_response
except ModuleNotFoundError:
    external_build_delivery_timeline_response = None


def build_showcase_summaries(
    issues: list[dict[str, Any]],
    events: list[dict[str, Any]],
    intake_profiles: list[dict[str, Any]],
    effort_estimates: list[dict[str, Any]],
    developer_metrics: list[dict[str, Any]],
    knowledge_risks: list[dict[str, Any]],
) -> dict[str, Any]:
    issue_lookup = {str(issue.get("issue_id") or ""): issue for issue in issues}
    profile_lookup = {str(profile.get("issue_id") or ""): profile for profile in intake_profiles}
    estimate_lookup = {str(estimate.get("issue_id") or ""): estimate for estimate in effort_estimates}
    risk_lookup = {normalize_spaces(str(risk.get("module") or "")).lower(): risk for risk in knowledge_risks}

    issue_to_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    developer_to_events: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for event in events:
        developer = event_actor(event)
        developer_to_events[developer].append(event)

        issue_id = normalize_spaces(str(event.get("issue_id") or event.get("linked_issue") or ""))
        if issue_id:
            issue_to_events[issue_id].append(event)

    delivery_timeline = build_delivery_timeline_snapshot(issues, events)
    timeline_records = delivery_timeline.get("records") or []
    timeline_lookup = {str(record.get("issue_id") or ""): record for record in timeline_records}
    coverage = build_summary_coverage(issues, events, delivery_timeline)

    developer_weekly = [
        build_developer_weekly_summary(
            metric,
            developer_to_events.get(metric["developer"], []),
            risk_lookup,
            timeline_lookup,
        )
        for metric in developer_metrics[:6]
    ]
    manager_contributions = [
        build_manager_contribution_summary(
            metric,
            developer_to_events.get(metric["developer"], []),
            issue_lookup,
            risk_lookup,
            timeline_lookup,
        )
        for metric in developer_metrics[:6]
    ]
    issue_impacts = [
        build_issue_impact_summary(
            issue_id,
            issue_lookup,
            profile_lookup,
            estimate_lookup,
            issue_to_events,
            risk_lookup,
            timeline_lookup,
        )
        for issue_id in [estimate["issue_id"] for estimate in effort_estimates[:6] if estimate.get("issue_id")]
    ]

    return {
        "meta": {
            "generated_at": first_present(delivery_timeline.get("generated_at")),
            "generated_from": [
                "issue metadata",
                "linked commit telemetry",
                "effort estimates",
                "developer metrics",
                "delivery stage records",
                "knowledge risk signals",
            ],
            "inference_level": inference_level_from_counts(
                connector_count=coverage["delivery"]["connector_stage_count"],
                inferred_count=coverage["delivery"]["inferred_stage_count"],
                mock_count=coverage["delivery"]["mocked_stage_count"],
            ),
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
        "portfolio_overview": build_portfolio_overview(
            issues=issues,
            events=events,
            effort_estimates=effort_estimates,
            developer_metrics=developer_metrics,
            knowledge_risks=knowledge_risks,
            coverage=coverage,
            delivery_timeline=delivery_timeline,
        ),
        "coverage": coverage,
        "developer_weekly": developer_weekly,
        "manager_contributions": manager_contributions,
        "issue_impacts": issue_impacts,
        "logic_notes": [
            "Observed facts come directly from requirement metadata, linked commits, delivery-stage records, and telemetry fields present in the current feed.",
            "Inferred judgments are deterministic interpretations of workload concentration, freshness, continuity risk, effort variance, and launch progression.",
            "Confidence reflects evidence richness across links, repositories, modules, and delivery-stage coverage. Low confidence usually means sparse telemetry rather than missing summary structure.",
        ],
    }


def build_portfolio_overview(
    *,
    issues: list[dict[str, Any]],
    events: list[dict[str, Any]],
    effort_estimates: list[dict[str, Any]],
    developer_metrics: list[dict[str, Any]],
    knowledge_risks: list[dict[str, Any]],
    coverage: dict[str, Any],
    delivery_timeline: dict[str, Any],
) -> dict[str, Any]:
    active_requirements = len([issue for issue in issues if issue.get("commits")])
    total_effort = round(sum(to_number(item.get("observed_effort_points")) for item in effort_estimates), 1)
    highest_workload = developer_metrics[0] if developer_metrics else {}
    high_risks = [risk for risk in knowledge_risks if risk.get("severity") == "high"]
    momentum_issues = [item for item in effort_estimates if item.get("observed_effort_points", 0) > 0]
    above_plan = [item for item in effort_estimates if item.get("variance") == "above plan"]
    timeline_summary = delivery_timeline.get("summary") or {}
    connector_stage_count = timeline_summary.get("connector_stage_count", 0)
    inferred_stage_count = timeline_summary.get("inferred_stage_count", 0)
    mocked_stage_count = timeline_summary.get("mocked_stage_count", 0)

    observed_facts = [
        f"{active_requirements} requirements have linked movement in the current view.",
        f"{total_effort} observed effort points are distributed across {len(events)} telemetry events.",
        f"{timeline_summary.get('deployments_live', 0)} requirements are already in a deployed stage.",
        f"{coverage['delivery']['connector_stage_coverage_pct']}% of delivery stages are connector-backed, {coverage['delivery']['inferred_stage_coverage_pct']}% are inferred from linked activity, and {mocked_stage_count} stages remain fully mocked.",
    ]
    inferred_judgments = [
        f"Execution is broad enough to track {len(momentum_issues)} active requirements with readable evidence.",
        f"Workload is currently led by {highest_workload.get('developer', 'the team')}, who carries {highest_workload.get('workload_share_pct', 0)}% of observed active time.",
        (
            f"Risk attention should stay on {len(high_risks)} high concentration areas and {coverage['delivery']['stale_requirements']} stale requirements."
            if high_risks or coverage["delivery"]["stale_requirements"]
            else "Current continuity and freshness signals are relatively stable."
        ),
        (
            f"{len(above_plan)} requirements are above heuristic effort plan and may indicate scope growth or hidden complexity."
            if above_plan
            else "Effort variance is not showing widespread overruns in the current snapshot."
        ),
        (
            f"Launch readiness is materially grounded because {connector_stage_count} delivery stages are connector-backed and {inferred_stage_count} more are inferred from branch, merge, or downstream delivery signals."
            if connector_stage_count or inferred_stage_count
            else "Launch readiness is still weak because downstream delivery evidence is absent from the current feed."
        ),
    ]
    confidence_detail = assess_summary_confidence(
        event_count=len(events),
        linked_commits=active_requirements,
        focus_available=coverage["telemetry"]["field_breakdown"].get("focus_pct", 0) > 0,
        module_count=len(top_modules_for_events(events, limit=6)),
        repository_count=len(ranked_repositories(events)),
        connector_stage_count=connector_stage_count,
        inferred_stage_count=inferred_stage_count,
    )
    confidence = confidence_detail["level"]
    confidence_reason = confidence_detail["reason"]
    risk_signal = (
        "High continuity or freshness risk needs manager attention."
        if high_risks or coverage["delivery"]["stale_requirements"]
        else "No immediate launch-blocking continuity signal stands out."
    )
    freshness_note = describe_portfolio_freshness(events, coverage["delivery"]["stale_requirements"])
    traceability_note = describe_portfolio_traceability(coverage)
    uncertainty_note = describe_uncertainty_note(
        confidence=confidence,
        confidence_detail=confidence_detail,
        inference_level=inference_level_from_counts(
            connector_count=connector_stage_count,
            inferred_count=inferred_stage_count,
            mock_count=mocked_stage_count,
        ),
    )
    follow_up = describe_portfolio_follow_up(
        coverage=coverage,
        stale_requirements=coverage["delivery"]["stale_requirements"],
        confidence=confidence,
        connector_stage_count=connector_stage_count,
        inferred_stage_count=inferred_stage_count,
    )
    risk_level = derive_risk_level(risk_signal)
    freshness_level = derive_freshness_level(freshness_note)
    action_priority = action_priority_from_signals(
        risk_level=risk_level,
        freshness_level=freshness_level,
        confidence=confidence,
    )
    review_window = review_window_from_priority(action_priority)
    weekly_review = build_weekly_review_struct(
        scope="portfolio",
        observed_facts=observed_facts,
        inferred_judgments=inferred_judgments,
        follow_up=follow_up,
        action_priority=action_priority,
        confidence_reason=confidence_reason,
        review_window=review_window,
        stable_signals=build_portfolio_stable_signals(
            connector_stage_count=connector_stage_count,
            stale_requirements=coverage["delivery"]["stale_requirements"],
            confidence=confidence,
            traceability_note=traceability_note,
        ),
        watch_signals=build_portfolio_watch_signals(
            stale_requirements=coverage["delivery"]["stale_requirements"],
            high_risk_count=len(high_risks),
            confidence_detail=confidence_detail,
            inferred_stage_count=inferred_stage_count,
        ),
        uncertainty_driver=describe_uncertainty_driver(confidence_detail, uncertainty_note),
    )
    why_it_matters = describe_portfolio_why_it_matters(
        active_requirements=active_requirements,
        stale_requirements=coverage["delivery"]["stale_requirements"],
        high_risk_count=len(high_risks),
        connector_stage_count=connector_stage_count,
    )
    review_focus = describe_portfolio_review_focus(
        coverage=coverage,
        stale_requirements=coverage["delivery"]["stale_requirements"],
        high_risk_count=len(high_risks),
    )
    top_risk_driver = describe_top_risk_driver(
        risk_signal=risk_signal,
        uncertainty_note=uncertainty_note,
        confidence_detail=confidence_detail,
    )
    summary_confidence_band = derive_summary_confidence_band(confidence, confidence_detail)

    return {
        "headline": "Engineering delivery can be reviewed as a launchable narrative, not just raw telemetry.",
        "executive_summary": (
            f"The portfolio shows {active_requirements} requirements with visible movement, {timeline_summary.get('deployments_live', 0)} already deployed, "
            f"and delivery evidence strongest in {human_list(top_modules_for_events(events, limit=3)) or 'tracked modules'}."
        ),
        "summary": (
            f"Overall execution health is readable across {len(momentum_issues)} active requirements, but weekly review should stay on "
            f"{coverage['delivery']['stale_requirements']} stale requirements and {len(high_risks)} concentrated knowledge areas."
        ),
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "confidence_detail": confidence_detail,
        "evidence_count": len(events),
        "top_requirements": [item["issue_id"] for item in effort_estimates[:4] if item.get("issue_id")],
        "top_modules": top_modules_for_events(events, limit=4),
        "top_repositories": ranked_repositories(events)[:4],
        "generated_from": [
            "issue metadata",
            "linked commit telemetry",
            "effort estimates",
            "developer metrics",
            "delivery stage records",
            "knowledge risk signals",
        ],
        "inference_level": inference_level_from_counts(
            connector_count=connector_stage_count,
            inferred_count=inferred_stage_count,
            mock_count=mocked_stage_count,
        ),
        "risk_signal": risk_signal,
        "risk_level": risk_level,
        "freshness_note": freshness_note,
        "freshness_level": freshness_level,
        "uncertainty_note": uncertainty_note,
        "traceability_note": traceability_note,
        "follow_up": follow_up,
        "why_it_matters": why_it_matters,
        "review_focus": review_focus,
        "top_risk_driver": top_risk_driver,
        "recommended_follow_up": follow_up,
        "summary_confidence_band": summary_confidence_band,
        "uncertainty_driver": describe_uncertainty_driver(confidence_detail, uncertainty_note),
        "action_priority": action_priority,
        "review_window": review_window,
        "review_owner": "engineering manager",
        "weekly_review": weekly_review,
        "observed_facts": observed_facts,
        "inferred_judgments": inferred_judgments,
        "stats": [
            {"label": "Requirements With Movement", "value": active_requirements},
            {"label": "Observed Effort Points", "value": total_effort},
            {"label": "Connector Stage Coverage", "value": coverage["delivery"]["connector_stage_coverage_pct"]},
            {"label": "Launch Signal Coverage", "value": coverage["delivery"]["launch_signal_coverage_pct"]},
        ],
    }


def build_delivery_timeline_snapshot(
    issues: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    if external_build_delivery_timeline_response is not None:
        return external_build_delivery_timeline_response(issues, events)

    event_map = {
        str(event.get("commit_id") or "").strip(): event
        for event in events
        if str(event.get("commit_id") or "").strip()
    }
    records = [build_delivery_record_fallback(issue, event_map) for issue in issues]
    deployments_live = len([record for record in records if record.get("delivery_stage") == "deployed"])
    return {
        "summary": {
            "requirements_total": len(records),
            "requirements_with_commits": len([record for record in records if record.get("commit_count")]),
            "deployments_live": deployments_live,
            "connector_stage_count": 0,
            "inferred_stage_count": 0,
            "mocked_stage_count": len(records) * 3,
        },
        "records": records,
    }


def build_summary_coverage(
    issues: list[dict[str, Any]],
    events: list[dict[str, Any]],
    delivery_timeline: dict[str, Any],
) -> dict[str, Any]:
    total_requirements = len(issues) or 1
    timeline_records = delivery_timeline.get("records") or []
    timeline_summary = delivery_timeline.get("summary") or {}
    total_stages = max(1, len(timeline_records) * 3)
    connector_backed_stages = int(to_number(timeline_summary.get("connector_stage_count")))
    inferred_stages = int(to_number(timeline_summary.get("inferred_stage_count")))
    mocked_stages = int(to_number(timeline_summary.get("mocked_stage_count")))

    if not (connector_backed_stages or inferred_stages or mocked_stages):
        mocked_stages = sum(len(record.get("mocked_stages") or []) for record in timeline_records)
        inferred_stages = max(0, total_stages - mocked_stages)

    covered_stages = min(total_stages, connector_backed_stages + inferred_stages)
    stale_requirements = len([record for record in timeline_records if is_stale_record(record)])
    launch_signals = len(
        [
            record
            for record in timeline_records
            if record.get("delivery_stage") in {"in review", "in ci", "ready to deploy", "deploying", "deployed"}
        ]
    )

    telemetry_fields = {
        "branch_pct": event_field_coverage(events, "branch"),
        "module_pct": event_field_coverage(events, "modules_touched", truthy_list=True),
        "file_pct": event_field_coverage(events, "files", truthy_list=True, allow_files_json=True),
        "focus_pct": event_field_coverage(events, "focus_ratio"),
        "attendance_pct": event_field_coverage(events, "attendance_pct"),
        "active_minutes_pct": event_field_coverage(events, "active_minutes"),
        "repository_pct": event_field_coverage(events, "repository_name"),
    }
    telemetry_field_coverage_pct = round(sum(telemetry_fields.values()) / len(telemetry_fields), 1) if telemetry_fields else 0.0

    requirements_with_timeline = len([issue for issue in issues if issue.get("jira_created_at") or issue.get("created_at")])
    requirements_with_owners = len([issue for issue in issues if issue.get("assignee_email") or issue.get("reporter_email")])
    requirements_with_links = len([issue for issue in issues if issue.get("commits")])

    return {
        "delivery": {
            "requirements_with_links_pct": percent(requirements_with_links, total_requirements),
            "requirements_with_timeline_pct": percent(requirements_with_timeline, total_requirements),
            "requirements_with_owner_pct": percent(requirements_with_owners, total_requirements),
            "stage_coverage_pct": round((covered_stages / total_stages) * 100, 1),
            "connector_stage_coverage_pct": round((connector_backed_stages / total_stages) * 100, 1),
            "inferred_stage_coverage_pct": round((inferred_stages / total_stages) * 100, 1),
            "launch_signal_coverage_pct": percent(launch_signals, len(timeline_records) or 1),
            "stale_requirements": stale_requirements,
            "tracked_requirements": len(timeline_records),
            "connector_stage_count": timeline_summary.get("connector_stage_count", connector_backed_stages),
            "inferred_stage_count": timeline_summary.get("inferred_stage_count", inferred_stages),
            "mocked_stage_count": timeline_summary.get("mocked_stage_count", mocked_stages),
        },
        "telemetry": {
            "field_coverage_pct": telemetry_field_coverage_pct,
            "field_breakdown": telemetry_fields,
            "tracked_events": len(events),
            "tracked_contributors": len({event_actor(event) for event in events}),
        },
    }


def build_delivery_record_fallback(
    issue: dict[str, Any],
    event_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    commit_ids = [str(commit_id) for commit_id in (issue.get("commits") or []) if str(commit_id or "").strip()]
    linked_events = [event_map[commit_id] for commit_id in commit_ids if commit_id in event_map]
    linked_events.sort(key=lambda item: datetime_sort_key(item.get("timestamp")))
    latest_event = linked_events[-1] if linked_events else {}

    mocked_stages: list[str] = []

    if any(value_present(event.get("pr_status")) or value_present(event.get("pr_number")) for event in linked_events):
        pr_status = normalize_spaces(str(latest_event.get("pr_status") or "open")).lower()
    elif commit_ids:
        pr_status = "open"
        mocked_stages.append("pull_request")
    else:
        pr_status = "not started"
        mocked_stages.append("pull_request")

    if any(value_present(event.get("ci_status")) for event in linked_events):
        ci_status = normalize_spaces(str(latest_event.get("ci_status") or "running")).lower()
    elif len(commit_ids) >= 2:
        ci_status = "running"
        mocked_stages.append("ci")
    else:
        ci_status = "blocked"
        mocked_stages.append("ci")

    if any(value_present(event.get("deployment_status")) for event in linked_events):
        deployment_status = normalize_spaces(str(latest_event.get("deployment_status") or "pending")).lower()
    elif len(commit_ids) >= 2 and ci_status in {"passed", "success"}:
        deployment_status = "pending"
        mocked_stages.append("deployment")
    else:
        deployment_status = "blocked"
        mocked_stages.append("deployment")

    return {
        "issue_id": issue.get("issue_id"),
        "delivery_stage": infer_delivery_stage_from_statuses(commit_ids, pr_status, ci_status, deployment_status),
        "mocked_stages": mocked_stages,
        "commit_count": len(commit_ids),
        "latest_activity_at": first_present(
            latest_event.get("deployed_at"),
            latest_event.get("timestamp"),
            issue.get("jira_updated_at"),
            issue.get("updated_at"),
        ),
    }


def build_developer_weekly_summary(
    metric: dict[str, Any],
    events: list[dict[str, Any]],
    risk_lookup: dict[str, dict[str, Any]],
    timeline_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    issue_ids = ranked_issue_ids(events)
    modules = ranked_modules(events)
    repositories = ranked_repositories(events)
    file_paths = ranked_file_paths(events)
    linked_commits = int(round(to_number(metric.get("linked_commits"))))
    active_minutes = int(round(to_number(metric.get("active_minutes"))))
    evidence_count = len(events)
    top_stage_evidence = summarize_stage_evidence_for_requirements(issue_ids, timeline_lookup)
    connector_count, inferred_count, mock_count = aggregate_timeline_source_counts(issue_ids, timeline_lookup)
    focus_available = any(event.get("focus_ratio") is not None for event in events)

    focus_signal = describe_focus(metric.get("focus_ratio"))
    workload_signal = describe_workload(metric.get("workload_share_pct"))
    risk_signal = describe_developer_risk(metric, modules, risk_lookup)
    confidence_detail = assess_summary_confidence(
        event_count=evidence_count,
        linked_commits=linked_commits,
        focus_available=focus_available,
        module_count=len(modules),
        repository_count=len(repositories),
        connector_stage_count=connector_count,
        inferred_stage_count=inferred_count,
    )
    confidence = confidence_detail["level"]
    confidence_reason = confidence_detail["reason"]
    follow_up = describe_developer_follow_up(focus_signal, workload_signal, risk_signal, issue_ids)
    freshness_note = describe_activity_freshness_note(events)
    uncertainty_note = describe_uncertainty_note(
        confidence=confidence,
        confidence_detail=confidence_detail,
        inference_level=inference_level_from_counts(
            connector_count=connector_count,
            inferred_count=inferred_count,
            mock_count=mock_count,
        ),
    )
    risk_level = derive_risk_level(risk_signal)
    freshness_level = derive_freshness_level(freshness_note)
    action_priority = action_priority_from_signals(
        risk_level=risk_level,
        freshness_level=freshness_level,
        confidence=confidence,
        stage_evidence=top_stage_evidence,
    )
    review_window = review_window_from_priority(action_priority)

    observed_facts = [
        f"{linked_commits} requirement-linked commits were attributed to {metric['developer']}.",
        f"{active_minutes} active minutes were observed across {human_list(repositories[:2]) or 'tracked repositories'}.",
        f"Linked requirements include {human_list(issue_ids[:3]) or 'no clearly ranked requirements yet'}.",
        f"Top modules include {human_list(modules[:3]) or 'no clear module concentration yet'}.",
    ]
    inferred_judgments = [
        f"Execution focus appears {focus_signal}.",
        workload_signal,
        describe_evidence_interpretation(confidence, confidence_detail, top_stage_evidence),
        risk_signal,
    ]
    weekly_review = build_weekly_review_struct(
        scope="developer",
        observed_facts=observed_facts,
        inferred_judgments=inferred_judgments,
        follow_up=follow_up,
        action_priority=action_priority,
        confidence_reason=confidence_reason,
        review_window=review_window,
        stable_signals=build_developer_stable_signals(
            linked_commits=linked_commits,
            freshness_level=freshness_level,
            modules=modules,
            repositories=repositories,
            confidence=confidence,
        ),
        watch_signals=build_developer_watch_signals(
            risk_signal=risk_signal,
            confidence_detail=confidence_detail,
            stage_evidence=top_stage_evidence,
        ),
        uncertainty_driver=describe_uncertainty_driver(confidence_detail, uncertainty_note),
    )
    why_it_matters = describe_developer_why_it_matters(issue_ids, modules, repositories)
    review_focus = describe_developer_review_focus(modules, confidence_detail, follow_up)
    top_risk_driver = describe_top_risk_driver(
        risk_signal=risk_signal,
        uncertainty_note=uncertainty_note,
        confidence_detail=confidence_detail,
    )
    summary_confidence_band = derive_summary_confidence_band(confidence, confidence_detail)

    return {
        "scope": "developer",
        "id": metric["developer"],
        "title": metric["developer"],
        "headline": (
            f"{metric['developer']} made the clearest weekly movement in {human_list(issue_ids[:2]) or 'linked requirements'}, "
            f"with effort concentrated in {human_list(modules[:2]) or 'tracked delivery work'}."
        ),
        "executive_summary": (
            f"{metric['developer']} moved {human_list(issue_ids[:2]) or 'linked requirements'} with visible effort concentrated in "
            f"{human_list(modules[:3]) or 'tracked modules'} across {human_list(repositories[:2]) or 'tracked repositories'}."
        ),
        "summary": (
            f"This week's visible work centered on {human_list(issue_ids[:2]) or 'linked requirements'}, with {linked_commits} linked commits, "
            f"{active_minutes} active minutes, and the clearest execution trail in {human_list(modules[:3]) or 'shared code paths'}."
        ),
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "confidence_detail": confidence_detail,
        "evidence_count": evidence_count,
        "generated_from": [
            "developer metrics",
            "linked commit telemetry",
            "issue linkage",
            "delivery stage records",
        ],
        "inference_level": inference_level_from_counts(
            connector_count=connector_count,
            inferred_count=inferred_count,
            mock_count=mock_count,
        ),
        "work_summary": (
            f"Personal work centered on {human_list(modules[:3]) or 'tracked delivery work'} for "
            f"{human_list(issue_ids[:3]) or 'linked requirements'}, primarily in {human_list(repositories[:2]) or 'tracked repositories'}."
        ),
        "what_changed": (
            f"The clearest movement landed in {human_list(issue_ids[:2]) or 'linked requirements'}, where work touched "
            f"{human_list(modules[:3]) or 'tracked delivery work'}."
        ),
        "effort_concentration": (
            f"Effort concentrated in {human_list(modules[:3]) or 'shared code paths'} across {human_list(repositories[:2]) or 'tracked repositories'}, "
            f"which is where the weekly telemetry is strongest."
        ),
        "focus_interpretation": (
            f"Focus and workload read as {focus_signal}, with {workload_signal.lower()} "
            f"{describe_focus_confidence_tail(confidence, confidence_detail)}"
        ),
        "follow_up": follow_up,
        "highlights": [
            {"label": "What Was Worked On", "value": f"{human_list(issue_ids[:2]) or 'Linked requirements'} through {human_list(modules[:3]) or 'tracked delivery work'}."},
            {"label": "Where Effort Concentrated", "value": human_list(repositories[:2]) or "Tracked repositories"},
            {"label": "Delivery Evidence", "value": top_stage_evidence},
            {"label": "Recommended Follow-Up", "value": follow_up},
        ],
        "top_requirements": issue_ids[:4],
        "top_modules": modules[:4],
        "top_repositories": repositories[:4],
        "top_files": file_paths[:4],
        "risk_signal": risk_signal,
        "risk_level": risk_level,
        "freshness_note": freshness_note,
        "freshness_level": freshness_level,
        "uncertainty_note": uncertainty_note,
        "why_it_matters": why_it_matters,
        "review_focus": review_focus,
        "top_risk_driver": top_risk_driver,
        "recommended_follow_up": follow_up,
        "summary_confidence_band": summary_confidence_band,
        "uncertainty_driver": describe_uncertainty_driver(confidence_detail, uncertainty_note),
        "action_priority": action_priority,
        "review_window": review_window,
        "review_owner": "developer",
        "weekly_review": weekly_review,
        "observed_facts": observed_facts,
        "inferred_judgments": inferred_judgments,
        "stage_evidence": top_stage_evidence,
    }


def build_manager_contribution_summary(
    metric: dict[str, Any],
    events: list[dict[str, Any]],
    issue_lookup: dict[str, dict[str, Any]],
    risk_lookup: dict[str, dict[str, Any]],
    timeline_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    issue_ids = ranked_issue_ids(events)
    modules = ranked_modules(events)
    repositories = ranked_repositories(events)
    linked_commits = int(round(to_number(metric.get("linked_commits"))))
    active_minutes = int(round(to_number(metric.get("active_minutes"))))
    evidence_count = len(events)
    issue_titles = [
        f"{issue_id} {normalize_spaces(str(issue_lookup.get(issue_id, {}).get('title') or ''))}".strip()
        for issue_id in issue_ids[:2]
    ]
    stage_mix = stage_mix_for_issues(issue_ids, timeline_lookup)
    top_stage_evidence = summarize_stage_evidence_for_requirements(issue_ids, timeline_lookup)
    connector_count, inferred_count, mock_count = aggregate_timeline_source_counts(issue_ids, timeline_lookup)
    focus_available = any(event.get("focus_ratio") is not None for event in events)

    workload_signal = describe_workload(metric.get("workload_share_pct"))
    risk_signal = describe_developer_risk(metric, modules, risk_lookup)
    confidence_detail = assess_summary_confidence(
        event_count=evidence_count,
        linked_commits=linked_commits,
        focus_available=focus_available,
        module_count=len(modules),
        repository_count=len(repositories),
        connector_stage_count=connector_count,
        inferred_stage_count=inferred_count,
    )
    confidence = confidence_detail["level"]
    confidence_reason = confidence_detail["reason"]
    freshness_note = describe_activity_freshness_note(events)
    uncertainty_note = describe_uncertainty_note(
        confidence=confidence,
        confidence_detail=confidence_detail,
        inference_level=inference_level_from_counts(
            connector_count=connector_count,
            inferred_count=inferred_count,
            mock_count=mock_count,
        ),
    )
    risk_level = derive_risk_level(risk_signal)
    freshness_level = derive_freshness_level(freshness_note)
    action_priority = action_priority_from_signals(
        risk_level=risk_level,
        freshness_level=freshness_level,
        confidence=confidence,
        stage_evidence=top_stage_evidence,
    )
    review_window = review_window_from_priority(action_priority)

    so_what = describe_manager_takeaway(issue_titles, stage_mix, risk_signal)
    follow_up = describe_manager_follow_up(stage_mix, risk_signal, top_stage_evidence)
    observed_facts = [
        f"{metric['developer']} advanced {len(issue_ids)} requirement streams through {linked_commits} linked commits.",
        f"{active_minutes} active minutes were recorded for this contribution window.",
        f"Most visible requirements were {human_list(issue_titles) or 'not yet clearly identifiable'}.",
        f"Current delivery stages cluster in {stage_mix}, with repositories led by {human_list(repositories[:2]) or 'tracked repositories'}.",
    ]
    inferred_judgments = [
        f"Contribution concentration appears strongest in {human_list(modules[:3]) or 'shared code paths'}.",
        so_what,
        describe_evidence_interpretation(confidence, confidence_detail, top_stage_evidence),
        risk_signal,
    ]
    weekly_review = build_weekly_review_struct(
        scope="manager",
        observed_facts=observed_facts,
        inferred_judgments=inferred_judgments,
        follow_up=follow_up,
        action_priority=action_priority,
        confidence_reason=confidence_reason,
        review_window=review_window,
        stable_signals=build_manager_stable_signals(
            stage_mix=stage_mix,
            confidence=confidence,
            risk_level=risk_level,
        ),
        watch_signals=build_manager_watch_signals(
            risk_signal=risk_signal,
            confidence_detail=confidence_detail,
            stage_evidence=top_stage_evidence,
        ),
        uncertainty_driver=describe_uncertainty_driver(confidence_detail, uncertainty_note),
    )
    why_it_matters = describe_manager_why_it_matters(issue_titles, stage_mix, risk_signal)
    review_focus = describe_manager_review_focus(stage_mix, confidence_detail, risk_signal, top_stage_evidence)
    top_risk_driver = describe_top_risk_driver(
        risk_signal=risk_signal,
        uncertainty_note=uncertainty_note,
        confidence_detail=confidence_detail,
    )
    summary_confidence_band = derive_summary_confidence_band(confidence, confidence_detail)

    return {
        "scope": "manager",
        "id": metric["developer"],
        "title": metric["developer"],
        "headline": (
            f"{metric['developer']} advanced requirement streams with delivery-visible movement, most clearly across {stage_mix}."
        ),
        "executive_summary": (
            f"Manager view: {human_list(issue_titles) or 'tracked requirements'} moved, with effort concentrated in "
            f"{human_list(modules[:3]) or 'shared modules'} and risk currently assessed as {derive_risk_level(risk_signal)}."
        ),
        "summary": (
            f"Manager-visible movement landed in {human_list(issue_titles) or 'tracked requirements'}, with the clearest effort concentration in "
            f"{human_list(modules[:3]) or 'shared modules'} across {human_list(repositories[:2]) or 'tracked repositories'} and the next review centered on {stage_mix}."
        ),
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "confidence_detail": confidence_detail,
        "evidence_count": evidence_count,
        "generated_from": [
            "developer metrics",
            "linked commit telemetry",
            "issue linkage",
            "delivery stage records",
            "knowledge risk signals",
        ],
        "inference_level": inference_level_from_counts(
            connector_count=connector_count,
            inferred_count=inferred_count,
            mock_count=mock_count,
        ),
        "what_moved": (
            f"What moved most clearly this week was {human_list(issue_titles) or 'tracked requirements'}, supported by {linked_commits} linked commits."
        ),
        "effort_concentration": (
            f"Team-visible effort concentrated in {human_list(modules[:3]) or 'shared code paths'} across "
            f"{human_list(repositories[:2]) or 'tracked repositories'}."
        ),
        "so_what": so_what,
        "risk_watch": risk_signal,
        "follow_up": follow_up,
        "highlights": [
            {"label": "What Moved", "value": human_list(issue_titles) or "Tracked requirements"},
            {"label": "Where Effort Concentrated", "value": human_list(modules[:3]) or "Shared code paths"},
            {"label": "Why It Matters", "value": so_what},
            {"label": "Recommended Follow-Up", "value": follow_up},
        ],
        "top_requirements": issue_ids[:4],
        "top_modules": modules[:4],
        "top_repositories": repositories[:4],
        "top_files": ranked_file_paths(events)[:4],
        "risk_signal": risk_signal,
        "risk_level": risk_level,
        "freshness_note": freshness_note,
        "freshness_level": freshness_level,
        "uncertainty_note": uncertainty_note,
        "why_it_matters": why_it_matters,
        "review_focus": review_focus,
        "top_risk_driver": top_risk_driver,
        "recommended_follow_up": follow_up,
        "summary_confidence_band": summary_confidence_band,
        "uncertainty_driver": describe_uncertainty_driver(confidence_detail, uncertainty_note),
        "action_priority": action_priority,
        "review_window": review_window,
        "review_owner": "engineering manager",
        "weekly_review": weekly_review,
        "impact_score": metric.get("impact_score", 0),
        "observed_facts": observed_facts,
        "inferred_judgments": inferred_judgments,
        "stage_evidence": top_stage_evidence,
    }


def build_issue_impact_summary(
    issue_id: str,
    issue_lookup: dict[str, dict[str, Any]],
    profile_lookup: dict[str, dict[str, Any]],
    estimate_lookup: dict[str, dict[str, Any]],
    issue_to_events: dict[str, list[dict[str, Any]]],
    risk_lookup: dict[str, dict[str, Any]],
    timeline_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    issue = issue_lookup.get(issue_id, {})
    profile = profile_lookup.get(issue_id, {})
    estimate = estimate_lookup.get(issue_id, {})
    events = issue_to_events.get(issue_id, [])
    timeline = timeline_lookup.get(issue_id, {})
    modules = ranked_modules(events)
    repositories = ranked_repositories(events)
    contributors = dedupe_preserve_order([event_actor(event) for event in events])
    evidence_count = len(events)
    linked_commits = int(round(to_number(profile.get("linked_commits"))))
    progress_pct = int(round(to_number(estimate.get("progress_pct"))))
    stage_evidence = summarize_stage_evidence(timeline)
    connector_count, inferred_count, mock_count = timeline_source_counts(timeline)

    progress_summary = describe_issue_progress(progress_pct, linked_commits, timeline.get("delivery_stage"))
    variance_summary = describe_issue_variance(estimate)
    freshness_signal = describe_freshness(events, issue)
    readiness_summary = describe_issue_readiness(timeline, connector_count, inferred_count, mock_count)
    risk_signal = describe_issue_risk(modules, contributors, risk_lookup, estimate, timeline)
    continuity_summary = describe_issue_continuity_risk(risk_signal, contributors)
    confidence_detail = assess_summary_confidence(
        event_count=evidence_count,
        linked_commits=linked_commits,
        focus_available=any(event.get("focus_ratio") is not None for event in events),
        module_count=len(modules),
        repository_count=len(repositories),
        connector_stage_count=connector_count,
        inferred_stage_count=inferred_count,
    )
    confidence = confidence_detail["level"]
    confidence_reason = confidence_detail["reason"]

    observed_facts = [
        f"{issue_id} maps to {normalize_spaces(str(issue.get('title') or issue_id))}.",
        f"{linked_commits} linked commits and {len(contributors)} contributors were observed for {issue_id}.",
        f"Observed effort is {estimate.get('observed_effort_points', 0)} points against {estimate.get('planned_effort_points', 0)} planned, or roughly {progress_pct}% of heuristic progress.",
        f"Current delivery stage is {timeline.get('delivery_stage', 'planned')} with modules concentrated in {human_list(modules[:3]) or 'not visible yet'}.",
        f"Primary repositories are {human_list(repositories[:2]) or 'not visible yet'} and visible contributors are {human_list(contributors[:3]) or 'not clearly identified yet'}.",
    ]
    inferred_judgments = [
        readiness_summary,
        variance_summary,
        freshness_signal,
        continuity_summary,
        describe_evidence_interpretation(confidence, confidence_detail, stage_evidence),
    ]

    follow_up = describe_issue_follow_up(
        delivery_stage=timeline.get("delivery_stage"),
        readiness_summary=readiness_summary,
        freshness_signal=freshness_signal,
        continuity_summary=continuity_summary,
    )
    uncertainty_note = describe_uncertainty_note(
        confidence=confidence,
        confidence_detail=confidence_detail,
        inference_level=inference_level_from_counts(
            connector_count=connector_count,
            inferred_count=inferred_count,
            mock_count=mock_count,
        ),
        stage_evidence=stage_evidence,
    )
    risk_level = derive_risk_level(risk_signal)
    freshness_level = derive_freshness_level(freshness_signal)
    action_priority = action_priority_from_signals(
        risk_level=risk_level,
        freshness_level=freshness_level,
        confidence=confidence,
        stage_evidence=stage_evidence,
    )
    review_window = review_window_from_priority(action_priority)
    weekly_review = build_weekly_review_struct(
        scope="issue",
        observed_facts=observed_facts,
        inferred_judgments=inferred_judgments,
        follow_up=follow_up,
        action_priority=action_priority,
        confidence_reason=confidence_reason,
        review_window=review_window,
        stable_signals=build_issue_stable_signals(
            delivery_stage=timeline.get("delivery_stage"),
            confidence=confidence,
            freshness_level=freshness_level,
            variance=estimate.get("variance", "untracked"),
        ),
        watch_signals=build_issue_watch_signals(
            risk_signal=risk_signal,
            freshness_signal=freshness_signal,
            confidence_detail=confidence_detail,
            stage_evidence=stage_evidence,
        ),
        uncertainty_driver=describe_uncertainty_driver(confidence_detail, uncertainty_note),
    )
    execution_maturity = describe_issue_execution_maturity(
        delivery_stage=timeline.get("delivery_stage"),
        linked_commits=linked_commits,
        progress_pct=progress_pct,
    )
    fulfillment_confidence = describe_issue_fulfillment_confidence(progress_pct, confidence, connector_count, inferred_count)
    downstream_visibility = describe_issue_downstream_visibility(stage_evidence, connector_count, inferred_count, mock_count)
    risk_to_completion = describe_issue_risk_to_completion(risk_signal, readiness_summary, freshness_signal)
    why_it_matters = describe_issue_why_it_matters(issue_id, timeline.get("delivery_stage"), risk_to_completion)
    review_focus = describe_issue_review_focus(readiness_summary, freshness_signal, follow_up)
    top_risk_driver = describe_top_risk_driver(
        risk_signal=risk_signal,
        uncertainty_note=uncertainty_note,
        confidence_detail=confidence_detail,
    )
    summary_confidence_band = derive_summary_confidence_band(confidence, confidence_detail)

    return {
        "scope": "issue",
        "id": issue_id,
        "issue_id": issue_id,
        "title": issue.get("title") or issue_id,
        "headline": (
            f"{issue_id} has progressed to {timeline.get('delivery_stage', 'planned')} with "
            f"{stage_evidence_label(connector_count, inferred_count, mock_count)}."
        ),
        "executive_summary": (
            f"{issue_id} represents {normalize_spaces(str(issue.get('title') or issue_id))}, with visible execution in "
            f"{human_list(modules[:3]) or 'tracked modules'} and delivery currently at {timeline.get('delivery_stage', 'planned')}."
        ),
        "summary": (
            f"{issue_id} is roughly {progress_pct}% through its heuristic effort plan, with visible execution in "
            f"{human_list(modules[:3]) or 'tracked product work'} and current delivery standing at {timeline.get('delivery_stage', 'planned')}."
        ),
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "confidence_detail": confidence_detail,
        "evidence_count": evidence_count,
        "generated_from": [
            "issue metadata",
            "linked commit telemetry",
            "effort estimates",
            "delivery stage records",
            "knowledge risk signals",
        ],
        "inference_level": inference_level_from_counts(
            connector_count=connector_count,
            inferred_count=inferred_count,
            mock_count=mock_count,
        ),
        "progress_summary": progress_summary,
        "readiness_summary": readiness_summary,
        "variance_summary": variance_summary,
        "continuity_summary": continuity_summary,
        "freshness_summary": freshness_signal,
        "follow_up": follow_up,
        "highlights": [
            {"label": "Requirement Progress", "value": progress_summary},
            {"label": "Delivery Readiness", "value": readiness_summary},
            {"label": "Effort Variance", "value": variance_summary},
            {"label": "Continuity Risk", "value": continuity_summary},
            {"label": "Freshness", "value": freshness_signal},
            {"label": "Recommended Follow-Up", "value": follow_up},
        ],
        "top_requirements": [issue_id],
        "top_modules": modules[:4],
        "top_repositories": repositories[:4],
        "top_files": ranked_file_paths(events)[:4],
        "top_contributors": contributors[:4],
        "risk_signal": risk_signal,
        "risk_level": risk_level,
        "freshness_note": freshness_signal,
        "freshness_level": freshness_level,
        "uncertainty_note": uncertainty_note,
        "why_it_matters": why_it_matters,
        "review_focus": review_focus,
        "top_risk_driver": top_risk_driver,
        "recommended_follow_up": follow_up,
        "summary_confidence_band": summary_confidence_band,
        "uncertainty_driver": describe_uncertainty_driver(confidence_detail, uncertainty_note),
        "execution_maturity": execution_maturity,
        "fulfillment_confidence": fulfillment_confidence,
        "downstream_visibility": downstream_visibility,
        "risk_to_completion": risk_to_completion,
        "action_priority": action_priority,
        "review_window": review_window,
        "review_owner": "issue owner",
        "weekly_review": weekly_review,
        "observed_facts": observed_facts,
        "inferred_judgments": inferred_judgments,
        "delivery_stage": timeline.get("delivery_stage", "planned"),
        "variance": estimate.get("variance", "untracked"),
        "stage_evidence": stage_evidence,
    }


def stage_mix_for_issues(issue_ids: list[str], timeline_lookup: dict[str, dict[str, Any]]) -> str:
    counter: Counter[str] = Counter()
    for issue_id in issue_ids:
        stage = normalize_spaces(str(timeline_lookup.get(issue_id, {}).get("delivery_stage") or "planned")).lower()
        if stage:
            counter[stage] += 1
    top = [f"{count} {stage}" for stage, count in counter.most_common(2)]
    return human_list(top) or "early delivery stages"


def summarize_stage_evidence_for_requirements(issue_ids: list[str], timeline_lookup: dict[str, dict[str, Any]]) -> str:
    evidence: list[str] = []
    for issue_id in issue_ids[:2]:
        stage_evidence = summarize_stage_evidence(timeline_lookup.get(issue_id, {}))
        if stage_evidence and stage_evidence not in evidence:
            evidence.append(stage_evidence)
    return human_list(evidence) or "Stage evidence is still weak in the current delivery feed."


def aggregate_timeline_source_counts(
    issue_ids: list[str],
    timeline_lookup: dict[str, dict[str, Any]],
) -> tuple[int, int, int]:
    connector_count = 0
    inferred_count = 0
    mock_count = 0
    for issue_id in issue_ids[:4]:
        issue_connector, issue_inferred, issue_mock = timeline_source_counts(timeline_lookup.get(issue_id, {}))
        connector_count += issue_connector
        inferred_count += issue_inferred
        mock_count += issue_mock
    return connector_count, inferred_count, mock_count


def timeline_source_counts(timeline: dict[str, Any]) -> tuple[int, int, int]:
    source_breakdown = timeline.get("source_breakdown") or {}
    return (
        int(to_number(source_breakdown.get("connector"))),
        int(to_number(source_breakdown.get("inferred"))),
        int(to_number(source_breakdown.get("mock"))),
    )


def inference_level_from_counts(
    *,
    connector_count: int,
    inferred_count: int,
    mock_count: int,
) -> str:
    if connector_count and inferred_count == 0 and mock_count == 0:
        return "low"
    if connector_count:
        return "medium"
    if inferred_count:
        return "high"
    return "high"


def stage_evidence_label(connector_count: int, inferred_count: int, mock_count: int) -> str:
    if connector_count and inferred_count == 0 and mock_count == 0:
        return "fully connector-backed stage evidence"
    if connector_count and (inferred_count or mock_count):
        return "mixed connector-backed and inferred stage evidence"
    if inferred_count:
        return "mostly inferred stage evidence"
    if mock_count:
        return "placeholder-only stage evidence"
    return "limited stage evidence"


def stage_evidence_source_sentence(connector_count: int, inferred_count: int, mock_count: int) -> str:
    if connector_count and inferred_count == 0 and mock_count == 0:
        return "Stage evidence is fully connector-backed."
    if connector_count and (inferred_count or mock_count):
        parts = [f"{connector_count} connector-backed"]
        if inferred_count:
            parts.append(f"{inferred_count} inferred")
        if mock_count:
            parts.append(f"{mock_count} placeholder")
        return f"Stage evidence is mixed: {human_list(parts)} stages contribute to the current delivery view."
    if inferred_count:
        suffix = f" with {mock_count} placeholder stages still filling gaps" if mock_count else ""
        return f"Stage evidence is present but mostly inferred from linked delivery signals{suffix}."
    if mock_count:
        return "Stage evidence is still weak and currently relies on placeholder stages."
    return "Stage evidence is still weak in the current delivery feed."


def stage_status_phrase(label: str, stage: dict[str, Any]) -> str:
    if not stage:
        return ""
    status = normalize_spaces(str(stage.get("status") or "")).lower()
    if not status or status == "unknown":
        return ""
    if label == "PR":
        if status == "merged":
            return "the PR is merged"
        if status in {"open", "approved"}:
            return f"the PR is {status}"
        if status == "blocked":
            return "the PR is blocked"
        return f"the PR is {status}"
    if label == "CI":
        if status == "passed":
            return "CI has passed"
        if status in {"running", "queued"}:
            return f"CI is {status}"
        if status == "blocked":
            return "CI is blocked"
        return f"CI is {status}"
    if label == "Deployment":
        if status in {"success", "live"}:
            return "deployment is live"
        if status in {"pending", "in progress"}:
            return f"deployment is {status}"
        if status == "blocked":
            return "deployment is blocked"
        return f"deployment is {status}"
    return ""


def summarize_stage_evidence(timeline: dict[str, Any]) -> str:
    if not timeline:
        return "Stage evidence is still weak in the current delivery feed."

    connector_count, inferred_count, mock_count = timeline_source_counts(timeline)
    source_sentence = stage_evidence_source_sentence(connector_count, inferred_count, mock_count)
    stage_signals = [
        stage_status_phrase("PR", timeline.get("pull_request") or {}),
        stage_status_phrase("CI", timeline.get("ci") or {}),
        stage_status_phrase("Deployment", timeline.get("deployment") or {}),
    ]
    stage_signals = [signal for signal in stage_signals if signal]
    if stage_signals:
        return f"{source_sentence} Current signals show {human_list(stage_signals)}."
    return source_sentence


def top_modules_for_events(events: list[dict[str, Any]], limit: int) -> list[str]:
    return ranked_modules(events)[:limit]


def ranked_issue_ids(events: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for event in events:
        issue_id = normalize_spaces(str(event.get("issue_id") or event.get("linked_issue") or ""))
        if issue_id:
            counter[issue_id] += max(1, int(round(to_number(event.get("active_minutes")) / 30)))
    return [issue_id for issue_id, _count in counter.most_common()]


def ranked_modules(events: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for event in events:
        for module in event.get("modules_touched") or []:
            normalized = normalize_spaces(str(module))
            if normalized:
                counter[normalized] += 1
    return [module for module, _count in counter.most_common()]


def ranked_repositories(events: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for event in events:
        repository = normalize_spaces(str(event.get("repository_name") or ""))
        if repository:
            counter[repository] += 1
    return [repository for repository, _count in counter.most_common()]


def ranked_file_paths(events: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for event in events:
        for file in extract_files(event):
            path = normalize_spaces(str(file.get("file_path") or ""))
            if path:
                counter[path] += 1
    return [path for path, _count in counter.most_common()]


def extract_files(event: dict[str, Any]) -> list[dict[str, Any]]:
    files = event.get("files")
    if isinstance(files, list):
        return [file for file in files if isinstance(file, dict)]

    files_json = event.get("files_json")
    if isinstance(files_json, dict):
        nested = files_json.get("files")
        if isinstance(nested, list):
            return [file for file in nested if isinstance(file, dict)]
    if isinstance(files_json, list):
        return [file for file in files_json if isinstance(file, dict)]
    return []


def event_field_coverage(
    events: list[dict[str, Any]],
    key: str,
    truthy_list: bool = False,
    allow_files_json: bool = False,
) -> float:
    if not events:
        return 0.0

    present = 0
    for event in events:
        if truthy_list:
            value = event.get(key)
            if isinstance(value, list) and len(value) > 0:
                present += 1
                continue
            if allow_files_json and extract_files(event):
                present += 1
                continue
        elif value_present(event.get(key)):
            present += 1
    return round((present / len(events)) * 100, 1)


def infer_delivery_stage_from_statuses(
    commit_ids: list[str],
    pr_status: str,
    ci_status: str,
    deployment_status: str,
) -> str:
    if deployment_status in {"success", "live", "deployed"}:
        return "deployed"
    if deployment_status in {"in progress", "pending"}:
        return "deploying"
    if ci_status in {"passed", "success"}:
        return "ready to deploy"
    if ci_status in {"running", "queued"}:
        return "in ci"
    if pr_status in {"merged", "approved", "open"}:
        return "in review"
    if commit_ids:
        return "coded"
    return "planned"


def assess_summary_confidence(
    *,
    event_count: int,
    linked_commits: int,
    focus_available: bool,
    module_count: int,
    repository_count: int,
    connector_stage_count: int = 0,
    inferred_stage_count: int = 0,
) -> dict[str, Any]:
    score = 0.0
    factors: list[str] = []
    gaps: list[str] = []

    suggestions: list[str] = []

    if event_count >= 4:
        score += 2.0
        factors.append(f"{event_count} telemetry events")
    elif event_count >= 2:
        score += 1.0
        factors.append(f"{event_count} telemetry events")
    else:
        gaps.append("only one telemetry event")
        suggestions.append("collect more than one linked telemetry event")

    if linked_commits >= 3:
        score += 1.5
        factors.append(f"{linked_commits} linked commits")
    elif linked_commits >= 1:
        score += 0.75
        factors.append(f"{linked_commits} linked commit")
    else:
        gaps.append("no linked commits")
        suggestions.append("link commits to the requirement")

    if focus_available:
        score += 0.5
        factors.append("focus telemetry available")
    else:
        gaps.append("missing focus telemetry")
        suggestions.append("capture focus telemetry")

    if module_count >= 2:
        score += 1.0
        factors.append(f"{module_count} modules touched")
    elif module_count == 1:
        score += 0.5
        factors.append("1 visible module")
    else:
        gaps.append("no visible modules")
        suggestions.append("capture module-level activity")

    if repository_count >= 2:
        score += 1.0
        factors.append(f"{repository_count} repositories represented")
    elif repository_count == 1:
        score += 0.5
        factors.append("1 repository represented")
    else:
        gaps.append("no visible repository")
        suggestions.append("capture repository metadata")

    if connector_stage_count >= 2:
        score += 1.5
        factors.append(f"{connector_stage_count} connector-backed delivery stages")
    elif connector_stage_count >= 1:
        score += 1.0
        factors.append("1 connector-backed delivery stage")
    elif inferred_stage_count >= 1:
        score += 0.5
        factors.append(f"{inferred_stage_count} inferred delivery stages")
        gaps.append("delivery evidence is inferred rather than connector-backed")
        suggestions.append("capture direct PR, CI, or deployment evidence")
    else:
        gaps.append("no delivery-stage evidence")
        suggestions.append("capture PR, CI, or deployment evidence")

    if score >= 6.0:
        confidence = "high"
    elif score >= 3.5:
        confidence = "medium"
    else:
        confidence = "low"

    if confidence == "high":
        reason = (
            f"High confidence because the summary is grounded in {human_list(factors[:3])}, "
            f"which is enough evidence for a weekly read."
        )
    elif confidence == "medium":
        reason = (
            f"Medium confidence because evidence includes {human_list(factors[:2])}, "
            f"but {human_list(gaps[:2]) or 'coverage is still partial'}."
        )
    else:
        reason = (
            f"Low confidence because {human_list(gaps[:3]) or 'evidence remains sparse'}, "
            f"so this is a directional weekly read rather than a complete one."
        )
    evidence_density = "rich" if len(factors) >= 5 else ("balanced" if len(factors) >= 3 else "sparse")
    certainty_bias = (
        "observed-heavy"
        if connector_stage_count >= max(1, inferred_stage_count)
        else "inferred-heavy"
    )

    return {
        "level": confidence,
        "reason": reason,
        "score": round(score, 2),
        "evidence_density": evidence_density,
        "certainty_bias": certainty_bias,
        "supporting_evidence": factors[:4],
        "missing_evidence": gaps[:4],
        "improve_confidence": confidence_improvement_hint(suggestions),
    }


def summary_confidence(
    *,
    event_count: int,
    linked_commits: int,
    focus_available: bool,
    module_count: int,
    repository_count: int,
    connector_stage_count: int = 0,
    inferred_stage_count: int = 0,
) -> tuple[str, str]:
    detail = assess_summary_confidence(
        event_count=event_count,
        linked_commits=linked_commits,
        focus_available=focus_available,
        module_count=module_count,
        repository_count=repository_count,
        connector_stage_count=connector_stage_count,
        inferred_stage_count=inferred_stage_count,
    )
    return detail["level"], detail["reason"]


def confidence_improvement_hint(suggestions: list[str]) -> str:
    unique = dedupe_preserve_order(suggestions)
    if not unique:
        return "Confidence is already supported by the current evidence profile."
    return f"To improve confidence, {human_list(unique[:2])}."


def derive_risk_level(risk_signal: str) -> str:
    text = normalize_spaces(risk_signal).lower()
    if any(token in text for token in ["high", "elevated", "launch-blocking", "stale", "blocked"]):
        return "high"
    if any(token in text for token in ["moderate", "meaningful", "watch", "concentration"]):
        return "medium"
    return "low"


def derive_freshness_level(freshness_note: str) -> str:
    text = normalize_spaces(freshness_note).lower()
    if any(token in text for token in ["stale", "unclear", "follow-up may be needed", "days old"]):
        return "stale"
    if any(token in text for token in ["slowing", "mixed"]):
        return "watch"
    return "fresh"


def action_priority_from_signals(
    *,
    risk_level: str,
    freshness_level: str,
    confidence: str,
    stage_evidence: str = "",
) -> str:
    evidence_text = normalize_spaces(stage_evidence).lower()
    if risk_level == "high" or freshness_level == "stale":
        return "urgent"
    if confidence == "low" or freshness_level == "watch" or "weak" in evidence_text or "placeholder" in evidence_text:
        return "watch"
    return "stable"


def review_window_from_priority(priority: str) -> str:
    if priority == "urgent":
        return "Review within 24 hours"
    if priority == "watch":
        return "Review within this sprint"
    return "Review in the next weekly cycle"


def build_weekly_review_struct(
    *,
    scope: str,
    observed_facts: list[str],
    inferred_judgments: list[str],
    follow_up: str,
    action_priority: str,
    confidence_reason: str,
    review_window: str,
    stable_signals: list[str],
    watch_signals: list[str],
    uncertainty_driver: str,
) -> dict[str, Any]:
    return {
        "scope": scope,
        "observed_snapshot": observed_facts[:2],
        "inferred_signal": inferred_judgments[:2],
        "decision_basis": confidence_reason,
        "next_action": follow_up,
        "action_priority": action_priority,
        "review_window": review_window,
        "stable_signals": stable_signals[:3],
        "watch_signals": watch_signals[:3],
        "uncertainty_driver": uncertainty_driver,
    }


def derive_summary_confidence_band(confidence: str, confidence_detail: dict[str, Any]) -> str:
    density = normalize_spaces(str(confidence_detail.get("evidence_density") or "sparse")).lower()
    if confidence == "high":
        return "Decision-ready"
    if confidence == "medium" and density in {"rich", "balanced"}:
        return "Review-ready"
    if confidence == "medium":
        return "Use with caution"
    return "Directional only"


def describe_uncertainty_driver(confidence_detail: dict[str, Any], uncertainty_note: str) -> str:
    missing = confidence_detail.get("missing_evidence") or []
    if missing:
        return human_list(missing[:2])
    return uncertainty_note


def describe_top_risk_driver(
    *,
    risk_signal: str,
    uncertainty_note: str,
    confidence_detail: dict[str, Any],
) -> str:
    missing = confidence_detail.get("missing_evidence") or []
    if derive_risk_level(risk_signal) == "high":
        return risk_signal
    if missing:
        return f"The main risk driver is incomplete evidence coverage: {human_list(missing[:2])}."
    return uncertainty_note or risk_signal


def describe_portfolio_why_it_matters(
    *,
    active_requirements: int,
    stale_requirements: int,
    high_risk_count: int,
    connector_stage_count: int,
) -> str:
    if stale_requirements or high_risk_count:
        return (
            f"Portfolio impact: {active_requirements} active requirements are visible in one review surface, "
            f"but {stale_requirements} stale requirements and {high_risk_count} concentration pockets can skew the weekly read."
        )
    if connector_stage_count:
        return "Portfolio impact: delivery progress is visible enough to support a weekly operating review instead of raw telemetry inspection."
    return "Portfolio impact: the overall execution picture is reviewable weekly, even though downstream delivery proof is still incomplete."


def describe_portfolio_review_focus(
    *,
    coverage: dict[str, Any],
    stale_requirements: int,
    high_risk_count: int,
) -> str:
    if stale_requirements:
        return (
            f"Start with the {stale_requirements} stale requirements before trusting the portfolio momentum read."
        )
    if high_risk_count:
        return f"Keep attention on the {high_risk_count} highest-risk knowledge concentration areas."
    connector_pct = to_number((coverage.get("delivery") or {}).get("connector_stage_coverage_pct"))
    if connector_pct < 40:
        return "Rebuild downstream delivery visibility because the portfolio is still inference-heavy."
    return "Protect current coverage quality while validating the next visible delivery checkpoints."


def describe_developer_why_it_matters(issue_ids: list[str], modules: list[str], repositories: list[str]) -> str:
    return (
        f"Developer impact: visible effort in {human_list(modules[:2]) or 'tracked modules'} moved "
        f"{human_list(issue_ids[:2]) or 'linked requirements'} across {human_list(repositories[:2]) or 'tracked repositories'}."
    )


def describe_developer_review_focus(modules: list[str], confidence_detail: dict[str, Any], follow_up: str) -> str:
    missing = confidence_detail.get("missing_evidence") or []
    if missing:
        return (
            f"Stay on {human_list(modules[:2]) or 'current modules'} while closing evidence gaps in "
            f"{human_list(missing[:2])} before declaring the work ready."
        )
    return follow_up or "Keep attention on the current module cluster and the next-phase work ahead."


def describe_manager_why_it_matters(issue_titles: list[str], stage_mix: str, risk_signal: str) -> str:
    requirement_phrase = human_list(issue_titles) or "tracked requirements"
    if derive_risk_level(risk_signal) == "high":
        return f"Manager impact: {requirement_phrase} are moving through {stage_mix}, but concentration risk can still affect delivery continuity."
    return f"Manager impact: {requirement_phrase} show enough delivery movement to support weekly prioritization through {stage_mix}."


def describe_manager_review_focus(
    stage_mix: str,
    confidence_detail: dict[str, Any],
    risk_signal: str,
    stage_evidence: str,
) -> str:
    missing = confidence_detail.get("missing_evidence") or []
    if derive_risk_level(risk_signal) == "high":
        return f"Secure ownership coverage and next-stage exits while work stays clustered in {stage_mix}."
    if "mostly inferred" in stage_evidence.lower() or missing:
        return f"Confirm downstream evidence and close {human_list(missing[:2]) or 'delivery proof gaps'} before trusting the chain."
    return f"Verify that {stage_mix} keeps moving without losing current delivery momentum."


def describe_issue_execution_maturity(delivery_stage: Any, linked_commits: int, progress_pct: int) -> str:
    stage = normalize_spaces(str(delivery_stage or "planned")).lower()
    if stage in {"deployed", "deploying", "ready to deploy"}:
        return f"Execution maturity is late-stage because the requirement is already {stage}."
    if stage in {"in ci", "in review"}:
        return f"Execution maturity is mid-stage because the requirement has moved into {stage}."
    if linked_commits >= 2 or progress_pct >= 30:
        return "Execution maturity is emerging because implementation is visible, but downstream checkpoints are still forming."
    return "Execution maturity is early because only thin implementation evidence is visible so far."


def describe_issue_fulfillment_confidence(progress_pct: int, confidence: str, connector_count: int, inferred_count: int) -> str:
    if confidence == "high" and (connector_count or progress_pct >= 70):
        return "Fulfillment confidence is strong because progress and downstream evidence both look credible."
    if confidence == "medium" and (connector_count or inferred_count):
        return "Fulfillment confidence is usable for weekly review, but completion still depends on downstream confirmation."
    return "Fulfillment confidence is limited because execution evidence is still sparse or heavily inferred."


def describe_issue_downstream_visibility(stage_evidence: str, connector_count: int, inferred_count: int, mock_count: int) -> str:
    if connector_count and inferred_count == 0 and mock_count == 0:
        return "Downstream visibility is strong because PR, CI, and deployment evidence are connector-backed."
    if connector_count:
        return "Downstream visibility is mixed because some release evidence is connector-backed and some is still inferred."
    if inferred_count:
        return "Downstream visibility is partial because delivery stages are visible but still inferred from linked activity."
    return f"Downstream visibility is weak because {stage_evidence.lower()}"


def describe_issue_risk_to_completion(risk_signal: str, readiness_summary: str, freshness_signal: str) -> str:
    if derive_risk_level(risk_signal) == "high":
        return "Risk to completion is elevated because the current ownership or continuity pattern could slow the remaining delivery path."
    if "early" in readiness_summary.lower() or "low" in readiness_summary.lower():
        return "Risk to completion is moderate because downstream readiness is still early."
    if "slowing momentum" in freshness_signal.lower() or "follow-up may be needed" in freshness_signal.lower():
        return "Risk to completion is moderate because freshness signals suggest momentum may be fading."
    return "Risk to completion is currently contained because visible execution is still progressing."


def describe_issue_why_it_matters(issue_id: str, delivery_stage: Any, risk_to_completion: str) -> str:
    stage = normalize_spaces(str(delivery_stage or "planned")).lower()
    return f"Requirement impact: {issue_id} is now reviewable at the {stage} stage, and {risk_to_completion.lower()}"


def describe_issue_review_focus(readiness_summary: str, freshness_signal: str, follow_up: str) -> str:
    if "early" in readiness_summary.lower() or "low" in readiness_summary.lower():
        return "Keep attention on the next downstream checkpoint so delivery evidence becomes more concrete."
    if "slowing momentum" in freshness_signal.lower() or "follow-up may be needed" in freshness_signal.lower():
        return "Refresh ownership and activity signals before the issue goes stale."
    return follow_up or "Keep attention on linking readiness signals to the next delivery checkpoint."


def build_portfolio_stable_signals(
    *,
    connector_stage_count: int,
    stale_requirements: int,
    confidence: str,
    traceability_note: str,
) -> list[str]:
    signals: list[str] = []
    if connector_stage_count:
        signals.append("Connector-backed delivery stages are present")
    if stale_requirements == 0:
        signals.append("No stale requirements are currently visible")
    if confidence in {"high", "medium"}:
        signals.append("Evidence is sufficient for weekly portfolio review")
    if "strong" in traceability_note.lower() or "usable" in traceability_note.lower():
        signals.append("Traceability is usable across linked scope")
    return signals or ["Some portfolio movement is visible in the current snapshot"]


def build_portfolio_watch_signals(
    *,
    stale_requirements: int,
    high_risk_count: int,
    confidence_detail: dict[str, Any],
    inferred_stage_count: int,
) -> list[str]:
    signals: list[str] = []
    if stale_requirements:
        signals.append(f"{stale_requirements} requirements look stale")
    if high_risk_count:
        signals.append(f"{high_risk_count} concentrated knowledge areas need review")
    if inferred_stage_count:
        signals.append("Some delivery progression is still inferred")
    signals.extend((confidence_detail.get("missing_evidence") or [])[:1])
    return signals or ["No immediate portfolio watch item stands out"]


def build_developer_stable_signals(
    *,
    linked_commits: int,
    freshness_level: str,
    modules: list[str],
    repositories: list[str],
    confidence: str,
) -> list[str]:
    signals: list[str] = []
    if linked_commits >= 2:
        signals.append("Multiple linked commits support the work pattern")
    if freshness_level == "fresh":
        signals.append("Recent activity is still within the weekly window")
    if modules:
        signals.append(f"Work concentration is visible in {human_list(modules[:2])}")
    if repositories:
        signals.append(f"Repository coverage includes {human_list(repositories[:2])}")
    if confidence == "high":
        signals.append("Confidence is strong enough for a durable weekly read")
    return signals or ["Some personal work movement is visible"]


def build_developer_watch_signals(
    *,
    risk_signal: str,
    confidence_detail: dict[str, Any],
    stage_evidence: str,
) -> list[str]:
    signals: list[str] = []
    if derive_risk_level(risk_signal) in {"high", "medium"}:
        signals.append(risk_signal)
    if "mostly inferred" in stage_evidence.lower() or "weak" in stage_evidence.lower():
        signals.append("Downstream delivery evidence is still thin")
    signals.extend((confidence_detail.get("missing_evidence") or [])[:2])
    return signals or ["No major developer watch signal stands out"]


def build_manager_stable_signals(
    *,
    stage_mix: str,
    confidence: str,
    risk_level: str,
) -> list[str]:
    signals: list[str] = [f"Delivery movement is visible across {stage_mix}"]
    if confidence in {"high", "medium"}:
        signals.append("Evidence is sufficient for a management checkpoint")
    if risk_level == "low":
        signals.append("No immediate concentration blocker is dominating the review")
    return signals


def build_manager_watch_signals(
    *,
    risk_signal: str,
    confidence_detail: dict[str, Any],
    stage_evidence: str,
) -> list[str]:
    signals: list[str] = []
    if derive_risk_level(risk_signal) in {"high", "medium"}:
        signals.append(risk_signal)
    if "mostly inferred" in stage_evidence.lower():
        signals.append("Delivery stage evidence still leans on inference")
    signals.extend((confidence_detail.get("missing_evidence") or [])[:1])
    return signals or ["No major manager watch signal stands out"]


def build_issue_stable_signals(
    *,
    delivery_stage: Any,
    confidence: str,
    freshness_level: str,
    variance: Any,
) -> list[str]:
    stage = normalize_spaces(str(delivery_stage or "planned")).lower()
    signals: list[str] = []
    if stage in {"in review", "in ci", "ready to deploy", "deploying", "deployed"}:
        signals.append(f"Delivery has reached the {stage} stage")
    if freshness_level == "fresh":
        signals.append("Recent execution is still fresh")
    if confidence in {"high", "medium"}:
        signals.append("Evidence is sufficient for an issue-level delivery read")
    if str(variance or "") == "on plan":
        signals.append("Effort is tracking close to plan")
    return signals or ["Some issue execution is visible"]


def build_issue_watch_signals(
    *,
    risk_signal: str,
    freshness_signal: str,
    confidence_detail: dict[str, Any],
    stage_evidence: str,
) -> list[str]:
    signals: list[str] = []
    if derive_risk_level(risk_signal) in {"high", "medium"}:
        signals.append(risk_signal)
    if "slowing momentum" in freshness_signal.lower() or "follow-up may be needed" in freshness_signal.lower():
        signals.append("Freshness signals suggest delivery momentum may be fading")
    if "mostly inferred" in stage_evidence.lower() or "weak" in stage_evidence.lower():
        signals.append("Downstream delivery proof is still limited")
    signals.extend((confidence_detail.get("missing_evidence") or [])[:1])
    return signals or ["No major issue watch signal stands out"]


def describe_workload(value: Any) -> str:
    workload = to_number(value)
    if workload >= 40:
        return "Workload concentration is high and worth balancing if this pattern continues."
    if workload >= 22:
        return "Workload concentration is meaningful but still within a manageable shared range."
    return "Workload concentration is light relative to the rest of the tracked team."


def describe_focus(value: Any) -> str:
    focus = to_number(value)
    if focus >= 0.92:
        return "consistently high"
    if focus >= 0.82:
        return "steady"
    return "under context-switch pressure"


def describe_developer_risk(
    metric: dict[str, Any],
    modules: list[str],
    risk_lookup: dict[str, dict[str, Any]],
) -> str:
    overtime_commits = int(round(to_number(metric.get("overtime_commits"))))
    concentrated_modules = [module for module in modules if risk_lookup.get(module.lower(), {}).get("severity") in {"high", "medium"}]

    if overtime_commits >= 3 and concentrated_modules:
        return f"Risk is elevated because overtime activity overlaps with concentrated ownership in {human_list(concentrated_modules[:2])}."
    if overtime_commits >= 3:
        return "Risk is elevated because a meaningful share of delivery landed outside standard working hours."
    if concentrated_modules:
        return f"Continuity risk is present because knowledge is concentrated in {human_list(concentrated_modules[:2])}."
    return "No immediate workload or continuity signal stands out in the current window."


def describe_issue_effort(estimate: dict[str, Any]) -> str:
    variance = str(estimate.get("variance") or "untracked")
    if variance == "above plan":
        return "Effort is running above the original heuristic plan, which may indicate scope growth or hidden complexity."
    if variance == "below plan":
        return "Effort is still below the heuristic plan, so delivery momentum may still be early."
    if variance == "on plan":
        return "Effort is tracking close to the heuristic plan."
    return "There is not enough observed execution yet to compare against the heuristic plan."


def describe_issue_variance(estimate: dict[str, Any]) -> str:
    variance = str(estimate.get("variance") or "untracked")
    if variance == "above plan":
        return "Effort variance is above plan, so this requirement may be absorbing more scope or complexity than first estimated."
    if variance == "below plan":
        return "Effort variance is still below plan, which usually means delivery is early or evidence is still accumulating."
    if variance == "on plan":
        return "Effort variance is close to plan, so current execution looks proportionate to the requirement size."
    return "Effort variance is still untracked because the execution footprint is too thin to compare reliably."


def describe_issue_progress(progress_pct: int, linked_commits: int, delivery_stage: Any) -> str:
    stage = normalize_spaces(str(delivery_stage or "planned")).lower()
    if progress_pct >= 80:
        return f"Requirement progress is advanced at roughly {progress_pct}% of plan, with delivery already in {stage}."
    if progress_pct >= 40:
        return f"Requirement progress is tangible at roughly {progress_pct}% of plan, with execution moving through {stage}."
    if linked_commits >= 1:
        return f"Requirement progress is early at roughly {progress_pct}% of plan, but linked implementation has started."
    return "Requirement progress is still early because little linked implementation is visible yet."


def describe_issue_readiness(
    timeline: dict[str, Any],
    connector_count: int,
    inferred_count: int,
    mock_count: int,
) -> str:
    stage = normalize_spaces(str(timeline.get("delivery_stage") or "planned")).lower()
    evidence_label = stage_evidence_label(connector_count, inferred_count, mock_count)
    if stage == "deployed":
        return f"Delivery readiness is high because the requirement is already deployed with {evidence_label}."
    if stage in {"deploying", "ready to deploy"}:
        return f"Delivery readiness is strengthening because the requirement is {stage} with {evidence_label}."
    if stage in {"in ci", "in review"}:
        return f"Delivery readiness is emerging because the requirement is {stage} and still depends on {evidence_label}."
    if stage == "coded":
        return f"Delivery readiness is still early because work is coded but downstream validation remains limited and {evidence_label}."
    return f"Delivery readiness is still low because visible execution remains in {stage} with {evidence_label}."


def describe_issue_continuity_risk(risk_signal: str, contributors: list[str]) -> str:
    contributor_count = len(contributors)
    if "No immediate delivery risk" in risk_signal:
        return "Continuity risk is currently contained because no clear ownership or freshness blocker stands out."
    if contributor_count <= 1:
        return f"Continuity risk is elevated because visible execution depends on {contributor_count} primary contributor and the current linkage shows limited bench depth."
    return risk_signal.replace("Delivery risk is", "Continuity risk is")


def describe_manager_takeaway(issue_titles: list[str], stage_mix: str, risk_signal: str) -> str:
    requirement_phrase = human_list(issue_titles) or "tracked requirements"
    if "No immediate workload or continuity signal" in risk_signal:
        return f"For managers, this means {requirement_phrase} are moving through {stage_mix} without an immediate continuity blocker."
    if "Risk is elevated" in risk_signal or "Continuity risk" in risk_signal:
        return f"For managers, this means {requirement_phrase} are moving, but concentration risk should be watched as delivery progresses through {stage_mix}."
    return f"For managers, this means {requirement_phrase} have measurable delivery movement and should remain reviewable through {stage_mix}."


def describe_portfolio_follow_up(
    *,
    coverage: dict[str, Any],
    stale_requirements: int,
    confidence: str,
    connector_stage_count: int,
    inferred_stage_count: int,
) -> str:
    if stale_requirements:
        return "Portfolio follow-up should review stale requirements first so visible movement matches current delivery stages."
    if confidence == "low":
        return "Portfolio follow-up should improve linkage quality before relying on the summaries for broader review decisions."
    if inferred_stage_count and not connector_stage_count:
        return "Portfolio follow-up should confirm downstream PR, CI, or deployment evidence so launch status is not mostly inferred."
    if to_number((coverage.get("delivery") or {}).get("requirements_with_links_pct")) < 70:
        return "Portfolio follow-up should improve requirement-to-commit linkage so the weekly picture covers more of the tracked scope."
    return "Portfolio follow-up should keep weekly review focused on the highest-risk modules and the next visible release checkpoints."


def describe_manager_follow_up(stage_mix: str, risk_signal: str, stage_evidence: str) -> str:
    if "Risk is elevated" in risk_signal or "Continuity risk" in risk_signal:
        return f"Next manager check should confirm ownership coverage and next-stage readiness while delivery remains clustered in {stage_mix}."
    if "mostly inferred" in stage_evidence.lower() or "weak" in stage_evidence.lower():
        return "Next manager check should confirm PR, CI, or deployment evidence so the delivery view is not relying mostly on inferred stages."
    return f"Next manager check should keep {stage_mix} moving by confirming the next visible checkpoint and preserving current execution momentum."


def describe_developer_follow_up(focus_signal: str, workload_signal: str, risk_signal: str, issue_ids: list[str]) -> str:
    if "under context-switch pressure" in focus_signal:
        return f"Next developer step should reduce switching across {human_list(issue_ids[:2]) or 'linked requirements'} and protect focus time around the current module cluster."
    if "high" in workload_signal.lower():
        return "Next developer step should protect handoff quality and review support so concentrated execution does not turn into continuity risk."
    if "Risk is elevated" in risk_signal or "Continuity risk" in risk_signal:
        return "Next developer step should document or spread knowledge in the concentrated modules before the next delivery stage."
    return f"Next developer step should keep momentum on {human_list(issue_ids[:2]) or 'linked requirements'} while preserving the current focus pattern."


def describe_evidence_interpretation(confidence: str, confidence_detail: dict[str, Any], stage_evidence: str) -> str:
    missing = confidence_detail.get("missing_evidence") or []
    if confidence == "low":
        return (
            f"Evidence is still thin for a weekly read because {human_list(missing[:2]) or 'coverage remains sparse'}, "
            f"and {stage_evidence.lower() if stage_evidence else 'delivery evidence is still weak'}"
        )
    if "mostly inferred" in stage_evidence.lower():
        return "Delivery evidence is usable for review, but it still leans on inferred stage progression rather than direct downstream signals."
    if missing:
        return f"Evidence is solid enough to review, though {human_list(missing[:2])} would make the narrative more complete."
    return "Evidence is broad enough to support a weekly review without major interpretive gaps."


def describe_focus_confidence_tail(confidence: str, confidence_detail: dict[str, Any]) -> str:
    missing = confidence_detail.get("missing_evidence") or []
    if confidence == "low":
        return f"because {human_list(missing[:2]) or 'evidence remains sparse'}."
    if confidence == "medium":
        return f"while still leaving some uncertainty around {human_list(missing[:2]) or 'downstream evidence gaps'}."
    return "with enough direct evidence to treat the pattern as durable for this weekly snapshot."


def describe_issue_follow_up(
    *,
    delivery_stage: Any,
    readiness_summary: str,
    freshness_signal: str,
    continuity_summary: str,
) -> str:
    stage = normalize_spaces(str(delivery_stage or "planned")).lower()
    if "slowing momentum" in freshness_signal.lower() or "follow-up may be needed" in freshness_signal.lower():
        return f"Next issue review should refresh delivery evidence for the {stage} stage before the requirement goes stale."
    if "elevated" in continuity_summary.lower():
        return f"Next issue review should reduce single-owner dependence before the requirement advances beyond {stage}."
    if stage in {"in review", "in ci", "ready to deploy", "deploying"}:
        return f"Next issue review should confirm the next release checkpoint because readiness is already visible at the {stage} stage."
    if stage == "deployed":
        return "Next issue review should verify adoption or post-release stability because the requirement already appears deployed."
    return f"Next issue review should create the next visible delivery checkpoint so the requirement can move beyond {stage}."


def describe_activity_freshness_note(events: list[dict[str, Any]]) -> str:
    latest = latest_timestamp(events)
    if not latest:
        return "Freshness is unclear because no recent telemetry timestamp is available."
    age_days = age_in_days(latest)
    if age_days >= 10:
        return f"Recent visible activity is stale at {age_days} days old."
    if age_days >= 5:
        return f"Recent visible activity is slowing, with the last movement {age_days} days ago."
    return "Recent visible activity is fresh enough for a weekly review."


def describe_portfolio_freshness(events: list[dict[str, Any]], stale_requirements: int) -> str:
    if stale_requirements:
        return f"{stale_requirements} requirements look stale relative to their current delivery stage."
    latest = latest_timestamp(events)
    if not latest:
        return "Portfolio freshness is unclear because telemetry recency is not available."
    age_days = age_in_days(latest)
    if age_days >= 5:
        return f"Portfolio freshness is mixed because the latest visible telemetry is {age_days} days old."
    return "Portfolio freshness is healthy because recent telemetry is still arriving within the weekly window."


def describe_portfolio_traceability(coverage: dict[str, Any]) -> str:
    delivery = coverage.get("delivery") or {}
    telemetry = coverage.get("telemetry") or {}
    if to_number(delivery.get("connector_stage_coverage_pct")) >= 60 and to_number(telemetry.get("field_coverage_pct")) >= 70:
        return "Traceability is strong because delivery stages and telemetry fields are mostly well-covered."
    if to_number(delivery.get("requirements_with_links_pct")) < 50:
        return "Traceability is weak because too few requirements are linked to visible engineering movement."
    return "Traceability is mixed: requirement linkage is usable, but some delivery or telemetry fields are still sparse."


def describe_uncertainty_note(
    *,
    confidence: str,
    confidence_detail: dict[str, Any],
    inference_level: str,
    stage_evidence: str = "",
) -> str:
    missing = confidence_detail.get("missing_evidence") or []
    if confidence == "low":
        return f"Uncertainty is high because {human_list(missing[:2]) or 'evidence remains sparse'}."
    if inference_level == "high" or "mostly inferred" in stage_evidence.lower():
        return "Uncertainty is moderate because the narrative still leans on inferred delivery evidence."
    if missing:
        return f"Uncertainty is limited, but {human_list(missing[:2])} would make the summary more complete."
    return "Uncertainty is relatively low because the current summary is supported by direct evidence."


def describe_issue_risk(
    modules: list[str],
    contributors: list[str],
    risk_lookup: dict[str, dict[str, Any]],
    estimate: dict[str, Any],
    timeline: dict[str, Any],
) -> str:
    concentrated_modules = [module for module in modules if risk_lookup.get(module.lower(), {}).get("severity") == "high"]
    if concentrated_modules:
        return f"Delivery risk is higher because {human_list(concentrated_modules[:2])} depends on concentrated knowledge ownership."
    if len(contributors) <= 1 and to_number(estimate.get("observed_effort_points")) >= 3:
        return "Delivery risk is moderate because execution is being carried by a single visible contributor."
    if is_stale_record(timeline):
        return "Delivery risk is moderate because the requirement looks stale relative to its current stage."
    return "No immediate delivery risk stands out from the current linkage and telemetry."


def describe_delivery_stage(timeline: dict[str, Any]) -> str:
    if not timeline:
        return "Delivery stage remains planned from the current evidence."
    stage = normalize_spaces(str(timeline.get("delivery_stage") or "planned")).lower()
    connector_count, inferred_count, mock_count = timeline_source_counts(timeline)
    return f"Delivery stage is {stage} with {stage_evidence_label(connector_count, inferred_count, mock_count)}."


def describe_freshness(events: list[dict[str, Any]], issue: dict[str, Any]) -> str:
    latest_event = latest_timestamp(events)
    latest_issue_time = parse_datetime(issue.get("jira_updated_at") or issue.get("updated_at"))
    latest = max_datetime(latest_event, latest_issue_time)
    if not latest:
        return "Freshness could not be determined from the current records."
    age_days = age_in_days(latest)
    if age_days >= 10:
        return f"Latest visible movement is {age_days} days old, so follow-up may be needed."
    if age_days >= 5:
        return f"Latest visible movement is {age_days} days old, which suggests slowing momentum."
    return "Freshness is healthy based on recent visible activity."


def is_stale_record(record: dict[str, Any]) -> bool:
    latest = parse_datetime(record.get("latest_activity_at"))
    if not latest:
        return False
    age_days = age_in_days(latest)
    stage = normalize_spaces(str(record.get("delivery_stage") or "planned")).lower()
    return age_days >= 7 and stage not in {"deployed"}


def latest_timestamp(events: list[dict[str, Any]]):
    values = [parse_datetime(event.get("timestamp")) for event in events]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return max(values)


def datetime_sort_key(value: Any) -> float:
    parsed = parse_datetime(value)
    if not parsed:
        return 0.0
    return parsed.timestamp()


def max_datetime(first: Optional[Any], second: Optional[Any]):
    if first is None:
        return second
    if second is None:
        return first
    return max(first, second)


def age_in_days(value: Any) -> int:
    from datetime import datetime, timezone

    current = datetime.now(timezone.utc)
    candidate = value
    if candidate.tzinfo is None:
        candidate = candidate.replace(tzinfo=timezone.utc)
    return max(0, (current - candidate).days)


def event_actor(event: dict[str, Any]) -> str:
    return normalize_spaces(
        str(event.get("author") or event.get("developer_id") or event.get("author_email") or "Unknown contributor")
    ) or "Unknown contributor"


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def human_list(values: list[str]) -> str:
    cleaned = [normalize_spaces(str(value)) for value in values if normalize_spaces(str(value))]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def first_present(*values: Any) -> Optional[Any]:
    for value in values:
        if value_present(value):
            return value
    return None


def normalize_spaces(text: str) -> str:
    return " ".join(str(text or "").split())

def value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


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


def percent(part: float, whole: float) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100, 1)


def to_number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
