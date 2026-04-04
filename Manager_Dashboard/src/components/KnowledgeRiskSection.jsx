function pillClass(prefix, value, fallback) {
  return `knowledge-risk-pill ${prefix}-${String(value || fallback).toLowerCase()}`;
}

function formatRecency(recencyDays) {
  if (recencyDays === null || recencyDays === undefined) {
    return "Untracked";
  }
  if (recencyDays <= 0) {
    return "Latest window";
  }
  if (recencyDays === 1) {
    return "1 day behind";
  }
  return `${recencyDays} days behind`;
}

function formatCoverage(value) {
  if (value === null || value === undefined) {
    return "0.000";
  }
  return Number(value).toFixed(3);
}

function formatBreakdown(item) {
  return `${item.score}/${item.max_score}`;
}

function titleize(value, fallback = "untracked") {
  return String(value || fallback)
    .split("_")
    .map((part) => (part ? `${part[0].toUpperCase()}${part.slice(1)}` : part))
    .join(" ");
}

function SummaryList({ title, items, emptyCopy }) {
  return (
    <div className="knowledge-risk-summary-list">
      <span>{title}</span>
      {items?.length ? (
        <div className="knowledge-risk-inline-list">
          {items.map((item, index) => {
            const normalized = typeof item === "string" ? { module: item } : item;
            return (
              <strong key={`${title}-${normalized.module}-${index}`}>
                {normalized.module}
                {normalized.recommended_backup_action ? (
                  <em>{` – ${normalized.recommended_backup_action}`}</em>
                ) : (
                  ""
                )}
              </strong>
            );
          })}
        </div>
      ) : (
        <p>{emptyCopy}</p>
      )}
    </div>
  );
}

function ActionCard({ label, item, emptyCopy }) {
  return (
    <article className="knowledge-risk-action-card">
      <span>{label}</span>
      {item ? (
        <>
          <div className="knowledge-risk-action-topline">
            <strong>{item.module}</strong>
            <div className="knowledge-risk-pill-row">
              <span className={pillClass("priority", item.mitigation_priority, "monitor")}>
                {titleize(item.mitigation_priority)}
              </span>
              <span className={pillClass("urgency", item.review_urgency, "routine")}>
                {titleize(item.review_urgency)}
              </span>
            </div>
          </div>
          <p>{item.manager_signal}</p>
          <div className="knowledge-risk-action-meta">
            <span>Stability: {titleize(item.ownership_stability)}</span>
            <span>Confidence: {titleize(item.continuity_confidence)}</span>
          </div>
          <strong className="knowledge-risk-action-next">{item.recommended_backup_action}</strong>
        </>
      ) : (
        <p>{emptyCopy}</p>
      )}
    </article>
  );
}

