from __future__ import annotations

from typing import Any, Optional

from delivery_timeline_connector_fields import latest_connector_value
from delivery_timeline_mock_data import build_mock_stage_records
from delivery_timeline_normalization import (
    dedupe_preserve_order,
    earliest_timestamp,
    extract_number,
    first_present,
    has_merge_signal,
    infer_environment_from_branch,
    infer_environment_from_url_hint,
    infer_target_from_url,
    iso_utc_now,
    latest_timestamp,
    latest_value,
    normalize_duration_minutes,
    normalize_environment,
    normalize_people_list,
    normalize_stage_status,
    normalize_text,
    normalize_url,
    safe_int,
    timeline_sort_key,
    value_present,
)

PRIMARY_PROVENANCE_ORDER = ("connector", "inferred", "mixed", "mock")
PROVENANCE_RULES = {
    "connector": {
        "label": "Connector-backed",
        "description": "All delivery stages are connector-backed.",
        "trust": "high",
    },
    "inferred": {
        "label": "Inferred-only",
        "description": "No connector stages are present; delivery stages are inferred from linked activity.",
        "trust": "derived",
    },
    "mixed": {
        "label": "Mixed provenance",
        "description": "More than one provenance type is present across PR, CI, and deployment stages.",
        "trust": "blended",
    },
    "mock": {
        "label": "Mock-backed",
        "description": "All delivery stages are placeholders because no delivery signal exists.",
        "trust": "placeholder",
    },
    "unknown": {
        "label": "Unknown provenance",
        "description": "Delivery provenance could not be classified.",
        "trust": "unknown",
    },
}
COMPLETENESS_RULES = {
    "complete": {
        "label": "Complete",
        "description": "Stage metadata is mostly complete and operationally usable.",
    },
    "partial": {
        "label": "Partial",
        "description": "Stage metadata is present but missing some operational detail.",
    },
    "minimal": {
        "label": "Minimal",
        "description": "Stage metadata is thin and should be treated as incomplete context.",
    },
    "missing": {
        "label": "Missing",
        "description": "Stage metadata is effectively absent beyond a placeholder state.",
    },
}
READINESS_RULES = {
    "code-linked-only": {
        "label": "Code-linked only",
        "description": "The requirement is linked to code, but no review, pipeline, or deployment evidence is visible yet.",
    },
    "review-visible": {
        "label": "Review-visible",
        "description": "Review activity is visible, but pipeline and deployment evidence are still missing.",
    },
    "pipeline-visible": {
        "label": "Pipeline-visible",
        "description": "Review and CI evidence are visible, but deployment evidence is still missing.",
    },
    "deployment-visible": {
        "label": "Deployment-visible",
        "description": "Deployment evidence is visible, but the full delivery chain is not yet fully traceable.",
    },
    "fully-traceable": {
        "label": "Fully traceable",
        "description": "Review, CI, and deployment evidence are all visible for this requirement.",
    },
}


