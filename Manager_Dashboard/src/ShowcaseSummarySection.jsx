function ShowcaseSummarySection({ analytics }) {
  const showcase = analytics?.showcase_summaries;

  if (!showcase) {
    return null;
  }

  return (
    <section className="section-block showcase-section" id="showcase">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Launchable Summaries</p>
          <h2>Readable engineering reviews for developers, managers, and issue owners</h2>
        </div>
      </div>

      <div className="showcase-stack">
        <section className="panel showcase-evidence-guide">
          <div className="panel-header">
            <h3>How To Read These Summaries</h3>
          </div>
          <div className="showcase-guide-grid">
            <GuideCard
              label={showcase.meta?.section_labels?.observed ?? "Observed Facts"}
              detail={
                showcase.meta?.section_descriptions?.observed ??
                "Facts are pulled directly from linked issues, commits, telemetry, and delivery-stage records."
              }
              tone="fact"
            />
            <GuideCard
              label={showcase.meta?.section_labels?.inferred ?? "Inferred Judgments"}
              detail={
                showcase.meta?.section_descriptions?.inferred ??
                "Judgments are deterministic interpretations of workload, freshness, continuity risk, and delivery readiness."
              }
              tone="judgment"
            />
          </div>
        </section>

        <section className="panel showcase-overview-panel">
          <div className="showcase-overview-copy">
            <p className="showcase-eyebrow">Portfolio overview</p>
            <h3>{showcase.portfolio_overview?.headline ?? "Summary unavailable"}</h3>
            <div className="showcase-meta-row">
              <MetaPill label="Confidence" value={showcase.portfolio_overview?.confidence ?? "medium"} tone={showcase.portfolio_overview?.confidence} />
              <MetaPill
                label="Risk"
                value={showcase.portfolio_overview?.risk_level ?? "low"}
                tone={riskTone(showcase.portfolio_overview?.risk_level)}
              />
              <MetaPill
                label="Inference"
                value={showcase.portfolio_overview?.inference_level ?? "high"}
                tone={inferenceTone(showcase.portfolio_overview?.inference_level)}
              />
              <MetaPill
                label="Evidence"
                value={formatEventCount(showcase.portfolio_overview?.evidence_count)}
                tone="neutral"
              />
              <MetaPill
                label="Freshness"
                value={showcase.portfolio_overview?.freshness_level ?? "watch"}
                tone={showcase.portfolio_overview?.freshness_level ?? "watch"}
              />
              <MetaPill
                label="Action"
                value={showcase.portfolio_overview?.action_priority ?? "watch"}
                tone={actionTone(showcase.portfolio_overview?.action_priority)}
              />
            </div>
            <div className="showcase-summary-brief">
              <span className="showcase-summary-label">Executive summary</span>
              <p className="showcase-summary-copy">
                {showcase.portfolio_overview?.executive_summary ?? showcase.portfolio_overview?.headline ?? "Summary unavailable"}
              </p>
            </div>
            <div className="showcase-summary-brief secondary">
              <span className="showcase-summary-label">Weekly takeaway</span>
              <p className="showcase-summary-copy">{showcase.portfolio_overview?.summary ?? "Weekly summary unavailable."}</p>
            </div>
            <SignalNote label="Freshness" value={showcase.portfolio_overview?.freshness_note} tone="neutral" />
            <SignalNote label="Risk signal" value={showcase.portfolio_overview?.risk_signal} tone="risk" />
            <SignalNote label="Uncertainty" value={showcase.portfolio_overview?.uncertainty_note} tone="neutral" />
            <SignalNote label="Traceability" value={showcase.portfolio_overview?.traceability_note} tone="neutral" />
            <SignalNote label="Review next" value={showcase.portfolio_overview?.follow_up} tone="neutral" />
            <SignalNote label="Review window" value={showcase.portfolio_overview?.review_window} tone="neutral" />
            <OperatingSignals item={showcase.portfolio_overview} />
            <WeeklyReviewLens review={showcase.portfolio_overview?.weekly_review} />
            <SummaryMetadata item={showcase.portfolio_overview} />
            <SummaryLists
              topRequirements={showcase.portfolio_overview?.top_requirements}
              topModules={showcase.portfolio_overview?.top_modules}
              topRepositories={showcase.portfolio_overview?.top_repositories}
            />
          </div>

          <div className="showcase-overview-aside">
            <div className="showcase-stat-grid">
              {(showcase.portfolio_overview?.stats ?? []).map((stat) => (
                <article key={stat.label} className="showcase-stat-card">
                  <span>{stat.label}</span>
                  <strong>{formatStatValue(stat.value)}</strong>
                </article>
              ))}
            </div>
            <div className="showcase-evidence-grid">
              <EvidenceBlock
                title={showcase.meta?.section_labels?.observed ?? "Observed Facts"}
                items={showcase.portfolio_overview?.observed_facts ?? []}
                tone="fact"
              />
              <EvidenceBlock
                title={showcase.meta?.section_labels?.inferred ?? "Inferred Judgments"}
                items={showcase.portfolio_overview?.inferred_judgments ?? []}
                tone="judgment"
              />
            </div>
          </div>
        </section>

        <section className="panel showcase-coverage-panel">
          <div className="panel-header">
            <h3>Coverage Review</h3>
          </div>
          <div className="showcase-coverage-grid">
            <CoverageCard
              label="Requirements With Links"
              value={formatPercent(showcase.coverage?.delivery?.requirements_with_links_pct)}
              detail="Requirement records that currently have linked engineering movement."
            />
            <CoverageCard
              label="Timeline Coverage"
              value={formatPercent(showcase.coverage?.delivery?.requirements_with_timeline_pct)}
              detail="Requirements with usable created or updated timestamps."
            />
            <CoverageCard
              label="Connector Stage Coverage"
              value={formatPercent(showcase.coverage?.delivery?.connector_stage_coverage_pct)}
              detail="Delivery stages backed directly by connector-style PR, CI, or deployment fields."
            />
            <CoverageCard
              label="Inferred Stage Coverage"
              value={formatPercent(showcase.coverage?.delivery?.inferred_stage_coverage_pct)}
              detail="Delivery stages derived from linked commits, branch flow, merge signals, or downstream progression."
            />
            <CoverageCard
              label="Launch Signal Coverage"
              value={formatPercent(showcase.coverage?.delivery?.launch_signal_coverage_pct)}
              detail="Requirements that already show review, CI, deploy, or deployed progression."
            />
            <CoverageCard
              label="Telemetry Field Coverage"
              value={formatPercent(showcase.coverage?.telemetry?.field_coverage_pct)}
              detail="Average coverage across branches, files, modules, focus, attendance, and active minutes."
            />
          </div>
        </section>

        <div className="showcase-grid">
          <SummaryPanel
            title="Developer Weekly Summaries"
            items={showcase.developer_weekly ?? []}
            sectionLabels={showcase.meta?.section_labels}
            emptyMessage="Developer summaries will appear when telemetry and requirement links are available."
          />

          <SummaryPanel
            title="Manager Contribution Summaries"
            items={showcase.manager_contributions ?? []}
            sectionLabels={showcase.meta?.section_labels}
            emptyMessage="Manager summaries will appear when linked delivery data is available."
          />

          <SummaryPanel
            title="Issue-Level Impact"
            items={showcase.issue_impacts ?? []}
            sectionLabels={showcase.meta?.section_labels}
            emptyMessage="Issue impact summaries will appear when linked commits are available."
          />
        </div>

        <section className="panel">
          <div className="panel-header">
            <h3>Logic Notes</h3>
          </div>
          <div className="showcase-logic-list">
            {(showcase.logic_notes ?? []).map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function SummaryPanel({ title, items, emptyMessage, sectionLabels }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h3>{title}</h3>
      </div>
      {items.length ? (
        <div className="showcase-card-list">
          {items.map((item) => (
            <article key={item.id || item.issue_id || item.title} className="showcase-summary-card">
              <div className="showcase-summary-header">
                <div>
                  <p className="link-label">{item.scope ?? "summary"}</p>
                  <h4>{item.headline ?? item.title}</h4>
                </div>
                <div className="showcase-meta-stack">
                  <MetaPill label="Confidence" value={item.confidence ?? "medium"} tone={item.confidence} />
                  <MetaPill label="Risk" value={item.risk_level ?? "low"} tone={riskTone(item.risk_level)} />
                  <MetaPill label="Inference" value={item.inference_level ?? "high"} tone={inferenceTone(item.inference_level)} />
                  <MetaPill label="Evidence" value={formatEventCount(item.evidence_count)} tone="neutral" />
                  <MetaPill label="Freshness" value={item.freshness_level ?? "watch"} tone={item.freshness_level ?? "watch"} />
                  <MetaPill label="Action" value={item.action_priority ?? "watch"} tone={actionTone(item.action_priority)} />
                </div>
              </div>

              <div className="showcase-card-layout">
                <div className="showcase-card-main">
                  <div className="showcase-summary-brief">
                    <span className="showcase-summary-label">Executive summary</span>
                    <p className="showcase-summary-copy">{item.executive_summary ?? item.summary}</p>
                  </div>

                  <div className="showcase-summary-brief secondary">
                    <span className="showcase-summary-label">Weekly takeaway</span>
                    <p className="showcase-summary-copy">{item.summary}</p>
                  </div>
                  <WeeklyReviewLens review={item.weekly_review} />

                  <ScopeReviewBlocks item={item} />
                </div>

                <aside className="showcase-card-side">
                  <div className="showcase-note-stack">
                    <SignalNote label="Risk signal" value={item.risk_signal} tone="risk" />
                    <SignalNote label="Freshness" value={item.freshness_note} tone="neutral" />
                    <SignalNote label="Uncertainty" value={item.uncertainty_note} tone="neutral" />
                    <SignalNote label="Review next" value={item.follow_up} tone="neutral" />
                    <SignalNote label="Review window" value={item.review_window} tone="neutral" />
                    <SignalNote label="Review owner" value={item.review_owner} tone="neutral" />
                  </div>

                  <ActionHighlights item={item} />
                  <OperatingSignals item={item} />
                  <SummaryMetadata item={item} />
                  <SummaryLists
                    topRequirements={item.top_requirements}
                    topModules={item.top_modules}
                    topRepositories={item.top_repositories}
                  />
                  <SummaryHighlights items={filterHighlightsForScope(item)} />
                </aside>
              </div>

              <div className="showcase-evidence-grid">
                <EvidenceBlock title={sectionLabels?.observed ?? "Observed Facts"} items={item.observed_facts ?? []} tone="fact" />
                <EvidenceBlock
                  title={sectionLabels?.inferred ?? "Inferred Judgments"}
                  items={item.inferred_judgments ?? []}
                  tone="judgment"
                />
              </div>

              {item.stage_evidence ? (
                <div className="showcase-stage-strip">
                  <span className="showcase-signal-label">Stage evidence</span>
                  <p>{item.stage_evidence}</p>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <p className="empty-state">{emptyMessage}</p>
      )}
    </section>
  );
}

function SummaryHighlights({ items }) {
  if (!(items ?? []).length) {
    return null;
  }

  return (
    <div className="showcase-highlight-grid">
      {items.map((item) => (
        <article key={`${item.label}-${item.value}`} className="showcase-highlight-card">
          <span>{item.label}</span>
          <p>{item.value}</p>
        </article>
      ))}
    </div>
  );
}

function ScopeReviewBlocks({ item }) {
  const sections =
    item.scope === "manager"
      ? [
          { label: "What Moved", value: item.what_moved },
          { label: "Where Effort Concentrated", value: item.effort_concentration },
          { label: "Why It Matters", value: item.so_what },
          { label: "Risk To Watch", value: item.risk_watch },
          { label: "Review Next", value: item.follow_up },
        ]
      : item.scope === "developer"
        ? [
            { label: "What Was Worked On", value: item.what_changed },
            { label: "Where Effort Concentrated", value: item.effort_concentration },
            { label: "Focus Interpretation", value: item.focus_interpretation },
            { label: "Personal Work Summary", value: item.work_summary },
            { label: "Review Next", value: item.follow_up },
          ]
        : item.scope === "issue"
          ? [
              { label: "Requirement Progress", value: item.progress_summary },
              { label: "Delivery Readiness", value: item.readiness_summary },
              { label: "Effort Variance", value: item.variance_summary },
              { label: "Freshness And Continuity", value: mergeIssueRiskReadout(item) },
              { label: "Review Next", value: item.follow_up },
            ]
          : [];

  const populated = sections.filter((section) => section.value);

  if (!populated.length) {
    return null;
  }

  return (
    <div className="showcase-review-grid">
      {populated.map((section) => (
        <article key={`${item.id}-${section.label}`} className="showcase-review-card">
          <span>{section.label}</span>
          <p>{section.value}</p>
        </article>
      ))}
    </div>
  );
}

function SignalNote({ label, value, tone }) {
  if (!value) {
    return null;
  }

  const className = tone === "risk" ? "showcase-note risk" : "showcase-note";
  return (
    <div className={className}>
      <span>{label}</span>
      <p>{value}</p>
    </div>
  );
}

function SummaryMetadata({ item }) {
  const generatedFrom = (item?.generated_from ?? []).join(", ");
  const confidenceReason = item?.confidence_reason;
  const confidenceDetail = item?.confidence_detail;

  if (!generatedFrom && !confidenceReason && !confidenceDetail) {
    return null;
  }

  return (
    <div className="showcase-metadata-block">
      <span className="showcase-summary-label">Confidence and evidence</span>
      {confidenceReason ? (
        <p className="showcase-metadata-line">
          <span>Confidence read</span>
          {confidenceReason}
        </p>
      ) : null}
      <DetailChipRow label="Evidence strength" items={confidenceDetail?.supporting_evidence ?? []} tone="support" />
      <DetailChipRow label="Evidence gaps" items={confidenceDetail?.missing_evidence ?? []} tone="gap" />
      {confidenceDetail?.evidence_density ? (
        <p className="showcase-metadata-line">
          <span>Evidence density</span>
          {confidenceDetail.evidence_density}
        </p>
      ) : null}
      {confidenceDetail?.certainty_bias ? (
        <p className="showcase-metadata-line">
          <span>Certainty bias</span>
          {confidenceDetail.certainty_bias}
        </p>
      ) : null}
      {confidenceDetail?.improve_confidence ? (
        <p className="showcase-metadata-line">
          <span>Confidence next step</span>
          {confidenceDetail.improve_confidence}
        </p>
      ) : null}
      {generatedFrom ? (
        <p className="showcase-metadata-line">
          <span>Evidence inputs</span>
          {generatedFrom}
        </p>
      ) : null}
    </div>
  );
}

function WeeklyReviewLens({ review }) {
  if (!review) {
    return null;
  }

  return (
    <div className="showcase-weekly-lens">
      <span className="showcase-summary-label">Weekly review lens</span>
      <div className="showcase-lens-grid">
        <article className="showcase-lens-card observed">
          <span>Observed snapshot</span>
          <p>{(review.observed_snapshot ?? []).join(" ") || "No observed snapshot provided."}</p>
        </article>
        <article className="showcase-lens-card inferred">
          <span>Inferred signal</span>
          <p>{(review.inferred_signal ?? []).join(" ") || "No inferred signal provided."}</p>
        </article>
      </div>
      <SignalChipGroup label="Stable now" items={review.stable_signals ?? []} tone="stable" />
      <SignalChipGroup label="Watch next" items={review.watch_signals ?? []} tone="watch" />
      <p className="showcase-lens-meta">
        <strong>Decision basis:</strong> {review.decision_basis ?? "No decision basis provided."}
      </p>
      <p className="showcase-lens-meta">
        <strong>Uncertainty driver:</strong> {review.uncertainty_driver ?? "No uncertainty driver provided."}
      </p>
      <p className="showcase-lens-meta">
        <strong>Next action:</strong> {review.next_action ?? "No next action provided."}
      </p>
    </div>
  );
}

function SignalChipGroup({ label, items, tone }) {
  if (!items.length) {
    return null;
  }

  return (
    <div className="showcase-lens-chip-block">
      <span>{label}</span>
      <div className="showcase-lens-chip-row">
        {items.map((item) => (
          <span
            key={`${label}-${item}`}
            className={tone === "watch" ? "showcase-lens-chip watch" : "showcase-lens-chip stable"}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function OperatingSignals({ item }) {
  const cards = [
    { label: "Why this matters", value: item?.why_it_matters },
    { label: "Review focus", value: item?.review_focus },
    { label: "Top risk driver", value: item?.top_risk_driver },
    { label: "Next action", value: item?.recommended_follow_up ?? item?.follow_up },
    { label: "Confidence band", value: item?.summary_confidence_band },
    { label: "Execution maturity", value: item?.execution_maturity },
    { label: "Fulfillment confidence", value: item?.fulfillment_confidence },
    { label: "Downstream visibility", value: item?.downstream_visibility },
    { label: "Risk to completion", value: item?.risk_to_completion },
  ].filter((card) => card.value);

  if (!cards.length) {
    return null;
  }

  return (
    <div className="showcase-operating-block">
      <span className="showcase-summary-label">Operating view</span>
      <div className="showcase-operating-grid">
        {cards.map((card) => (
          <article key={`${card.label}-${card.value}`} className="showcase-operating-card">
            <span>{card.label}</span>
            <p>{card.value}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function ActionHighlights({ item }) {
  const highlights = [
    { label: "Why this matters", value: item?.why_it_matters },
    { label: "Review focus", value: item?.review_focus },
    {
      label: "Next action",
      value: item?.recommended_follow_up ?? item?.follow_up,
    },
    { label: "Confidence band", value: item?.summary_confidence_band },
    { label: "Freshness", value: item?.freshness_note },
    { label: "Uncertainty", value: item?.uncertainty_note },
  ].filter((highlight) => highlight.value);

  if (!highlights.length) {
    return null;
  }

  return (
    <div className="showcase-action-grid">
      <span className="showcase-summary-label">Action signals</span>
      <div className="showcase-action-grid-inner">
        {highlights.map((highlight) => (
          <article key={`${highlight.label}-${highlight.value}`} className="showcase-action-card">
            <span>{highlight.label}</span>
            <p>{highlight.value}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function DetailChipRow({ label, items, tone }) {
  if (!items.length) {
    return null;
  }

  return (
    <div className="showcase-detail-row">
      <span>{label}</span>
      <div className="showcase-detail-chip-row">
        {items.map((item) => (
          <span
            key={`${label}-${item}`}
            className={tone === "gap" ? "showcase-detail-chip gap" : "showcase-detail-chip support"}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function filterHighlightsForScope(item) {
  const labelsToHide =
    item.scope === "manager"
      ? new Set(["What Moved", "Where Effort Concentrated", "Why It Matters", "Recommended Follow-Up"])
      : item.scope === "developer"
        ? new Set(["What Was Worked On", "Where Effort Concentrated", "Recommended Follow-Up"])
        : item.scope === "issue"
          ? new Set(["Requirement Progress", "Delivery Readiness", "Effort Variance", "Continuity Risk", "Freshness", "Recommended Follow-Up"])
          : new Set();

  return (item.highlights ?? []).filter((highlight) => !labelsToHide.has(highlight.label));
}

function GuideCard({ label, detail, tone }) {
  const className = tone === "fact" ? "showcase-guide-card fact" : "showcase-guide-card judgment";
  return (
    <article className={className}>
      <span>{label}</span>
      <p>{detail}</p>
    </article>
  );
}

function SummaryLists({ topRequirements, topModules, topRepositories }) {
  const items = [
    { label: "Top Requirements", values: topRequirements },
    { label: "Top Modules", values: topModules },
    { label: "Top Repos", values: topRepositories },
  ].filter((item) => (item.values ?? []).length);

  if (!items.length) {
    return null;
  }

  return (
    <div className="showcase-list-grid">
      <span className="showcase-summary-label">Evidence map</span>
      {items.map((item) => (
        <div key={item.label} className="showcase-list-block">
          <span>{item.label}</span>
          <div className="showcase-chip-row">
            {item.values.slice(0, 4).map((value) => (
              <span key={`${item.label}-${value}`} className="showcase-chip">
                {value}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function EvidenceBlock({ title, items, tone }) {
  if (!items.length) {
    return null;
  }

  return (
    <div className={tone === "fact" ? "showcase-evidence-block fact" : "showcase-evidence-block judgment"}>
      <span className="showcase-summary-label">{tone === "fact" ? "Observed facts" : "Deterministic judgments"}</span>
      <span className="showcase-block-label">{title}</span>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function CoverageCard({ label, value, detail }) {
  return (
    <article className="showcase-coverage-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

function MetaPill({ label, value, tone }) {
  const className =
    tone === "high"
      ? "showcase-meta-pill high"
      : tone === "medium"
        ? "showcase-meta-pill medium"
        : tone === "low"
          ? "showcase-meta-pill low"
          : tone === "urgent"
            ? "showcase-meta-pill stale"
            : tone === "stable"
              ? "showcase-meta-pill fresh"
              : tone === "watch"
                ? "showcase-meta-pill watch"
          : tone === "fresh"
            ? "showcase-meta-pill fresh"
            : tone === "watch"
              ? "showcase-meta-pill watch"
              : tone === "stale"
                ? "showcase-meta-pill stale"
          : "showcase-meta-pill";

  return (
    <span className={className}>
      <strong>{label}</strong>
      <span>{value}</span>
    </span>
  );
}

function formatStatValue(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Number.isInteger(value) ? value : value.toFixed(1);
  }
  return value ?? "0";
}

function formatPercent(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function formatEventCount(value) {
  const count = Number(value || 0);
  return `${count} ${count === 1 ? "event" : "events"}`;
}

function mergeIssueRiskReadout(item) {
  const parts = [item.freshness_summary, item.continuity_summary].filter(Boolean);
  return parts.join(" ");
}

function inferenceTone(value) {
  if (value === "low") {
    return "high";
  }
  if (value === "medium") {
    return "medium";
  }
  return "low";
}

function riskTone(value) {
  if (value === "high") {
    return "low";
  }
  if (value === "medium") {
    return "medium";
  }
  return "high";
}

function actionTone(value) {
  if (value === "urgent") {
    return "low";
  }
  if (value === "watch") {
    return "medium";
  }
  return "high";
}

export default ShowcaseSummarySection;
