from __future__ import annotations

from typing import Any, Optional


REVIEWER_ROTATION = [
    "Platform reviewer",
    "Backend reviewer",
    "Frontend reviewer",
    "Release manager",
]

CI_WORKFLOWS = [
    "showcase-validation",
    "quality-gates",
    "release-smoke",
]

DEPLOYMENT_ENVIRONMENTS = [
    "staging",
    "preview",
    "production",
]

DEPLOYMENT_TARGETS = [
    "Vercel",
    "Render",
    "Supabase Edge",
]


def build_mock_stage_records(
    issue: dict[str, Any],
    commits: list[dict[str, Any]],
    latest_commit: Optional[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    issue_id = str(issue.get("issue_id") or "REQ-000")
    seed = stable_seed(issue_id + str((latest_commit or {}).get("commit_id") or ""))
    commit_count = len(commits)
    branch = str((latest_commit or {}).get("branch") or f"feature/{issue_id.lower()}")
    repository_name = str((latest_commit or {}).get("repository_name") or "devhouse-app")
    author = str((latest_commit or {}).get("author") or "Recent contributor")
    latest_timestamp = (latest_commit or {}).get("timestamp")

    if commit_count <= 0:
        return {
            "pull_request": {
                "status": "not started",
                "summary": "No pull request yet",
                "source": "mock",
                "provenance_detail": "placeholder",
                "is_mock": True,
                "note": "Waiting for the first linked commit before opening a PR.",
                "evidence": ["No linked commits yet"],
            },
            "ci": {
                "status": "blocked",
                "summary": "CI blocked",
                "source": "mock",
                "provenance_detail": "placeholder",
                "is_mock": True,
                "note": "CI will start after a PR or branch build exists.",
                "evidence": ["No delivery execution signals available"],
            },
            "deployment": {
                "status": "blocked",
                "summary": "Deployment blocked",
                "environment": "staging",
                "source": "mock",
                "provenance_detail": "placeholder",
                "is_mock": True,
                "note": "Deployment depends on CI completion.",
                "evidence": ["No deployment telemetry available"],
            },
        }

    pr_number = 100 + (seed % 900)
    reviewer = REVIEWER_ROTATION[seed % len(REVIEWER_ROTATION)]
    workflow = CI_WORKFLOWS[seed % len(CI_WORKFLOWS)]
    environment = DEPLOYMENT_ENVIRONMENTS[seed % len(DEPLOYMENT_ENVIRONMENTS)]
    target = DEPLOYMENT_TARGETS[seed % len(DEPLOYMENT_TARGETS)]
    commit_suffix = str((latest_commit or {}).get("commit_id") or "sha")[:7] or "sha"

    if commit_count == 1:
        pr_status = "open"
        ci_status = "queued"
        deployment_status = "blocked"
    else:
        state_index = seed % 3
        if state_index == 0:
            pr_status = "approved"
            ci_status = "running"
            deployment_status = "pending"
        elif state_index == 1:
            pr_status = "merged"
            ci_status = "passed"
            deployment_status = "success"
        else:
            pr_status = "merged"
            ci_status = "passed"
            deployment_status = "in progress"

    return {
        "pull_request": {
            "status": pr_status,
            "number": pr_number,
            "title": f"{issue_id}: {issue.get('title') or 'Requirement delivery'}",
            "summary": f"PR #{pr_number}",
            "repository_name": repository_name,
            "author": author,
            "branch": branch,
            "reviewers": [reviewer],
            "created_at": latest_timestamp,
            "updated_at": latest_timestamp,
            "merged_at": latest_timestamp if pr_status == "merged" else None,
            "source": "mock",
            "provenance_detail": "placeholder",
            "is_mock": True,
            "note": f"Placeholder PR generated from linked commits on {branch}.",
            "evidence": [f"{commit_count} linked commits", f"branch {branch}"],
        },
        "ci": {
            "status": ci_status,
            "summary": workflow.replace("-", " ").title(),
            "workflow": workflow,
            "run_id": f"run-{issue_id.lower()}-{seed % 1000}",
            "started_at": latest_timestamp,
            "completed_at": latest_timestamp if ci_status == "passed" else None,
            "duration_minutes": 8 + (seed % 9),
            "source": "mock",
            "provenance_detail": "placeholder",
            "is_mock": True,
            "note": "Placeholder CI state derived from delivery stage progression.",
            "evidence": [f"{commit_count} linked commits", "No connector CI run available"],
        },
        "deployment": {
            "status": deployment_status,
            "summary": f"{environment.title()} deployment",
            "environment": environment,
            "target": target,
            "version": f"{branch.replace('/', '-')}-{commit_suffix}",
            "deployed_at": latest_timestamp if deployment_status == "success" else None,
            "source": "mock",
            "provenance_detail": "placeholder",
            "is_mock": True,
            "note": f"Placeholder deployment generated for showcase on {target}.",
            "evidence": [f"environment {environment}", f"target {target}"],
        },
    }


def stable_seed(value: str) -> int:
    return sum((index + 1) * ord(character) for index, character in enumerate(str(value or "")))