def build_delivery_timeline_response(
    issues: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    event_map = {
        str(event.get("commit_id") or "").strip(): event
        for event in events
        if str(event.get("commit_id") or "").strip()
    }

    records = [build_delivery_record(issue, event_map) for issue in issues]
    records.sort(
        key=lambda item: (
            sort_status_rank(item.get("delivery_stage")),
            timeline_sort_key(item.get("latest_activity_at")),
        ),
        reverse=True,
    )

    all_stage_sources = [
        stage.get("source")
        for record in records
        for stage in (record.get("pull_request"), record.get("ci"), record.get("deployment"))
        if isinstance(stage, dict)
    ]
    requirement_rollups = build_requirement_provenance_rollups(records)
    quality_rollups = build_timeline_quality_rollups(records)

    summary = {
        "requirements_total": len(records),
        "requirements_with_commits": len([item for item in records if item.get("commit_count")]),
        "requirements_with_prs": len([item for item in records if item.get("pull_request", {}).get("status") not in {"not started", "blocked", "unknown"}]),
        "ci_passing": len([item for item in records if item.get("ci", {}).get("status") in {"passed"}]),
        "deployments_live": len([item for item in records if item.get("deployment", {}).get("status") in {"success", "live"}]),
        "connector_stage_count": len([source for source in all_stage_sources if source == "connector"]),
        "inferred_stage_count": len([source for source in all_stage_sources if source == "inferred"]),
        "mocked_stage_count": len([source for source in all_stage_sources if source == "mock"]),
        **requirement_rollups,
        **quality_rollups,
        "traceability_strength_counts": quality_rollups.get("traceability_strength_counts", {}),
        "delivery_evidence_strength_counts": quality_rollups.get("delivery_evidence_strength_counts", {}),
        "downstream_coverage_pct": quality_rollups.get("downstream_evidence_coverage_pct"),
    }

    return {
        "generated_at": iso_utc_now(),
        "summary": summary,
        "meta": {
            "real_data": "Requirements and commits are live. Delivery stages prefer connector fields when present.",
            "mocked_data": "Inference is used before placeholders; fully mocked stages remain only where delivery signals are absent.",
            "provenance_rules": {key: dict(value) for key, value in PROVENANCE_RULES.items() if key != "unknown"},
            "completeness_rules": {key: dict(value) for key, value in COMPLETENESS_RULES.items()},
            "readiness_rules": {key: dict(value) for key, value in READINESS_RULES.items()},
        },
        "records": records,
    }


def build_delivery_record(
    issue: dict[str, Any],
    event_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    commit_ids = [str(commit_id) for commit_id in (issue.get("commits") or []) if str(commit_id or "").strip()]
    linked_events = [event_map.get(commit_id) for commit_id in commit_ids if event_map.get(commit_id)]
    linked_events.sort(key=lambda item: timeline_sort_key(item.get("timestamp")))

    commits = [build_commit_entry(event_map.get(commit_id), commit_id) for commit_id in commit_ids]
    latest_commit = linked_events[-1] if linked_events else None
    fallback_stages = build_mock_stage_records(issue, commits, latest_commit)

    pr_connector = extract_pull_request_record(linked_events)
    ci_connector = extract_ci_record(linked_events)
    deployment_connector = extract_deployment_record(linked_events)

    pr_inferred = infer_pull_request_record(issue, commits, linked_events, ci_connector, deployment_connector)
    ci_inferred = infer_ci_record(issue, commits, linked_events, pr_connector or pr_inferred, deployment_connector)
    deployment_inferred = infer_deployment_record(
        issue,
        commits,
        linked_events,
        pr_connector or pr_inferred,
        ci_connector or ci_inferred,
    )

    pull_request = merge_stage_record(pr_connector, pr_inferred, fallback_stages["pull_request"])
    ci = merge_stage_record(ci_connector, ci_inferred, fallback_stages["ci"])
    deployment = merge_stage_record(deployment_connector, deployment_inferred, fallback_stages["deployment"])

    pull_request = enrich_stage_record("pull_request", pull_request)
    ci = enrich_stage_record("ci", ci)
    deployment = enrich_stage_record("deployment", deployment)

    mocked_stages = [
        stage_name
        for stage_name, stage in (
            ("pull_request", pull_request),
            ("ci", ci),
            ("deployment", deployment),
        )
        if stage.get("source") == "mock"
    ]

    source_breakdown = count_stage_sources(pull_request, ci, deployment)
    provenance_rollup = classify_requirement_provenance(source_breakdown)
    latest_activity_at = first_present(
        deployment.get("deployed_at"),
        deployment.get("updated_at"),
        ci.get("completed_at"),
        ci.get("started_at"),
        pull_request.get("merged_at"),
        pull_request.get("updated_at"),
        get_latest_commit_timestamp(commits),
        issue.get("jira_updated_at"),
        issue.get("updated_at"),
    )

    readiness = build_requirement_readiness_descriptor(len(commits), pull_request, ci, deployment)
    return {
        "issue_id": issue.get("issue_id"),
        "title": issue.get("title"),
        "status": issue.get("status") or "Unknown",
        "priority": issue.get("priority") or "Unspecified",
        "project_key": issue.get("project_key") or "N/A",
        "delivery_stage": infer_delivery_stage(commits, pull_request, ci, deployment),
        "latest_activity_at": latest_activity_at,
        "mocked_stages": mocked_stages,
        "source_breakdown": source_breakdown,
        "provenance_rollup": provenance_rollup,
        "provenance": build_requirement_provenance_descriptor(provenance_rollup, source_breakdown),
        "readiness": readiness,
        "quality": build_requirement_quality_descriptor(
            pull_request,
            ci,
            deployment,
            latest_activity_at,
            len(commits),
            source_breakdown,
            readiness,
        ),
        "requirement": {
            "status": issue.get("status") or "Unknown",
            "owner": first_present(issue.get("assignee_email"), issue.get("reporter_email"), "Unassigned"),
            "source": issue.get("source") or "jira",
            "created_at": first_present(issue.get("jira_created_at"), issue.get("created_at")),
            "updated_at": first_present(issue.get("jira_updated_at"), issue.get("updated_at")),
        },
        "commit_count": len(commits),
        "commits": commits,
        "pull_request": pull_request,
        "ci": ci,
        "deployment": deployment,
    }


def build_commit_entry(event: Optional[dict[str, Any]], commit_id: str) -> dict[str, Any]:
    if not event:
        return {
            "commit_id": commit_id,
            "message": "Commit not found in current event feed",
            "author": "Unknown contributor",
            "timestamp": None,
            "repository_name": "Unknown repository",
            "branch": None,
            "source": "telemetry",
            "files_changed": 0,
        }

    files = extract_event_files(event)

    return {
        "commit_id": commit_id,
        "message": event.get("message") or "Commit without message",
        "author": event.get("author") or event.get("developer_id") or event.get("author_email") or "Unknown contributor",
        "timestamp": event.get("timestamp"),
        "repository_name": event.get("repository_name") or "Unknown repository",
        "branch": event.get("branch"),
        "source": "telemetry",
        "files_changed": safe_int(event.get("files_changed_count")) if value_present(event.get("files_changed_count")) else len(files),
        "total_changes": safe_int(event.get("total_changes")),
    }


def extract_event_files(event: dict[str, Any]) -> list[dict[str, Any]]:
    direct_files = event.get("files")
    if isinstance(direct_files, list):
        return [item for item in direct_files if isinstance(item, dict)]

    files_json = event.get("files_json")
    if isinstance(files_json, dict):
        nested_files = files_json.get("files")
        if isinstance(nested_files, list):
            return [item for item in nested_files if isinstance(item, dict)]

    if isinstance(files_json, list):
        return [item for item in files_json if isinstance(item, dict)]

    return []


def extract_pull_request_record(events: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    number_value, number_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "pull_request_number",
            "pr_number",
            "pull_request_id",
            "pr_id",
            "pull_number",
            "pull_request_iid",
            "merge_request_iid",
            "mr_iid",
            "number",
        ),
        nested_paths=(
            ("pull_request", "number"),
            ("pull_request", "id"),
            ("pull_request", "iid"),
            ("pull_request", "node_id"),
            ("pr", "number"),
            ("merge_request", "iid"),
            ("merge_request", "number"),
        ),
    )
    title_value, title_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "pr_title",
            "pull_request_title",
            "pull_request_name",
            "pull_request_subject",
            "pull_request_headline",
            "merge_request_title",
            "mr_title",
            "pr_subject",
            "title",
        ),
        nested_paths=(
            ("pull_request", "title"),
            ("pull_request", "name"),
            ("pull_request", "subject"),
            ("pr", "title"),
            ("merge_request", "title"),
        ),
    )
    status_value, status_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "pr_status",
            "pr_state",
            "pull_request_status",
            "pull_request_state",
            "pull_request_conclusion",
            "pull_request_result",
            "pull_request_merged",
            "pr_merged",
            "merge_request_state",
            "merge_request_status",
            "mr_state",
            "mr_status",
            "merge_state",
            "state",
        ),
        nested_paths=(
            ("pull_request", "state"),
            ("pull_request", "status"),
            ("pull_request", "merged"),
            ("pull_request", "merge_status"),
            ("pr", "state"),
            ("pr", "status"),
            ("merge_request", "state"),
            ("merge_request", "status"),
        ),
    )
    merged_at, merged_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "pr_merged_at",
            "pull_request_merged_at",
            "merged_timestamp",
            "merge_completed_at",
            "merged_at",
            "merge_commit_timestamp",
            "merge_request_merged_at",
            "mr_merged_at",
        ),
        nested_paths=(
            ("pull_request", "merged_at"),
            ("pull_request", "merge_completed_at"),
            ("pr", "merged_at"),
            ("merge_request", "merged_at"),
        ),
    )
    merged_flag_value, merged_flag_key, _ = latest_connector_value(
        events,
        flat_keys=("pull_request_merged", "pr_merged", "merge_request_merged", "mr_merged", "is_merged"),
        nested_paths=(
            ("pull_request", "merged"),
            ("pull_request", "is_merged"),
            ("pr", "merged"),
            ("merge_request", "merged"),
        ),
    )
    branch_value, branch_key, _ = latest_connector_value(
        events,
        flat_keys=("pr_branch", "pull_request_branch", "head_branch", "head_ref", "source_branch", "source_ref", "branch_name"),
        nested_paths=(
            ("pull_request", "head", "ref"),
            ("pull_request", "head_ref"),
            ("pull_request", "source_branch"),
            ("pull_request", "source", "branch"),
            ("pr", "branch"),
            ("merge_request", "source_branch"),
        ),
    )
    created_at, created_key, _ = latest_connector_value(
        events,
        flat_keys=("pr_created_at", "pull_request_created_at", "pull_request_opened_at", "created_at"),
        nested_paths=(("pull_request", "created_at"), ("pull_request", "opened_at"), ("pr", "created_at"), ("merge_request", "created_at")),
    )
    updated_at, updated_key, _ = latest_connector_value(
        events,
        flat_keys=("pr_updated_at", "pull_request_updated_at", "pull_request_closed_at", "updated_at", "closed_at"),
        nested_paths=(("pull_request", "updated_at"), ("pull_request", "closed_at"), ("pr", "updated_at"), ("merge_request", "updated_at")),
    )
    author_value, author_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "pr_author",
            "pull_request_author",
            "pr_author_name",
            "pull_request_author_name",
            "pr_author_login",
            "pull_request_user",
            "pull_request_user_login",
            "opened_by",
            "opened_by_login",
            "creator",
            "creator_name",
            "user_name",
            "user_login",
        ),
        nested_paths=(
            ("pull_request", "author"),
            ("pull_request", "author", "login"),
            ("pull_request", "author", "name"),
            ("pull_request", "user", "login"),
            ("pull_request", "user", "name"),
            ("pr", "author"),
            ("pr", "author", "login"),
            ("merge_request", "author", "name"),
            ("merge_request", "author", "username"),
        ),
    )
    url_value, url_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "pr_url",
            "pr_link",
            "pull_request_url",
            "pull_request_html_url",
            "pull_request_web_url",
            "pr_html_url",
            "pr_web_url",
            "pull_request_html_link",
            "pull_request_link",
            "web_url",
            "html_url",
            "url",
        ),
        nested_paths=(
            ("pull_request", "url"),
            ("pull_request", "html_url"),
            ("pull_request", "web_url"),
            ("pull_request", "links", "html", "href"),
            ("pr", "url"),
            ("merge_request", "web_url"),
            ("merge_request", "url"),
        ),
    )
    reviewer_values = normalize_people_list(
        latest_connector_value(
            events,
            flat_keys=("pr_reviewers", "pull_request_reviewers", "requested_reviewers", "reviewers", "requested_reviewer_logins", "approved_by", "approvers", "approver", "reviewer", "reviewed_by", "approval_reviewers"),
            nested_paths=(
                ("pull_request", "reviewers"),
                ("pull_request", "requested_reviewers"),
                ("pull_request", "approved_by"),
                ("pr", "reviewers"),
                ("merge_request", "reviewers"),
                ("merge_request", "approved_by"),
            ),
        )[0],
    )
    repository_name_value, _, _ = latest_connector_value(
        events,
        flat_keys=("repository_name",),
        nested_paths=(
            ("repository", "name"),
            ("pull_request", "base", "repo", "name"),
            ("pull_request", "repository", "name"),
            ("merge_request", "references", "full"),
        ),
    )

    number = extract_number(number_value)
    title = normalize_text(title_value)
    author = first_present(*(normalize_people_list(author_value)), normalize_text(author_value))
    merged_flag = bool_signal(merged_flag_value)
    if merged_flag and not merged_at:
        merged_at = latest_timestamp(events)
    has_approval_signal = bool(normalize_people_list(latest_value(events, "approved_by")[0], latest_value(events, "approver")[0]))
    status = normalize_stage_status(
        "pull_request",
        first_present(
            status_value,
            "merged" if merged_at or merged_flag else None,
            "approved" if has_approval_signal else None,
            "open" if number or title or reviewer_values or url_value else None,
        ),
    )
    if status == "closed" and merged_at:
        status = "merged"
    url = normalize_url(url_value)

    if not any([number, title, url, merged_at, reviewer_values, status not in {"unknown"}]):
        return None

    evidence = []
    if number_key:
        evidence.append(f"PR number from {number_key}")
    if title_key:
        evidence.append(f"title from {title_key}")
    if status_key or merged_key:
        evidence.append("state from connector event fields")
    if merged_flag_key:
        evidence.append(f"merge signal from {merged_flag_key}")
    if branch_key:
        evidence.append(f"branch from {branch_key}")
    if reviewer_values:
        evidence.append("reviewer metadata present")
    if author_key:
        evidence.append(f"author from {author_key}")
    if url_key:
        evidence.append("linked PR URL available")

    return build_stage_record(
        source="connector",
        status=status,
        summary=f"PR #{number}" if number else "Pull request",
        note="Connector-backed pull request metadata.",
        provenance_detail="explicit connector" if status_key or merged_key or merged_flag_key else "partial connector",
        evidence=evidence,
        number=number,
        title=title,
        state=status,
        author=author,
        branch=normalize_text(branch_value),
        created_at=first_present(created_at, earliest_timestamp(events)),
        updated_at=first_present(updated_at, latest_timestamp(events)),
        merged_at=merged_at,
        url=url,
        reviewers=reviewer_values,
        repository_name=normalize_text(repository_name_value),
    )


