# Attribution System Quickstart Guide

This guide helps you get started with the DevIQ Attribution System for mapping work items to developers and analyzing cross-team dependencies.

---

## Prerequisites

- Python 3.9+
- Supabase account (for persistence)
- Git repository access (for commit history)
- Optional: Employee directory access (for org mapping)

---

## Installation

### 1. Install Dependencies

The attribution system is part of the main Req_codeMapping module. No additional installation needed.

### 2. Run Database Migrations

Execute the SQL schema in your Supabase SQL Editor:

```bash
# Via psql
psql $DATABASE_URL -f sql/create_attribution_tables.sql

# Or via Supabase SQL Editor
# Copy contents of sql/create_attribution_tables.sql and execute
```

This creates:
- `canonical_identities` - Unified developer records
- `identity_aliases` - Source system mappings
- `team_memberships` - Developer-to-team mappings
- `manager_mappings` - Team-to-manager mappings
- `attribution_decisions` - Work item attributions
- `ambiguity_queue` - Cases requiring manual review
- `ownership_evidence` - Weighted attribution factors
- `dependency_edges` - Cross-team dependencies

### 3. Configure Environment

Add to your `.env` file:

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Optional: Attribution-specific
BURNOUT_SLACK_WEBHOOK_URL=  # For alerts
BURNOUT_THRESHOLD_HIGH=55
BURNOUT_THRESHOLD_CRITICAL=75
```

---

## Quickstart

### Basic Usage

```python
from identity_resolution import IdentityResolver, create_resolver
from work_item_resolution import AttributionEngine, create_attribution_engine
from ownership_graph import OwnershipGraph, create_ownership_graph
from org_mapping import OrgMapper, create_org_mapper
from dependency_graph import DependencyGraph

# Initialize engines
resolver = create_resolver()
engine = create_attribution_engine(resolver)
ownership = create_ownership_graph(resolver, engine)
org_mapper = create_org_mapper()
dependency_graph = DependencyGraph(events=[], team_assignments={})
```

### 1. Identity Resolution

Resolve a developer from multiple sources:

```python
# Create a canonical developer
dev = resolver.resolve_identity(
    git_email="john.doe@company.com",
    git_name="John Doe",
    jira_assignee="john.doe",
    pr_author="jdoe123",
    employee_email="john.doe@company.com",
    team="Engineering",
    manager_email="jane.smith@company.com"
)

print(f"Canonical ID: {dev.id}")
print(f"Confidence: {dev.resolution_confidence}")
print(f"Ambiguous: {dev.is_ambiguous}")
```

### 2. Work Item Attribution

Attribute a commit to a developer:

```python
decision = engine.attribute_work_item(
    work_item_id="commit-abc123",
    work_item_type="commit",
    commit_data={
        "commit_id": "abc123",
        "author_email": "john.doe@company.com",
        "author": "John Doe",
        "timestamp": "2026-04-05T12:00:00+00:00"
    }
)

print(f"Attributed to: {decision.canonical_id}")
print(f"Confidence: {decision.confidence_score} ({decision.confidence_label})")
print(f"Ambiguity flag: {decision.ambiguity_flag}")
```

### 3. Ownership Calculation

Calculate ownership for a file:

```python
# Process events first
ownership.process_events(events=[
    {"author": "john.doe", "files_changed": [{"path": "auth.py"}]},
    # ... more events
])

# Get primary owner
developer, confidence = ownership.get_primary_owner("auth.py")
print(f"Owner: {developer.canonical_id} (confidence: {confidence})")

# Get all owners with shares
owners = ownership.get_all_owners("auth.py")
for owner in owners:
    print(f"{owner['developer_id']}: {owner['ownership_share_pct']}%")
