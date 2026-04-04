import json
import math
import os
import re
import time
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
from urllib import error, parse, request

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import analytics as analytics_service
import storage as storage_service

# Novelty Features (Option A Implementation)
try:
    from burnout_detector import BurnoutDetector, BurnoutAlertManager, RiskLevel, run_burnout_detection_job
    from predictive_delivery import PredictiveDeliveryEngine, DeveloperVelocity, create_developer_velocity
    NOVELTY_FEATURES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Novelty features not available: {e}")
    NOVELTY_FEATURES_AVAILABLE = False

from schemas import (
    AmbiguityRecord,
    AttributionDecision,
    AttributionSummaryResponse,
    DashboardResponse,
    DeliveryTimelineResponse,
    DependencyEdge,
    DependencyGraphResponse,
    HealthResponse,
    MappingFeedbackListResponse,
    MappingFeedbackPayload,
    MappingFeedbackSaveResponse,
    MatchCommitResponse,
    ProjectIntakePayload,
    ProjectIntakeListResponse,
    ProjectIntakeResponse,
    SyncResponse,
)
from pydantic import BaseModel

# Attribution Engine Imports
try:
    from identity_resolution import IdentityResolver, create_resolver
    from work_item_resolution import AttributionEngine, create_attribution_engine
    from ownership_graph import OwnershipGraph, create_ownership_graph
    from dependency_graph import DependencyGraph
    from org_mapping import OrgMapper, create_org_mapper
    ATTRIBUTION_FEATURES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Attribution features not available: {e}")
    ATTRIBUTION_FEATURES_AVAILABLE = False
    IdentityResolver = None
    AttributionEngine = None
    OwnershipGraph = None
    DependencyGraph = None
    OrgMapper = None
    create_resolver = None
    create_attribution_engine = None
    create_ownership_graph = None
    create_org_mapper = None

ROOT_DIR = Path(__file__).resolve().parent
FEEDBACK_STORE_PATH = ROOT_DIR / "mapping_feedback.json"
MAPPING_FEEDBACK_TABLE = "mapping_feedback"
PROJECT_INTAKE_TABLE = "project_intake_records"
ANALYTICS_SNAPSHOTS_TABLE = "analytics_snapshots"
DASHBOARD_ANALYTICS_SNAPSHOT_KEY = "dashboard_analytics_v1"
DELIVERY_TIMELINE_SNAPSHOT_KEY = "delivery_timeline_v1"
load_dotenv()

ENV_CONFIG_WARNINGS: list[str] = []


def parse_int_env(name: str, default: int, minimum: Optional[int] = None) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(str(raw).strip())
    except ValueError:
        ENV_CONFIG_WARNINGS.append(f"{name} must be an integer. Falling back to {default}.")
        return default
    if minimum is not None and value < minimum:
        ENV_CONFIG_WARNINGS.append(f"{name} must be at least {minimum}. Falling back to {default}.")
        return default
    return value


def parse_float_env(name: str, default: float, minimum: Optional[float] = None, maximum: Optional[float] = None) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = float(str(raw).strip())
    except ValueError:
        ENV_CONFIG_WARNINGS.append(f"{name} must be numeric. Falling back to {default}.")
        return default
    if minimum is not None and value < minimum:
        ENV_CONFIG_WARNINGS.append(f"{name} must be >= {minimum}. Falling back to {default}.")
        return default
    if maximum is not None and value > maximum:
        ENV_CONFIG_WARNINGS.append(f"{name} must be <= {maximum}. Falling back to {default}.")
        return default
    return value

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
SUPABASE_API_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or os.getenv("VITE_SUPABASE_ANON_KEY")
)
BASE_REST_URL = f"{(SUPABASE_URL or '').rstrip('/')}/rest/v1"

FASTEMBED_MODEL_NAME = os.getenv("REQ_MATCH_MODEL", "BAAI/bge-small-en-v1.5")
MATCH_THRESHOLD = parse_float_env("REQ_MATCH_THRESHOLD", 0.45, minimum=0.0, maximum=1.0)
MAX_PATCH_CHARS = parse_int_env("REQ_MATCH_MAX_PATCH_CHARS", 4000, minimum=1)
MAX_COMMIT_TEXT_CHARS = parse_int_env("REQ_MATCH_MAX_COMMIT_TEXT_CHARS", 12000, minimum=1)
TOP_MATCHES_PER_SYNC = parse_int_env("REQ_MATCH_TOP_MATCHES", 25, minimum=1)
WRITE_API_KEY = os.getenv("DEVHOUSE_WRITE_API_KEY", "").strip()
DISABLE_FILE_FALLBACK = os.getenv("DEVHOUSE_DISABLE_FILE_FALLBACK", "").strip().lower() == "true"
STORAGE_PROBE_TTL_SECONDS = parse_int_env("DEVHOUSE_STORAGE_PROBE_TTL_SECONDS", 30, minimum=1)
ANALYTICS_SNAPSHOTS_ENABLED = os.getenv("DEVHOUSE_ANALYTICS_SNAPSHOTS_ENABLED", "true").strip().lower() != "false"
ANALYTICS_SNAPSHOT_MAX_AGE_SECONDS = parse_int_env("DEVHOUSE_ANALYTICS_SNAPSHOT_MAX_AGE_SECONDS", 120, minimum=1)
_storage_probe_cache: dict[str, tuple[float, bool]] = {}
_startup_diagnostics_logged = False

STOP_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "into", "your", "when",
    "were", "been", "have", "has", "had", "about", "after", "before", "there",
    "their", "them", "then", "than", "also", "only", "each", "able", "using",
    "used", "will", "would", "could", "should", "into", "over", "under", "main",
    "feat", "fix", "task", "jira", "issue", "commit", "code", "test", "tests",
}

if not SUPABASE_URL or not SUPABASE_API_KEY:
    print("WARNING: Missing Supabase credentials! The service will not be able to sync.")

DEFAULT_HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
}

app = FastAPI(title="Supabase Commit Sync API")

try:
    import delivery_timeline as delivery_timeline_service
    DELIVERY_TIMELINE_IMPORT_ERROR = ""
except ModuleNotFoundError:
    delivery_timeline_service = None
    DELIVERY_TIMELINE_IMPORT_ERROR = "delivery_timeline module not installed"


def build_optional_module_details() -> dict[str, dict[str, Any]]:
    showcase_error = ""
    if hasattr(analytics_service, "showcase_summaries_import_error"):
        showcase_error = str(analytics_service.showcase_summaries_import_error() or "")
    return {
        "delivery_timeline": {
            "available": delivery_timeline_service is not None,
            "status": "ready" if delivery_timeline_service is not None else "missing",
            "reason": "" if delivery_timeline_service is not None else DELIVERY_TIMELINE_IMPORT_ERROR,
            "action": ""
            if delivery_timeline_service is not None
            else "Restore or install backend/Req_codeMapping/delivery_timeline.py so delivery traceability stays available.",
        },
        "showcase_summaries": {
            "available": analytics_service.showcase_summaries_available(),
            "status": "ready" if analytics_service.showcase_summaries_available() else "missing",
            "reason": showcase_error,
            "action": ""
            if analytics_service.showcase_summaries_available()
            else "Restore or install backend/Req_codeMapping/showcase_summaries.py so readable weekly summaries stay available.",
        },
    }


def parse_allowed_origins() -> list[str]:
    configured = os.getenv("ALLOWED_ORIGINS", "")
    parsed = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]

    frontend_url = (os.getenv("FRONTEND_URL") or "http://localhost:5173").rstrip("/")
    default_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        frontend_url,
    ]

    seen: set[str] = set()
    origins: list[str] = []
    for origin in [*default_origins, *parsed]:
        if origin and origin not in seen:
            seen.add(origin)
            origins.append(origin)
    return origins


def parse_origin_candidates() -> list[str]:
    configured = os.getenv("ALLOWED_ORIGINS", "")
    frontend_url = (os.getenv("FRONTEND_URL") or "http://localhost:5173").rstrip("/")
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        frontend_url,
        *[origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()],
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_allowed_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_embedder():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=FASTEMBED_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    cleaned = [normalize_spaces(text) for text in texts]
    if not cleaned:
        return []
    embeddings = list(get_embedder().embed(cleaned))
    return [[float(value) for value in vector.tolist()] for vector in embeddings]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    runtime = build_runtime_health()
    return runtime


def require_write_access(x_api_key: Optional[str], authorization: Optional[str]) -> None:
    if not WRITE_API_KEY:
        return

    bearer_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()

    presented = (x_api_key or bearer_token or "").strip()
    if presented != WRITE_API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid write API key")


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard() -> DashboardResponse:
    issues = fetch_issues()
    events = fetch_events(order="timestamp.desc")
    sync_result = summarize_current_links(issues)
    analytics_payload, snapshot_meta = get_dashboard_analytics_payload(issues, events, sync_result)
    
    # Add attribution summary if available
    attribution_summary = None
    if ATTRIBUTION_FEATURES_AVAILABLE and _attribution_engine and _identity_resolver:
        stats = _attribution_engine.get_stats()
        identity_stats = _identity_resolver.get_stats()
        attribution_summary = {
            "resolved_developers": identity_stats.get("total_developers", 0),
            "total_aliases": identity_stats.get("total_aliases", 0),
            "attributed_work_items": stats.get("total_decisions", 0),
            "ambiguous_items": stats.get("ambiguous_decisions", 0),
            "pending_ambiguities": stats.get("pending_ambiguities", 0),
            "engines_ready": {
                "identity_resolver": _identity_resolver is not None,
                "attribution_engine": _attribution_engine is not None,
                "ownership_graph": _ownership_graph is not None,
                "org_mapper": _org_mapper is not None,
            },
        }
    
    meta = {**build_storage_meta(), **snapshot_meta}
    
    response = {
        "sync": sync_result,
        "issues": issues,
        "events": events,
        "feedback": list(load_feedback_store().values()),
        "analytics": analytics_payload,
        "meta": meta,
    }
    
    # Add attribution summary as meta field for backward compatibility
    if attribution_summary:
        response["meta"]["attribution"] = attribution_summary
    
    return response


@app.get("/api/delivery-timeline", response_model=DeliveryTimelineResponse)
def delivery_timeline_endpoint() -> DeliveryTimelineResponse:
    return get_delivery_timeline_payload()