def extract_ci_record(events: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    status_value, status_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "ci_status",
            "ci_conclusion",
            "check_status",
            "check_suite_status",
            "check_conclusion",
            "workflow_status",
            "workflow_conclusion",
            "run_status",
            "run_conclusion",
            "build_status",
            "action_status",
            "pipeline_status",
            "pipeline_state",
            "pipeline_result",
            "check_run_status",
            "check_run_conclusion",
            "job_status",
            "job_conclusion",
            "build_result",
            "status",
            "conclusion",
        ),
        nested_paths=(
            ("ci", "status"),
            ("ci", "conclusion"),
            ("workflow_run", "status"),
            ("workflow_run", "conclusion"),
            ("pipeline", "status"),
            ("pipeline", "state"),
            ("check_run", "status"),
            ("check_run", "conclusion"),
            ("build", "status"),
            ("build", "result"),
        ),
    )
    workflow_value, workflow_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "ci_workflow",
            "workflow_name",
            "workflow_display_name",
            "workflow",
            "action_name",
            "check_name",
            "pipeline_name",
            "pipeline_display_name",
            "pipeline",
            "job_name",
            "job_display_name",
            "workflow_title",
        ),
        nested_paths=(
            ("ci", "workflow"),
            ("ci", "name"),
            ("workflow_run", "name"),
            ("workflow_run", "display_title"),
            ("pipeline", "name"),
            ("pipeline", "display_name"),
            ("build", "name"),
            ("job", "name"),
        ),
    )
    run_id_value, run_id_key, _ = latest_connector_value(
        events,
        flat_keys=("ci_run_id", "workflow_run_id", "run_id", "build_id", "job_id", "check_run_id", "pipeline_id", "run_number", "workflow_run_number"),
        nested_paths=(
            ("ci", "run_id"),
            ("workflow_run", "id"),
            ("workflow_run", "run_number"),
            ("pipeline", "id"),
            ("build", "id"),
            ("job", "id"),
            ("check_run", "id"),
        ),
    )
    started_at, started_key, _ = latest_connector_value(
        events,
        flat_keys=("ci_started_at", "run_started_at", "workflow_started_at", "check_started_at", "check_run_started_at", "pipeline_started_at", "started_at"),
        nested_paths=(
            ("ci", "started_at"),
            ("workflow_run", "run_started_at"),
            ("workflow_run", "started_at"),
            ("pipeline", "started_at"),
            ("check_run", "started_at"),
            ("build", "started_at"),
        ),
    )
    completed_at, completed_key, _ = latest_connector_value(
        events,
        flat_keys=("ci_completed_at", "run_completed_at", "workflow_completed_at", "check_completed_at", "check_run_completed_at", "pipeline_completed_at", "finished_at", "ended_at", "completed_at"),
        nested_paths=(
            ("ci", "completed_at"),
            ("workflow_run", "updated_at"),
            ("workflow_run", "completed_at"),
            ("pipeline", "finished_at"),
            ("pipeline", "completed_at"),
            ("check_run", "completed_at"),
            ("build", "completed_at"),
        ),
    )
    duration_minutes_value, duration_minutes_key, _ = latest_connector_value(
        events,
        flat_keys=("ci_duration_minutes", "duration_minutes"),
        nested_paths=(("ci", "duration_minutes"), ("workflow_run", "duration_minutes"), ("pipeline", "duration_minutes"), ("build", "duration_minutes")),
    )
    duration_seconds_value, duration_seconds_key, _ = latest_connector_value(
        events,
        flat_keys=("ci_duration_seconds", "duration_seconds", "run_duration_seconds", "pipeline_duration_seconds", "job_duration_seconds"),
        nested_paths=(("ci", "duration_seconds"), ("workflow_run", "duration_seconds"), ("pipeline", "duration_seconds"), ("build", "duration_seconds")),
    )
    duration_ms_value, duration_ms_key, _ = latest_connector_value(
        events,
        flat_keys=("ci_duration_ms", "duration_ms", "run_duration_ms", "pipeline_duration_ms"),
        nested_paths=(("ci", "duration_ms"), ("workflow_run", "run_duration_ms"), ("pipeline", "duration_ms"), ("build", "duration_ms")),
    )
    url_value, url_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "ci_url",
            "workflow_url",
            "workflow_run_url",
            "workflow_html_url",
            "run_url",
            "run_html_url",
            "build_url",
            "pipeline_url",
            "pipeline_link",
            "checks_url",
            "check_url",
            "job_url",
            "details_url",
            "target_url",
            "html_url",
        ),
        nested_paths=(
            ("ci", "url"),
            ("workflow_run", "html_url"),
            ("workflow_run", "url"),
            ("pipeline", "web_url"),
            ("pipeline", "url"),
            ("build", "url"),
            ("check_run", "html_url"),
            ("check_run", "details_url"),
        ),
    )

    status = normalize_stage_status("ci", status_value)
    workflow = normalize_text(workflow_value)
    run_id = normalize_text(run_id_value)
    duration_minutes = normalize_duration_minutes(duration_minutes_value, duration_seconds_value, duration_ms_value)
    url = normalize_url(url_value)

    if status == "unknown":
        if completed_at:
            status = "passed"
        elif started_at:
            status = "running"
        elif workflow or run_id or url:
            status = "queued"

    if not any([status not in {"unknown"}, workflow, run_id, url, completed_at, started_at]):
        return None

    evidence = []
    if status_key:
        evidence.append(f"status from {status_key}")
    if workflow_key:
        evidence.append(f"workflow from {workflow_key}")
    if run_id_key:
        evidence.append(f"run identifier from {run_id_key}")
    if started_key or completed_key:
        evidence.append("timing from connector run fields")
    if url_key:
        evidence.append("linked CI URL available")

    if duration_minutes_key or duration_seconds_key or duration_ms_key:
        evidence.append("duration normalized from connector timing")

    return build_stage_record(
        source="connector",
        status=status,
        summary=workflow or "CI pipeline",
        note="Connector-backed CI metadata.",
        provenance_detail="explicit connector" if status_key else "partial connector",
        evidence=evidence,
        workflow=workflow,
        run_id=run_id,
        started_at=first_present(started_at, earliest_timestamp(events)),
        completed_at=completed_at,
        duration_minutes=duration_minutes,
        url=url,
    )