```

### 4. Org Mapping

Add team membership:

```python
membership = org_mapper.add_team_membership(
    canonical_id="dev-000001",
    team_id="team-engineering",
    role="senior_developer",
    confidence_score=0.90,
    provenance="hr_system"
)
```

Add manager mapping:

```python
mapping = org_mapper.add_manager_mapping(
    team_id="team-engineering",
    manager_canonical_id="dev-000010",
    manager_role="engineering_manager",
    confidence_score=0.90,
    provenance="hr_system"
)
```

### 5. Dependency Detection

Detect cross-team dependencies:

```python
# Set up team assignments
team_assignments = {
    "alice": "team-backend",
    "bob": "team-frontend",
    "charlie": "team-backend"
}

# Process events
dependency_graph.process_events(events)
dependency_graph.team_assignments = team_assignments

# Detect cross-team overlaps
edges = dependency_graph.detect_cross_team_overlap("/repo", events, team_assignments)

for edge in edges:
    print(f"{edge.source_team_id} → {edge.target_team_id}: {edge.strength}")
```

---

## API Endpoints

### Health & Status

```bash
# Check attribution system status
GET /api/attribution/status

# Check identity resolver
GET /api/identity-resolution/status
```

### Developer Attribution

```bash
# Get developer ownership
GET /api/developers/{developer_id}/ownership

# Get attribution history
GET /api/developers/{developer_id}/attribution-history?limit=100
```

### Manager Rollups

```bash
# Get team attribution rollup
GET /api/managers/{manager_id}/team-attribution

# Get team dependencies
GET /api/managers/{manager_id}/team-dependencies
```

### Dependency Graph

```bash
# Get repository dependency graph
GET /api/repositories/{repo_name}/dependency-graph
```

### Attribution Tracing

```bash
# Get issue attribution trace
GET /api/issues/{issue_id}/attribution-trace
```

### Ambiguity Resolution

```bash
# Get ambiguity queue
GET /api/ambiguity-queue?status=pending&priority=high

# Resolve ambiguity (requires write access)
POST /api/ambiguity-queue/{ambiguity_id}/resolve
Content-Type: application/json

{
    "canonical_id": "dev-000001",
    "resolution_notes": "Verified via employee directory",
    "resolved_by": "admin-001"
}
```

---

## Configuration Options

### Attribution Engine Weights

Customize evidence weights (in `work_item_resolution.py`):

```python
engine = AttributionEngine(resolver)
engine.WEIGHTS["commit_author"] = 1.0      # Default: 1.0
engine.WEIGHTS["pr_author"] = 0.9           # Default: 0.9
engine.WEIGHTS["jira_assignee"] = 0.7      # Default: 0.7
```

### Ownership Calculation Weights

Customize ownership factors (in `ownership_graph.py`):

```python
weights = ownership.compute_ownership_weights(
    recency=0.8,
    commit_count=5,
    churn=100,
    review_participation=2
)
# Returns: {"recency": 0.24, "volume_commits": 0.125, ...}
```

### Confidence Thresholds

Adjust confidence thresholds:

```python
# In identity_resolution.py
MatchConfidence.EXACT = 0.95    # Exact email match
MatchConfidence.HIGH = 0.85     # Multiple strong signals
MatchConfidence.MEDIUM = 0.70   # Name + domain
MatchConfidence.LOW = 0.40      # Name-only
MatchConfidence.SUSPICIOUS = 0.20  # Weak signal
MatchConfidence.AMBIGUOUS = 0.00   # Conflicting
```

---

## Manual Review Workflow

### When Manual Review is Required

1. **Ambiguous matches**: Multiple developers with similar scores
2. **Unknown authors**: No matching identity found
3. **Conflicting signals**: Email matches but name differs significantly
4. **Shared ownership**: Multiple teams touching same work item

### Review Process

```python
# Get ambiguity queue
queue = engine.get_ambiguity_queue(status="pending")

for ambiguity in queue:
    print(f"{ambiguity.ambiguity_id}: {ambiguity.work_item_id}")
    print(f"Possible: {ambiguity.possible_canonical_ids}")
    print(f"Reasons: {ambiguity.ambiguity_reasons}")