@app.post("/api/sync", response_model=SyncResponse)
def sync_endpoint(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> SyncResponse:
    require_write_access(x_api_key, authorization)
    result = sync_commit_links()
    
    # Use AttributionEngine for commit-to-developer mapping if available
    if ATTRIBUTION_FEATURES_AVAILABLE and _attribution_engine and _identity_resolver:
        try:
            events = fetch_events()
            attribution_count = 0
            
            for event in events:
                commit_id = event.get("commit_id")
                if not commit_id:
                    continue
                
                # Build commit data for attribution
                commit_data = {
                    "commit_id": commit_id,
                    "author_email": event.get("author_email"),
                    "author": event.get("author"),
                    "timestamp": event.get("timestamp"),
                    "additions": event.get("additions", 0),
                    "deletions": event.get("deletions", 0),
                }
                
                # Resolve identity first
                if event.get("author_email"):
                    _identity_resolver.resolve_identity(
                        git_email=event.get("author_email"),
                        git_name=event.get("author"),
                    )
                
                # Attribute work item
                _attribution_engine.attribute_work_item(
                    work_item_id=commit_id,
                    work_item_type="commit",
                    commit_data=commit_data,
                )
                attribution_count += 1
            
            result["attribution_processed"] = attribution_count
            result["attribution_engines_ready"] = True
        except Exception as e:
            result["attribution_error"] = str(e)
            result["attribution_engines_ready"] = False
    
    refresh_cached_views(sync_result=result)
    return result


@app.get("/api/mapping-feedback", response_model=MappingFeedbackListResponse)
def get_mapping_feedback() -> MappingFeedbackListResponse:
    feedback = list(load_feedback_store().values())
    feedback.sort(key=lambda item: str(item.get("reviewed_at") or ""), reverse=True)
    return {"feedback": feedback}


@app.post("/api/mapping-feedback", response_model=MappingFeedbackSaveResponse)
def save_mapping_feedback(
    payload: MappingFeedbackPayload,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> MappingFeedbackSaveResponse:
    require_write_access(x_api_key, authorization)
    commit_id = str(payload.commit_id or "").strip()
    feedback_type = str(payload.feedback_type or "").strip().lower()
    predicted_issue_id = normalize_issue_id(payload.predicted_issue_id)
    corrected_issue_id = normalize_issue_id(payload.corrected_issue_id)
    reviewed_by = str(payload.reviewed_by or "dashboard-reviewer").strip()

    if not commit_id:
        raise HTTPException(status_code=400, detail="commit_id is required")
    if feedback_type not in {"approved", "rejected", "reassigned", "cleared"}:
        raise HTTPException(status_code=400, detail="feedback_type must be approved, rejected, reassigned, or cleared")
    if feedback_type == "reassigned" and not corrected_issue_id:
        raise HTTPException(status_code=400, detail="corrected_issue_id is required for reassigned feedback")

    if feedback_type == "cleared":
        feedback = delete_feedback_record(commit_id)
    else:
        feedback = {
            "commit_id": commit_id,
            "feedback_type": feedback_type,
            "predicted_issue_id": predicted_issue_id or None,
            "corrected_issue_id": corrected_issue_id or None,
            "reviewed_by": reviewed_by,
            "reviewed_at": iso_utc_now(),
        }
        persist_feedback_record(feedback)

    refresh_cached_views()
    return {"status": "ok", "feedback": feedback}


@app.post("/api/project-intake", response_model=ProjectIntakeResponse)
def project_intake(
    payload: ProjectIntakePayload,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> ProjectIntakeResponse:
    require_write_access(x_api_key, authorization)
    title = normalize_spaces(payload.title)
    description = normalize_spaces(payload.description)
    project_key = normalize_issue_id(payload.project_key or "MANUAL")
    issue_type = normalize_spaces(payload.issue_type or "Requirement") or "Requirement"
    priority = normalize_spaces(payload.priority or "Medium") or "Medium"
    owner_email = normalize_spaces(payload.owner_email or payload.assignee_email or "")
    reporter_email = normalize_spaces(payload.reporter_email or owner_email)
    issue_id = normalize_issue_id(payload.issue_id or "")
    timeline_start = normalize_timestamp_input(payload.timeline_start)
    timeline_end = normalize_timestamp_input(payload.timeline_end)

    if not issue_id:
        issue_id = generate_manual_issue_id(project_key)
    if timeline_start and timeline_end:
        start_dt = parse_datetime(timeline_start)
        end_dt = parse_datetime(timeline_end)
        if start_dt and end_dt and end_dt < start_dt:
            raise HTTPException(status_code=400, detail="timeline_end must be later than timeline_start")

    record = {
        "issue_id": issue_id,
        "title": title,
        "description": description,
        "status": normalize_spaces(payload.status or "Draft") or "Draft",
        "issue_type": issue_type,
        "priority": priority,
        "project_key": project_key or "MANUAL",
        "assignee_email": owner_email or None,
        "reporter_email": reporter_email or None,
        "jira_created_at": timeline_start or iso_utc_now(),
        "jira_updated_at": timeline_end or timeline_start or iso_utc_now(),
        "source": "manual",
        "commits": [],
    }
    try:
        post_rows("req_code_mapping", [record], upsert=True, on_conflict="issue_id")
    except HTTPException:
        legacy_record = {key: value for key, value in record.items() if key != "source"}
        post_rows("req_code_mapping", [legacy_record], upsert=True, on_conflict="issue_id")
    intake_record = {
        "issue_id": issue_id,
        "title": title,
        "description": description,
        "project_key": project_key or "MANUAL",
        "issue_type": issue_type,
        "priority": priority,
        "status": record["status"],
        "owner_email": owner_email or None,
        "reporter_email": reporter_email or None,
        "timeline_start": timeline_start or record["jira_created_at"],
        "timeline_end": timeline_end or record["jira_updated_at"],
        "source": "manual",
        "submitted_at": iso_utc_now(),
    }
    persist_project_intake_record(intake_record)
    refresh_cached_views()
    return {
        "status": "accepted",
        "record": record,
        "intake_record": intake_record,
        "roles": {
            "owner": owner_email or None,
            "reporter": reporter_email or None,
        },
    }


@app.get("/api/project-intake", response_model=ProjectIntakeListResponse)
def list_project_intake_records() -> ProjectIntakeListResponse:
    return {"records": fetch_project_intake_records()}


@app.post("/api/match-commit", response_model=MatchCommitResponse)
def match_commit_endpoint(
    payload: dict[str, Any],
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> MatchCommitResponse:
    require_write_access(x_api_key, authorization)
    event = extract_event_from_payload(payload)
    result = process_single_commit_event(event)
    refresh_cached_views()
    return result


@app.post("/api/extension-events/webhook", response_model=MatchCommitResponse)
def extension_events_webhook(
    payload: dict[str, Any],
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> MatchCommitResponse:
    require_write_access(x_api_key, authorization)
    event_type = str(payload.get("type") or payload.get("eventType") or payload.get("event_type") or "").lower()
    if event_type and "insert" not in event_type and "create" not in event_type:
        return {"status": "ignored", "reason": f"unsupported_event_type:{event_type}"}

    event = extract_event_from_payload(payload)
    result = process_single_commit_event(event)
    refresh_cached_views()
    return result


def sync_commit_links() -> dict[str, Any]:
    issues = fetch_issues()
    events = fetch_events()
    feedback_store = load_feedback_store()
    valid_event_commit_ids = {
        str(event.get("commit_id"))
        for event in events
        if event.get("commit_id") is not None and str(event.get("commit_id")).strip()
    }

    issue_to_commits: dict[str, list[str]] = {str(issue["issue_id"]): [] for issue in issues}
    issue_to_matches: dict[str, list[dict[str, Any]]] = {str(issue["issue_id"]): [] for issue in issues}

    commit_rows = []
    for event in events:
        commit_id = str(event.get("commit_id") or "").strip()
        commit_text = build_commit_text(event)
        if commit_id and commit_text:
            commit_rows.append(
                {
                    "commit_id": commit_id,
                    "text": commit_text,
                    "selected_issue_id": normalize_issue_id(event.get("issue_id")),
                    "linked_issue": normalize_issue_id(event.get("linked_issue")),
                    "tokens": tokenize(commit_text),
                    "context_terms": extract_context_terms(event),
                }
            )

    match_results = match_commit_rows(commit_rows, issues, feedback_store)
    unmatched_commits: list[dict[str, Any]] = []
    for result in match_results:
        if not result.get("issue_id"):
            unmatched_commits.append(
                {
                    "commit_id": str(result["commit_id"]),
                    "score": round(float(result["score"]), 4),
                    "confidence": result["confidence"],
                    "reasons": result["reasons"],
                    "feedback": feedback_store.get(str(result["commit_id"])),
                }
            )
            continue
        issue_id = str(result["issue_id"])
        issue_to_commits[issue_id].append(str(result["commit_id"]))
        issue_to_matches[issue_id].append(
            {
                "commit_id": str(result["commit_id"]),
                "score": round(float(result["score"]), 4),
                "confidence": result["confidence"],
                "reasons": result["reasons"],
                "feedback": feedback_store.get(str(result["commit_id"])),
            }
        )

    updates: list[dict[str, Any]] = []
    matched_issue_count = 0
    total_linked_commits = 0

    for issue in issues:
        issue_id = str(issue["issue_id"])
        matched_commit_ids = dedupe_preserve_order(issue_to_commits[issue_id])
        existing = [
            str(commit_id)
            for commit_id in (issue.get("commits") or [])
            if commit_id is not None and str(commit_id).strip() and str(commit_id) in valid_event_commit_ids
        ]

        if sorted(matched_commit_ids) != sorted(existing):
            patch_row(
                "req_code_mapping",
                f"issue_id=eq.{parse.quote(issue_id)}",
                {"commits": matched_commit_ids},
            )

        if matched_commit_ids:
            matched_issue_count += 1
            total_linked_commits += len(matched_commit_ids)

        updates.append(
            {
                "issue_id": issue_id,
                "commits": matched_commit_ids,
                "matches": issue_to_matches[issue_id],
            }
        )

    return {
        "updated_issues": len(updates),
        "matched_issues": matched_issue_count,
        "linked_commits": total_linked_commits,
        "unmatched_commits": unmatched_commits[:TOP_MATCHES_PER_SYNC],
        "feedback_count": len(feedback_store),
        "updates": updates,
    }


def process_single_commit_event(event: dict[str, Any]) -> dict[str, Any]:
    commit_id = str(event.get("commit_id") or "").strip()
    if not commit_id:
        raise HTTPException(status_code=400, detail="Missing commit_id in payload")

    issues = fetch_issues()
    commit_text = build_commit_text(event)
    feedback_store = load_feedback_store()
    if not commit_text:
        return {
            "status": "ignored",
            "reason": "empty_commit_text",
            "commit_id": commit_id,
        }

    matches = match_commit_rows([build_commit_row(event, commit_text)], issues, feedback_store)
    match = matches[0] if matches else None
    update_commit_mapping(commit_id, match, issues)

    if not match or not match.get("issue_id"):
        return {
            "status": "unmapped",
            "commit_id": commit_id,
            "confidence": match["confidence"] if match else "low",
            "reasons": match["reasons"] if match else [f"best score stayed below threshold {MATCH_THRESHOLD:.2f}"],
            "feedback": feedback_store.get(commit_id),
            "threshold": MATCH_THRESHOLD,
        }

    return {
        "status": "mapped",
        "commit_id": commit_id,
        "issue_id": match["issue_id"],
        "score": round(float(match["score"]), 4),
        "confidence": match["confidence"],
        "reasons": match["reasons"],
        "feedback": feedback_store.get(commit_id),
        "threshold": MATCH_THRESHOLD,
    }


def fetch_issues(order: str = "created_at.asc") -> list[dict[str, Any]]:
    try:
        return get_rows(
            "req_code_mapping",
            "issue_id,title,description,status,issue_type,priority,project_key,assignee_email,reporter_email,jira_created_at,jira_updated_at,created_at,updated_at,source,commits",
            order=order,
            limit=500,
        )
    except HTTPException:
        return get_rows(
            "req_code_mapping",
            "issue_id,title,description,status,issue_type,priority,project_key,assignee_email,reporter_email,jira_created_at,jira_updated_at,created_at,updated_at,commits",
            order=order,
            limit=500,
        )


def fetch_events(order: str = "timestamp.asc") -> list[dict[str, Any]]:
    return get_rows(
        "extension_events",
        "commit_id,message,timestamp,files,files_json,diff_patch,repository_name,branch,issue_id,linked_issue,modules_touched,background_apps,developer_id,author,author_email,additions,deletions,total_changes,attendance_pct,active_minutes,idle_minutes,focus_ratio,debug_session_count",
        order=order,
        limit=500,
    )


def fetch_delivery_timeline_events(order: str = "timestamp.asc") -> list[dict[str, Any]]:
    select_candidates = [
        (
            "commit_id,message,timestamp,files,files_json,diff_patch,repository_name,branch,issue_id,linked_issue,"
            "modules_touched,background_apps,developer_id,author,author_email,additions,deletions,total_changes,"
            "attendance_pct,active_minutes,idle_minutes,focus_ratio,debug_session_count,pull_request_number,pr_number,"
            "pr_status,pr_state,pr_title,pr_url,pr_created_at,pr_updated_at,pr_merged_at,ci_status,ci_conclusion,"
            "ci_workflow,workflow_name,ci_run_id,ci_started_at,ci_completed_at,ci_duration_minutes,ci_duration_seconds,"
            "ci_duration_ms,ci_url,deployment_status,deploy_status,deployment_environment,environment,deployment_target,"
            "deployment_version,deployed_at,deployment_url,is_merge_commit,commit_type,commit_category,event_type,"
            "files_changed_count"
        ),
        (
            "commit_id,message,timestamp,files,files_json,diff_patch,repository_name,branch,issue_id,linked_issue,"
            "modules_touched,background_apps,developer_id,author,author_email,additions,deletions,total_changes,"
            "attendance_pct,active_minutes,idle_minutes,focus_ratio,debug_session_count,pull_request_number,pr_title,"
            "is_merge_commit,commit_type,commit_category,event_type,files_changed_count"
        ),
    ]

    for select_clause in select_candidates:
        try:
            return get_rows(
                "extension_events",
                select_clause,
                order=order,
                limit=500,
            )
        except HTTPException:
            continue
    return fetch_events(order=order)


def match_commit_rows(
    commit_rows: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    feedback_store: Optional[dict[str, dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    issue_rows = []
    for issue in issues:
        issue_id = str(issue.get("issue_id") or "").strip()
        issue_text = build_requirement_text(issue)
        if not issue_id or not issue_text:
            continue
        issue_rows.append(
            {
                "issue_id": issue_id,
                "text": issue_text,
                "tokens": tokenize(issue_text),
            }
        )
    issue_rows = [issue for issue in issue_rows if issue["issue_id"] and issue["text"]]
    if not issue_rows or not commit_rows:
        return []

    issue_embeddings = embed_texts([f"passage: {issue['text']}" for issue in issue_rows])
    commit_embeddings = embed_texts([f"query: {commit['text']}" for commit in commit_rows])
    results: list[dict[str, Any]] = []

    for commit_row, commit_embedding in zip(commit_rows, commit_embeddings):
        feedback = (feedback_store or {}).get(str(commit_row["commit_id"]))
        best_issue_id = None
        best_score = -1.0
        best_reasons: list[str] = []
        best_confidence = "low"

        for issue_row, issue_embedding in zip(issue_rows, issue_embeddings):
            base_score = cosine_similarity(commit_embedding, issue_embedding)
            score = base_score
            reasons = [f"semantic similarity {base_score:.2f}"]

            selected_issue_id = normalize_issue_id(commit_row.get("selected_issue_id"))
            linked_issue_id = normalize_issue_id(commit_row.get("linked_issue"))
            context_terms = set(commit_row.get("context_terms") or [])
            token_overlap = sorted(set(commit_row.get("tokens") or []) & set(issue_row["tokens"]))
            context_overlap = sorted(context_terms & set(issue_row["tokens"]))

            if selected_issue_id and selected_issue_id == issue_row["issue_id"]:
                score += 0.35
                reasons.append("developer-selected Jira issue")

            if linked_issue_id and linked_issue_id == issue_row["issue_id"]:
                score += 0.30
                reasons.append("issue key found in commit metadata")

            meaningful_token_overlap = [token for token in token_overlap if len(token) > 3][:5]
            if meaningful_token_overlap:
                token_boost = min(0.15, 0.03 * len(meaningful_token_overlap))
                score += token_boost
                reasons.append(f"shared terms: {', '.join(meaningful_token_overlap)}")

            meaningful_context_overlap = [term for term in context_overlap if len(term) > 3][:4]
            if meaningful_context_overlap:
                context_boost = min(0.12, 0.04 * len(meaningful_context_overlap))
                score += context_boost
                reasons.append(f"file/module overlap: {', '.join(meaningful_context_overlap)}")

            if score > best_score:
                best_score = score
                best_issue_id = issue_row["issue_id"]
                best_reasons = reasons
                best_confidence = confidence_band(score)

        overridden = apply_feedback_override(
            {
                "commit_id": commit_row["commit_id"],
                "issue_id": best_issue_id,
                "score": best_score,
                "confidence": best_confidence,
                "reasons": best_reasons,
            },
            feedback,
        )

        if overridden["issue_id"] and overridden["score"] >= MATCH_THRESHOLD:
            results.append(
                {
                    **overridden,
                    "feedback": feedback,
                }
            )
        else:
            results.append(
                {
                    "commit_id": overridden["commit_id"],
                    "issue_id": None,
                    "score": overridden["score"],
                    "confidence": overridden["confidence"],
                    "reasons": overridden["reasons"] or [f"best score {overridden['score']:.2f} stayed below threshold {MATCH_THRESHOLD:.2f}"],
                    "feedback": feedback,
                }
            )

    return results


def update_commit_mapping(commit_id: str, match: Optional[dict[str, Any]], issues: list[dict[str, Any]]) -> None:
    target_issue_id = str(match.get("issue_id") or "") if match else ""

    for issue in issues:
        issue_id = str(issue.get("issue_id") or "")
        existing = [str(value) for value in (issue.get("commits") or []) if str(value).strip()]

        if issue_id == target_issue_id:
            updated = dedupe_preserve_order([*existing, commit_id])
        else:
            updated = [value for value in existing if value != commit_id]

        if updated != existing:
            patch_row(
                "req_code_mapping",
                f"issue_id=eq.{parse.quote(issue_id)}",
                {"commits": updated},
            )


def extract_event_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    for key in ("record", "new", "data"):
        candidate = payload.get(key)
        if isinstance(candidate, dict) and candidate.get("commit_id"):
            return candidate

    if payload.get("commit_id"):
        return payload

    raise HTTPException(status_code=400, detail="No commit record found in payload")


def summarize_current_links(issues: list[dict[str, Any]]) -> dict[str, Any]:
    matched_issues = 0
    linked_commits = 0

    for issue in issues:
        commits = issue.get("commits") or []
        if commits:
            matched_issues += 1
            linked_commits += len(commits)

    return {
        "updated_issues": 0,
        "matched_issues": matched_issues,
        "linked_commits": linked_commits,
        "feedback_count": len(load_feedback_store()),
        "updates": [],
    }


def build_requirement_text(issue: dict[str, Any]) -> str:
    parts = [
        str(issue.get("issue_id") or ""),
        str(issue.get("title") or ""),
        str(issue.get("description") or ""),
    ]
    return normalize_spaces(" ".join(parts))


def build_commit_text(event: dict[str, Any]) -> str:
    files = extract_event_files(event)
    segments = [str(event.get("message") or "").strip()]

    for file in files:
        file_path = str(file.get("file_path") or "").strip()
        patch = str(file.get("patch") or "").strip()
        if patch:
            patch = patch[:MAX_PATCH_CHARS]
        piece = normalize_spaces(" ".join(part for part in [file_path, patch] if part))
        if piece:
            segments.append(piece)

    diff_patch = str(event.get("diff_patch") or "").strip()
    if diff_patch:
        segments.append(diff_patch[:MAX_PATCH_CHARS])

    return normalize_spaces(" ".join(segments))[:MAX_COMMIT_TEXT_CHARS]


def extract_event_files(event: dict[str, Any]) -> list[dict[str, Any]]:
    direct_files = event.get("files")
    if isinstance(direct_files, list):
        return [file for file in direct_files if isinstance(file, dict)]

    files_json = event.get("files_json")
    if isinstance(files_json, dict):
        nested_files = files_json.get("files")
        if isinstance(nested_files, list):
            return [file for file in nested_files if isinstance(file, dict)]
    if isinstance(files_json, list):
        return [file for file in files_json if isinstance(file, dict)]

    return []


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def normalize_spaces(text: str) -> str:
    return " ".join(str(text or "").split())


def is_valid_origin(origin: str) -> bool:
    value = normalize_spaces(origin)
    if not value:
        return False
    return bool(re.match(r"^https?://[^/]+$", value))


def normalize_issue_id(value: Any) -> str:
    return str(value or "").strip().upper()


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9_]+", str(text or "").lower())
    return [token for token in tokens if len(token) > 2 and token not in STOP_WORDS]


def extract_context_terms(event: dict[str, Any]) -> list[str]:
    files = extract_event_files(event)
    raw_terms: list[str] = []

    for file in files:
        raw_terms.extend(tokenize(str(file.get("file_path") or "")))
        raw_terms.extend(tokenize(str(file.get("module") or "")))
        raw_terms.extend(tokenize(str(file.get("directory") or "")))

    for module in event.get("modules_touched") or []:
        raw_terms.extend(tokenize(str(module)))

    raw_terms.extend(tokenize(str(event.get("branch") or "")))
    return dedupe_preserve_order(raw_terms)


def confidence_band(score: float) -> str:
    if score >= 0.9:
        return "high"
    if score >= 0.65:
        return "medium"
    return "low"


def build_commit_row(event: dict[str, Any], commit_text: Optional[str] = None) -> dict[str, Any]:
    text = commit_text or build_commit_text(event)
    return {
        "commit_id": str(event.get("commit_id") or "").strip(),
        "text": text,
        "selected_issue_id": normalize_issue_id(event.get("issue_id")),
        "linked_issue": normalize_issue_id(event.get("linked_issue")),
        "tokens": tokenize(text),
        "context_terms": extract_context_terms(event),
    }


def apply_feedback_override(match: dict[str, Any], feedback: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not feedback:
        return match

    feedback_type = str(feedback.get("feedback_type") or "").lower()
    predicted_issue_id = normalize_issue_id(feedback.get("predicted_issue_id"))
    corrected_issue_id = normalize_issue_id(feedback.get("corrected_issue_id"))
    updated_reasons = list(match.get("reasons") or [])

    if feedback_type == "approved":
        if predicted_issue_id:
            match["issue_id"] = predicted_issue_id
        match["score"] = max(float(match.get("score") or 0), 0.95)
        match["confidence"] = "high"
        updated_reasons.append("manual approval from reviewer")
    elif feedback_type == "reassigned":
        match["issue_id"] = corrected_issue_id or match.get("issue_id")
        match["score"] = 1.0
        match["confidence"] = "high"
        updated_reasons.append(f"manually reassigned to {match['issue_id']}")
    elif feedback_type == "rejected":
        match["issue_id"] = None
        match["score"] = min(float(match.get("score") or 0), MATCH_THRESHOLD - 0.01)
        match["confidence"] = "low"
        updated_reasons.append("manual rejection from reviewer")

    match["reasons"] = dedupe_preserve_order(updated_reasons)
    return match


def load_feedback_store() -> dict[str, dict[str, Any]]:
    remote_store = load_feedback_store_from_supabase()
    if remote_store:
        return remote_store

    if DISABLE_FILE_FALLBACK:
        return {}

    if not FEEDBACK_STORE_PATH.exists():
        return {}
    try:
        data = json.loads(FEEDBACK_STORE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {
                str(commit_id): feedback
                for commit_id, feedback in data.items()
                if isinstance(feedback, dict)
            }
    except Exception as exc:
        print(f"[WARN] Failed to load mapping feedback store: {exc}")
    return {}


def build_storage_meta() -> dict[str, Any]:
    supabase_configured = bool(SUPABASE_URL and SUPABASE_API_KEY)
    if supabase_feedback_available():
        feedback_storage_mode = "supabase"
    elif DISABLE_FILE_FALLBACK:
        feedback_storage_mode = "strict-supabase"
    else:
        feedback_storage_mode = "file-fallback" if FEEDBACK_STORE_PATH.exists() else "memory"
    file_fallback_active = feedback_storage_mode == "file-fallback"
    intake_storage_mode = "supabase" if supabase_project_intake_available() else "derived"
    analytics_storage_mode = "supabase" if analytics_snapshots_available() else "live-only"
    return {
        "supabase_configured": supabase_configured,
        "write_auth_enabled": bool(WRITE_API_KEY),
        "feedback_storage_mode": feedback_storage_mode,
        "intake_storage_mode": intake_storage_mode,
        "analytics_storage_mode": analytics_storage_mode,
        "file_fallback_active": file_fallback_active,
        "storage_probe_ttl_seconds": STORAGE_PROBE_TTL_SECONDS,
    }


def build_configuration_audit(
    *,
    missing_required_env: list[str],
    invalid_origins: list[str],
    invalid_supabase_url: bool,
    storage_meta: dict[str, Any],
    snapshot_health: dict[str, Any],
) -> dict[str, Any]:
    required_env = [
        {
            "key": "SUPABASE_URL",
            "present": "SUPABASE_URL" not in missing_required_env,
            "valid": bool(SUPABASE_URL) and not invalid_supabase_url,
            "status": "ready"
            if ("SUPABASE_URL" not in missing_required_env and not invalid_supabase_url)
            else ("invalid" if invalid_supabase_url else "missing"),
            "detail": SUPABASE_URL or "Missing",
        },
        {
            "key": "SUPABASE_SERVICE_KEY_OR_ANON_KEY",
            "present": "SUPABASE_SERVICE_KEY_OR_ANON_KEY" not in missing_required_env,
            "valid": "SUPABASE_SERVICE_KEY_OR_ANON_KEY" not in missing_required_env,
            "status": "ready" if "SUPABASE_SERVICE_KEY_OR_ANON_KEY" not in missing_required_env else "missing",
            "detail": "Configured" if "SUPABASE_SERVICE_KEY_OR_ANON_KEY" not in missing_required_env else "Missing",
        },
        {
            "key": "DEVHOUSE_WRITE_API_KEY",
            "present": bool(WRITE_API_KEY),
            "valid": bool(WRITE_API_KEY),
            "status": "ready" if WRITE_API_KEY else "optional-for-demo",
            "detail": "Configured" if WRITE_API_KEY else "Not set",
        },
    ]

    table_dependencies = [
        {
            "table": MAPPING_FEEDBACK_TABLE,
            "purpose": "Persist mapping review feedback across sessions and deployments.",
            "required_for": "self-serve launch",
            "available": storage_meta["feedback_storage_mode"] == "supabase",
            "status": storage_meta["feedback_storage_mode"],
            "action": "Apply sql/create_mapping_feedback.sql and enable strict Supabase-backed feedback persistence."
            if storage_meta["feedback_storage_mode"] != "supabase"
            else "",
        },
        {
            "table": PROJECT_INTAKE_TABLE,
            "purpose": "Persist manual requirement intake and audit records.",
            "required_for": "pilot rollout",
            "available": storage_meta["intake_storage_mode"] == "supabase",
            "status": storage_meta["intake_storage_mode"],
            "action": "Apply sql/create_project_intake_records.sql so manual intake records stop falling back to derived issue data."
            if storage_meta["intake_storage_mode"] != "supabase"
            else "",
        },
        {
            "table": ANALYTICS_SNAPSHOTS_TABLE,
            "purpose": "Serve cached dashboard analytics and delivery timeline views.",
            "required_for": "self-serve launch",
            "available": storage_meta["analytics_storage_mode"] == "supabase",
            "status": storage_meta["analytics_storage_mode"],
            "action": "Apply sql/create_analytics_snapshots.sql so cached dashboard and timeline reads stay available."
            if storage_meta["analytics_storage_mode"] != "supabase"
            else "",
        },
    ]

    cached_views = [
        {
            "name": "dashboard_analytics",
            "available": bool(snapshot_health.get("dashboard_analytics", {}).get("available")),
            "fresh": bool(snapshot_health.get("dashboard_analytics", {}).get("fresh")),
            "valid_payload": bool(snapshot_health.get("dashboard_analytics", {}).get("valid_payload")),
            "source": snapshot_health.get("dashboard_analytics", {}).get("source") or "unknown",
        },
        {
            "name": "delivery_timeline",
            "available": bool(snapshot_health.get("delivery_timeline", {}).get("available")),
            "fresh": bool(snapshot_health.get("delivery_timeline", {}).get("fresh")),
            "valid_payload": bool(snapshot_health.get("delivery_timeline", {}).get("valid_payload")),
            "source": snapshot_health.get("delivery_timeline", {}).get("source") or "unknown",
        },
    ]

    return {
        "required_env": required_env,
        "cors": {
            "status": "ready" if not invalid_origins else "invalid",
            "invalid_origins": invalid_origins,
            "allowed_origins_count": len(parse_allowed_origins()),
        },
        "write_protection": {
            "status": "ready" if WRITE_API_KEY else "demo-open",
            "backend_key_configured": bool(WRITE_API_KEY),
            "dashboard_key_required": bool(WRITE_API_KEY),
            "detail": "Mutating endpoints require DEVHOUSE_WRITE_API_KEY."
            if WRITE_API_KEY
            else "Mutating endpoints are open for local demo mode because DEVHOUSE_WRITE_API_KEY is not set.",
        },
        "table_dependencies": table_dependencies,
        "cached_views": cached_views,
        "strict_mode": {
            "file_fallback_disabled": DISABLE_FILE_FALLBACK,
            "status": "strict" if DISABLE_FILE_FALLBACK else "fallback-enabled",
        },
    }


def build_snapshot_health(storage_meta: dict[str, Any]) -> dict[str, Any]:
    snapshot_keys = {
        "dashboard_analytics": {
            "key": DASHBOARD_ANALYTICS_SNAPSHOT_KEY,
            "validator": is_valid_dashboard_snapshot_payload,
        },
        "delivery_timeline": {
            "key": DELIVERY_TIMELINE_SNAPSHOT_KEY,
            "validator": is_valid_delivery_timeline_snapshot_payload,
        },
    }
    result: dict[str, Any] = {}
    if not ANALYTICS_SNAPSHOTS_ENABLED:
        for name in snapshot_keys:
            result[name] = {
                "enabled": False,
                "available": False,
                "fresh": False,
                "valid_payload": False,
                "source": "disabled",
                "age_seconds": None,
                "generated_at": None,
            }
        return result

    if storage_meta["analytics_storage_mode"] != "supabase":
        for name in snapshot_keys:
            result[name] = {
                "enabled": True,
                "available": False,
                "fresh": False,
                "valid_payload": False,
                "source": "live-only",
                "age_seconds": None,
                "generated_at": None,
            }
        return result

    for name, snapshot_config in snapshot_keys.items():
        snapshot_key = snapshot_config["key"]
        validator = snapshot_config["validator"]
        try:
            snapshot = fetch_analytics_snapshot(snapshot_key)
        except Exception:
            snapshot = None
        if not snapshot:
            result[name] = {
                "enabled": True,
                "available": False,
                "fresh": False,
                "valid_payload": False,
                "source": "missing",
                "age_seconds": None,
                "generated_at": None,
            }
            continue
        age_seconds = snapshot_age_seconds(snapshot.get("generated_at"))
        fresh = age_seconds is not None and age_seconds <= ANALYTICS_SNAPSHOT_MAX_AGE_SECONDS
        payload = snapshot.get("payload")
        valid_payload = bool(validator(payload))
        result[name] = {
            "enabled": True,
            "available": True,
            "fresh": fresh and valid_payload,
            "valid_payload": valid_payload,
            "source": "snapshot" if (fresh and valid_payload) else ("invalid-snapshot" if not valid_payload else "stale-snapshot"),
            "age_seconds": age_seconds,
            "generated_at": snapshot.get("generated_at"),
        }
    return result


def build_readiness_checks(
    *,
    missing_required_env: list[str],
    storage_meta: dict[str, Any],
    invalid_origins: list[str],
    invalid_supabase_url: bool,
) -> list[dict[str, Any]]:
    optional_modules = {
        name: bool(details.get("available"))
        for name, details in build_optional_module_details().items()
    }
    enabled_optional_modules = sum(1 for enabled in optional_modules.values() if enabled)
    total_optional_modules = len(optional_modules)
    checks: list[dict[str, Any]] = [
        {
            "key": "supabase_credentials",
            "label": "Supabase credentials",
            "category": "configuration",
            "status": "healthy" if not missing_required_env else "degraded",
            "severity": "critical" if missing_required_env else "info",
            "current": ", ".join(missing_required_env) if missing_required_env else "Configured",
            "desired": "SUPABASE_URL and service or anon key configured",
            "action": None
            if not missing_required_env
            else "Set SUPABASE_URL and SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY in backend/Req_codeMapping/.env.",
        },
        {
            "key": "supabase_endpoint",
            "label": "Supabase endpoint URL",
            "category": "configuration",
            "status": "healthy" if not invalid_supabase_url else "degraded",
            "severity": "critical" if invalid_supabase_url else "info",
            "current": SUPABASE_URL or "Missing",
            "desired": "Valid https://<project>.supabase.co base URL",
            "action": None
            if not invalid_supabase_url
            else "Correct SUPABASE_URL so it is a valid https://<project>.supabase.co base URL with no extra path.",
        },
        {
            "key": "allowed_origins",
            "label": "Allowed origins",
            "category": "configuration",
            "status": "healthy" if not invalid_origins else "degraded",
            "severity": "critical" if invalid_origins else "info",
            "current": ", ".join(invalid_origins) if invalid_origins else "Origins validated",
            "desired": "Only valid http(s):// origins in FRONTEND_URL / ALLOWED_ORIGINS",
            "action": None
            if not invalid_origins
            else "Clean invalid ALLOWED_ORIGINS or FRONTEND_URL values so CORS behavior is predictable.",
        },
        {
            "key": "write_auth",
            "label": "Write endpoint auth",
            "category": "security",
            "status": "healthy" if WRITE_API_KEY else "warning",
            "severity": "info" if WRITE_API_KEY else "warning",
            "current": "Protected" if WRITE_API_KEY else "Open in demo mode",
            "desired": "Protected with DEVHOUSE_WRITE_API_KEY outside local demo mode",
            "action": None
            if WRITE_API_KEY
            else "Set DEVHOUSE_WRITE_API_KEY and VITE_WRITE_API_KEY before exposing mutating endpoints.",
        },
        {
            "key": "feedback_storage",
            "label": "Feedback persistence",
            "category": "persistence",
            "status": "healthy"
            if storage_meta["feedback_storage_mode"] == "supabase"
            else ("degraded" if DISABLE_FILE_FALLBACK else "warning"),
            "severity": "info"
            if storage_meta["feedback_storage_mode"] == "supabase"
            else ("critical" if DISABLE_FILE_FALLBACK else "warning"),
            "current": storage_meta["feedback_storage_mode"],
            "desired": "Supabase-backed persistence",
            "action": None
            if storage_meta["feedback_storage_mode"] == "supabase"
            else "Apply SQL migrations and set DEVHOUSE_DISABLE_FILE_FALLBACK=true for deployed environments.",
        },
        {
            "key": "intake_storage",
            "label": "Project intake persistence",
            "category": "persistence",
            "status": "healthy" if storage_meta["intake_storage_mode"] == "supabase" else "warning",
            "severity": "info" if storage_meta["intake_storage_mode"] == "supabase" else "warning",
            "current": storage_meta["intake_storage_mode"],
            "desired": "Dedicated Supabase intake table",
            "action": None
            if storage_meta["intake_storage_mode"] == "supabase"
            else "Apply sql/create_project_intake_records.sql so manual intake records are persisted in Supabase.",
        },
        {
            "key": "analytics_snapshots",
            "label": "Analytics snapshots",
            "category": "caching",
            "status": "healthy"
            if (not ANALYTICS_SNAPSHOTS_ENABLED or storage_meta["analytics_storage_mode"] == "supabase")
            else "warning",
            "severity": "info"
            if (not ANALYTICS_SNAPSHOTS_ENABLED or storage_meta["analytics_storage_mode"] == "supabase")
            else "warning",
            "current": storage_meta["analytics_storage_mode"] if ANALYTICS_SNAPSHOTS_ENABLED else "Disabled by config",
            "desired": "Fresh Supabase-backed analytics snapshots",
            "action": None
            if (not ANALYTICS_SNAPSHOTS_ENABLED or storage_meta["analytics_storage_mode"] == "supabase")
            else "Apply sql/create_analytics_snapshots.sql to enable cached analytics reads.",
        },
        {
            "key": "optional_modules",
            "label": "Optional launch modules",
            "category": "optional-modules",
            "status": "healthy" if enabled_optional_modules == total_optional_modules else "warning",
            "severity": "info" if enabled_optional_modules == total_optional_modules else "warning",
            "current": f"{enabled_optional_modules}/{total_optional_modules} enabled",
            "desired": "All optional launch modules available",
            "action": None
            if enabled_optional_modules == total_optional_modules
            else "Install or restore optional modules so timeline and summary features stay available.",
        },
    ]
    return checks


def determine_operating_mode(
    ready: bool,
    missing_required_env: list[str],
    storage_meta: dict[str, Any],
    invalid_origins: list[str],
    invalid_supabase_url: bool,
) -> str:
    if (
        ready
        and WRITE_API_KEY
        and storage_meta["feedback_storage_mode"] == "supabase"
        and storage_meta["intake_storage_mode"] == "supabase"
        and (not ANALYTICS_SNAPSHOTS_ENABLED or storage_meta["analytics_storage_mode"] == "supabase")
    ):
        return "production-ready"
    if missing_required_env or invalid_origins or invalid_supabase_url:
        return "degraded"
    if storage_meta["feedback_storage_mode"] in {"memory", "file-fallback"} or not WRITE_API_KEY:
        return "local-demo"
    return "pilot-ready"


def build_capabilities(
    *,
    ready: bool,
    operating_mode: str,
    storage_meta: dict[str, Any],
    snapshot_health: dict[str, Any],
    readiness_checks: list[dict[str, Any]],
) -> dict[str, bool]:
    check_status = {check["key"]: check["status"] for check in readiness_checks}
    return {
        "can_sync_requirements_and_events": ready,
        "can_review_and_persist_feedback": storage_meta["feedback_storage_mode"] == "supabase",
        "can_persist_manual_intake": storage_meta["intake_storage_mode"] == "supabase",
        "can_serve_cached_dashboard": bool(snapshot_health.get("dashboard_analytics", {}).get("fresh")),
        "can_serve_cached_timeline": bool(snapshot_health.get("delivery_timeline", {}).get("fresh")),
        "can_protect_write_endpoints": bool(WRITE_API_KEY),
        "can_render_delivery_timeline": delivery_timeline_service is not None,
        "can_render_showcase_summaries": analytics_service.showcase_summaries_available(),
        "can_run_pilot": operating_mode in {"pilot-ready", "production-ready"},
        "can_launch_self_serve": operating_mode == "production-ready",
        "has_critical_readiness_failures": any(check["severity"] == "critical" and check["status"] != "healthy" for check in readiness_checks),
        "uses_local_demo_fallbacks": operating_mode == "local-demo"
        or storage_meta["feedback_storage_mode"] in {"memory", "file-fallback"}
        or storage_meta["intake_storage_mode"] != "supabase"
        or check_status.get("analytics_snapshots") != "healthy",
    }


def build_rollout_blockers(
    *,
    readiness_checks: list[dict[str, Any]],
    operating_mode: str,
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for check in readiness_checks:
        if check["status"] == "healthy":
            continue
        blockers.append(
            {
                "key": check["key"],
                "label": check["label"],
                "category": check["category"],
                "severity": check["severity"],
                "current": check["current"],
                "target": check["desired"],
                "action": check.get("action") or "No remediation recorded.",
            }
        )
    if operating_mode == "production-ready":
        return []
    return blockers


def classify_rollout_status(blockers: list[dict[str, str]]) -> str:
    if any(blocker.get("severity") == "critical" for blocker in blockers):
        return "blocked"
    if blockers:
        return "caution"
    return "ready"


def summarize_rollout_status(scope: str, status: str, blocker_count: int) -> str:
    if status == "ready":
        return f"{scope.capitalize()} rollout checks are satisfied."
    if status == "blocked":
        return f"{scope.capitalize()} rollout is blocked by {blocker_count} critical or high-impact readiness gaps."
    return f"{scope.capitalize()} rollout is possible with caution; {blocker_count} non-critical checks still need attention."


def rollout_next_actions(blockers: list[dict[str, str]]) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for blocker in blockers:
        action = str(blocker.get("action") or "").strip()
        if action and action not in seen:
            seen.add(action)
            actions.append(action)
    return actions[:5]


def build_rollout_assessment(
    *,
    readiness_checks: list[dict[str, Any]],
    capabilities: dict[str, bool],
) -> dict[str, dict[str, Any]]:
    blockers_by_key = {check["key"]: check for check in readiness_checks if check["status"] != "healthy"}

    pilot_keys = {
        "supabase_credentials",
        "supabase_endpoint",
        "allowed_origins",
        "optional_modules",
    }
    launch_keys = {
        "supabase_credentials",
        "supabase_endpoint",
        "allowed_origins",
        "write_auth",
        "feedback_storage",
        "intake_storage",
        "analytics_snapshots",
        "optional_modules",
    }

    pilot_blockers = [
        {
            "key": check["key"],
            "label": check["label"],
            "category": check["category"],
            "severity": check["severity"],
            "current": check["current"],
            "target": check["desired"],
            "action": check.get("action") or "No remediation recorded.",
        }
        for key, check in blockers_by_key.items()
        if key in pilot_keys and (check["severity"] == "critical" or key == "optional_modules")
    ]
    if not capabilities.get("can_run_pilot", False):
        pilot_blockers.extend(
            blocker
            for blocker in [
                {
                    "key": "pilot_capability",
                    "label": "Pilot capability",
                    "category": "optional-modules",
                    "severity": "critical",
                    "current": "Pilot rollout is not currently supported by capability checks.",
                    "target": "Backend should support pilot operations without critical readiness gaps.",
                    "action": "Resolve critical health blockers and verify timeline/summary modules remain available.",
                }
            ]
            if not any(existing["key"] == blocker["key"] for existing in pilot_blockers)
        )

    launch_blockers = [
        {
            "key": check["key"],
            "label": check["label"],
            "category": check["category"],
            "severity": check["severity"],
            "current": check["current"],
            "target": check["desired"],
            "action": check.get("action") or "No remediation recorded.",
        }
        for key, check in blockers_by_key.items()
        if key in launch_keys
    ]
    if not capabilities.get("can_launch_self_serve", False):
        launch_blockers.extend(
            blocker
            for blocker in [
                {
                    "key": "launch_capability",
                    "label": "Self-serve launch capability",
                    "category": "security",
                    "severity": "warning",
                    "current": "Self-serve launch expectations are not fully satisfied.",
                    "target": "Production-ready rollout state with protected writes and durable persistence.",
                    "action": "Resolve launch blockers so the backend can move from pilot-safe to production-ready.",
                }
            ]
            if not any(existing["key"] == blocker["key"] for existing in launch_blockers)
        )

    pilot_status = classify_rollout_status(pilot_blockers)
    launch_status = classify_rollout_status(launch_blockers)

    return {
        "pilot": {
            "status": pilot_status,
            "summary": summarize_rollout_status("pilot", pilot_status, len(pilot_blockers)),
            "blocker_count": len(pilot_blockers),
            "blockers": pilot_blockers,
            "next_actions": rollout_next_actions(pilot_blockers),
        },
        "launch": {
            "status": launch_status,
            "summary": summarize_rollout_status("launch", launch_status, len(launch_blockers)),
            "blocker_count": len(launch_blockers),
            "blockers": launch_blockers,
            "next_actions": rollout_next_actions(launch_blockers),
        },
    }


def build_readiness_overview(
    *,
    readiness_checks: list[dict[str, Any]],
    rollout_assessment: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    status_counts = {"healthy": 0, "warning": 0, "degraded": 0}
    category_counts: dict[str, int] = {}
    blocking_category_counts: dict[str, int] = {}

    for check in readiness_checks:
        status = str(check.get("status") or "warning")
        category = str(check.get("category") or "configuration")
        if status in status_counts:
            status_counts[status] += 1
        category_counts[category] = category_counts.get(category, 0) + 1
        if status != "healthy":
            blocking_category_counts[category] = blocking_category_counts.get(category, 0) + 1

    return {
        "status_counts": status_counts,
        "category_counts": category_counts,
        "blocking_category_counts": blocking_category_counts,
        "blocking_categories": sorted(blocking_category_counts.keys()),
        "pilot_blockers": int(rollout_assessment.get("pilot", {}).get("blocker_count") or 0),
        "launch_blockers": int(rollout_assessment.get("launch", {}).get("blocker_count") or 0),
    }


def build_setup_progress(
    *,
    configuration_audit: dict[str, Any],
    readiness_checks: list[dict[str, Any]],
    rollout_assessment: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    required_env = configuration_audit.get("required_env") or []
    table_dependencies = configuration_audit.get("table_dependencies") or []
    cached_views = configuration_audit.get("cached_views") or []

    env_ready = sum(1 for entry in required_env if entry.get("status") == "ready")
    migrations_ready = sum(1 for entry in table_dependencies if entry.get("available"))
    cached_ready = sum(1 for entry in cached_views if entry.get("fresh") and entry.get("valid_payload"))
    checks_healthy = sum(1 for entry in readiness_checks if entry.get("status") == "healthy")

    return {
        "required_env_ready": env_ready,
        "required_env_total": len(required_env),
        "migrations_ready": migrations_ready,
        "migrations_total": len(table_dependencies),
        "cached_views_ready": cached_ready,
        "cached_views_total": len(cached_views),
        "readiness_checks_healthy": checks_healthy,
        "readiness_checks_total": len(readiness_checks),
        "pilot_ready": rollout_assessment.get("pilot", {}).get("status") == "ready",
        "launch_ready": rollout_assessment.get("launch", {}).get("status") == "ready",
    }


def build_runtime_health() -> dict[str, Any]:
    degraded_reasons: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    missing_required_env = [
        name
        for name, value in (
            ("SUPABASE_URL", SUPABASE_URL),
            ("SUPABASE_SERVICE_KEY_OR_ANON_KEY", SUPABASE_API_KEY),
        )
        if not str(value or "").strip()
    ]
    storage_meta = build_storage_meta()
    snapshot_health = build_snapshot_health(storage_meta)
    optional_module_details = build_optional_module_details()
    invalid_supabase_url = bool(SUPABASE_URL) and not is_valid_origin(SUPABASE_URL)
    if ENV_CONFIG_WARNINGS:
        warnings.extend(ENV_CONFIG_WARNINGS)
        recommendations.append("Fix invalid numeric environment values so runtime behavior matches deployment intent.")
    if missing_required_env:
        degraded_reasons.append("missing_required_env")
        recommendations.append("Set SUPABASE_URL and SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY in backend/Req_codeMapping/.env.")
    if invalid_supabase_url:
        degraded_reasons.append("invalid_supabase_url")
        warnings.append("SUPABASE_URL is present but not a valid https base URL, so REST requests will fail.")
        recommendations.append("Correct SUPABASE_URL so it points to a valid Supabase project base URL.")

    if storage_meta["feedback_storage_mode"] == "file-fallback":
        warnings.append("Mapping feedback is using local file fallback instead of Supabase-backed persistence.")
        recommendations.append("Apply SQL migrations and set DEVHOUSE_DISABLE_FILE_FALLBACK=true for deployed environments.")

    if ANALYTICS_SNAPSHOTS_ENABLED and storage_meta["analytics_storage_mode"] != "supabase":
        warnings.append("Analytics snapshots are enabled but the analytics_snapshots table is unavailable, so live recomputation is still being used.")
        recommendations.append("Apply sql/create_analytics_snapshots.sql to enable cached analytics reads.")
    elif ANALYTICS_SNAPSHOTS_ENABLED:
        stale_or_missing_snapshots = [
            name for name, snapshot in snapshot_health.items() if snapshot.get("enabled") and not snapshot.get("fresh")
        ]
        if stale_or_missing_snapshots:
            warnings.append(
                "Some snapshot-backed views are missing or stale: " + ", ".join(stale_or_missing_snapshots) + "."
            )
            recommendations.append("Run sync or trigger a write path to refresh cached dashboard and timeline snapshots.")
        invalid_snapshots = [
            name for name, snapshot in snapshot_health.items() if snapshot.get("available") and not snapshot.get("valid_payload")
        ]
        if invalid_snapshots:
            warnings.append(
                "Some snapshot payloads are invalid and will be ignored: " + ", ".join(invalid_snapshots) + "."
            )
            recommendations.append("Refresh invalid snapshots by triggering sync or another mutating path after schema-compatible code is deployed.")

    if not WRITE_API_KEY:
        warnings.append("Write endpoints are currently unprotected because DEVHOUSE_WRITE_API_KEY is not set.")
        recommendations.append("Set DEVHOUSE_WRITE_API_KEY and VITE_WRITE_API_KEY before exposing write actions outside local demo mode.")

    invalid_origins = [origin for origin in dedupe_preserve_order(parse_origin_candidates()) if not is_valid_origin(origin)]
    if invalid_origins:
        degraded_reasons.append("invalid_allowed_origins")
        recommendations.append("Clean invalid ALLOWED_ORIGINS or FRONTEND_URL values so CORS behavior is predictable.")

    if storage_meta["intake_storage_mode"] != "supabase":
        warnings.append("Project intake records are not fully persisted to their dedicated Supabase table.")
        recommendations.append("Apply sql/create_project_intake_records.sql so manual intake records are persisted in Supabase.")

    readiness_checks = build_readiness_checks(
        missing_required_env=missing_required_env,
        storage_meta=storage_meta,
        invalid_origins=invalid_origins,
        invalid_supabase_url=invalid_supabase_url,
    )
    configuration_audit = build_configuration_audit(
        missing_required_env=missing_required_env,
        invalid_origins=invalid_origins,
        invalid_supabase_url=invalid_supabase_url,
        storage_meta=storage_meta,
        snapshot_health=snapshot_health,
    )
    ready = not degraded_reasons
    operating_mode = determine_operating_mode(
        ready=ready,
        missing_required_env=missing_required_env,
        storage_meta=storage_meta,
        invalid_origins=invalid_origins,
        invalid_supabase_url=invalid_supabase_url,
    )
    capabilities = build_capabilities(
        ready=ready,
        operating_mode=operating_mode,
        storage_meta=storage_meta,
        snapshot_health=snapshot_health,
        readiness_checks=readiness_checks,
    )
    rollout_blockers = build_rollout_blockers(
        readiness_checks=readiness_checks,
        operating_mode=operating_mode,
    )
    rollout_assessment = build_rollout_assessment(
        readiness_checks=readiness_checks,
        capabilities=capabilities,
    )
    readiness_overview = build_readiness_overview(
        readiness_checks=readiness_checks,
        rollout_assessment=rollout_assessment,
    )
    setup_progress = build_setup_progress(
        configuration_audit=configuration_audit,
        readiness_checks=readiness_checks,
        rollout_assessment=rollout_assessment,
    )
    return {
        "status": "ok" if ready else "degraded",
        "ready": ready,
        "operating_mode": operating_mode,
        "file_fallback_disabled": DISABLE_FILE_FALLBACK,
        "analytics_snapshots_enabled": ANALYTICS_SNAPSHOTS_ENABLED,
        "match_model": FASTEMBED_MODEL_NAME,
        "missing_required_env": missing_required_env,
        "allowed_origins": parse_allowed_origins(),
        "optional_modules": {
            name: bool(details.get("available"))
            for name, details in optional_module_details.items()
        },
        "optional_module_details": optional_module_details,
        "degraded_reasons": degraded_reasons,
        "warnings": warnings,
        "recommendations": dedupe_preserve_order(recommendations),
        "readiness_checks": readiness_checks,
        "configuration_audit": configuration_audit,
        "readiness_overview": readiness_overview,
        "setup_progress": setup_progress,
        "snapshot_health": snapshot_health,
        "capabilities": capabilities,
        "rollout_blockers": rollout_blockers,
        "rollout_assessment": rollout_assessment,
        "configuration": {
            "frontend_url": (os.getenv("FRONTEND_URL") or "http://localhost:5173").rstrip("/"),
            "supabase_url": SUPABASE_URL or "",
            "allowed_origins_count": len(parse_allowed_origins()),
            "invalid_origin_entries": invalid_origins,
            "invalid_supabase_url": invalid_supabase_url,
            "match_threshold": MATCH_THRESHOLD,
            "max_patch_chars": MAX_PATCH_CHARS,
            "max_commit_text_chars": MAX_COMMIT_TEXT_CHARS,
            "top_matches_per_sync": TOP_MATCHES_PER_SYNC,
            "storage_probe_ttl_seconds": STORAGE_PROBE_TTL_SECONDS,
            "analytics_snapshot_max_age_seconds": ANALYTICS_SNAPSHOT_MAX_AGE_SECONDS,
            "write_auth_required": bool(WRITE_API_KEY),
        },
        **storage_meta,
    }


def save_feedback_store(store: dict[str, dict[str, Any]]) -> None:
    FEEDBACK_STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def load_feedback_store_from_supabase() -> dict[str, dict[str, Any]]:
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        return {}
    try:
        rows = get_rows(
            MAPPING_FEEDBACK_TABLE,
            "commit_id,feedback_type,predicted_issue_id,corrected_issue_id,reviewed_by,reviewed_at",
            order="reviewed_at.desc",
            limit=500,
        )
        return {
            str(row.get("commit_id")): row
            for row in rows
            if str(row.get("commit_id") or "").strip()
        }
    except (HTTPException, ValueError):
        return {}


def supabase_feedback_available() -> bool:
    return probe_table_available(
        cache_key="feedback",
        table=MAPPING_FEEDBACK_TABLE,
        order_field="reviewed_at.desc",
        select_field="commit_id",
    )


def persist_feedback_record(record: dict[str, Any]) -> None:
    try:
        post_rows(MAPPING_FEEDBACK_TABLE, [record], upsert=True, on_conflict="commit_id")
    except HTTPException:
        if DISABLE_FILE_FALLBACK:
            raise HTTPException(status_code=503, detail="Supabase feedback storage is unavailable") from None
        store = load_feedback_store()
        store[str(record["commit_id"])] = record
        save_feedback_store(store)


def delete_feedback_record(commit_id: str) -> Optional[dict[str, Any]]:
    existing = load_feedback_store().get(commit_id)
    try:
        delete_rows(MAPPING_FEEDBACK_TABLE, f"commit_id=eq.{parse.quote(commit_id)}")
        return existing
    except HTTPException:
        if DISABLE_FILE_FALLBACK:
            raise HTTPException(status_code=503, detail="Supabase feedback storage is unavailable") from None
        store = load_feedback_store()
        removed = store.pop(commit_id, None)
        save_feedback_store(store)
        return removed


def persist_project_intake_record(record: dict[str, Any]) -> None:
    try:
        post_rows(PROJECT_INTAKE_TABLE, [record], upsert=True, on_conflict="issue_id")
    except HTTPException:
        return


def fetch_project_intake_records() -> list[dict[str, Any]]:
    if supabase_project_intake_available():
        try:
            return get_rows(
                PROJECT_INTAKE_TABLE,
                "issue_id,title,description,project_key,issue_type,priority,status,owner_email,reporter_email,timeline_start,timeline_end,source,submitted_at",
                order="submitted_at.desc",
                limit=100,
            )
        except HTTPException:
            pass

    fallback_records: list[dict[str, Any]] = []
    for issue in fetch_issues(order="jira_updated_at.desc"):
        if profile_source(issue) != "manual":
            continue
        fallback_records.append(
            {
                "issue_id": issue.get("issue_id"),
                "title": issue.get("title"),
                "description": issue.get("description"),
                "project_key": issue.get("project_key"),
                "issue_type": issue.get("issue_type"),
                "priority": issue.get("priority"),
                "status": issue.get("status"),
                "owner_email": issue.get("assignee_email"),
                "reporter_email": issue.get("reporter_email"),
                "timeline_start": issue.get("jira_created_at") or issue.get("created_at"),
                "timeline_end": issue.get("jira_updated_at") or issue.get("updated_at"),
                "source": profile_source(issue),
                "submitted_at": issue.get("created_at") or issue.get("updated_at"),
            }
        )
    return fallback_records[:100]


def supabase_project_intake_available() -> bool:
    return probe_table_available(
        cache_key="project_intake",
        table=PROJECT_INTAKE_TABLE,
        order_field="submitted_at.desc",
        select_field="issue_id",
    )


def analytics_snapshots_available() -> bool:
    if not ANALYTICS_SNAPSHOTS_ENABLED:
        return False
    return probe_table_available(
        cache_key="analytics_snapshots",
        table=ANALYTICS_SNAPSHOTS_TABLE,
        order_field="generated_at.desc",
        select_field="snapshot_key",
    )


def probe_table_available(cache_key: str, table: str, order_field: str, select_field: str) -> bool:
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        return False

    cached = _storage_probe_cache.get(cache_key)
    now = time.monotonic()
    if cached and now - cached[0] < STORAGE_PROBE_TTL_SECONDS:
        return cached[1]

    try:
        get_rows(
            table,
            select_field,
            order=order_field,
            limit=1,
        )
        result = True
    except HTTPException:
        result = False

    _storage_probe_cache[cache_key] = (now, result)
    return result


def iso_utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def generate_manual_issue_id(project_key: str) -> str:
    safe_project = normalize_issue_id(project_key or "MANUAL") or "MANUAL"
    return f"{safe_project}-{int(Path.cwd().stat().st_mtime_ns % 1_000_000)}"


def normalize_timestamp_input(value: Optional[str]) -> Optional[str]:
    raw = normalize_spaces(value or "")
    if not raw:
        return None
    try:
        from datetime import datetime, timezone

        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp value: {raw}") from exc


def profile_source(issue: dict[str, Any]) -> str:
    source = normalize_spaces(str(issue.get("source") or "")).lower()
    return source or "jira"


def build_dashboard_analytics(
    issues: list[dict[str, Any]],
    events: list[dict[str, Any]],
    sync_result: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return analytics_service.build_dashboard_analytics(
        issues,
        events,
        sync_result=sync_result,
        feedback_count=len(load_feedback_store()),
    )


def get_dashboard_analytics_payload(
    issues: list[dict[str, Any]],
    events: list[dict[str, Any]],
    sync_result: Optional[dict[str, Any]] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot = fetch_analytics_snapshot(DASHBOARD_ANALYTICS_SNAPSHOT_KEY)
    if snapshot:
        age_seconds = snapshot_age_seconds(snapshot.get("generated_at"))
        snapshot_payload = snapshot.get("payload") or {}
        if (
            age_seconds is not None
            and age_seconds <= ANALYTICS_SNAPSHOT_MAX_AGE_SECONDS
            and is_valid_dashboard_snapshot_payload(snapshot_payload)
        ):
            return (
                snapshot_payload,
                {
                    "analytics_source": "snapshot",
                    "analytics_generated_at": snapshot.get("generated_at"),
                    "analytics_snapshot_age_seconds": age_seconds,
                },
            )

    analytics_payload = build_dashboard_analytics(issues, events, sync_result)
    generated_at = iso_utc_now()
    persist_analytics_snapshot(
        DASHBOARD_ANALYTICS_SNAPSHOT_KEY,
        analytics_payload,
        generated_at=generated_at,
    )
    return (
        analytics_payload,
        {
            "analytics_source": "live",
            "analytics_generated_at": generated_at,
            "analytics_snapshot_age_seconds": 0,
        },
    )


def refresh_dashboard_analytics_snapshot(sync_result: Optional[dict[str, Any]] = None) -> None:
    if not analytics_snapshots_available():
        return
    try:
        issues = fetch_issues()
        events = fetch_events(order="timestamp.desc")
        effective_sync = sync_result or summarize_current_links(issues)
        analytics_payload = build_dashboard_analytics(issues, events, effective_sync)
        persist_analytics_snapshot(
            DASHBOARD_ANALYTICS_SNAPSHOT_KEY,
            analytics_payload,
            generated_at=iso_utc_now(),
        )
    except HTTPException:
        return


def get_delivery_timeline_payload() -> dict[str, Any]:
    snapshot = fetch_analytics_snapshot(DELIVERY_TIMELINE_SNAPSHOT_KEY)
    if snapshot:
        age_seconds = snapshot_age_seconds(snapshot.get("generated_at"))
        payload = snapshot.get("payload") or {}
        if (
            age_seconds is not None
            and age_seconds <= ANALYTICS_SNAPSHOT_MAX_AGE_SECONDS
            and is_valid_delivery_timeline_snapshot_payload(payload)
        ):
            meta = dict(payload.get("meta") or {})
            meta.update(
                {
                    "snapshot_source": "snapshot",
                    "snapshot_generated_at": snapshot.get("generated_at"),
                    "snapshot_age_seconds": age_seconds,
                }
            )
            payload["meta"] = meta
            return payload
    payload = get_delivery_timeline_payload_live()
    generated_at = payload.get("generated_at") or iso_utc_now()
    meta = dict(payload.get("meta") or {})
    meta.update(
        {
            "snapshot_source": "live",
            "snapshot_generated_at": generated_at,
            "snapshot_age_seconds": 0,
        }
    )
    payload["meta"] = meta
    persist_analytics_snapshot(DELIVERY_TIMELINE_SNAPSHOT_KEY, payload, generated_at=generated_at)
    return payload


def refresh_delivery_timeline_snapshot() -> None:
    if not analytics_snapshots_available():
        return
    try:
        payload = get_delivery_timeline_payload_live()
        generated_at = payload.get("generated_at") or iso_utc_now()
        persist_analytics_snapshot(DELIVERY_TIMELINE_SNAPSHOT_KEY, payload, generated_at=generated_at)
    except HTTPException:
        return


def get_delivery_timeline_payload_live() -> dict[str, Any]:
    issues = fetch_issues()
    events = fetch_delivery_timeline_events(order="timestamp.asc")
    
    # Enrich events with developer_canonical_id if attribution available
    if ATTRIBUTION_FEATURES_AVAILABLE and _identity_resolver:
        for event in events:
            author_email = event.get("author_email")
            developer_id = event.get("developer_id")
            
            # Try to resolve to canonical ID
            canonical_id = None
            if author_email:
                dev = _identity_resolver.get_developer_by_email(author_email)
                if dev:
                    canonical_id = dev.id
            
            if not canonical_id and developer_id:
                # Try by various source types
                for src_type in ["git", "github", "jira"]:
                    dev = _identity_resolver.get_developer_by_alias(src_type, developer_id)
                    if dev:
                        canonical_id = dev.id
                        break
            
            # Add canonical ID to event (in attribution sub-field for backward compatibility)
            if canonical_id:
                if "attribution" not in event:
                    event["attribution"] = {}
                event["attribution"]["developer_canonical_id"] = canonical_id
                event["attribution"]["identity_resolved"] = True
            else:
                if "attribution" not in event:
                    event["attribution"] = {}
                event["attribution"]["developer_canonical_id"] = None
                event["attribution"]["identity_resolved"] = False
    
    if delivery_timeline_service is None:
        return {
            "generated_at": iso_utc_now(),
            "summary": {
                "requirements_total": len(issues),
                "requirements_with_commits": len([issue for issue in issues if issue.get("commits")]),
                "requirements_with_prs": 0,
                "ci_passing": 0,
                "deployments_live": 0,
                "mocked_stage_count": 0,
                "attribution_enriched": ATTRIBUTION_FEATURES_AVAILABLE and _identity_resolver is not None,
            },
            "meta": {
                "real_data": "Requirements and linked commits are available.",
                "mocked_data": "Delivery timeline module is unavailable in this deployment.",
                "attribution": {
                    "available": ATTRIBUTION_FEATURES_AVAILABLE,
                    "identity_resolver_ready": _identity_resolver is not None,
                } if ATTRIBUTION_FEATURES_AVAILABLE else {"available": False},
            },
            "records": [],
        }
    return delivery_timeline_service.build_delivery_timeline_response(issues, events)


def refresh_cached_views(sync_result: Optional[dict[str, Any]] = None) -> None:
    refresh_dashboard_analytics_snapshot(sync_result=sync_result)
    refresh_delivery_timeline_snapshot()


def fetch_analytics_snapshot(snapshot_key: str) -> Optional[dict[str, Any]]:
    if not analytics_snapshots_available():
        return None
    try:
        rows = get_rows_filtered(
            ANALYTICS_SNAPSHOTS_TABLE,
            "snapshot_key,payload,generated_at",
            filters={"snapshot_key": f"eq.{snapshot_key}"},
            order="generated_at.desc",
            limit=1,
        )
    except HTTPException:
        return None
    if not rows:
        return None
    return rows[0]


def persist_analytics_snapshot(snapshot_key: str, payload: dict[str, Any], generated_at: Optional[str] = None) -> None:
    if not analytics_snapshots_available():
        return
    try:
        post_rows(
            ANALYTICS_SNAPSHOTS_TABLE,
            [
                {
                    "snapshot_key": snapshot_key,
                    "scope_type": "global",
                    "scope_id": "dashboard",
                    "payload": payload,
                    "generated_at": generated_at or iso_utc_now(),
                }
            ],
            upsert=True,
            on_conflict="snapshot_key",
        )
    except HTTPException:
        return


def snapshot_age_seconds(generated_at: Optional[str]) -> Optional[int]:
    generated_dt = parse_datetime(generated_at)
    if not generated_dt:
        return None
    now_dt = parse_datetime(iso_utc_now())
    if not now_dt:
        return None
    return max(0, int((now_dt - generated_dt).total_seconds()))


def is_valid_dashboard_snapshot_payload(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    required_sections = {"project_intake", "effort_estimates", "developer_metrics", "impact_summaries", "transparency", "knowledge_risks", "activity_log"}
    if not required_sections.issubset(set(payload.keys())):
        return False
    return True


def is_valid_delivery_timeline_snapshot_payload(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if not isinstance(payload.get("summary"), dict):
        return False
    if not isinstance(payload.get("records"), list):
        return False
    return True


def build_project_intake_profiles(
    issues: list[dict[str, Any]],
    event_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return analytics_service.build_project_intake_profiles(issues, event_map)


def build_effort_estimates(
    issues: list[dict[str, Any]],
    event_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return analytics_service.build_effort_estimates(issues, event_map)


def build_developer_metrics(
    events: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    linked_commit_ids: set[str],
) -> list[dict[str, Any]]:
    return analytics_service.build_developer_metrics(events, issues, linked_commit_ids)


def build_issue_impact_summaries(
    intake_profiles: list[dict[str, Any]],
    effort_estimates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return analytics_service.build_issue_impact_summaries(intake_profiles, effort_estimates)


def build_developer_impact_summaries(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return analytics_service.build_developer_impact_summaries(metrics)


def build_knowledge_risks(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return analytics_service.build_knowledge_risks(events)


def build_activity_log(events: list[dict[str, Any]]) -> dict[str, Any]:
    return analytics_service.build_activity_log(events)


def event_actor(event: dict[str, Any]) -> str:
    return analytics_service.event_actor(event)


def performance_trend(events: list[dict[str, Any]], latest_timestamp: Optional[Any]) -> str:
    return analytics_service.performance_trend(events, latest_timestamp)


def is_overtime_event(event: dict[str, Any]) -> bool:
    return analytics_service.is_overtime_event(event)


def parse_datetime(value: Any):
    return analytics_service.parse_datetime(value)


def average(values: list[float]) -> float:
    return analytics_service.average(values)


def to_number(value: Any) -> float:
    return analytics_service.to_number(value)


def percent(part: float, whole: float) -> float:
    return analytics_service.percent(part, whole)


def get_rows(table: str, select: str, order: Optional[str] = None, limit: Optional[int] = None) -> list[dict[str, Any]]:
    return storage_service.get_rows(
        BASE_REST_URL,
        DEFAULT_HEADERS,
        table,
        select,
        order=order,
        limit=limit,
    )


def get_rows_filtered(
    table: str,
    select: str,
    filters: Optional[dict[str, str]] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    return storage_service.get_rows_filtered(
        BASE_REST_URL,
        DEFAULT_HEADERS,
        table,
        select,
        filters=filters,
        order=order,
        limit=limit,
    )


def patch_row(table: str, filters: str, payload: dict[str, Any]) -> Any:
    return storage_service.patch_row(BASE_REST_URL, DEFAULT_HEADERS, table, filters, payload)


def post_rows(table: str, payload: list[dict[str, Any]], upsert: bool = False, on_conflict: Optional[str] = None) -> Any:
    return storage_service.post_rows(
        BASE_REST_URL,
        DEFAULT_HEADERS,
        table,
        payload,
        upsert=upsert,
        on_conflict=on_conflict,
    )


def delete_rows(table: str, filters: str) -> Any:
    return storage_service.delete_rows(BASE_REST_URL, DEFAULT_HEADERS, table, filters)


def request_json(method: str, url: str, payload: Optional[Any] = None, headers: Optional[dict[str, str]] = None) -> Any:
    return storage_service.request_json(method, url, DEFAULT_HEADERS, payload=payload, headers=headers)


def log_startup_diagnostics() -> None:
    global _startup_diagnostics_logged
    if _startup_diagnostics_logged:
        return
    runtime = build_runtime_health()
    print(
        "[STARTUP] Req_codeMapping "
        f"status={runtime['status']} "
        f"mode={runtime.get('operating_mode', 'unknown')} "
        f"supabase={runtime['supabase_configured']} "
        f"write_auth={runtime['write_auth_enabled']} "
        f"feedback_storage={runtime['feedback_storage_mode']} "
        f"intake_storage={runtime['intake_storage_mode']} "
        f"analytics_storage={runtime['analytics_storage_mode']}"
    )
    if runtime.get("degraded_reasons"):
        print(f"[STARTUP] degraded_reasons={', '.join(runtime['degraded_reasons'])}")
    if runtime.get("warnings"):
        print(f"[STARTUP] warnings={'; '.join(runtime['warnings'])}")
    if runtime.get("recommendations"):
        print(f"[STARTUP] recommendations={'; '.join(runtime['recommendations'])}")
    _startup_diagnostics_logged = True


log_startup_diagnostics()


# =============================================================================
# NOVELTY FEATURES API ENDPOINTS (Option A Implementation)
# Burnout Detection & Predictive Delivery
# =============================================================================

if NOVELTY_FEATURES_AVAILABLE:
    print("[STARTUP] Novelty features enabled: Burnout Detection, Predictive Delivery")
    
    # Initialize engines
    _burnout_detector = BurnoutDetector()
    _burnout_alert_manager = BurnoutAlertManager()
    _predictive_engine = PredictiveDeliveryEngine()
else:
    print("[STARTUP] Novelty features disabled (import failed)")
    _burnout_detector = None
    _burnout_alert_manager = None
    _predictive_engine = None


@app.get("/api/developers/{developer_id}/burnout-risk")
def get_developer_burnout_risk(
    developer_id: str,
    team_id: Optional[str] = None,
    x_developer_id: Optional[str] = Header(None)
):
    """
    Get burnout risk assessment for a developer.
    
    - Developers can only see their own data
    - Managers can see team members
    """
    if not NOVELTY_FEATURES_AVAILABLE or not _burnout_detector:
        raise HTTPException(status_code=503, detail="Burnout detection not available")
    
    # Security: Can only view own data (or manager can view team)
    if x_developer_id and x_developer_id != developer_id:
        # TODO: Add manager check
        raise HTTPException(status_code=403, detail="Can only view own burnout data")
    
    # Fetch activity data from storage
    # TODO: Implement actual data fetching from extension_events
    activity_data = []  # Placeholder
    
    # Calculate risk
    risk_score = _burnout_detector.calculate_risk(
        developer_id=developer_id,
        team_id=team_id or "",
        activity_data=activity_data,
        historical_scores=[]  # TODO: Fetch from burnout_risk_snapshots
    )
    
    return risk_score.to_dict()


@app.get("/api/teams/{team_id}/burnout-summary")
def get_team_burnout_summary(team_id: str):
    """
    Get privacy-preserving burnout summary for a team.
    
    Returns aggregated counts only (no individual scores exposed to team).
    """
    if not NOVELTY_FEATURES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Burnout detection not available")
    
    # TODO: Fetch latest snapshots for team members from Supabase
    # For now, return template
    return {
        "team_id": team_id,
        "distribution": {
            "low": 8,
            "moderate": 3,
            "high": 1,
            "critical": 0
        },
        "total_members": 12,
        "needing_attention_count": 1,
        "calculated_at": datetime.utcnow().isoformat(),
        "privacy_notice": "Individual scores not shown. Manager dashboard shows details."
    }


@app.post("/api/developers/{developer_id}/burnout-risk/acknowledge")
def acknowledge_burnout_alert(developer_id: str):
    """Developer acknowledges they saw the burnout warning."""
    if not NOVELTY_FEATURES_AVAILABLE or not _burnout_alert_manager:
        raise HTTPException(status_code=503, detail="Burnout detection not available")
    
    # TODO: Record acknowledgment in burnout_alerts table
    return {
        "developer_id": developer_id,
        "acknowledged_at": datetime.utcnow().isoformat(),
        "message": "Alert acknowledged. Consider discussing with your manager."
    }


@app.get("/api/requirements/{requirement_id}/delivery-prediction")
def get_delivery_prediction(
    requirement_id: str,
    project_id: Optional[str] = None
):
    """
    Get delivery prediction for a requirement from Supabase data.
    """
    if not NOVELTY_FEATURES_AVAILABLE or not _predictive_engine:
        raise HTTPException(status_code=503, detail="Predictive delivery not available")
    
    # Query requirement from Supabase using storage service
    try:
        # Fetch requirement details from Supabase
        req_query = f"eq.req_id={requirement_id}"
        requirements = storage_service.get_rows(
            BASE_REST_URL,
            DEFAULT_HEADERS,
            "requirements",
            "*",
        )
        
        # Filter manually since we can't easily do eq filter with get_rows
        requirement = None
        for r in requirements:
            if r.get("req_id") == requirement_id:
                requirement = r
                break
        
        if not requirement:
            raise HTTPException(status_code=404, detail=f"Requirement {requirement_id} not found")
        
        assigned_to = requirement.get("assigned_to", "")
        
        # Fetch developer activity for velocity calculation
        dev_activities = storage_service.get_rows(
            BASE_REST_URL,
            DEFAULT_HEADERS,
            "developer_activity",
            "*",
        )
        
        # Filter activities for assigned developer
        developer_activities = [a for a in dev_activities if a.get("developer_id") == assigned_to]
        
        # Calculate velocity metrics from actual data
        if developer_activities:
            total_commits = sum(a.get("commits", 0) for a in developer_activities)
            avg_commits_per_day = total_commits / len(developer_activities) if developer_activities else 0
            
            # Calculate burnout indicators from activity
            after_hours_count = sum(1 for a in developer_activities if a.get("is_after_hours"))
            weekend_count = sum(1 for a in developer_activities if a.get("is_weekend"))
            total_days = len(developer_activities)
            
            # Estimate burnout score based on patterns
            burnout_score = 0.0
            if total_days > 0:
                after_hours_ratio = after_hours_count / total_days
                weekend_ratio = weekend_count / total_days
                burnout_score = min(100, (after_hours_ratio * 40) + (weekend_ratio * 60))
            
            # Create developer velocity profile from real data
            sample_dev = DeveloperVelocity(
                developer_id=assigned_to,
                developer_name=assigned_to,
                avg_days_per_requirement=max(1.0, 8.0 / max(1, avg_commits_per_day)),
                completion_rate=0.8 if burnout_score < 50 else 0.5,
                current_workload=1,
                burnout_risk_score=burnout_score,
                module_familiarity={"default": 0.7},
                availability_score=1.0 if burnout_score < 60 else 0.6
            )
        else:
            # No activity data - assume ghost/idle developer (high risk)
            sample_dev = DeveloperVelocity(
                developer_id=assigned_to or "unknown",
                developer_name=assigned_to or "Unknown",
                avg_days_per_requirement=21.0,
                completion_rate=0.3,
                current_workload=0,
                burnout_risk_score=75.0,
                module_familiarity={"default": 0.3},
                availability_score=0.4
            )
        
        # Calculate target date
        target_date_str = requirement.get("target_date", "")
        if target_date_str:
            try:
                target_date = datetime.fromisoformat(target_date_str.replace('Z', '+00:00'))
            except:
                target_date = datetime.utcnow() + timedelta(days=14)
        else:
            target_date = datetime.utcnow() + timedelta(days=14)
        
        # Calculate complexity from story points
        story_points = requirement.get("story_points", 5) or 5
        complexity = min(10, max(1, story_points // 3))
        
        # Generate prediction with real data
        prediction = _predictive_engine.predict_delivery(
            requirement_id=requirement_id,
            requirement_title=requirement.get("title", "Unknown"),
            requirement_description=requirement.get("description", ""),
            requirement_complexity=complexity,
            target_date=target_date,
            assigned_developers=[sample_dev],
            similar_requirements_history=[],
            team_velocity_trend=0.0
        )
        
        return prediction.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching real data for prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate prediction: {str(e)}")


@app.get("/api/projects/{project_id}/at-risk-requirements")
def get_at_risk_requirements(
    project_id: str,
    threshold: int = 60
):
    """
    Get list of requirements at risk of missing deadlines.
    
    Query params:
    - threshold: Probability below which = at risk (default 60%)
    """
    if not NOVELTY_FEATURES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Predictive delivery not available")
    
    try:
        # Fetch all requirements from Supabase
        requirements = storage_service.get_rows(
            BASE_REST_URL,
            DEFAULT_HEADERS,
            "requirements",
            "*",
        )
        
        # Fetch developer activity to calculate velocity
        activities = storage_service.get_rows(
            BASE_REST_URL,
            DEFAULT_HEADERS,
            "developer_activity",
            "*",
        )
        
        at_risk = []
        for req in requirements:
            assigned_to = req.get("assigned_to", "")
            target_date_str = req.get("target_date", "")
            story_points = req.get("story_points", 5) or 5
            
            # Get developer activities for this requirement's assignee
            dev_activities = [a for a in activities if a.get("developer_id") == assigned_to]
            
            # Calculate metrics
            if dev_activities:
                total_commits = sum(a.get("commits", 0) for a in dev_activities)
                avg_commits_per_day = total_commits / len(dev_activities) if dev_activities else 0
                
                # Calculate burnout indicators
                after_hours_count = sum(1 for a in dev_activities if a.get("is_after_hours"))
                weekend_count = sum(1 for a in dev_activities if a.get("is_weekend"))
                
                burnout_score = min(100, (after_hours_count / len(dev_activities) * 40) + 
                                        (weekend_count / len(dev_activities) * 60)) if dev_activities else 0
                
                # Predict days needed
                predicted_days = max(1.0, story_points / max(1, avg_commits_per_day))
                
                # Calculate completion probability
                if burnout_score > 60:
                    probability = 25.0
                elif burnout_score > 40:
                    probability = 45.0
                else:
                    probability = 75.0
                
                # Check if overdue
                if target_date_str:
                    try:
                        target = datetime.fromisoformat(target_date_str.replace('Z', '+00:00'))
                        days_until = (target - datetime.now(timezone.utc)).days
                        if days_until < 0:
                            probability = max(0, probability - 40)  # Penalty for overdue
                            expected_delay = abs(days_until) + predicted_days
                        else:
                            expected_delay = max(0, predicted_days - days_until)
                    except:
                        expected_delay = predicted_days
                else:
                    expected_delay = predicted_days
                
                # Determine risk level
                if probability < 30:
                    risk_level = "critical"
                elif probability < 50:
                    risk_level = "high"
                elif probability < threshold:
                    risk_level = "moderate"
                else:
                    continue  # Skip - not at risk
                
                # Determine primary risk
                if burnout_score > 50:
                    primary_risk = "Developer showing burnout signs"
                elif expected_delay > 5:
                    primary_risk = "Tight timeline with unfamiliar module"
                else:
                    primary_risk = "High complexity with tight timeline"
                
                at_risk.append({
                    "id": req.get("req_id", "unknown"),
                    "title": req.get("title", "Unknown"),
                    "probability": probability,
                    "risk_level": risk_level,
                    "predicted_delay_days": round(expected_delay, 1),
                    "primary_risk": primary_risk
                })
        
        return {
            "project_id": project_id,
            "threshold": threshold,
            "count": len(at_risk),
            "requirements": at_risk,
            "calculated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Error fetching at-risk requirements: {e}")
        # Fallback to empty list instead of hardcoded data
        return {
            "project_id": project_id,
            "threshold": threshold,
            "count": 0,
            "requirements": [],
            "error": str(e),
            "calculated_at": datetime.utcnow().isoformat()
        }


@app.get("/api/novelty-features/status")
def get_novelty_features_status():
    """Get status of all novelty features."""
    return {
        "burnout_detection": {
            "available": NOVELTY_FEATURES_AVAILABLE and _burnout_detector is not None,
            "endpoints": [
                "/api/developers/{id}/burnout-risk",
                "/api/teams/{id}/burnout-summary"
            ]
        },
        "predictive_delivery": {
            "available": NOVELTY_FEATURES_AVAILABLE and _predictive_engine is not None,
            "endpoints": [
                "/api/requirements/{id}/delivery-prediction",
                "/api/projects/{id}/at-risk-requirements"
            ]
        },
        "configuration_required": [
            "Run SQL: backend/Req_codeMapping/sql/create_novelty_tables.sql",
            "Add DEVHOUSE_BURNOUT_ALERTS_ENABLED to .env",
            "Add DEVHOUSE_PREDICTIVE_DELIVERY_ENABLED to .env"
        ],
        "code_complexity": {
            "available": True,
            "endpoints": [
                "/api/commits/{commit_id}/complexity",
                "/api/repositories/{repo}/complexity-overview"
            ],
            "note": "Run locally: python run_complexity_analysis.py"
        }
    }


@app.get("/api/commits/{commit_id}/complexity")
def get_commit_complexity(commit_id: str):
    """
    Get code complexity analysis for a specific commit.
    
    Returns complexity metrics, risk scores, and architectural impact.
    """
    try:
        # Fetch from Supabase
        headers = DEFAULT_HEADERS.copy()
        if SUPABASE_API_KEY:
            headers["apikey"] = SUPABASE_API_KEY
            headers["Authorization"] = f"Bearer {SUPABASE_API_KEY}"
        
        # Get commit complexity analysis
        complexity_data = storage_service.get_rows(
            BASE_REST_URL,
            headers,
            "commit_complexity_analysis",
            "*",
            filters={"commit_id": f"eq.{commit_id}"}
        )
        
        if not complexity_data:
            return {
                "commit_id": commit_id,
                "analyzed": False,
                "message": "Complexity analysis not yet available. Run local analyzer.",
                "run_command": "python run_complexity_analysis.py"
            }
        
        analysis = complexity_data[0]
        
        # Get file-level metrics
        file_metrics = storage_service.get_rows(
            BASE_REST_URL,
            headers,
            "file_complexity_snapshots",
            "*",
            filters={"commit_id": f"eq.{commit_id}"}
        )
        
        return {
            "commit_id": commit_id,
            "analyzed": True,
            "repository_name": analysis.get("repository_name"),
            "author": analysis.get("author"),
            "timestamp": analysis.get("timestamp"),
            "files_changed": analysis.get("files_changed"),
            "complexity_summary": {
                "total_delta": analysis.get("total_complexity_delta"),
                "max_file_complexity": analysis.get("max_file_complexity"),
                "architectural_impact": analysis.get("architectural_impact"),
                "trend": analysis.get("complexity_trend")
            },
            "risk_assessment": {
                "level": "critical" if analysis.get("max_file_complexity", 0) > 70 
                         else "high" if analysis.get("max_file_complexity", 0) > 50
                         else "medium" if analysis.get("max_file_complexity", 0) > 30
                         else "low",
                "score": analysis.get("max_file_complexity"),
                "explanation": _get_risk_explanation(analysis)
            },
            "file_breakdown": [
                {
                    "file_path": fm.get("file_path"),
                    "language": fm.get("language"),
                    "lines_of_code": fm.get("lines_of_code"),
                    "cyclomatic_complexity": fm.get("cyclomatic_complexity"),
                    "cognitive_complexity": fm.get("cognitive_complexity"),
                    "function_count": fm.get("function_count"),
                    "risk_score": fm.get("risk_score"),
                    "dependencies": fm.get("dependencies", [])
                }
                for fm in (file_metrics or [])
            ],
            "calculated_at": analysis.get("calculated_at")
        }
        
    except Exception as e:
        print(f"Error fetching complexity: {e}")
        return {
            "commit_id": commit_id,
            "analyzed": False,
            "error": str(e),
            "message": "Run local analyzer: python run_complexity_analysis.py"
        }


@app.get("/api/repositories/{repo_name}/complexity-overview")
def get_repository_complexity_overview(repo_name: str):
    """
    Get complexity overview for a repository.
    
    Shows aggregate complexity trends and high-risk files.
    """
    try:
        headers = DEFAULT_HEADERS.copy()
        if SUPABASE_API_KEY:
            headers["apikey"] = SUPABASE_API_KEY
            headers["Authorization"] = f"Bearer {SUPABASE_API_KEY}"
        
        # Get repository overview from view
        overview_data = storage_service.get_rows(
            BASE_REST_URL,
            headers,
            "repository_complexity_overview",
            "*",
            filters={"repository_name": f"eq.{repo_name}"}
        )
        
        # Get high complexity commits
        high_complexity = storage_service.get_rows(
            BASE_REST_URL,
            headers,
            "high_complexity_commits",
            "*",
            filters={"repository_name": f"eq.{repo_name}"},
            limit=10
        )
        
        # Get developer trends
        developer_trends = storage_service.get_rows(
            BASE_REST_URL,
            headers,
            "developer_complexity_trends",
            "*",
            filters={"repository_name": f"eq.{repo_name}"},
            limit=10
        )
        
        if not overview_data:
            return {
                "repository": repo_name,
                "analyzed": False,
                "message": "No complexity data available. Run local analyzer.",
                "run_command": f"python run_complexity_analysis.py"
            }
        
        overview = overview_data[0]
        
        return {
            "repository": repo_name,
            "analyzed": True,
            "summary": {
                "total_commits_analyzed": overview.get("total_commits_analyzed"),
                "avg_max_complexity": round(overview.get("avg_max_complexity", 0), 2),
                "overall_max_complexity": overview.get("overall_max_complexity"),
                "critical_commits": overview.get("critical_commits"),
                "high_impact_commits": overview.get("high_impact_commits"),
                "complexity_increasing": overview.get("complexity_increasing"),
                "contributing_developers": overview.get("contributing_developers")
            },
            "health_score": _calculate_repo_health(overview),
            "recent_high_complexity": [
                {
                    "commit_id": hc.get("commit_id"),
                    "author": hc.get("author"),
                    "max_complexity": hc.get("max_file_complexity"),
                    "impact": hc.get("architectural_impact"),
                    "timestamp": hc.get("timestamp")
                }
                for hc in (high_complexity or [])
            ],
            "developer_trends": [
                {
                    "author": dt.get("author"),
                    "week": dt.get("week"),
                    "commits": dt.get("commit_count"),
                    "avg_complexity_delta": round(dt.get("avg_complexity_delta", 0), 2),
                    "high_impact_commits": dt.get("high_impact_commits")
                }
                for dt in (developer_trends or [])
            ],
            "recommendations": _generate_complexity_recommendations(overview, high_complexity or [])
        }
        
    except Exception as e:
        print(f"Error fetching repo complexity: {e}")
        return {
            "repository": repo_name,
            "analyzed": False,
            "error": str(e)
        }


def _get_risk_explanation(analysis: dict) -> str:
    """Generate human-readable risk explanation."""
    risk_score = analysis.get("max_file_complexity", 0)
    impact = analysis.get("architectural_impact", "low")
    trend = analysis.get("complexity_trend", "stable")
    
    if risk_score > 70 or impact == "critical":
        return f"CRITICAL: This commit introduces significant complexity ({risk_score:.0f} risk score). Code review strongly recommended."
    elif risk_score > 50 or impact == "high":
        return f"HIGH: Notable complexity increase ({risk_score:.0f} risk score). Review for architectural impact."
    elif risk_score > 30:
        return f"MODERATE: Some complexity added ({risk_score:.0f} risk score). Monitor for tech debt accumulation."
    else:
        return f"LOW: Complexity is within acceptable range ({risk_score:.0f} risk score). {trend} trend."


def _calculate_repo_health(overview: dict) -> dict:
    """Calculate repository health score from complexity data."""
    total_commits = overview.get("total_commits_analyzed", 1)
    critical = overview.get("critical_commits", 0)
    high = overview.get("high_impact_commits", 0)
    increasing = overview.get("complexity_increasing", 0)
    
    # Calculate scores (0-100)
    complexity_score = max(0, 100 - (critical * 10) - (high * 5))
    trend_score = max(0, 100 - (increasing / total_commits * 100) * 2)
    
    overall = (complexity_score + trend_score) / 2
    
    return {
        "overall": round(overall, 1),
        "complexity_score": round(complexity_score, 1),
        "trend_score": round(trend_score, 1),
        "status": "healthy" if overall > 75 else "concerning" if overall > 50 else "at-risk",
        "summary": f"Repository complexity is {'under control' if overall > 75 else 'increasing - review needed' if overall > 50 else 'critical - immediate action required'}"
    }


def _generate_complexity_recommendations(overview: dict, high_complexity: list) -> list:
    """Generate recommendations based on complexity data."""
    recommendations = []
    
    avg_complexity = overview.get("avg_max_complexity", 0)
    critical_count = overview.get("critical_commits", 0)
    high_count = overview.get("high_impact_commits", 0)
    increasing = overview.get("complexity_increasing", 0)
    
    if critical_count > 0:
        recommendations.append(f"🚨 {critical_count} critical complexity commits detected. Immediate code review required.")
    
    if high_count > 5:
        recommendations.append(f"⚠️ {high_count} high-impact commits. Consider refactoring sprints.")
    
    if avg_complexity > 40:
        recommendations.append(f"📊 Average complexity ({avg_complexity:.1f}) is above healthy threshold (30).")
    
    if increasing > 10:
        recommendations.append(f"📈 {increasing} commits show increasing complexity trend. Review coding standards.")
    
    if not recommendations:
        recommendations.append("✅ Complexity metrics are healthy. Continue monitoring.")
    
    return recommendations


# =============================================================================
# ATTRIBUTION & DEPENDENCY MAPPING API ENDPOINTS
# Identity Resolution, Work Item Attribution, Ownership Graph, Org Mapping
# =============================================================================

if ATTRIBUTION_FEATURES_AVAILABLE:
    print("[STARTUP] Attribution features enabled: Identity Resolution, Work Item Attribution, Ownership Graph")
    
    # Initialize attribution engines
    _identity_resolver = create_resolver() if create_resolver else None
    _attribution_engine = create_attribution_engine(_identity_resolver) if create_attribution_engine else None
    _ownership_graph = create_ownership_graph(_identity_resolver, _attribution_engine) if create_ownership_graph else None
    _dependency_graph = DependencyGraph([]) if DependencyGraph else None
    _org_mapper = create_org_mapper(_identity_resolver) if create_org_mapper else None
else:
    print("[STARTUP] Attribution features disabled (import failed)")
    _identity_resolver = None
    _attribution_engine = None
    _ownership_graph = None
    _dependency_graph = None
    _org_mapper = None


@app.get("/api/identity-resolution/status")
def get_identity_resolution_status():
    """
    Get identity resolver health and statistics.
    
    Returns stats about resolved identities, aliases, and pending collisions.
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE or not _identity_resolver:
        raise HTTPException(status_code=503, detail="Identity resolution not available")
    
    stats = _identity_resolver.get_stats()
    
    return {
        "status": "healthy" if stats["total_developers"] > 0 else "initializing",
        "stats": stats,
        "resolver_ready": True,
        "timestamp": iso_utc_now(),
    }


@app.get("/api/developers/{developer_id}/ownership")
def get_developer_ownership(developer_id: str):
    """
    Get ownership graph for a developer.
    
    Returns all code artifacts (files, modules, components) owned by this developer
    along with ownership strength and contribution metrics.
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE or not _ownership_graph:
        raise HTTPException(status_code=503, detail="Ownership graph not available")
    
    # Verify developer exists
    developer = _identity_resolver.get_developer(developer_id) if _identity_resolver else None
    if not developer:
        raise HTTPException(status_code=404, detail=f"Developer {developer_id} not found")
    
    # Get ownership graph data
    ownership_data = _ownership_graph.get_ownership_graph_for_developer(developer_id)
    
    return {
        "developer_id": developer_id,
        "developer_name": developer.primary_name if developer else None,
        "ownership": ownership_data,
        "generated_at": iso_utc_now(),
    }


@app.get("/api/developers/{developer_id}/attribution-history")
def get_developer_attribution_history(developer_id: str, limit: int = 100):
    """
    Get work items attributed to a developer.
    
    Returns list of commits, PRs, issues attributed to this developer
    with confidence scores and evidence.
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE or not _attribution_engine:
        raise HTTPException(status_code=503, detail="Attribution engine not available")
    
    # Verify developer exists
    developer = _identity_resolver.get_developer(developer_id) if _identity_resolver else None
    if not developer:
        raise HTTPException(status_code=404, detail=f"Developer {developer_id} not found")
    
    # Get attribution history
    decisions = _attribution_engine.get_attribution_history(developer_id)
    
    # Convert to response format
    history = []
    for decision in decisions[:limit]:
        history.append({
            "work_item_id": decision.work_item_id,
            "work_item_type": decision.work_item_type,
            "ownership_score": decision.ownership_score,
            "confidence": decision.confidence_score,
            "confidence_label": decision.confidence_label,
            "ambiguity_flag": decision.ambiguity_flag,
            "evidence_count": len(decision.evidence),
            "created_at": decision.created_at,
        })
    
    return {
        "developer_id": developer_id,
        "total_items": len(decisions),
        "returned_items": len(history),
        "history": history,
        "generated_at": iso_utc_now(),
    }


@app.get("/api/developers/{developer_id}/skills")
def get_developer_skills(developer_id: str, limit: int = 10):
    """
    Get inferred skill profile for a developer.
    
    Returns ranked skills with confidence scores and evidence commits.
    Skills are inferred from commit history (file paths, complexity, recency).
    """
    # Import skill profiler
    try:
        from skill_profile import SkillProfiler
    except ImportError:
        raise HTTPException(status_code=503, detail="Skill profiling not available")
    
    # Fetch developer's commits from extension_events
    try:
        # Query Supabase for developer commits
        response = supabase_client.table("extension_events")\
            .select("*")\
            .eq("developer_id", developer_id)\
            .order("timestamp", desc=True)\
            .limit(100)\
            .execute()
        
        commits = response.data if hasattr(response, 'data') else []
    except Exception as e:
        print(f"Error fetching commits for skill analysis: {e}")
        commits = []
    
    # Generate skill profile
    profiler = SkillProfiler(recency_half_life_days=30)
    skill_scores = profiler.profile_developer(
        developer_id=developer_id,
        commits=commits,
    )
    
    # Format response
    skills = []
    for score in skill_scores[:limit]:
        skills.append({
            "skill_tag": score.skill_tag,
            "skill_category": score.skill_category,
            "score": score.total_score,
            "confidence_score": score.confidence_score,
            "confidence_label": score.confidence_label,
            "frequency_score": score.frequency_score,
            "recency_score": score.recency_score,
            "complexity_score": score.complexity_score,
            "churn_score": score.churn_score,
            "evidence_count": score.evidence_count,
            "evidence_commits": [
                {
                    "commit_id": e.commit_id,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    "impact_score": e.impact_score,
                    "file_paths": e.file_paths,
                    "detection_method": e.detection_method,
                }
                for e in score.evidence_commits[:5]  # Top 5 evidence
            ],
            "last_commit_at": score.last_commit_at.isoformat() if score.last_commit_at else None,
        })
    
    return {
        "developer_id": developer_id,
        "skills": skills,
        "top_skill": skills[0]["skill_tag"] if skills else None,
        "skill_count": len(skills),
        "calculated_at": datetime.utcnow().isoformat(),
    }


@app.get("/api/managers/{manager_id}/team-attribution")
def get_manager_team_attribution(manager_id: str):
    """
    Get attribution rollup for a manager's team.
    
    Returns aggregated attribution summary for all teams managed by this manager.
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE or not _org_mapper or not _attribution_engine:
        raise HTTPException(status_code=503, detail="Team attribution not available")
    
    # Get all attribution decisions
    decisions = list(_attribution_engine._decisions.values())
    
    # Get manager rollup
    rollup = _org_mapper.get_manager_rollup(manager_id, decisions)
    
    return {
        "manager_id": manager_id,
        "rollup": rollup,
        "generated_at": iso_utc_now(),
    }


@app.get("/api/managers/{manager_id}/team-dependencies")
def get_manager_team_dependencies(manager_id: str):
    """
    Get cross-team dependencies for teams managed by this manager.
    
    Returns incoming and outgoing dependencies across team boundaries.
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE or not _org_mapper or not _dependency_graph:
        raise HTTPException(status_code=503, detail="Team dependencies not available")
    
    # Get managed teams
    managed_teams = _org_mapper.get_manager_teams(manager_id)
    
    # Build team assignments from managed teams
    team_assignments = {}
    for mapping in managed_teams:
        team_members = _org_mapper.get_team_members(mapping.team_id)
        for member in team_members:
            team_assignments[member.canonical_id] = mapping.team_id
    
    # Process events through dependency graph
    events = _ownership_graph.events if _ownership_graph else []
    _dependency_graph.events = events
    _dependency_graph.team_assignments = team_assignments
    _dependency_graph.process_events()
    
    # Get all dependencies
    all_deps = _dependency_graph.get_cross_team_dependencies()
    
    # Aggregate dependencies for all managed teams
    team_dependencies = []
    for mapping in managed_teams:
        team_id = mapping.team_id
        team_name = _org_mapper.get_team(team_id)
        # Filter deps for this team
        team_deps = [d for d in all_deps if d.source_team == team_id or d.target_team == team_id]
        team_dependencies.append({
            "team_id": team_id,
            "team_name": team_name.name if team_name else "Unknown",
            "dependencies": [d.dict() for d in team_deps],
        })
    
    return {
        "manager_id": manager_id,
        "managed_teams_count": len(managed_teams),
        "team_dependencies": team_dependencies,
        "generated_at": iso_utc_now(),
    }


@app.get("/api/repositories/{repo_name}/dependency-graph")
def get_repository_dependency_graph(repo_name: str):
    """
    Get cross-team dependency graph within a repository.
    
    Returns nodes (work items) and edges (dependencies) for visualization.
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE or not _ownership_graph:
        raise HTTPException(status_code=503, detail="Dependency graph not available")
    
    # Get dependency graph for repository
    graph_data = _ownership_graph.get_dependency_graph(repo_name=repo_name)
    
    return graph_data


@app.get("/api/issues/{issue_id}/attribution-trace")
def get_issue_attribution_trace(issue_id: str):
    """
    Get full attribution trace for an issue.
    
    Shows how the issue was mapped to commits and developers,
    including all evidence and confidence scores.
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE or not _attribution_engine:
        raise HTTPException(status_code=503, detail="Attribution trace not available")
    
    # Get attribution trace
    trace = _attribution_engine.get_attribution_trace(issue_id)
    
    if not trace:
        # Check if we can build a trace from existing data
        return {
            "issue_id": issue_id,
            "attributed": False,
            "message": "No attribution trace found for this issue. Issue may not be linked to commits yet.",
            "suggestion": "Use /api/sync to link commits to issues",
        }
    
    return {
        "issue_id": issue_id,
        "attributed": True,
        "trace": trace,
        "generated_at": iso_utc_now(),
    }


@app.get("/api/ambiguity-queue")
def get_ambiguity_queue(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
):
    """
    Get unresolved ambiguous mappings requiring manual review.
    
    Query params:
    - status: Filter by status (pending, in_review, resolved, escalated, deferred)
    - priority: Filter by priority (low, medium, high, critical)
    - limit: Maximum number of records to return
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE or not _attribution_engine:
        raise HTTPException(status_code=503, detail="Ambiguity queue not available")
    
    # Get ambiguity records
    records = _attribution_engine.get_ambiguity_queue(status=status)
    
    # Apply additional filters
    if priority:
        records = [r for r in records if r.priority == priority]
    
    # Convert to response format
    queue = []
    for record in records[:limit]:
        queue.append({
            "ambiguity_id": record.ambiguity_id,
            "work_item_id": record.work_item_id,
            "work_item_type": record.work_item_type,
            "ambiguity_type": record.ambiguity_type,
            "possible_canonical_ids": record.possible_canonical_ids,
            "source_identifiers": record.source_identifiers,
            "status": record.status,
            "priority": record.priority,
            "confidence": record.confidence_score,
            "evidence": record.evidence,
            "ambiguity_reasons": record.ambiguity_reasons,
            "assigned_reviewer": record.assigned_reviewer,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        })
    
    return {
        "total_ambiguities": len(records),
        "returned_count": len(queue),
        "queue": queue,
        "filters_applied": {
            "status": status,
            "priority": priority,
        },
        "generated_at": iso_utc_now(),
    }


class AmbiguityResolutionPayload(BaseModel):
    """Payload for resolving an ambiguity."""
    canonical_id: str
    resolution_notes: Optional[str] = None
    resolved_by: str = "system"


@app.post("/api/ambiguity-queue/{ambiguity_id}/resolve")
def resolve_ambiguity(
    ambiguity_id: str,
    payload: AmbiguityResolutionPayload,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
):
    """
    Manually resolve an ambiguous attribution.
    
    Requires write access. Assigns the work item to the specified developer.
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE or not _attribution_engine:
        raise HTTPException(status_code=503, detail="Ambiguity resolution not available")
    
    require_write_access(x_api_key, authorization)
    
    # Resolve the ambiguity
    success = _attribution_engine.resolve_ambiguity(
        ambiguity_id=ambiguity_id,
        canonical_id=payload.canonical_id,
        resolved_by=payload.resolved_by,
        resolution_notes=payload.resolution_notes,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Ambiguity {ambiguity_id} not found")
    
    return {
        "status": "resolved",
        "ambiguity_id": ambiguity_id,
        "resolved_to": payload.canonical_id,
        "resolved_by": payload.resolved_by,
        "resolved_at": iso_utc_now(),
    }


@app.get("/api/attribution/status")
def get_attribution_status():
    """
    Get overall attribution system status.
    
    Returns health and stats for all attribution engines.
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE:
        return {
            "available": False,
            "status": "disabled",
            "message": "Attribution features not available - import failed",
        }
    
    return {
        "available": True,
        "status": "healthy",
        "engines": {
            "identity_resolver": {
                "ready": _identity_resolver is not None,
                "stats": _identity_resolver.get_stats() if _identity_resolver else None,
            },
            "attribution_engine": {
                "ready": _attribution_engine is not None,
                "stats": _attribution_engine.get_stats() if _attribution_engine else None,
            },
            "ownership_graph": {
                "ready": _ownership_graph is not None,
                "stats": _ownership_graph.get_stats() if _ownership_graph else None,
            },
            "org_mapper": {
                "ready": _org_mapper is not None,
                "stats": _org_mapper.get_org_stats() if _org_mapper else None,
            },
        },
        "timestamp": iso_utc_now(),
    }


@app.get("/api/attribution/summary")
def get_attribution_summary():
    """
    Get high-level attribution summary across all work items and developers.
    
    Returns summary statistics including:
    - Total work items attributed
    - Confidence distribution (high/medium/low/ambiguous)
    - Unique developers identified
    - Cross-team dependencies count
    - Pending ambiguities requiring review
    """
    if not ATTRIBUTION_FEATURES_AVAILABLE or not _attribution_engine:
        raise HTTPException(status_code=503, detail="Attribution summary not available")
    
    # Get attribution stats
    engine_stats = _attribution_engine.get_stats() if hasattr(_attribution_engine, 'get_stats') else {}
    
    # Get identity stats
    identity_stats = _identity_resolver.get_stats() if _identity_resolver else {}
    
    # Get dependency summary if available
    dependency_summary = {}
    if _dependency_graph:
        try:
            dependency_summary = _dependency_graph.get_dependency_summary()
        except Exception:
            dependency_summary = {"error": "Could not compute dependency summary"}
    
    # Calculate confidence distribution
    decisions = list(_attribution_engine._decisions.values()) if hasattr(_attribution_engine, '_decisions') else []
    confidence_dist = {"high": 0, "medium": 0, "low": 0, "ambiguous": 0}
    for d in decisions:
        label = d.confidence_label if hasattr(d, 'confidence_label') else "unknown"
        if label in confidence_dist:
            confidence_dist[label] += 1
    
    # Get ambiguity queue count
    ambiguity_count = len(_attribution_engine.get_ambiguity_queue()) if hasattr(_attribution_engine, 'get_ambiguity_queue') else 0
    
    return {
        "summary": {
            "total_work_items_attributed": len(decisions),
            "unique_developers": identity_stats.get("total_developers", 0),
            "confidence_distribution": confidence_dist,
            "pending_ambiguities": ambiguity_count,
            "cross_team_dependencies": dependency_summary.get("cross_team_dependencies", 0),
            "shared_modules": dependency_summary.get("shared_modules", 0),
            "bottlenecks_total": dependency_summary.get("bottlenecks_total", 0),
            "requires_manager_attention": dependency_summary.get("requires_manager_attention", 0),
        },
        "assessment": dependency_summary.get("assessment", "No dependency data available"),
        "generated_at": iso_utc_now(),
    }
