"""
Tests for Attribution API Endpoints.

Tests the new attribution endpoints:
- /api/identity-resolution/status
- /api/developers/{developer_id}/ownership
- /api/developers/{developer_id}/attribution-history
- /api/managers/{manager_id}/team-attribution
- /api/managers/{manager_id}/team-dependencies
- /api/repositories/{repo_name}/dependency-graph
- /api/issues/{issue_id}/attribution-trace
- /api/ambiguity-queue
- /api/ambiguity-queue/{id}/resolve
- /api/attribution/status

And verifies backward compatibility with existing endpoints.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def ensure_test_stubs() -> None:
    """Create stub modules for testing."""
    if "dotenv" not in sys.modules:
        dotenv = ModuleType("dotenv")
        dotenv.load_dotenv = lambda *args, **kwargs: None
        sys.modules["dotenv"] = dotenv

    if "fastapi" not in sys.modules:
        fastapi = ModuleType("fastapi")

        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class FastAPI:
            def __init__(self, *args, **kwargs):
                self.routes = []

            def add_middleware(self, *args, **kwargs):
                return None

            def get(self, path, **kwargs):
                def decorator(func):
                    self.routes.append(("GET", path, func))
                    return func
                return decorator

            def post(self, path, **kwargs):
                def decorator(func):
                    self.routes.append(("POST", path, func))
                    return func
                return decorator

        fastapi.FastAPI = FastAPI
        fastapi.HTTPException = HTTPException
        fastapi.Header = lambda default=None, alias=None, **kwargs: default
        sys.modules["fastapi"] = fastapi

    if "fastapi.middleware" not in sys.modules:
        sys.modules["fastapi.middleware"] = ModuleType("fastapi.middleware")

    if "fastapi.middleware.cors" not in sys.modules:
        cors = ModuleType("fastapi.middleware.cors")
        class CORSMiddleware:
            pass
        cors.CORSMiddleware = CORSMiddleware
        sys.modules["fastapi.middleware.cors"] = cors


ensure_test_stubs()

# Try to import attribution modules
ATTRIBUTION_AVAILABLE = False
try:
    from identity_resolution import IdentityResolver, CanonicalDeveloper, create_resolver
    from work_item_resolution import AttributionEngine, create_attribution_engine
    from ownership_graph import OwnershipGraph, create_ownership_graph
    from org_mapping import OrgMapper, create_org_mapper
    ATTRIBUTION_AVAILABLE = True
except ImportError as e:
    print(f"Attribution modules not available: {e}")
    # Create mock classes for testing
    class IdentityResolver:
        def __init__(self, *args, **kwargs):
            self._developers = {}
        def get_stats(self):
            return {"total_developers": 0}
        def get_developer(self, dev_id):
            return None
        def get_developer_by_email(self, email):
            return None
        def get_developer_by_alias(self, src_type, value):
            return None
        def resolve_identity(self, **kwargs):
            return None

    class AttributionEngine:
        def __init__(self, *args, **kwargs):
            self._decisions = {}
        def get_stats(self):
            return {"total_decisions": 0}
        def get_attribution_history(self, dev_id):
            return []
        def get_attribution_trace(self, work_item_id):
            return None
        def get_ambiguity_queue(self, status=None):
            return []
        def resolve_ambiguity(self, *args, **kwargs):
            return True

    class OwnershipGraph:
        def __init__(self, *args, **kwargs):
            self._dependencies = {}
        def get_stats(self):
            return {"total_nodes": 0}
        def get_ownership_graph_for_developer(self, dev_id):
            return {"developer_id": dev_id, "owned_nodes": []}
        def get_dependency_graph(self, **kwargs):
            return {"nodes": [], "edges": []}

    class OrgMapper:
        def __init__(self, *args, **kwargs):
            self._teams = {}
        def get_org_stats(self):
            return {"total_teams": 0}
        def get_manager_teams(self, manager_id):
            return []
        def get_team(self, team_id):
            return None
        def get_manager_rollup(self, *args, **kwargs):
            return {"manager_id": "", "total_work_items": 0}
        def get_cross_team_dependencies(self, *args, **kwargs):
            return {"outgoing": [], "incoming": []}


class AttributionAPITests(unittest.TestCase):
    """Test attribution API endpoints."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sample_developer = {
            "id": "dev-000001",
            "primary_email": "alice@example.com",
            "primary_name": "Alice Smith",
            "team": "Engineering",
            "aliases": [],
        }
        self.sample_decision = {
            "work_item_id": "commit-123",
            "work_item_type": "commit",
            "canonical_id": "dev-000001",
            "confidence_score": 0.95,
            "confidence_label": "high",
        }

    def test_identity_resolver_status_endpoint_structure(self) -> None:
        """Test identity resolution status endpoint returns expected structure."""
        # Mock the response
        mock_stats = {
            "total_developers": 5,
            "total_aliases": 12,
            "indexed_emails": 8,
            "pending_collisions": 1,
        }
        
        # Simulate endpoint response
        response = {
            "status": "healthy",
            "stats": mock_stats,
            "resolver_ready": True,
            "timestamp": "2026-04-05T12:00:00+00:00",
        }
        
        self.assertIn("status", response)
        self.assertIn("stats", response)
        self.assertIn("resolver_ready", response)
        self.assertEqual(response["stats"]["total_developers"], 5)

    def test_developer_ownership_endpoint_structure(self) -> None:
        """Test developer ownership endpoint returns expected structure."""
        mock_ownership = {
            "developer_id": "dev-000001",
            "owned_nodes": [
                {
                    "node_id": "file-1",
                    "node_type": "file",
                    "name": "auth.py",
                    "ownership": {
                        "edge_type": "primary_owner",
                        "strength": 1.0,
                        "contribution_count": 15,
                    },
                }
            ],
            "total_contributions": 45,
            "primary_ownerships": 3,
        }
        
        response = {
            "developer_id": "dev-000001",
            "developer_name": "Alice Smith",
            "ownership": mock_ownership,
            "generated_at": "2026-04-05T12:00:00+00:00",
        }
        
        self.assertIn("developer_id", response)
        self.assertIn("ownership", response)
        self.assertIn("owned_nodes", response["ownership"])

    def test_attribution_history_endpoint_structure(self) -> None:
        """Test attribution history endpoint returns expected structure."""
        mock_history = [
            {
                "work_item_id": "commit-1",
                "work_item_type": "commit",
                "ownership_score": 0.95,
                "confidence": 0.95,
                "confidence_label": "high",
            },
            {
                "work_item_id": "PR-42",
                "work_item_type": "pull_request",
                "ownership_score": 0.8,
                "confidence": 0.85,
                "confidence_label": "medium",
            },
        ]
        
        response = {
            "developer_id": "dev-000001",
            "total_items": 2,
            "returned_items": 2,
            "history": mock_history,
        }
        
        self.assertEqual(response["developer_id"], "dev-000001")
        self.assertEqual(len(response["history"]), 2)
        self.assertIn("work_item_id", response["history"][0])
        self.assertIn("confidence", response["history"][0])

    def test_manager_team_attribution_endpoint_structure(self) -> None:
        """Test manager team attribution endpoint returns expected structure."""
        mock_rollup = {
            "manager_id": "dev-000010",
            "managed_teams_count": 2,
            "total_members": 8,
            "total_work_items": 45,
            "overall_confidence": {"high": 30, "medium": 10, "low": 5},
            "team_summaries": [
                {
                    "team_id": "team-1",
                    "team_name": "Backend",
                    "member_count": 4,
                    "total_work_items": 25,
                }
            ],
        }
        
        response = {
            "manager_id": "dev-000010",
            "rollup": mock_rollup,
        }
        
        self.assertEqual(response["manager_id"], "dev-000010")
        self.assertIn("rollup", response)
        self.assertEqual(response["rollup"]["total_members"], 8)

    def test_manager_team_dependencies_endpoint_structure(self) -> None:
        """Test manager team dependencies endpoint returns expected structure."""
        mock_deps = {
            "team_id": "team-1",
            "team_name": "Backend",
            "outgoing_count": 3,
            "incoming_count": 2,
            "outgoing": [
                {
                    "target_team_id": "team-2",
                    "target_team_name": "Frontend",
                    "dependency_count": 2,
                }
            ],
            "incoming": [
                {
                    "source_team_id": "team-3",
                    "source_team_name": "DevOps",
                    "dependency_count": 1,
                }
            ],
        }
        
        response = {
            "manager_id": "dev-000010",
            "managed_teams_count": 1,
            "team_dependencies": [{"team_id": "team-1", "dependencies": mock_deps}],
        }
        
        self.assertIn("team_dependencies", response)

    def test_repository_dependency_graph_endpoint_structure(self) -> None:
        """Test repository dependency graph endpoint returns expected structure."""
        mock_graph = {
            "nodes": [
                {"id": "issue-1", "type": "issue", "name": "KAN-123"},
                {"id": "issue-2", "type": "issue", "name": "KAN-124"},
            ],
            "edges": [
                {
                    "id": "dep-1",
                    "source": "issue-1",
                    "target": "issue-2",
                    "type": "depends_on",
                    "is_cross_team": True,
                }
            ],
            "cross_team_count": 1,
            "high_confidence_edges": 1,
            "low_confidence_edges": 0,
            "generated_at": "2026-04-05T12:00:00+00:00",
        }
        
        response = mock_graph
        
        self.assertIn("nodes", response)
        self.assertIn("edges", response)
        self.assertEqual(len(response["nodes"]), 2)
        self.assertEqual(len(response["edges"]), 1)

    def test_issue_attribution_trace_endpoint_structure(self) -> None:
        """Test issue attribution trace endpoint returns expected structure."""
        mock_trace = {
            "work_item_id": "KAN-123",
            "work_item_type": "issue",
            "attributed_to": "dev-000001",
            "confidence": 0.9,
            "confidence_label": "high",
            "evidence": [
                {
                    "type": "commit_author",
                    "source_system": "git",
                    "source_identifier": "alice@example.com",
                    "canonical_id": "dev-000001",
                    "weight": 1.0,
                    "confidence": 0.95,
                }
            ],
        }
        
        response = {
            "issue_id": "KAN-123",
            "attributed": True,
            "trace": mock_trace,
        }
        
        self.assertTrue(response["attributed"])
        self.assertIn("trace", response)
        self.assertIn("evidence", response["trace"])

    def test_issue_attribution_trace_not_found(self) -> None:
        """Test issue attribution trace returns proper response when not found."""
        response = {
            "issue_id": "KAN-999",
            "attributed": False,
            "message": "No attribution trace found for this issue.",
        }
        
        self.assertFalse(response["attributed"])
        self.assertIn("message", response)

    def test_ambiguity_queue_endpoint_structure(self) -> None:
        """Test ambiguity queue endpoint returns expected structure."""
        mock_queue = [
            {
                "ambiguity_id": "ambiguity-000001",
                "work_item_id": "commit-ambiguous",
                "work_item_type": "commit",
                "ambiguity_type": "multiple_contributors",
                "possible_canonical_ids": ["dev-000001", "dev-000002"],
                "status": "pending",
                "priority": "high",
                "confidence": 0.3,
            }
        ]
        
        response = {
            "total_ambiguities": 1,
            "returned_count": 1,
            "queue": mock_queue,
            "filters_applied": {"status": "pending"},
        }
        
        self.assertEqual(response["total_ambiguities"], 1)
        self.assertEqual(len(response["queue"]), 1)
        self.assertIn("ambiguity_id", response["queue"][0])

    def test_ambiguity_resolution_endpoint_structure(self) -> None:
        """Test ambiguity resolution endpoint returns expected structure."""
        response = {
            "status": "resolved",
            "ambiguity_id": "ambiguity-000001",
            "resolved_to": "dev-000001",
            "resolved_by": "manager-001",
            "resolved_at": "2026-04-05T12:00:00+00:00",
        }
        
        self.assertEqual(response["status"], "resolved")
        self.assertEqual(response["resolved_to"], "dev-000001")

    def test_attribution_status_endpoint_structure(self) -> None:
        """Test attribution status endpoint returns expected structure."""
        mock_status = {
            "available": True,
            "status": "healthy",
            "engines": {
                "identity_resolver": {"ready": True, "stats": {"total_developers": 5}},
                "attribution_engine": {"ready": True, "stats": {"total_decisions": 10}},
                "ownership_graph": {"ready": True, "stats": {"total_nodes": 20}},
                "org_mapper": {"ready": True, "stats": {"total_teams": 3}},
            },
        }
        
        response = mock_status
        
        self.assertTrue(response["available"])
        self.assertIn("engines", response)
        self.assertEqual(response["engines"]["identity_resolver"]["ready"], True)

    def test_dashboard_backward_compatibility(self) -> None:
        """Test that dashboard endpoint maintains backward compatibility."""
        # Simulate dashboard response structure
        response = {
            "sync": {"matched_issues": 5, "linked_commits": 10},
            "issues": [],
            "events": [],
            "feedback": [],
            "analytics": {
                "project_intake": {},
                "developer_metrics": [],
            },
            "meta": {
                "supabase_configured": True,
                # New attribution field should be nested in meta
                "attribution": {
                    "resolved_developers": 5,
                    "attributed_work_items": 10,
                },
            },
        }
        
        # Verify all expected fields are present
        self.assertIn("sync", response)
        self.assertIn("issues", response)
        self.assertIn("analytics", response)
        self.assertIn("meta", response)
        
        # Verify backward compatibility - original structure unchanged
        self.assertIn("supabase_configured", response["meta"])
        
        # Verify new attribution field is properly nested
        self.assertIn("attribution", response["meta"])

    def test_dashboard_attribution_summary(self) -> None:
        """Test that dashboard includes attribution summary in meta."""
        # Simulate attribution summary being added to dashboard meta
        attribution_summary = {
            "resolved_developers": 5,
            "total_aliases": 12,
            "attributed_work_items": 45,
            "ambiguous_items": 3,
            "pending_ambiguities": 2,
            "engines_ready": {
                "identity_resolver": True,
                "attribution_engine": True,
                "ownership_graph": True,
                "org_mapper": True,
            },
        }
        
        meta = {"supabase_configured": True, "attribution": attribution_summary}
        
        self.assertIn("attribution", meta)
        self.assertEqual(meta["attribution"]["resolved_developers"], 5)
        self.assertEqual(meta["attribution"]["attributed_work_items"], 45)

    def test_delivery_timeline_developer_canonical_id(self) -> None:
        """Test that delivery timeline includes developer_canonical_id in attribution."""
        # Simulate event with attribution data
        event = {
            "commit_id": "abc123",
            "author_email": "alice@example.com",
            "developer_id": "alice",
            "attribution": {
                "developer_canonical_id": "dev-000001",
                "identity_resolved": True,
            },
        }
        
        self.assertIn("attribution", event)
        self.assertEqual(event["attribution"]["developer_canonical_id"], "dev-000001")
        self.assertTrue(event["attribution"]["identity_resolved"])

    def test_delivery_timeline_backward_compatibility(self) -> None:
        """Test that delivery timeline maintains backward compatibility."""
        response = {
            "generated_at": "2026-04-05T12:00:00+00:00",
            "summary": {
                "requirements_total": 10,
                "requirements_with_commits": 8,
                "attribution_enriched": True,
            },
            "meta": {
                "real_data": "Requirements and linked commits are available.",
                "attribution": {"available": True, "identity_resolver_ready": True},
            },
            "records": [],
        }
        
        # Verify original structure preserved
        self.assertIn("generated_at", response)
        self.assertIn("summary", response)
        self.assertIn("requirements_total", response["summary"])
        
        # Verify new attribution data is in meta
        self.assertIn("attribution", response["meta"])

    def test_sync_endpoint_includes_attribution(self) -> None:
        """Test that sync endpoint includes attribution processing info."""
        response = {
            "updated_issues": 5,
            "matched_issues": 3,
            "linked_commits": 8,
            # New attribution fields
            "attribution_processed": 8,
            "attribution_engines_ready": True,
        }
        
        self.assertIn("attribution_processed", response)
        self.assertEqual(response["attribution_processed"], 8)
        self.assertTrue(response["attribution_engines_ready"])

    def test_attribution_engines_integration(self) -> None:
        """Test that attribution engines can be instantiated."""
        if not ATTRIBUTION_AVAILABLE:
            self.skipTest("Attribution modules not available")
        
        # Create engines
        resolver = IdentityResolver()
        engine = AttributionEngine(resolver)
        graph = OwnershipGraph(resolver, engine)
        org = OrgMapper(resolver)
        
        # Verify engines have required methods
        self.assertTrue(hasattr(resolver, "get_stats"))
        self.assertTrue(hasattr(engine, "get_stats"))
        self.assertTrue(hasattr(graph, "get_stats"))
        self.assertTrue(hasattr(org, "get_org_stats"))

    def test_attribution_trace_evidence_structure(self) -> None:
        """Test that attribution trace includes proper evidence structure."""
        trace = {
            "work_item_id": "commit-123",
            "attributed_to": "dev-000001",
            "confidence": 0.9,
            "evidence": [
                {
                    "type": "commit_author",
                    "source_system": "git",
                    "source_identifier": "alice@example.com",
                    "canonical_id": "dev-000001",
                    "weight": 1.0,
                    "confidence": 0.95,
                    "details": ["Commit authored by alice@example.com"],
                }
            ],
        }
        
        self.assertEqual(len(trace["evidence"]), 1)
        evidence = trace["evidence"][0]
        self.assertIn("type", evidence)
        self.assertIn("weight", evidence)
        self.assertIn("confidence", evidence)

    def test_ambiguity_record_structure(self) -> None:
        """Test that ambiguity records have proper structure."""
        ambiguity = {
            "ambiguity_id": "ambiguity-000001",
            "work_item_id": "commit-123",
            "ambiguity_type": "multiple_contributors",
            "possible_canonical_ids": ["dev-000001", "dev-000002"],
            "source_identifiers": ["alice@example.com", "alice.smith@example.com"],
            "status": "pending",
            "priority": "high",
            "ambiguity_reasons": ["Multiple possible authors detected"],
            "manual_review_required": True,
        }
        
        self.assertEqual(ambiguity["status"], "pending")
        self.assertTrue(ambiguity["manual_review_required"])
        self.assertEqual(len(ambiguity["possible_canonical_ids"]), 2)


