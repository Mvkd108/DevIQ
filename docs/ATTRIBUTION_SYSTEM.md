# Attribution System Documentation

## Overview

The DevIQ Attribution System maps work items (commits, pull requests, issues) to canonical developer identities and provides cross-team dependency analysis. It uses **conservative inference with explicit confidence scoring** - never claiming certainty where only patterns exist.

---

## The Five Graphs

### 1. Identity Graph (`identity_resolution.py`)

**Purpose**: Unify developer identities across multiple source systems (git, GitHub, Jira, employee directory).

**Maturity Class**: **Inferred/Heuristic**

**How it works**:
- Email matching (highest confidence: 0.95)
- Name similarity + domain match (medium confidence: 0.7)
- Name-only similarity (low confidence: 0.4)
- Cross-source conflict detection lowers confidence
- Organizational conflicts (team/manager mismatch) flag as ambiguous

**Key Classes**:
```python
IdentityResolver          # Main resolution engine
CanonicalDeveloper        # Unified developer identity
IdentityAlias             # Source system mappings
IdentityMatch             # Potential matches with confidence
IdentityCollision         # Conflicts requiring manual review
```

**Confidence Scoring**:
| Match Type | Confidence | When Used |
|------------|------------|-----------|
| Exact email | 0.95 | Same email across systems |
| Name + domain | 0.70 | High name similarity, same domain |
| Name only | 0.40 | High name similarity only |
| Suspicious | 0.20 | Weak signal, needs review |
| Ambiguous | 0.00 | Conflicting signals |

**Truthfulness Notes**:
- Never auto-merges identities with conflicting team/manager assignments
- Exposes all evidence for every resolution
- Flags ambiguous cases for manual review instead of guessing
- Email aliases (john+tag@example.com) are normalized but tracked

---

### 2. Work-Item Attribution Graph (`work_item_resolution.py`)

**Purpose**: Attribute commits, PRs, and issues to canonical developers with evidence-based confidence.

**Maturity Class**: **Inferred/Heuristic**

**How it works**:
- Extracts evidence from multiple sources (git, GitHub, Jira)
- Applies weighted scoring based on evidence type
- Aggregates scores by canonical developer
- Flags ambiguous cases (multiple strong candidates)

**Evidence Weights**:
| Evidence Type | Weight | Confidence |
|---------------|--------|------------|
| Commit author | 1.0 | 0.95 |
| PR author | 0.9 | 0.90 |
| Code owner | 0.85 | 0.85 |
| Commit committer | 0.8 | 0.85 |
| PR approver | 0.7 | 0.70 |
| Jira assignee | 0.7 | 0.70 |
| PR merger | 0.5 | 0.70 |
| Jira reporter | 0.5 | 0.50 |
| File path pattern | 0.3 | 0.30 |
| Inferred from team | 0.2 | 0.40 |

**Attribution Decision Flow**:
1. Extract evidence from all available sources
2. Resolve source identifiers to canonical IDs
3. Calculate weighted scores per developer
4. Single clear winner (>1.5x next) → automatic attribution
5. Multiple strong candidates → flagged ambiguous
6. No valid candidates → unknown, queued for review

**Truthfulness Notes**:
- Disagreement between sources lowers confidence
- Cross-source agreement boosts confidence
- All decisions include full evidence trail
- Manual review queue for ambiguous cases

---

### 3. Ownership Graph (`ownership_graph.py`)

**Purpose**: Calculate file and module ownership based on contribution patterns.

**Maturity Class**: **Heuristic**

**How it works**:
- Recency-weighted contributions (exponential decay)
- Code churn volume analysis
- Contribution concentration (Gini coefficient)
- Bus factor calculation
- Review participation tracking

**Ownership Factors**:
| Factor | Weight | Description |
|--------|--------|-------------|
| Recency | 30% | More recent = higher weight |
| Volume (commits) | 25% | Number of commits |
| Volume (churn) | 25% | Lines of code changed |
| Review participation | 20% | Reviews given to others |

**Bus Factor**: Minimum number of developers needed to cover 70% of work.
- Bus factor = 1: Single point of failure
- Bus factor ≥ 3: Good distribution

**Risk Detection**:
- **High risk**: Primary owner ≥80% AND bus factor ≤1
- **Medium risk**: Primary owner ≥60% OR bus factor ≤1
- **Low risk**: Distributed ownership with bus factor ≥2

**Truthfulness Notes**:
- Ownership is calculated, not declared
- Recency decay means recent contributions weigh more
- Shared ownership reduces individual confidence scores
- No ownership data = high risk, not neutral

---

### 4. Org Mapping Graph (`org_mapping.py`)

**Purpose**: Map developers to teams and teams to managers with time-aware tracking.

