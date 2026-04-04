# Feature Maturity Matrix

Use this matrix to describe the product honestly during evaluation and pilot conversations.

## Maturity classes

| Class | Meaning | Presentation rule |
| --- | --- | --- |
| Real | Direct record or explicit persisted state | Safe to present as observed system evidence |
| Inferred | Deterministic interpretation from linked activity | Present as interpreted, not directly observed |
| Heuristic | Best-effort score, ranking, or synthesized judgment | Present as directional, not authoritative |
| Fallback/Mock | Placeholder or continuity coverage when evidence is absent | Present as non-proof, demo continuity only |

## Feature matrix

| Surface | Typical class | Why |
| --- | --- | --- |
| Requirement rows in `req_code_mapping` | Real | Stored table-backed records |
| Extension event rows in `extension_events` | Real | Stored event records when uploads succeed |
| Feedback persistence | Real when Supabase-backed; fallback otherwise | Depends on `feedback_storage_mode` |
| Manual intake persistence | Real when Supabase-backed; weaker otherwise | Depends on `intake_storage_mode` |
| Connector-backed PR/CI/deploy stages | Real | Based on explicit connector/event fields |
| Inferred PR/CI/deploy stages | Inferred | Derived from linked activity and downstream evidence |
| Timeline rollups mixing connector and inferred stages | Mixed real and inferred | Needs provenance disclosed |
| Mocked stage continuity | Fallback/Mock | Placeholder only |
| Summary judgments | Inferred or heuristic | Derived from workload, freshness, continuity, and readiness logic |
| Impact, risk, and transparency scores | Heuristic | Useful directional signals, not direct source-of-truth records |
| Snapshot-backed dashboard reads | Real cached data | Still real, but freshness must be disclosed |
| **Identity resolution (canonical developers)** | **Inferred/Heuristic** | **Email/name matching with confidence scores; ambiguous cases flagged** |
| **Work-item attribution (commits/PRs/issues)** | **Inferred/Heuristic** | **Multiple signals weighted; confidence scored; manual review queue for ambiguous** |
| **Ownership graph (file/module ownership)** | **Inferred/Heuristic** | **Recency-weighted commit analysis; confidence varies by contribution density** |
| **Org mapping (teams/managers)** | **Real if directory-backed; Inferred otherwise** | **High confidence with HR system; lower when inferred from commit patterns** |
| **Dependency graph (cross-team edges)** | **Inferred/Heuristic** | **Detected from code overlap patterns; strength estimated from event frequency** |
| **Manager rollups** | **Derived** | **Computed from individual attributions; accuracy depends on underlying data quality** |

## Operator guidance

Before presenting a feature:

1. Identify its class.
2. Check whether storage mode changes that class.
3. Use the safer label if mixed.

Examples:

- call timeline stages `connector-backed` when they are explicit
- call summary statements `inferred` or `directional`
- call mocked stages `placeholder coverage`

## Attribution system guidance

The attribution system uses multiple inference layers with varying confidence:

| Attribution Feature | Maturity | When to disclose |
| --- | --- | --- |
| Identity resolution | Inferred/Heuristic | Always disclose confidence scores; flag ambiguous matches |
| Work-item attribution | Inferred/Heuristic | Present as "attributed to" with confidence label; explain evidence |
| Ownership calculation | Heuristic | Present as ownership "indicators"; not authoritative ownership |
| Dependency detection | Inferred | Present as "detected dependencies"; explain detection method |
| Manager rollups | Derived | Accuracy depends on org data quality; disclose when inferred |

### Confidence labels to use

- **High (≥0.8)**: Multiple corroborating sources, exact email match
- **Medium (0.5-0.8)**: Single strong source or multiple weak sources
- **Low (<0.5)**: Pattern-based inference, single weak signal
- **Ambiguous**: Multiple conflicting signals requiring manual review

### Required disclosures

When presenting attribution data:

1. **Always show confidence scores** - never hide them
2. **Explain the evidence** - what sources contributed to this attribution
3. **Flag ambiguous cases** - items in the manual review queue
4. **Disclose inference methods** - was this from commit history, HR data, or patterns?
5. **Acknowledge limitations** - attribution is directional, not absolute truth

## Cross-check docs

- [DATA_PROVENANCE.md](DATA_PROVENANCE.md)
- [PILOT_READINESS_CHECKLIST.md](PILOT_READINESS_CHECKLIST.md)
- [DEMO_OPERATOR_RUNBOOK.md](DEMO_OPERATOR_RUNBOOK.md)
- [ATTRIBUTION_SYSTEM.md](ATTRIBUTION_SYSTEM.md) - Full attribution system documentation