export default function KnowledgeRiskSection({ analytics, compact = false }) {
  const risks = analytics?.knowledge_risks ?? [];
  const model = analytics?.transparency?.knowledge_risk_model ?? [];
  const summary = analytics?.knowledge_risk_summary ?? {};

  if (!risks.length) {
    return <p className="empty-state">No subsystem ownership risk is visible in the current event window.</p>;
  }

  const counts = summary.counts ?? {};
  
  // Compact view: only show summary cards and top risks
  if (compact) {
    const topRisks = risks
      .filter(r => r.mitigation_priority === "urgent" || r.mitigation_priority === "critical")
      .slice(0, 3);
      
    return (
      <div className="knowledge-risk-compact">
        <div className="knowledge-risk-summary-grid compact">
          <article className="knowledge-risk-summary-card">
            <span>Urgent Reviews</span>
            <strong>{counts.urgent_reviews ?? 0}</strong>
          </article>
          <article className="knowledge-risk-summary-card">
            <span>Backup Needed</span>
            <strong>{counts.backup_needed ?? 0}</strong>
          </article>
          <article className="knowledge-risk-summary-card">
            <span>Stale Critical</span>
            <strong>{counts.stale_critical ?? 0}</strong>
          </article>
          <article className="knowledge-risk-summary-card">
            <span>Active Risks</span>
            <strong>{counts.active_right_now ?? 0}</strong>
          </article>
        </div>
        
        {topRisks.length > 0 && (
          <div className="top-risks-list">
            <h4>Top Priority Subsystems</h4>
            {topRisks.map(risk => (
              <div key={risk.module} className="top-risk-item">
                <div className="top-risk-header">
                  <strong>{risk.module}</strong>
                  <span className={`priority-pill ${risk.mitigation_priority}`}>
                    {risk.mitigation_priority}
                  </span>
                </div>
                <p className="top-risk-action">{risk.recommended_backup_action}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="knowledge-risk-section">
      <div className="knowledge-risk-decision-panel">
        <div>
          <p className="link-label">Decision Support</p>
          <h3>{summary.headline ?? "Ownership continuity actions are available."}</h3>
          <p className="knowledge-risk-readout">
            {summary.manager_readout ??
              "Use the cards below to decide where backup ownership and review coverage should move first."}
          </p>
        </div>
        <div className="knowledge-risk-summary-grid">
          <article className="knowledge-risk-summary-card">
            <span>Urgent Reviews</span>
            <strong>{counts.urgent_reviews ?? 0}</strong>
            <p>Subsystems that need immediate continuity review before more delivery moves through them.</p>
          </article>
          <article className="knowledge-risk-summary-card">
            <span>Backup Needed</span>
            <strong>{counts.backup_needed ?? 0}</strong>
            <p>Modules where ownership is fragile enough that a named backup should be visible to managers.</p>
          </article>
          <article className="knowledge-risk-summary-card">
            <span>Stale Critical</span>
            <strong>{counts.stale_critical ?? 0}</strong>
            <p>Subsystems with aging or stale tacit knowledge that still deserve manager attention.</p>
          </article>
          <article className="knowledge-risk-summary-card">
            <span>Active Now</span>
            <strong>{counts.active_right_now ?? 0}</strong>
            <p>Concentrated modules where the continuity gap is live in the current delivery window.</p>
          </article>
          <article className="knowledge-risk-summary-card">
            <span>Acceptable Spread</span>
            <strong>{counts.acceptable ?? 0}</strong>
            <p>Modules where concentration currently looks acceptable or shared rather than dangerous.</p>
          </article>
        </div>
      </div>

      <div className="knowledge-risk-action-grid">
        <ActionCard
          label="Highest-Priority Subsystem"
          item={summary.highest_priority_subsystem}
          emptyCopy="No elevated subsystem needs immediate mitigation."
        />
        <ActionCard
          label="Most Urgent Continuity Gap"
          item={summary.most_urgent_continuity_gap}
          emptyCopy="No urgent continuity gap is currently visible."
        />
      </div>

      <div className="knowledge-risk-rollup-grid">
        <SummaryList
          title="Modules Needing Backup Ownership"
          items={summary.modules_needing_backup_ownership}
          emptyCopy="No backup ownership gap is currently elevated."
        />
        <SummaryList
          title="Stale-But-Critical Areas"
          items={summary.stale_but_critical_areas}
          emptyCopy="No stale critical areas are currently visible."
        />
        <SummaryList
          title="Active Right Now"
          items={summary.active_right_now_risks}
          emptyCopy="No active hotspot is currently visible."
        />
        <SummaryList
          title="Acceptable Concentration"
          items={summary.acceptable_concentration_areas}
          emptyCopy="No modules currently read as clearly acceptable."
        />
      </div>

      <div className="knowledge-risk-model-note">
        <p>
          Ownership risk blends top-contributor concentration, backup depth, freshness, linked commit volume, and module breadth so managers can decide where to add backup coverage first.
        </p>
        {model.length ? (
          <div className="knowledge-risk-model-chip-row">
            {model.map((item) => (
              <span key={item.component} className="knowledge-risk-model-chip">
                <strong>{item.component}</strong>
                <span>{item.weight}%</span>
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <div className="knowledge-risk-table" role="table" aria-label="Subsystem continuity priorities">
        <div className="knowledge-risk-row knowledge-risk-head" role="row">
          <span role="columnheader">Subsystem</span>
          <span role="columnheader">Priority</span>
          <span role="columnheader">Urgency</span>
          <span role="columnheader">Activity</span>
          <span role="columnheader">Stability</span>
          <span role="columnheader">Confidence</span>
          <span role="columnheader">Top Owner</span>
          <span role="columnheader">Concentration</span>
        </div>
        {risks.map((risk) => (
          <div key={risk.module} className="knowledge-risk-row" role="row">
            <strong role="cell">{risk.module}</strong>
            <span role="cell">
              <span className={pillClass("priority", risk.mitigation_priority, "monitor")}>
                {titleize(risk.mitigation_priority)}
              </span>
            </span>
            <span role="cell">
              <span className={pillClass("urgency", risk.review_urgency, "routine")}>
                {titleize(risk.review_urgency)}
              </span>
            </span>
            <span role="cell">{formatRecency(risk.recency_days)}</span>
            <span role="cell">
              <span className={pillClass("stability", risk.ownership_stability, "watch")}>
                {titleize(risk.ownership_stability)}
              </span>
            </span>
            <span role="cell">
              <span className={pillClass("confidence", risk.continuity_confidence, "low")}>
                {titleize(risk.continuity_confidence)}
              </span>
            </span>
            <span role="cell">{risk.top_contributor}</span>
            <span role="cell">{risk.ownership_share_pct}%</span>
          </div>
        ))}
      </div>

      <div className="knowledge-risk-card-list">
        {risks.map((risk) => (
          <article key={`${risk.module}-detail`} className="knowledge-risk-card">
            <div className="knowledge-risk-card-header">
              <div>
                <p className="link-label">Subsystem Ownership</p>
                <h3>{risk.module}</h3>
              </div>
              <div className="knowledge-risk-pill-row">
                <span className={pillClass("priority", risk.mitigation_priority, "monitor")}>
                  {titleize(risk.mitigation_priority)}
                </span>
                <span className={pillClass("urgency", risk.review_urgency, "routine")}>
                  {titleize(risk.review_urgency)}
                </span>
                <span className={pillClass("profile", risk.continuity_profile, "shared_coverage")}>
                  {risk.continuity_label}
                </span>
                <span className={pillClass("severity", risk.severity, "low")}>
                  {titleize(risk.severity)}
                </span>
              </div>
            </div>

            <p className="knowledge-risk-summary">{risk.summary}</p>
            <p className="knowledge-risk-manager-summary">{risk.manager_summary}</p>

            <div className="knowledge-risk-action-callout">
              <span>Recommended backup action</span>
              <strong>{risk.recommended_backup_action}</strong>
              <p>{risk.continuity_guidance}</p>
            </div>

            <div className="knowledge-risk-metric-grid">
              <div>
                <span>Top contributor</span>
                <strong>{risk.top_contributor}</strong>
              </div>
              <div>
                <span>Concentration</span>
                <strong>{risk.ownership_share_pct}%</strong>
              </div>
              <div>
                <span>Backup gap</span>
                <strong>{risk.backup_gap_pct}%</strong>
              </div>
              <div>
                <span>Stability</span>
                <strong>{titleize(risk.ownership_stability)}</strong>
              </div>
              <div>
                <span>Confidence</span>
                <strong>{titleize(risk.continuity_confidence)}</strong>
              </div>
              <div>
                <span>Bus factor</span>
                <strong>{risk.bus_factor}</strong>
              </div>
              <div>
                <span>Linked requirements</span>
                <strong>{risk.linked_requirement_count}</strong>
              </div>
              <div>
                <span>Recency</span>
                <strong>{formatRecency(risk.recency_days)}</strong>
              </div>
              <div>
                <span>Coverage index</span>
                <strong>{formatCoverage(risk.coverage_index)}</strong>
              </div>
            </div>

            <div className="knowledge-risk-recent-activity">
              <span>Why it matters now</span>
              <p>{risk.recent_activity_summary}</p>
              <strong>{risk.why_it_matters}</strong>
            </div>

            <div className="knowledge-risk-owner-row">
              {(risk.top_contributors ?? []).map((contributor) => (
                <div key={`${risk.module}-${contributor.contributor}`} className="knowledge-risk-owner-chip">
                  <strong>{contributor.contributor}</strong>
                  <span>{contributor.ownership_share_pct}% share</span>
                </div>
              ))}
            </div>

            {(risk.dominant_risk_drivers ?? []).length ? (
              <div className="knowledge-risk-driver-row">
                {(risk.dominant_risk_drivers ?? []).map((driver) => (
                  <span key={`${risk.module}-${driver.label}`} className="knowledge-risk-driver-chip">
                    <strong>{driver.label}</strong>
                    <span>{driver.score}</span>
                  </span>
                ))}
              </div>
            ) : null}

            <div className="knowledge-risk-breakdown-grid">
              {(risk.risk_breakdown ?? []).map((item) => (
                <div key={`${risk.module}-${item.label}`} className="knowledge-risk-breakdown-card">
                  <div className="knowledge-risk-breakdown-header">
                    <span>{item.label}</span>
                    <strong>{formatBreakdown(item)}</strong>
                  </div>
                  <p>{item.detail}</p>
                </div>
              ))}
            </div>

            <div className="knowledge-risk-explanation">
              <span>Decision basis</span>
              <ul className="knowledge-risk-explanation-list">
                {(risk.explanation_points ?? []).map((point) => (
                  <li key={`${risk.module}-${point}`}>{point}</li>
                ))}
              </ul>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
