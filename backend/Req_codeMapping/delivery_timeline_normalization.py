from __future__ import annotations

import math
import re
from urllib.parse import urlparse
from typing import Any, Optional


PR_STATUS_ALIASES = {
    "true": "merged",
    "false": "open",
    "open": "open",
    "opened": "open",
    "ready for review": "open",
    "ready for merge": "approved",
    "review required": "open",
    "review requested": "open",
    "under review": "open",
    "in review": "open",
    "draft": "draft",
    "work in progress": "draft",
    "approved": "approved",
    "review approved": "approved",
    "accepted": "approved",
    "auto merge enabled": "approved",
    "merge queued": "approved",
    "merged": "merged",
    "merge": "merged",
    "auto merged": "merged",
    "closed merged": "merged",
    "merged closed": "merged",
    "merged by queue": "merged",
    "closed": "closed",
}

CI_STATUS_ALIASES = {
    "queued": "queued",
    "pending": "queued",
    "requested": "queued",
    "waiting": "queued",
    "waiting for checks": "queued",
    "created": "queued",
    "running": "running",
    "in progress": "running",
    "in progress running": "running",
    "inprogress": "running",
    "working": "running",
    "passed": "passed",
    "pass": "passed",
    "successful": "passed",
    "success": "passed",
    "completed": "passed",
    "completed success": "passed",
    "ok": "passed",
    "neutral": "passed",
    "completed successfully": "passed",
    "failed": "failed",
    "failure": "failed",
    "completed failure": "failed",
    "error": "failed",
    "timed out": "failed",
    "startup failure": "failed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "skipped": "skipped",
    "blocked": "blocked",
    "action required": "blocked",
}

DEPLOYMENT_STATUS_ALIASES = {
    "pending": "pending",
    "queued": "pending",
    "scheduled": "pending",
    "running": "in progress",
    "in progress": "in progress",
    "deploying": "in progress",
    "building": "in progress",
    "ready": "pending",
    "success": "success",
    "successful": "success",
    "succeeded": "success",
    "completed": "success",
    "released": "success",
    "live": "live",
    "active": "live",
    "healthy": "live",
    "available": "live",
    "deployed": "success",
    "promoted": "success",
    "current": "live",
    "failed": "failed",
    "error": "failed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "blocked": "blocked",
    "not started": "not started",
}

ENVIRONMENT_ALIASES = {
    "prod": "production",
    "production": "production",
    "pre production": "staging",
    "pre-production": "staging",
    "live": "production",
    "preprod": "staging",
    "staging": "staging",
    "stage": "staging",
    "stg": "staging",
    "preview": "preview",
    "qa": "preview",
    "uat": "preview",
    "sandbox": "preview",
    "dev": "development",
    "development": "development",
    "test": "development",
}


def value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def first_present(*values: Any) -> Any:
    for value in values:
        if value_present(value):
            return value
    return None


def normalize_text(value: Any) -> Optional[str]:
    if not value_present(value):
        return None
    return " ".join(str(value).split())


def normalize_url(value: Any) -> Optional[str]:
    text = normalize_text(value)
    if not text:
        return None
    text = text.strip("[](){}<>\"'`")
    text = text.rstrip(").,;:\"'")
    text = text.replace("&amp;", "&")
    if text.lower().startswith("url:"):
        text = text.split(":", 1)[1].strip()
    if text.startswith("//"):
        return f"https:{text}"
    embedded_match = re.search(r"(https?://[^\s)>,;]+)", text)
    if embedded_match:
        text = embedded_match.group(1)
    if text.startswith(("http://", "https://")):
        return text
    if re.match(r"^((localhost)|([A-Za-z0-9.-]+\.[A-Za-z]{2,}))(:\d+)?([/?#]\S*)?$", text):
        return f"https://{text}"
    return None


def safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def extract_number(value: Any) -> Optional[int]:
    if not value_present(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


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


def timeline_sort_key(value: Any) -> float:
    parsed = parse_datetime(value)
    if not parsed:
        return 0.0
    return parsed.timestamp()


def sort_events_desc(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(events, key=lambda item: timeline_sort_key(item.get("timestamp")), reverse=True)


def latest_value(events: list[dict[str, Any]], *keys: str) -> tuple[Any, Optional[str], Optional[dict[str, Any]]]:
    for event in sort_events_desc(events):
        for key in keys:
            value = event.get(key)
            if value_present(value):
                return value, key, event
    return None, None, None


def earliest_timestamp(events: list[dict[str, Any]]) -> Optional[str]:
    timestamps = [event.get("timestamp") for event in events if value_present(event.get("timestamp"))]
    if not timestamps:
        return None
    return min(timestamps, key=timeline_sort_key)


def latest_timestamp(events: list[dict[str, Any]]) -> Optional[str]:
    timestamps = [event.get("timestamp") for event in events if value_present(event.get("timestamp"))]
    if not timestamps:
        return None
    return max(timestamps, key=timeline_sort_key)


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = normalize_text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def normalize_stage_status(stage: str, value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return "unknown"
    token = text.lower().replace("_", " ").replace("-", " ")
    token = " ".join(token.split())
    alias_map = {
        "pull_request": PR_STATUS_ALIASES,
        "ci": CI_STATUS_ALIASES,
        "deployment": DEPLOYMENT_STATUS_ALIASES,
    }.get(stage, {})
    return alias_map.get(token, token)


def normalize_environment(value: Any) -> Optional[str]:
    text = normalize_text(value)
    if not text:
        return None
    token = text.lower()
    alias = ENVIRONMENT_ALIASES.get(token)
    if alias:
        return alias

    collapsed = re.sub(r"[-_/]+", " ", token)
    collapsed = " ".join(collapsed.split())
    alias = ENVIRONMENT_ALIASES.get(collapsed)
    if alias:
        return alias

    if "prod" in collapsed or "live" in collapsed:
        return "production"
    if "stag" in collapsed or "preprod" in collapsed:
        return "staging"
    if "preview" in collapsed or "qa" in collapsed or "uat" in collapsed or "sandbox" in collapsed:
        return "preview"
    if "dev" in collapsed or "test" in collapsed:
        return "development"
    if "canary" in collapsed:
        return "preview"
    return collapsed


def normalize_duration_minutes(raw_minutes: Any = None, raw_seconds: Any = None, raw_milliseconds: Any = None) -> Optional[int]:
    if value_present(raw_minutes):
        minutes = safe_int(raw_minutes)
        return minutes if minutes > 0 else None
    if value_present(raw_seconds):
        seconds = safe_int(raw_seconds)
        return max(1, int(math.ceil(seconds / 60))) if seconds > 0 else None
    if value_present(raw_milliseconds):
        milliseconds = safe_int(raw_milliseconds)
        return max(1, int(math.ceil(milliseconds / 60000))) if milliseconds > 0 else None
    return None


def infer_environment_from_url_hint(url_key: Any, url_value: Any) -> Optional[str]:
    key = (normalize_text(url_key) or "").lower()
    url = normalize_url(url_value) or ""
    combined = f"{key} {url}".lower()
    if not combined.strip():
        return None
    if any(token in combined for token in ("production", "prod", "live")):
        return "production"
    if any(token in combined for token in ("preview", "qa", "sandbox", "uat")):
        return "preview"
    if "staging" in combined or "stage" in combined:
        return "staging"
    if "dev" in combined or "test" in combined:
        return "development"
    return None


def infer_target_from_url(url_value: Any) -> Optional[str]:
    normalized = normalize_url(url_value)
    if not normalized:
        return None
    hostname = (urlparse(normalized).hostname or "").lower()
    if not hostname:
        return None
    if "vercel" in hostname:
        return "Vercel"
    if "render" in hostname or "onrender.com" in hostname:
        return "Render"
    if "supabase" in hostname:
        return "Supabase Edge"
    if "netlify" in hostname:
        return "Netlify"
    if "pages.dev" in hostname or "cloudflare" in hostname:
        return "Cloudflare Pages"
    if "fly.dev" in hostname:
        return "Fly.io"
    return None


def iso_utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def infer_environment_from_branch(branch: Any, pr_status: Any = None, ci_status: Any = None) -> str:
    branch_text = normalize_text(branch) or ""
    pr_token = normalize_stage_status("pull_request", pr_status)
    ci_token = normalize_stage_status("ci", ci_status)
    lowered_branch = branch_text.lower()

    if pr_token == "merged" or ci_token in {"passed"}:
        return "staging"
    if lowered_branch.startswith(("release/", "hotfix/", "main", "master")):
        return "production"
    return "preview"


def has_merge_signal(events: list[dict[str, Any]]) -> bool:
    for event in events:
        if event.get("is_merge_commit") is True:
            return True
        commit_type = normalize_text(event.get("commit_type")) or ""
        commit_category = normalize_text(event.get("commit_category")) or ""
        event_type = normalize_text(event.get("event_type")) or ""
        if any(token in value.lower() for value in (commit_type, commit_category, event_type) for token in ("merge", "pull request merged", "pull_request_merged")):
            return True
    return False


def present_keys(record: Optional[dict[str, Any]], keys: list[str]) -> bool:
    if not record:
        return False
    return any(value_present(record.get(key)) for key in keys)


def normalize_people_list(*values: Any) -> list[str]:
    people: list[str] = []
    for value in values:
        people.extend(extract_people_values(value))
    return dedupe_preserve_order(people)


def extract_people_values(value: Any) -> list[str]:
    if not value_present(value):
        return []
    if isinstance(value, list):
        results: list[str] = []
        for item in value:
            results.extend(extract_people_values(item))
        return results
    if isinstance(value, dict):
        for key in ("name", "login", "username", "email", "reviewer", "reviewed_by", "display_name", "full_name"):
            if value_present(value.get(key)):
                normalized = normalize_text(value.get(key))
                return [normalized] if normalized else []
        return []

    text = normalize_text(value)
    if not text:
        return []
    if "," in text:
        return [item for item in (normalize_text(part) for part in text.split(",")) if item]
    return [text]