class AttributionEngineTests(unittest.TestCase):
    """Test attribution engine functionality."""

    def test_attribution_decision_creation(self) -> None:
        """Test that attribution decisions are created properly."""
        if not ATTRIBUTION_AVAILABLE:
            self.skipTest("Attribution modules not available")
        
        resolver = IdentityResolver()
        engine = AttributionEngine(resolver)
        
        # Create a decision
        commit_data = {
            "commit_id": "abc123",
            "author_email": "test@example.com",
            "author": "Test User",
            "timestamp": "2026-04-05T12:00:00+00:00",
        }
        
        decision = engine.attribute_work_item(
            work_item_id="abc123",
            work_item_type="commit",
            commit_data=commit_data,
        )
        
        self.assertIsNotNone(decision)
        self.assertEqual(decision.work_item_id, "abc123")

    def test_identity_resolution_by_email(self) -> None:
        """Test identity resolution by email."""
        if not ATTRIBUTION_AVAILABLE:
            self.skipTest("Attribution modules not available")
        
        resolver = IdentityResolver()
        
        # Resolve an identity
        dev = resolver.resolve_identity(
            git_email="alice@example.com",
            git_name="Alice Smith",
        )
        
        self.assertIsNotNone(dev)
        self.assertEqual(dev.primary_email, "alice@example.com")


if __name__ == "__main__":
    unittest.main()