def extract_deployment_record(events: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    status_value, status_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "deployment_status",
            "deploy_status",
            "deployment_state",
            "deployment_conclusion",
            "release_status",
            "release_state",
            "release_result",
            "deployment_result",
            "deploy_result",
            "vercel_status",
            "vercel_state",
            "status",
        ),
        nested_paths=(
            ("deployment", "status"),
            ("deployment", "state"),
            ("release", "status"),
            ("release", "state"),
            ("deployment", "ready_state"),
            ("deployment", "conclusion"),
        ),
    )
    environment_value, environment_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "deployment_environment",
            "environment",
            "deployment_env",
            "deploy_environment",
            "release_environment",
            "release_env",
            "target_environment",
            "environment_name",
            "vercel_environment",
            "deploy_environment_name",
        ),
        nested_paths=(
            ("deployment", "environment"),
            ("deployment", "environment_name"),
            ("release", "environment"),
            ("deployment", "target", "environment"),
        ),
    )
    deployed_at, deployed_key, _ = latest_connector_value(
        events,
        flat_keys=("deployed_at", "deployment_completed_at", "deployment_finished_at", "released_at", "release_created_at", "published_at", "completed_at"),
        nested_paths=(
            ("deployment", "deployed_at"),
            ("deployment", "completed_at"),
            ("deployment", "ready_at"),
            ("release", "published_at"),
            ("release", "created_at"),
        ),
    )
    target_value, target_key, _ = latest_connector_value(
        events,
        flat_keys=("deployment_target", "deploy_target", "deployment_provider", "hosting_provider", "platform", "provider", "service", "project_name", "app_name"),
        nested_paths=(
            ("deployment", "target"),
            ("deployment", "platform"),
            ("deployment", "provider"),
            ("release", "target"),
            ("release", "platform"),
            ("deployment", "target", "name"),
        ),
    )
    version_value, version_key, _ = latest_connector_value(
        events,
        flat_keys=("deployment_version", "release_version", "release_tag", "version", "release_name", "release_id", "tag_name", "version_name"),
        nested_paths=(
            ("deployment", "version"),
            ("deployment", "release"),
            ("release", "version"),
            ("release", "tag_name"),
            ("release", "name"),
        ),
    )
    url_value, url_key, _ = latest_connector_value(
        events,
        flat_keys=(
            "deployment_url",
            "deployment_web_url",
            "deployment_link",
            "deploy_link",
            "deploy_url",
            "release_url",
            "service_url",
            "site_url",
            "live_url",
            "preview_url",
            "environment_url",
            "production_url",
            "public_url",
            "vercel_url",
            "url",
        ),
        nested_paths=(
            ("deployment", "url"),
            ("deployment", "web_url"),
            ("deployment", "public_url"),
            ("deployment", "environment_url"),
            ("release", "url"),
            ("release", "html_url"),
        ),
    )

    status = normalize_stage_status("deployment", first_present(status_value, "success" if deployed_at else None))
    url = normalize_url(url_value)
    environment = normalize_environment(environment_value) or infer_environment_from_url_hint(url_key, url)
    target = normalize_text(target_value) or infer_target_from_url(url)
    version = normalize_text(version_value)

    if status == "unknown":
        if deployed_at:
            status = "live" if environment == "production" else "success"
        elif environment or target or version or url:
            status = "pending"

    if not any([status not in {"unknown"}, environment, target, version, deployed_at, url]):
        return None

    evidence = []
    if status_key or deployed_key:
        evidence.append("deployment state from connector fields")
    if environment_key:
        evidence.append(f"environment from {environment_key}")
    elif environment:
        evidence.append("environment inferred from deployment URL")
    if target_key:
        evidence.append(f"target from {target_key}")
    elif target:
        evidence.append("target inferred from deployment URL")
    if version_key:
        evidence.append(f"version from {version_key}")
    if url_key:
        evidence.append("linked deployment URL available")

    return build_stage_record(
        source="connector",
        status=status,
        summary=f"{(environment or 'deployment').title()} deployment",
        note="Connector-backed deployment metadata.",
        provenance_detail="explicit connector" if status_key or deployed_key else "partial connector",
        evidence=evidence,
        environment=environment,
        target=target,
        version=version,
        deployed_at=deployed_at,
        updated_at=first_present(deployed_at, latest_timestamp(events)),
        url=url,
    )