**Maturity Class**: **Real (if directory-backed); Inferred (otherwise)**

**Confidence Rules**:
| Data Source | Confidence | Description |
|-------------|------------|-------------|
| Employee directory | 0.90 | Official HR system |
| Git/Jira consistent | 0.65 | Matching team mentions |
| Inferred from patterns | 0.40 | Commit pattern analysis |

**Time-Aware Support**:
- `effective_from` / `effective_to` for historical queries
- Current membership vs historical state
- Manager changes tracked over time

**Monorepo Safety**:
- Multiple teams can work in same repository
- Attribution based on developer membership, NOT repository membership
- Prevents incorrect rollup attribution

**Truthfulness Notes**:
- Low-confidence memberships flagged for review
- Historical queries supported for past state
- Manager rollups depend on underlying data quality

---

### 5. Dependency Graph (`dependency_graph.py`)

**Purpose**: Detect cross-team dependencies from code overlap patterns.

**Maturity Class**: **Inferred/Heuristic**

**How it works**:
- Detects when multiple teams touch same file/module
- Creates dependency edges between teams
- Identifies bottlenecks (high cross-team + low bus factor)
- Tracks handoff chains (ownership changes over time)

**Dependency Detection**:
| Strength | Events Required | Use Case |
|----------|-----------------|----------|
| Strong | >5 events each | Active collaboration |
| Moderate | 2-5 events each | Occasional overlap |
| Weak | <2 events | Minimal overlap |

**Bottleneck Score Formula**:
```
bottleneck_score = (cross_team_count × 10) / (bus_factor + 1)
```

| Score | Risk Level | Action |
|-------|------------|--------|
| ≥25 | Critical | Immediate attention |
| 15-25 | High | Review needed |
| 10-15 | Medium | Monitor |
| <10 | Low | Acceptable |

**Truthfulness Notes**:
- Dependencies are **detected**, not declared
- Based on commit activity patterns, not explicit dependency declarations
- Manager-to-manager edges inferred from team overlaps
- Shared modules flagged for attention, not labeled as problems

---

## Confidence Scoring Model

### Individual Confidence (0.0 - 1.0)

| Range | Label | Interpretation |
|-------|-------|----------------|
| 0.80 - 1.00 | High | Multiple corroborating sources or exact match |
| 0.50 - 0.79 | Medium | Single strong source or multiple weak |
| 0.20 - 0.49 | Low | Pattern-based inference |
| 0.00 - 0.19 | Suspicious | Weak signal, likely error |

### Confidence Factors

**Boosting confidence**:
- Multiple corroborating sources (+10%)
- High-confidence evidence count ≥2 (+5%)
- Exact email match (+15%)

**Reducing confidence**:
- Source disagreement (-10%)
- Highly concentrated ownership (-10%)
- Sparse contribution data (-20%)

### System-Wide Confidence Metrics

The system tracks:
- Total attributions by confidence level
- Ambiguous items requiring review
- Average confidence per developer
- Confidence trends over time

---

## Interpreting Ambiguity Flags

### Ambiguity Types

| Type | Cause | Resolution |
|------|-------|------------|
| Multiple contributors | Multiple developers with similar scores | Manual review or let highest win |
| Unknown author | No matching identity found | Add identity alias |
| Ambiguous alias | Multiple candidates for same identifier | Disambiguate sources |
| Team owned | No individual attribution possible | Assign to team lead |
| Automated commit | CI/bot commit | Flag as automated |
| Merge commit | Multiple parent commits | Attribute to merger |
| Identity conflict | Same email, different org contexts | Manual merge decision |

### Ambiguity Queue Workflow

1. **Detection**: System flags ambiguous case during attribution
2. **Queueing**: Added to ambiguity queue with priority (low/medium/high/critical)
3. **Review**: Manager/admin reviews evidence and possible candidates
4. **Resolution**: Manual assignment to canonical developer
5. **Learning**: Resolution improves future matching

### When Ambiguity is Expected

- New developers not yet in directory
- Contract workers with multiple email domains
- Teams with shared/service accounts
- Merge commits with multiple authors
- Cross-team collaboration on same work item

---

## Manual Review Workflow

### Ambiguity Queue API

```
GET /api/ambiguity-queue?status=pending&priority=high
POST /api/ambiguity-queue/{id}/resolve
```

### Resolution Options

1. **Assign to developer**: Specify canonical_id
2. **Mark as team-owned**: No individual attribution
3. **Flag as automated**: Bot/CI attribution
4. **Defer**: Decision postponed
5. **Escalate**: Requires higher authority

### Resolution Evidence

All resolutions require:
- `resolved_by`: Who made the decision
- `resolution_notes`: Why this decision
- `resolved_at`: Timestamp
- Previous state preserved for audit