# Resolve an ambiguity
engine.resolve_ambiguity(
    ambiguity_id="ambiguity-000001",
    canonical_id="dev-000001",
    resolved_by="manager-001",
    resolution_notes="Verified via HR system"
)
```

---

## Monorepo Support

### Handling Multiple Teams in Same Repository

The system correctly handles monorepos by attributing to **developers** first, then deriving team attribution:

```python
# 1. Attribute work items to developers
decision = engine.attribute_work_item(...)

# 2. Map developers to teams
memberships = org_mapper.map_developer_to_teams(
    canonical_id=decision.canonical_id,
    active_only=True
)

# 3. Team attribution derived from developer membership
for membership in memberships:
    print(f"Team: {membership.team_id} (confidence: {membership.confidence_score})")
```

### Shared Module Detection

```python
# Detect modules touched by multiple teams
report = dependency_graph.identify_shared_modules("/monorepo")

for module in report["shared_modules"]:
    print(f"{module['module']}: {module['team_count']} teams")
    print(f"  Risk: {module['risk_level']}")
    print(f"  Bus factor: {module['bus_factor']}")
```

---

## SQL Views for Common Queries

The migration creates helpful views:

```sql
-- Current active developers
SELECT * FROM current_developers;

-- Current team memberships
SELECT * FROM current_team_members;

-- Pending ambiguities
SELECT * FROM pending_ambiguities;

-- Cross-team dependencies
SELECT * FROM cross_team_dependencies;

-- Attribution summary by developer
SELECT * FROM developer_attribution_summary;

-- Team dependency summary
SELECT * FROM team_dependency_summary;
```

---

## Troubleshooting

### No Attributions Being Created

1. Check if events are being processed:
```python
stats = engine.get_stats()
print(f"Total decisions: {stats['total_decisions']}")
```

2. Verify identity resolution:
```python
stats = resolver.get_stats()
print(f"Total developers: {stats['total_developers']}")
print(f"Pending collisions: {stats['pending_collisions']}")
```

### High Ambiguity Rate

1. Check identity alias coverage:
```python
stats = resolver.get_stats()
print(f"Total aliases: {stats['total_aliases']}")
print(f"Ambiguous developers: {stats['ambiguous_developers']}")
```

2. Add missing aliases:
```python
resolver.add_alias(
    canonical_id="dev-000001",
    source_type="github",
    source_value="john.doe.alt",
    confidence=0.95,
    evidence=["Verified via email confirmation"]
)
```

### Team Mappings Not Working

1. Verify team memberships exist:
```python
memberships = org_mapper.map_developer_to_teams("dev-000001")
print(f"Found {len(memberships)} memberships")
```

2. Check manager mappings:
```python
manager = org_mapper.map_team_to_manager("team-engineering")
print(f"Manager: {manager.manager_canonical_id if manager else 'None'}")
```

---

## Testing

Run attribution tests:

```bash
# All attribution tests
pytest tests/test_attribution_api.py -v

# Identity resolution tests
pytest tests/test_identity_resolution.py -v

# Ownership and dependency tests
pytest tests/test_ownership_dependency.py -v

# Org mapping tests
pytest tests/test_org_mapping.py -v
```

---

## Privacy and Security

### Row Level Security

All tables have RLS policies. Ensure your Supabase client sets:

```python
# Set current user for RLS
supabase.rpc('set_claim', {'claim': 'app.current_user_id', 'value': 'dev-000001'})

# For service operations
supabase.rpc('set_claim', {'claim': 'app.is_service_role', 'value': 'true'})
```

### Opt-Out

Developers can opt out via:
```sql
UPDATE developer_wellness_settings
SET monitoring_opt_out = true
WHERE canonical_id = 'dev-000001';
```

---

## Further Documentation

- [Full Attribution System Docs](../../docs/ATTRIBUTION_SYSTEM.md)
- [Feature Maturity Matrix](../../docs/FEATURE_MATURITY_MATRIX.md)
- [SQL Schema](sql/create_attribution_tables.sql)

---

## Support

For issues or questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review test files for usage examples
- Contact: devhouse26-team@example.com