def infer_pull_request_record(
    issue: dict[str, Any],
    commits: list[dict[str, Any]],
    events: list[dict[str, Any]],
    ci_record: Optional[dict[str, Any]],
    deployment_record: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    if not commits:
        return None

    latest_commit = commits[-1]
    branch = first_present(latest_commit.get("branch"), latest_branch(events))
    first_commit_at = first_commit_timestamp(commits)
    last_commit_at = get_latest_commit_timestamp(commits)
    deployment_status = normalize_stage_status("deployment", (deployment_record or {}).get("status"))
    ci_status = normalize_stage_status("ci", (ci_record or {}).get("status"))

    merged_at = None
    if deployment_status in {"success", "live", "in progress", "pending"}:
        status = "merged"
        merged_at = first_present((deployment_record or {}).get("deployed_at"), (deployment_record or {}).get("updated_at"), last_commit_at)
    elif has_merge_signal(events):
        status = "merged"
        merged_at = last_commit_at
    elif ci_status == "passed":
        status = "approved"
    elif ci_status in {"running", "queued"}:
        status = "open"
    else:
        status = "open"

    evidence = [
        f"{len(commits)} linked commits",
        branch and f"branch {branch}",
        deployment_status in {"success", "live", "in progress", "pending"} and "downstream deployment signal",
        ci_status == "passed" and "CI signal suggests review completed",
        has_merge_signal(events) and "merge commit observed",
    ]

    return build_stage_record(
        source="inferred",
        status=status,
        summary="Inferred pull request",
        note="Inferred from linked branch and downstream delivery signals.",
        provenance_detail="inferred from linked activity",
        evidence=[item for item in evidence if item],
        number=None,
        title=f"{issue.get('issue_id')}: {issue.get('title')}" if issue.get("issue_id") and issue.get("title") else issue.get("title"),
        state=status,
        author=latest_commit.get("author"),
        branch=branch,
        created_at=first_commit_at,
        updated_at=last_commit_at,
        merged_at=merged_at,
        url=None,
        repository_name=latest_commit.get("repository_name"),
    )


def infer_ci_record(
    issue: dict[str, Any],
    commits: list[dict[str, Any]],
    events: list[dict[str, Any]],
    pull_request_record: Optional[dict[str, Any]],
    deployment_record: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    if not commits:
        return None

    pr_status = normalize_stage_status("pull_request", (pull_request_record or {}).get("status"))
    deployment_status = normalize_stage_status("deployment", (deployment_record or {}).get("status"))
    started_at = first_commit_timestamp(commits)
    latest_commit_at = get_latest_commit_timestamp(commits)

    if deployment_status in {"success", "live", "in progress", "pending"}:
        status = "passed"
        completed_at = first_present((deployment_record or {}).get("deployed_at"), (deployment_record or {}).get("updated_at"), latest_commit_at)
    elif pr_status == "merged":
        status = "passed"
        completed_at = first_present((pull_request_record or {}).get("merged_at"), latest_commit_at)
    elif pr_status in {"approved", "open", "draft"}:
        status = "running"
        completed_at = None
    else:
        status = "queued"
        completed_at = None

    duration_minutes = None
    if started_at and completed_at:
        duration_minutes = max(1, round((timeline_sort_key(completed_at) - timeline_sort_key(started_at)) / 60))

    evidence = [
        f"{len(commits)} linked commits",
        pr_status in {"merged", "approved", "open", "draft"} and f"PR state {pr_status}",
        deployment_status in {"success", "live", "in progress", "pending"} and "deployment implies completed validation",
    ]

    return build_stage_record(
        source="inferred",
        status=status,
        summary="Inferred CI",
        note="Inferred from commit flow and upstream review progression.",
        provenance_detail="inferred from linked activity",
        evidence=[item for item in evidence if item],
        workflow="inferred-validation",
        run_id=None,
        started_at=started_at,
        completed_at=completed_at,
        duration_minutes=duration_minutes,
        url=None,
    )


def infer_deployment_record(
    issue: dict[str, Any],
    commits: list[dict[str, Any]],
    events: list[dict[str, Any]],
    pull_request_record: Optional[dict[str, Any]],
    ci_record: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    if not commits:
        return None

    pr_status = normalize_stage_status("pull_request", (pull_request_record or {}).get("status"))
    ci_status = normalize_stage_status("ci", (ci_record or {}).get("status"))
    latest_commit = commits[-1]
    branch = first_present(latest_commit.get("branch"), latest_branch(events))
    environment = infer_environment_from_branch(branch, pr_status=pr_status, ci_status=ci_status)

    if ci_status == "passed":
        status = "pending"
    elif ci_status in {"running", "queued"}:
        status = "blocked"
    elif pr_status == "merged":
        status = "pending"
    elif pr_status in {"approved", "open", "draft"}:
        status = "blocked"
    else:
        status = "blocked"

    evidence = [
        ci_status and f"CI state {ci_status}",
        pr_status and f"PR state {pr_status}",
        branch and f"branch {branch}",
    ]

    return build_stage_record(
        source="inferred",
        status=status,
        summary=f"{environment.title()} deployment",
        note="Inferred from CI outcome, PR state, and branch context.",
        provenance_detail="inferred from linked activity",
        evidence=[item for item in evidence if item],
        environment=environment,
        target=None,
        version=None,
        deployed_at=None,
        updated_at=get_latest_commit_timestamp(commits),
        url=None,
    )


def latest_branch(events: list[dict[str, Any]]) -> Optional[str]:
    value, _, _ = latest_value(events, "branch", "head_branch", "head_ref")
    return normalize_text(value)


def first_commit_timestamp(commits: list[dict[str, Any]]) -> Optional[str]:
    timestamps = [commit.get("timestamp") for commit in commits if value_present(commit.get("timestamp"))]
    if not timestamps:
        return None
    return min(timestamps, key=timeline_sort_key)


def merge_stage_record(
    connector_record: Optional[dict[str, Any]],
    inferred_record: Optional[dict[str, Any]],
    mock_record: Optional[dict[str, Any]],
) -> dict[str, Any]:
    if connector_record:
        base = dict(inferred_record or {})
        base.update({key: value for key, value in connector_record.items() if key in {"source", "note", "evidence", "summary", "status"} or value_present(value)})
        selected = connector_record
    elif inferred_record:
        base = dict(inferred_record)
        selected = inferred_record
    else:
        base = dict(mock_record or {})
        selected = mock_record or {}

    base["source"] = selected.get("source", "mock")
    base["is_mock"] = base["source"] == "mock"
    base["provenance_detail"] = selected.get("provenance_detail")
    base["evidence"] = dedupe_preserve_order(
        list((connector_record or {}).get("evidence") or [])
        + list((inferred_record or {}).get("evidence") or [])
        + list((mock_record or {}).get("evidence") or [])
    )
    base["status"] = normalize_selected_status(base)
    return base


def enrich_stage_record(stage_name: str, stage: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(stage or {})
    completeness = assess_stage_completeness(stage_name, enriched)
    enriched["completeness_pct"] = completeness["pct"]
    enriched["completeness_label"] = completeness["label"]
    enriched["missing_fields"] = completeness["missing_fields"]
    enriched["quality"] = {
        "completeness_pct": completeness["pct"],
        "completeness_label": completeness["label"],
        "completeness_title": COMPLETENESS_RULES[completeness["label"]]["label"],
        "missing_fields": completeness["missing_fields"],
        "present_fields": completeness["present_fields"],
        "present_fields_count": completeness["present_count"],
        "total_fields": completeness["total_count"],
        "confidence": infer_stage_confidence(stage_name, enriched, completeness),
        "is_partial_connector": enriched.get("source") == "connector" and enriched.get("provenance_detail") == "partial connector",
        "is_mock_fallback": enriched.get("source") == "mock",
        "weak_evidence": enriched.get("source") == "inferred" and len(list(enriched.get("evidence") or [])) < 2,
        "is_missing": completeness["label"] == "missing",
    }
    enriched["provenance"] = build_stage_provenance_descriptor(stage_name, enriched, completeness)
    return enriched


def normalize_selected_status(stage: dict[str, Any]) -> str:
    if "environment" in stage or "deployed_at" in stage or "target" in stage:
        return normalize_stage_status("deployment", stage.get("status"))
    if "workflow" in stage or "run_id" in stage:
        return normalize_stage_status("ci", stage.get("status"))
    return normalize_stage_status("pull_request", stage.get("status"))


def build_stage_record(
    source: str,
    status: str,
    summary: str,
    note: str,
    evidence: list[str],
    **fields: Any,
) -> dict[str, Any]:
    return {
        "source": source,
        "status": status,
        "summary": summary,
        "note": note,
        "evidence": dedupe_preserve_order(evidence),
        **fields,
    }


def build_stage_provenance_descriptor(stage_name: str, stage: dict[str, Any], completeness: dict[str, Any]) -> dict[str, Any]:
    source = stage.get("source") or "unknown"
    confidence = infer_stage_confidence(stage_name, stage, completeness)
    detail = stage.get("provenance_detail") or ""
    if source == "connector":
        description = "Connector-backed stage metadata." if detail == "explicit connector" else "Partially connector-backed stage metadata with inferred field fill."
    elif source == "inferred":
        description = "Stage synthesized from linked activity and downstream evidence."
    elif source == "mock":
        description = "Fallback placeholder stage because no reliable delivery signal exists."
    else:
        description = "Stage provenance unavailable."

    return {
        "source": source,
        "label": PROVENANCE_RULES.get(source, PROVENANCE_RULES["unknown"])["label"],
        "description": description,
        "trust": confidence,
        "detail": detail,
        "completeness_pct": completeness["pct"],
        "completeness_label": completeness["label"],
        "completeness_title": COMPLETENESS_RULES[completeness["label"]]["label"],
        "missing_fields": completeness["missing_fields"],
        "present_fields": completeness["present_fields"],
        "is_partial_connector": source == "connector" and detail == "partial connector",
        "is_mock_fallback": source == "mock",
        "weak_evidence": source == "inferred" and len(list(stage.get("evidence") or [])) < 2,
    }


def assess_stage_completeness(stage_name: str, stage: dict[str, Any]) -> dict[str, Any]:
    checks = stage_field_checks(stage_name, stage)
    total = len(checks)
    present_fields = [label for label, is_present in checks if is_present]
    present = len(present_fields)
    pct = safe_pct(present, total)
    if present == 0 or present_fields == ["status"]:
        label = "missing"
    elif pct >= 85:
        label = "complete"
    elif pct >= 55:
        label = "partial"
    else:
        label = "minimal"
    return {
        "pct": pct,
        "label": label,
        "missing_fields": [label for label, is_present in checks if not is_present],
        "present_fields": present_fields,
        "present_count": present,
        "total_count": total,
    }


def stage_field_checks(stage_name: str, stage: dict[str, Any]) -> list[tuple[str, bool]]:
    if stage_name == "pull_request":
        checks = [
            ("number", value_present(stage.get("number"))),
            ("title", value_present(stage.get("title"))),
            ("status", value_present(stage.get("state")) or value_present(stage.get("status"))),
            ("author", value_present(stage.get("author"))),
            ("reviewers", bool(stage.get("reviewers"))),
            ("branch", value_present(stage.get("branch"))),
            ("url", value_present(stage.get("url"))),
            ("activity timestamp", any(value_present(stage.get(key)) for key in ("created_at", "updated_at", "merged_at"))),
        ]
        if normalize_stage_status("pull_request", stage.get("status")) == "merged":
            checks.append(("merged timestamp", value_present(stage.get("merged_at"))))
        return checks
    if stage_name == "ci":
        checks = [
            ("workflow", value_present(stage.get("workflow"))),
            ("run id", value_present(stage.get("run_id"))),
            ("status", value_present(stage.get("status"))),
            ("started timestamp", value_present(stage.get("started_at"))),
            ("url", value_present(stage.get("url"))),
        ]
        ci_status = normalize_stage_status("ci", stage.get("status"))
        if ci_status in {"passed", "failed", "cancelled", "skipped", "blocked"}:
            checks.append(("completed timestamp", value_present(stage.get("completed_at"))))
            checks.append(("duration", value_present(stage.get("duration_minutes"))))
        return checks
    return [
        ("environment", value_present(stage.get("environment"))),
        ("target", value_present(stage.get("target"))),
        ("status", value_present(stage.get("status"))),
        ("version", value_present(stage.get("version"))),
        ("url", value_present(stage.get("url"))),
        ("release timestamp", any(value_present(stage.get(key)) for key in ("deployed_at", "updated_at"))),
    ]


def infer_stage_confidence(stage_name: str, stage: dict[str, Any], completeness: dict[str, Any]) -> str:
    source = stage.get("source")
    pct = int(completeness.get("pct") or 0)
    evidence_count = len(list(stage.get("evidence") or []))
    if source == "connector":
        return "high" if pct >= 70 and stage.get("provenance_detail") == "explicit connector" else "medium"
    if source == "inferred":
        return "medium" if pct >= 55 and evidence_count >= 2 else "low"
    if source == "mock":
        return "low"
    return "unknown"


def bool_signal(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if not value_present(value):
        return False
    token = (normalize_text(value) or "").lower()
    if token in {"true", "1", "yes", "y", "merged", "success", "succeeded"}:
        return True
    if token in {"false", "0", "no", "n", "open", "pending"}:
        return False
    return False


def infer_delivery_stage(
    commits: list[dict[str, Any]],
    pull_request: dict[str, Any],
    ci: dict[str, Any],
    deployment: dict[str, Any],
) -> str:
    deployment_status = normalize_stage_status("deployment", deployment.get("status"))
    ci_status = normalize_stage_status("ci", ci.get("status"))
    pr_status = normalize_stage_status("pull_request", pull_request.get("status"))

    if deployment_status in {"success", "live"}:
        return "deployed"
    if deployment_status in {"in progress", "pending"}:
        return "deploying"
    if ci_status == "passed":
        return "ready to deploy"
    if ci_status in {"running", "queued"}:
        return "in ci"
    if pr_status in {"merged", "approved", "open", "draft"}:
        return "in review"
    if commits:
        return "coded"
    return "planned"


def sort_status_rank(value: Any) -> int:
    ranking = {
        "deployed": 6,
        "deploying": 5,
        "ready to deploy": 4,
        "in ci": 3,
        "in review": 2,
        "coded": 1,
        "planned": 0,
    }
    return ranking.get(str(value or "").lower(), 0)


def count_stage_sources(*stages: dict[str, Any]) -> dict[str, int]:
    return {
        "connector": len([stage for stage in stages if stage.get("source") == "connector"]),
        "inferred": len([stage for stage in stages if stage.get("source") == "inferred"]),
        "mock": len([stage for stage in stages if stage.get("source") == "mock"]),
    }


def build_requirement_provenance_rollups(records: list[dict[str, Any]]) -> dict[str, int]:
    provenance_counts = {key: 0 for key in PRIMARY_PROVENANCE_ORDER}
    mostly_inferred_requirements = 0
    requirements_with_mocked_stages = 0

    for record in records:
        source_breakdown = record.get("source_breakdown") or {}
        connector_count = int(source_breakdown.get("connector") or 0)
        inferred_count = int(source_breakdown.get("inferred") or 0)
        mock_count = int(source_breakdown.get("mock") or 0)
        provenance = classify_requirement_provenance(record)

        if provenance in provenance_counts:
            provenance_counts[provenance] += 1
        if inferred_count > 0 and inferred_count >= connector_count and inferred_count > mock_count:
            mostly_inferred_requirements += 1
        if mock_count > 0:
            requirements_with_mocked_stages += 1

    return {
        "connector_backed_requirements": provenance_counts["connector"],
        "inferred_only_requirements": provenance_counts["inferred"],
        "mostly_inferred_requirements": mostly_inferred_requirements,
        "requirements_with_mocked_stages": requirements_with_mocked_stages,
        "mocked_requirements": provenance_counts["mock"],
        "mixed_source_requirements": provenance_counts["mixed"],
    }


def classify_requirement_provenance(record_or_breakdown: dict[str, Any]) -> str:
    source_breakdown = record_or_breakdown.get("source_breakdown") if isinstance(record_or_breakdown, dict) and "source_breakdown" in record_or_breakdown else record_or_breakdown
    source_breakdown = source_breakdown or {}
    connector_count = int(source_breakdown.get("connector") or 0)
    inferred_count = int(source_breakdown.get("inferred") or 0)
    mock_count = int(source_breakdown.get("mock") or 0)
    active_source_types = len([count for count in (connector_count, inferred_count, mock_count) if count > 0])

    if connector_count > 0 and active_source_types == 1:
        return "connector"
    if active_source_types > 1:
        return "mixed"
    if connector_count == 0 and inferred_count > 0 and mock_count == 0:
        return "inferred"
    if connector_count == 0 and inferred_count == 0 and mock_count > 0:
        return "mock"
    return "unknown"


def build_requirement_provenance_descriptor(provenance_rollup: str, source_breakdown: dict[str, Any]) -> dict[str, Any]:
    rule = PROVENANCE_RULES.get(provenance_rollup, PROVENANCE_RULES["unknown"])
    counts = normalize_source_breakdown(source_breakdown)
    return {
        "rollup": provenance_rollup,
        "label": rule["label"],
        "description": rule["description"],
        "trust": rule["trust"],
        "counts": counts,
    }


def normalize_source_breakdown(source_breakdown: dict[str, Any]) -> dict[str, int]:
    return {
        "connector": int((source_breakdown or {}).get("connector") or 0),
        "inferred": int((source_breakdown or {}).get("inferred") or 0),
        "mock": int((source_breakdown or {}).get("mock") or 0),
    }


def build_requirement_quality_descriptor(
    pull_request: dict[str, Any],
    ci: dict[str, Any],
    deployment: dict[str, Any],
    latest_activity_at: Any,
    commit_count: int,
    source_breakdown: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    stages = [pull_request, ci, deployment]
    completeness_values = [int((stage.get("quality") or {}).get("completeness_pct") or stage.get("completeness_pct") or 0) for stage in stages]
    completeness_pct = round(sum(completeness_values) / len(completeness_values)) if completeness_values else 0
    if completeness_pct >= 85:
        completeness_label = "strong"
    elif completeness_pct >= 55:
        completeness_label = "partial"
    else:
        completeness_label = "thin"
    freshness = infer_freshness_hint(latest_activity_at)
    missing_downstream_evidence = (
        commit_count > 0
        and pull_request.get("source") != "mock"
        and ci.get("source") != "connector"
        and deployment.get("source") != "connector"
        and not any(value_present(ci.get(key)) for key in ("completed_at", "url"))
        and not any(value_present(deployment.get(key)) for key in ("deployed_at", "url"))
    )
    connector_stage_pct = safe_pct(int((source_breakdown or {}).get("connector") or 0), len(stages) or 1)
    connector_stage_count = int((source_breakdown or {}).get("connector") or 0)
    inferred_stage_count = int((source_breakdown or {}).get("inferred") or 0)
    mock_stage_count = int((source_breakdown or {}).get("mock") or 0)
    downstream_coverage_pct = safe_pct(
        len(
            [
                1
                for stage_name, stage in (("pull_request", pull_request), ("ci", ci), ("deployment", deployment))
                if stage_visibility_signal(stage_name, stage)
            ]
        ),
        len(stages) or 1,
    )
    non_mock_stages = [stage for stage in stages if stage.get("source") != "mock"]
    downstream_evidence_strength = "verified" if any(stage.get("source") == "connector" for stage in (ci, deployment)) else "derived"
    if not non_mock_stages or missing_downstream_evidence:
        downstream_evidence_strength = "missing"
    weakest_stage = identify_weakest_stage(pull_request, ci, deployment)
    traceability_strength = infer_traceability_strength(
        commit_count=commit_count,
        completeness_pct=completeness_pct,
        connector_stage_count=connector_stage_count,
        mock_stage_count=mock_stage_count,
        downstream_coverage_pct=downstream_coverage_pct,
        delivery_evidence_strength=downstream_evidence_strength,
    )
    delivery_evidence_strength = infer_delivery_evidence_strength(
        pull_request=pull_request,
        ci=ci,
        deployment=deployment,
        commit_count=commit_count,
        readiness_code=readiness.get("code"),
        missing_downstream_evidence=missing_downstream_evidence,
    )
    return {
        "completeness_pct": completeness_pct,
        "completeness_label": completeness_label,
        "freshness": freshness,
        "missing_downstream_evidence": missing_downstream_evidence,
        "connector_stage_pct": connector_stage_pct,
        "downstream_coverage_pct": downstream_coverage_pct,
        "connector_stage_count": connector_stage_count,
        "inferred_stage_count": inferred_stage_count,
        "mock_stage_count": mock_stage_count,
        "downstream_evidence_strength": delivery_evidence_strength,
        "delivery_evidence_strength": delivery_evidence_strength,
        "traceability_strength": traceability_strength,
        "weakest_stage": weakest_stage,
        "readiness_code": readiness.get("code"),
        "readiness_label": readiness.get("label"),
        "readiness_description": readiness.get("description"),
        "blocking_visibility_gap": readiness.get("blocking_gap"),
    }


def build_requirement_readiness_descriptor(
    commit_count: int,
    pull_request: dict[str, Any],
    ci: dict[str, Any],
    deployment: dict[str, Any],
) -> dict[str, Any]:
    pr_visible = stage_visibility_signal("pull_request", pull_request)
    ci_visible = stage_visibility_signal("ci", ci)
    deployment_visible = stage_visibility_signal("deployment", deployment)

    if pr_visible and ci_visible and deployment_visible:
        code = "fully-traceable"
    elif deployment_visible:
        code = "deployment-visible"
    elif ci_visible:
        code = "pipeline-visible"
    elif pr_visible or commit_count > 0:
        code = "review-visible" if pr_visible else "code-linked-only"
    else:
        code = "code-linked-only"

    blocking_gap = None
    if not pr_visible:
        blocking_gap = "review"
    elif not ci_visible:
        blocking_gap = "pipeline"
    elif not deployment_visible:
        blocking_gap = "deployment"

    rule = READINESS_RULES[code]
    return {
        "code": code,
        "label": rule["label"],
        "description": rule["description"],
        "blocking_gap": blocking_gap,
        "review_visible": pr_visible,
        "pipeline_visible": ci_visible,
        "deployment_visible": deployment_visible,
    }


def stage_visibility_signal(stage_name: str, stage: dict[str, Any]) -> bool:
    if not stage or stage.get("source") == "mock":
        return False
    if stage.get("source") == "connector":
        return True
    if stage_name == "pull_request":
        return any(value_present(stage.get(key)) for key in ("number", "url", "merged_at")) or bool(stage.get("reviewers"))
    if stage_name == "ci":
        return any(value_present(stage.get(key)) for key in ("run_id", "url", "completed_at"))
    return any(value_present(stage.get(key)) for key in ("url", "deployed_at", "target", "version"))


def identify_weakest_stage(pull_request: dict[str, Any], ci: dict[str, Any], deployment: dict[str, Any]) -> dict[str, Any]:
    stage_definitions = [
        ("pull_request", "Pull Request", pull_request),
        ("ci", "CI", ci),
        ("deployment", "Deployment", deployment),
    ]

    def stage_rank(item: tuple[str, str, dict[str, Any]]) -> tuple[int, int, int]:
        key, _, stage = item
        quality = stage.get("quality") or {}
        completeness_pct = int(quality.get("completeness_pct") or 0)
        completeness_label = str(quality.get("completeness_label") or "missing").lower()
        label_rank = {"missing": 0, "minimal": 1, "partial": 2, "complete": 3}.get(completeness_label, 0)
        downstream_priority = {"deployment": 0, "ci": 1, "pull_request": 2}.get(key, 3)
        return (label_rank, completeness_pct, downstream_priority)

    weakest_key, weakest_label, weakest_stage = min(stage_definitions, key=stage_rank)
    quality = weakest_stage.get("quality") or {}
    source = weakest_stage.get("source") or "unknown"
    reason = weak_stage_reason(weakest_label, weakest_stage)
    return {
        "key": weakest_key,
        "label": weakest_label,
        "source": source,
        "status": weakest_stage.get("status") or "unknown",
        "completeness_pct": int(quality.get("completeness_pct") or 0),
        "completeness_label": quality.get("completeness_label") or "missing",
        "reason": reason,
    }


def weak_stage_reason(stage_label: str, stage: dict[str, Any]) -> str:
    quality = stage.get("quality") or {}
    if quality.get("is_mock_fallback"):
        return f"{stage_label} is still placeholder-backed."
    if quality.get("is_partial_connector"):
        return f"{stage_label} is connector-backed but still missing operational detail."
    if quality.get("weak_evidence"):
        return f"{stage_label} is inferred from limited evidence."
    missing_fields = list(quality.get("missing_fields") or [])
    if missing_fields:
        return f"{stage_label} is missing {', '.join(missing_fields[:2])}."
    return f"{stage_label} is the thinnest part of the delivery chain."


def infer_traceability_strength(
    *,
    commit_count: int,
    completeness_pct: int,
    connector_stage_count: int,
    mock_stage_count: int,
    downstream_coverage_pct: int,
    delivery_evidence_strength: str,
) -> str:
    if commit_count <= 0 and mock_stage_count >= 3:
        return "missing"
    if downstream_coverage_pct >= 100 and connector_stage_count >= 2 and completeness_pct >= 75 and delivery_evidence_strength == "verified":
        return "strong"
    if downstream_coverage_pct >= 67 and mock_stage_count <= 1 and delivery_evidence_strength != "missing":
        return "moderate"
    if downstream_coverage_pct >= 34 or commit_count > 0:
        return "weak"
    return "missing"


def infer_delivery_evidence_strength(
    *,
    pull_request: dict[str, Any],
    ci: dict[str, Any],
    deployment: dict[str, Any],
    commit_count: int,
    readiness_code: Any,
    missing_downstream_evidence: bool,
) -> str:
    if commit_count <= 0:
        return "missing"
    if any(stage.get("source") == "connector" for stage in (ci, deployment)):
        return "verified"
    if missing_downstream_evidence:
        return "weak"
    if readiness_code in {"fully-traceable", "deployment-visible", "pipeline-visible"}:
        return "partial"
    if pull_request.get("source") != "mock":
        return "weak"
    return "missing"


def build_timeline_quality_rollups(records: list[dict[str, Any]]) -> dict[str, Any]:
    total_requirements = len(records) or 1
    total_stages = max(1, len(records) * 3)
    connector_stage_total = sum(int((record.get("source_breakdown") or {}).get("connector") or 0) for record in records)
    inferred_stage_total = sum(int((record.get("source_breakdown") or {}).get("inferred") or 0) for record in records)
    mock_stage_total = sum(int((record.get("source_breakdown") or {}).get("mock") or 0) for record in records)
    avg_stage_completeness = round(
        sum(int((record.get("quality") or {}).get("completeness_pct") or 0) for record in records) / len(records)
    ) if records else 0

    traceability_strength_counts = {"strong": 0, "moderate": 0, "weak": 0, "missing": 0}
    delivery_evidence_strength_counts = {"verified": 0, "partial": 0, "weak": 0, "missing": 0}

    freshness_counts = {"fresh": 0, "active": 0, "stale": 0, "unknown": 0}
    missing_downstream_evidence_requirements = 0
    partial_connector_requirements = 0
    weak_inference_requirements = 0
    readiness_counts = {
        "code-linked-only": 0,
        "review-visible": 0,
        "pipeline-visible": 0,
        "deployment-visible": 0,
        "fully-traceable": 0,
    }
    weak_connector_confidence_requirements = 0
    weak_traceability_requirements = 0
    stage_completeness_counts = {"complete": 0, "partial": 0, "minimal": 0, "missing": 0}
    for record in records:
        quality = record.get("quality") or {}
        freshness = (quality.get("freshness") or "unknown").lower()
        freshness_counts[freshness if freshness in freshness_counts else "unknown"] += 1
        if quality.get("missing_downstream_evidence"):
            missing_downstream_evidence_requirements += 1
        readiness_code = (record.get("readiness") or {}).get("code")
        if readiness_code in readiness_counts:
            readiness_counts[readiness_code] += 1
        if quality.get("traceability_strength") in {"weak", "missing"}:
            weak_traceability_requirements += 1
        traceability_strength_counts[(quality.get("traceability_strength") or "missing")] = (
            traceability_strength_counts.get((quality.get("traceability_strength") or "missing"), 0) + 1
        )
        delivery_strength = (quality.get("delivery_evidence_strength") or "missing")
        delivery_evidence_strength_counts[delivery_strength] = delivery_evidence_strength_counts.get(delivery_strength, 0) + 1
        stages = [record.get("pull_request") or {}, record.get("ci") or {}, record.get("deployment") or {}]
        has_partial_connector = False
        has_weak_inference = False
        has_weak_connector_confidence = False
        for stage in stages:
            stage_quality = stage.get("quality") or {}
            label = (stage_quality.get("completeness_label") or "").lower()
            if label in stage_completeness_counts:
                stage_completeness_counts[label] += 1
            if stage_quality.get("is_partial_connector"):
                has_partial_connector = True
            if stage_quality.get("weak_evidence"):
                has_weak_inference = True
            if stage.get("source") == "connector" and stage_quality.get("confidence") != "high":
                has_weak_connector_confidence = True
        if has_partial_connector:
            partial_connector_requirements += 1
        if has_weak_inference:
            weak_inference_requirements += 1
        if has_weak_connector_confidence:
            weak_connector_confidence_requirements += 1

    return {
        "connector_coverage_pct": safe_pct(connector_stage_total, total_stages),
        "synthesized_delivery_pct": safe_pct(inferred_stage_total + mock_stage_total, total_stages),
        "mock_fallback_stage_pct": safe_pct(mock_stage_total, total_stages),
        "stage_completeness_pct": avg_stage_completeness,
        "complete_stage_pct": safe_pct(stage_completeness_counts["complete"], total_stages),
        "partial_stage_pct": safe_pct(stage_completeness_counts["partial"], total_stages),
        "minimal_stage_pct": safe_pct(stage_completeness_counts["minimal"], total_stages),
        "missing_stage_pct": safe_pct(stage_completeness_counts["missing"], total_stages),
        "downstream_evidence_coverage_pct": safe_pct(total_requirements - missing_downstream_evidence_requirements, total_requirements),
        "fully_traceable_requirements": readiness_counts["fully-traceable"],
        "deployment_visible_requirements": readiness_counts["deployment-visible"],
        "pipeline_visible_requirements": readiness_counts["pipeline-visible"],
        "review_visible_requirements": readiness_counts["review-visible"],
        "requirements_not_visible_beyond_code": readiness_counts["code-linked-only"],
        "requirements_missing_review_visibility": readiness_counts["code-linked-only"],
        "requirements_missing_pipeline_visibility": readiness_counts["review-visible"],
        "requirements_missing_deployment_visibility": readiness_counts["pipeline-visible"],
        "fresh_requirements": freshness_counts["fresh"],
        "stale_requirements": freshness_counts["stale"],
        "missing_downstream_evidence_requirements": missing_downstream_evidence_requirements,
        "requirements_with_partial_connector_stages": partial_connector_requirements,
        "requirements_with_weak_inference": weak_inference_requirements,
        "requirements_with_weak_connector_confidence": weak_connector_confidence_requirements,
        "weak_traceability_requirements": weak_traceability_requirements,
        "traceability_strength_counts": traceability_strength_counts,
        "delivery_evidence_strength_counts": delivery_evidence_strength_counts,
    }


def infer_freshness_hint(timestamp_value: Any) -> str:
    if not value_present(timestamp_value):
        return "unknown"
    from datetime import datetime, timezone

    age_seconds = datetime.now(timezone.utc).timestamp() - timeline_sort_key(timestamp_value)
    if age_seconds <= 3 * 86400:
        return "fresh"
    if age_seconds <= 14 * 86400:
        return "active"
    return "stale"


def safe_pct(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return round((numerator / denominator) * 100)


def get_latest_commit_timestamp(commits: list[dict[str, Any]]) -> Optional[str]:
    timestamps = [commit.get("timestamp") for commit in commits if value_present(commit.get("timestamp"))]
    if not timestamps:
        return None
    return max(timestamps, key=timeline_sort_key)