---

## Monorepo Support

### Challenge

Multiple teams working in the same repository can lead to:
- Incorrect cross-team attribution
- Manager rollups attributing wrong work to teams
- Dependency detection noise

### Solution

**Developer-based attribution** (not repository-based):
- Work items attributed to developers
- Developers mapped to teams via org graph
- Team attributions derived from developer mappings
- Multiple teams in same repo handled correctly

### Example

```
Repo: /monorepo
├── Team A works on /monorepo/auth → Attributed to Team A
├── Team B works on /monorepo/payments → Attributed to Team B
└── Both touch /monorepo/shared → Cross-team dependency detected
```

### Shared Module Detection

When multiple teams touch the same module:
- Ownership shares calculated per team
- Bus factor computed across all contributors
- Risk level assessed (high/medium/low)
- Manager notification for critical shared modules

---

## API Endpoint Reference

### Identity Resolution

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/identity-resolution/status` | GET | Resolver health and stats |
| `/api/developers/{id}/ownership` | GET | Developer ownership graph |
| `/api/developers/{id}/attribution-history` | GET | Work items attributed to developer |

### Attribution

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/issues/{id}/attribution-trace` | GET | Full attribution evidence for issue |
| `/api/ambiguity-queue` | GET | List ambiguous cases |
| `/api/ambiguity-queue/{id}/resolve` | POST | Manually resolve ambiguity |
| `/api/attribution/status` | GET | Overall attribution system health |

### Manager Rollups

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/managers/{id}/team-attribution` | GET | Aggregated attribution for manager's teams |
| `/api/managers/{id}/team-dependencies` | GET | Cross-team dependencies for manager's teams |

### Dependency Graph

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/repositories/{repo}/dependency-graph` | GET | Cross-team dependencies in repository |

### Response Format Example

```json
{
  "work_item_id": "commit-abc123",
  "work_item_type": "commit",
  "attributed_to": "dev-000001",
  "confidence": 0.95,
  "confidence_label": "high",
  "evidence": [
    {
      "type": "commit_author",
      "source_system": "git",
      "source_identifier": "alice@example.com",
      "canonical_id": "dev-000001",
      "weight": 1.0,
      "confidence": 0.95
    }
  ],
  "ambiguity_flag": false,
  "manual_review_required": false
}
```

---

## Limitations

### What the System Cannot Do

1. **Prove identity**: It matches patterns, it doesn't verify identity
2. **Guarantee attribution**: Confidence scores acknowledge uncertainty
3. **See implicit dependencies**: Only detects dependencies from activity patterns
4. **Know intent**: Cannot distinguish intentional collaboration from accidental overlap
5. **Predict future**: Historical patterns may not reflect current state

### Known Edge Cases

| Scenario | Behavior | Recommendation |
|----------|----------|----------------|
| Same name, different people | Flagged ambiguous | Manual review required |
| Shared email (group accounts) | Low confidence | Create team attribution |
| Contractor with changing emails | Multiple aliases | Merge after identity resolution |
| Cherry-picked commits | Multiple attribution | Usually assign to committer |
| Rebased commits | Timestamp changes | Recency weighting affected |
| Fork contributions | Source confusion | Track upstream vs downstream |

### Accuracy Expectations

| Metric | Expected Accuracy | Notes |
|--------|-------------------|-------|
| Identity resolution | 90-95% | Higher with directory integration |
| Work-item attribution | 85-90% | Lower for ambiguous cases |
| Ownership calculation | 70-85% | Heuristic, not authoritative |
| Dependency detection | 60-75% | Pattern-based inference |
| Manager rollups | 80-90% | Depends on org data quality |

---

## Privacy and Security

### Row Level Security (RLS)

All attribution tables have RLS policies:

- **Developers**: Can only see their own data
- **Team members**: Can see team-level aggregates
- **Managers**: Can see their team members' data
- **Admins**: Can see all data
- **Service role**: Full access for system operations

### Opt-Out

Developers can opt out via `developer_wellness_settings.monitoring_opt_out`.

### Data Retention

- Attribution decisions: Kept for audit trail
- Ambiguity queue: Archived after resolution
- Identity aliases: Preserved for historical accuracy
- Dependency edges: Pruned if inactive > 1 year

---

## Related Documentation

- [FEATURE_MATURITY_MATRIX.md](FEATURE_MATURITY_MATRIX.md) - Truthfulness classifications
- [DATA_PROVENANCE.md](DATA_PROVENANCE.md) - Data source tracking
- [backend/Req_codeMapping/ATTRIBUTION_README.md](../backend/Req_codeMapping/ATTRIBUTION_README.md) - Quickstart guide
