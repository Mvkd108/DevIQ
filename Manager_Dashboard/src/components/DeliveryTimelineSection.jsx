import { useMemo, useState } from "react";

function DeliveryTimelineSection({
  id = "timeline",
  records = [],
  summary = null,
  meta = null,
  loading = false,
  error = "",
  query = "",
  compact = false,
}) {
  const [recordFilter, setRecordFilter] = useState("all");
  const [sortMode, setSortMode] = useState("weakest-traceability");

  const queryFilteredRecords = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return records;
    }

    return records.filter((record) =>
      [
        record.issue_id,
        record.title,
        record.status,
        record.priority,
        record.delivery_stage,
        ...(record.commits ?? []).flatMap((commit) => [commit.commit_id, commit.message, commit.author, commit.repository_name]),
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalized)),
    );
  }, [records, query]);

  const displayedRecords = useMemo(() => {
    const filtered = queryFilteredRecords.filter((record) => {
      if (recordFilter === "all") {
        return true;
      }
      if (recordFilter === "weak-only") {
        return isWeakRecord(record);
      }
      if (recordFilter === "mock-heavy") {
        return (record?.quality?.mock_stage_count ?? 0) > 0;
      }
      if (recordFilter === "connector-gaps") {
        return (
          record?.quality?.traceability_strength !== "strong" ||
          (record?.quality?.connector_stage_count ?? 0) < 2 ||
          record?.quality?.missing_downstream_evidence
        );
      }
      if (recordFilter === "fully-traceable") {
        return record?.readiness?.code === "fully-traceable";
      }
      if (recordFilter === "delivery-ready") {
        return record?.quality?.delivery_evidence_strength === "verified";
      }
      return true;
    });

    return [...filtered].sort((left, right) => compareRecords(left, right, sortMode));
  }, [queryFilteredRecords, recordFilter, sortMode]);

  // Compact view: only show summary cards, skip the detailed records
  if (compact) {
    const atRiskRecords = displayedRecords.filter(r => isWeakRecord(r));
    
    return (
      <section className="section-block delivery-timeline-section compact" id={id}>
        {loading && !records.length ? (
          <section className="panel">Loading delivery timeline...</section>
        ) : error ? (
          <section className="panel error-panel">{error}</section>
        ) : (
          <>
            <div className="timeline-summary-grid timeline-summary-grid-operational compact">
              <SummaryCard
                label="Connector-Backed"
                value={summary?.connector_backed_requirements ?? 0}
                tone="connector"
                caption="Full delivery visibility"
                emphasis="primary"
              />
              <SummaryCard
                label="Inferred-Only"
                value={summary?.inferred_only_requirements ?? 0}
                tone="inferred"
                caption="Limited visibility"
                emphasis="primary"
              />
              <SummaryCard
                label="Mocked"
                value={summary?.mocked_requirements ?? 0}
                tone="mock"
                caption="Placeholder data"
                emphasis="primary"
              />
              <SummaryCard
                label="Weak Traceability"
                value={summary?.weak_traceability_requirements ?? 0}
                tone="warning"
                caption="Needs attention"
                emphasis="primary"
              />
            </div>
            
            {/* Show only at-risk records */}
            {atRiskRecords.length > 0 && (
              <div className="at-risk-records">
                <h4>At-Risk Requirements ({atRiskRecords.length})</h4>
                {atRiskRecords.slice(0, 3).map((record) => (
                  <article key={record.issue_id} className="risk-record-card">
                    <div className="risk-record-header">
                      <strong>{record.issue_id}</strong>
                      <span className={`status-pill ${record.quality?.traceability_strength}`}>
                        {record.quality?.traceability_strength}
                      </span>
                    </div>
                    <p>{record.title}</p>
                    <p className="risk-reason">
                      {record.quality?.missing_downstream_evidence ? "Missing downstream evidence" : ""}
                      {record.quality?.mock_stage_count > 0 ? " • Has mocked stages" : ""}
                    </p>
                  </article>
                ))}
              </div>
            )}
          </>
        )}
      </section>
    );
  }

  return (
    <section className="section-block delivery-timeline-section" id={id}>
      <div className="section-heading">
        <div>
          <p className="section-kicker">Delivery Timeline</p>
          <h2>Requirement to commit to PR, CI, and deployment</h2>
        </div>
        <div className="timeline-heading-note">
          <strong>{summary?.requirements_total ?? records.length}</strong>
          <span>requirements tracked</span>
        </div>
      </div>

      {loading && !records.length ? (
        <section className="panel">Loading delivery timeline...</section>
      ) : (
        <>
          <div className="timeline-summary-grid timeline-summary-grid-operational">
            <SummaryCard
              label="Connector-Backed Requirements"
              value={summary?.connector_backed_requirements ?? 0}
              tone="connector"
              caption="All delivery stages are connector-backed"
              emphasis="primary"
            />
            <SummaryCard
              label="Inferred-Only Requirements"
              value={summary?.inferred_only_requirements ?? 0}
              tone="inferred"
              caption="No connector stages; delivery flow is inferred from linked activity"
              emphasis="primary"
            />
            <SummaryCard
              label="Mixed Provenance Requirements"
              value={summary?.mixed_source_requirements ?? 0}
              tone="mixed"
              caption="More than one provenance type is present across PR, CI, and deployment"
              emphasis="primary"
            />
            <SummaryCard
              label="Mocked Requirements"
              value={summary?.mocked_requirements ?? 0}
              tone="mock"
              caption="All delivery stages are placeholders because no delivery signal exists"
              emphasis="primary"
            />
          </div>

          <div className="timeline-summary-grid timeline-summary-grid-secondary">
            <SummaryCard label="Requirements With Commits" value={summary?.requirements_with_commits ?? 0} />
            <SummaryCard label="Requirements With PRs" value={summary?.requirements_with_prs ?? 0} />
            <SummaryCard label="Passing CI" value={summary?.ci_passing ?? 0} />
            <SummaryCard label="Live Deployments" value={summary?.deployments_live ?? 0} />
          </div>

          <div className="timeline-rollup-grid">
            <SummaryCard label="Mostly Inferred" value={summary?.mostly_inferred_requirements ?? 0} tone="inferred-soft" caption="Requirements where inferred stages dominate" />
            <SummaryCard label="Using Mock Stages" value={summary?.requirements_with_mocked_stages ?? 0} tone="mock" caption="Requirements with at least one placeholder stage" />
            <SummaryCard
              label="Partial Connector Requirements"
              value={summary?.requirements_with_partial_connector_stages ?? 0}
              tone="mixed-soft"
              caption="Requirements with connector stages that still need inferred field fill"
            />
            <SummaryCard
              label="Weak Inference Requirements"
              value={summary?.requirements_with_weak_inference ?? 0}
              tone="warning"
              caption="Requirements with inferred stages backed by limited evidence"
            />
          </div>

          <div className="timeline-rollup-grid timeline-rollup-grid-operational">
            <SummaryCard label="Not Visible Beyond Code" value={summary?.requirements_not_visible_beyond_code ?? 0} tone="warning" caption="Requirements without visible review, pipeline, or deployment evidence" />
            <SummaryCard label="Missing Review Evidence" value={summary?.requirements_missing_review_visibility ?? 0} tone="warning" caption="Requirements still blocked before review becomes visible" />
            <SummaryCard label="Missing Pipeline Evidence" value={summary?.requirements_missing_pipeline_visibility ?? 0} tone="inferred-soft" caption="Requirements with review visibility but no pipeline evidence yet" />
            <SummaryCard label="Missing Deployment Evidence" value={summary?.requirements_missing_deployment_visibility ?? 0} tone="mixed-soft" caption="Requirements with review and CI visibility but no deployment evidence yet" />
            <SummaryCard label="Weak Connector Confidence" value={summary?.requirements_with_weak_connector_confidence ?? 0} tone="warning" caption="Requirements with partial or low-confidence connector stages" />
            <SummaryCard label="Weak Traceability" value={summary?.weak_traceability_requirements ?? 0} tone="warning" caption="Requirements where the delivery chain is still weak or missing" />
          </div>

          <div className="timeline-quality-grid">
            <SummaryCard label="Connector Coverage" value={`${summary?.connector_coverage_pct ?? 0}%`} tone="connector-soft" caption="Delivery stages backed by connector data in this view" />
            <SummaryCard label="Synthesized Delivery" value={`${summary?.synthesized_delivery_pct ?? 0}%`} tone="mixed-soft" caption="Inferred or mocked delivery stages across this view" />
            <SummaryCard label="Mock Fallback Stages" value={`${summary?.mock_fallback_stage_pct ?? 0}%`} tone="mock" caption="Stage slots still using placeholder fallback data" />
            <SummaryCard label="Stage Completeness" value={`${summary?.stage_completeness_pct ?? 0}%`} tone="neutral" caption="Average metadata completeness across PR, CI, and deployment" />
            <SummaryCard
              label="Downstream Evidence Coverage"
              value={`${summary?.downstream_evidence_coverage_pct ?? 0}%`}
              tone="warning"
              caption={`${summary?.missing_downstream_evidence_requirements ?? 0} requirements still lack reliable CI or deployment evidence`}
            />
          </div>

          <div className="timeline-quality-grid timeline-quality-grid-completeness">
            <SummaryCard label="Complete Stages" value={`${summary?.complete_stage_pct ?? 0}%`} tone="connector-soft" caption="Stage cards with high operational completeness" />
            <SummaryCard label="Partial Stages" value={`${summary?.partial_stage_pct ?? 0}%`} tone="mixed-soft" caption="Stage cards with useful but incomplete metadata" />
            <SummaryCard label="Minimal Stages" value={`${summary?.minimal_stage_pct ?? 0}%`} tone="inferred-soft" caption="Stage cards with thin inferred context" />
            <SummaryCard label="Missing Stages" value={`${summary?.missing_stage_pct ?? 0}%`} tone="mock" caption="Stage cards effectively missing beyond placeholder state" />
          </div>

          <div className="timeline-quality-grid timeline-quality-grid-strength">
            <SummaryCard label="Strong Traceability" value={summary?.traceability_strength_counts?.strong ?? 0} tone="connector" caption="Requirements with strong connector-backed delivery" />
            <SummaryCard label="Moderate Traceability" value={summary?.traceability_strength_counts?.moderate ?? 0} tone="mixed-soft" caption="Requirements with partial delivery evidence" />
            <SummaryCard label="Weak Traceability" value={summary?.traceability_strength_counts?.weak ?? 0} tone="warning" caption="Requirements where the delivery chain is thin" />
            <SummaryCard label="Missing Traceability" value={summary?.traceability_strength_counts?.missing ?? 0} tone="mock" caption="Requirements missing reliable delivery evidence" />
          </div>

          <div className="timeline-quality-grid timeline-quality-grid-strength">
            <SummaryCard label="Verified Delivery" value={summary?.delivery_evidence_strength_counts?.verified ?? 0} tone="connector-soft" caption="Requirements with connector-backed downstream evidence" />
            <SummaryCard label="Partial Delivery" value={summary?.delivery_evidence_strength_counts?.partial ?? 0} tone="mixed-soft" caption="Requirements with some delivery evidence, but not fully verified" />
            <SummaryCard label="Weak Delivery" value={summary?.delivery_evidence_strength_counts?.weak ?? 0} tone="warning" caption="Requirements relying on inferred delivery stages" />
            <SummaryCard label="Missing Delivery" value={summary?.delivery_evidence_strength_counts?.missing ?? 0} tone="mock" caption="Requirements lacking observable downstream evidence" />
          </div>

          <section className="panel timeline-context-panel">
            <div className="timeline-context-copy">
              <p>{meta?.real_data ?? "Requirement and commit data is loaded from the live backend feed."}</p>
              <p>{meta?.mocked_data ?? "PR, CI, and deployment cards can fall back to placeholders for showcase flow coverage."}</p>
              {meta?.provenance_rules ? (
                <div className="timeline-provenance-legend">
                  {Object.entries(meta.provenance_rules).map(([key, value]) => (
                    <div key={key} className="timeline-provenance-legend-item">
                      <span className={`timeline-source-tag ${key}`}>{value?.label || key}</span>
                      <p>{value?.description || value}</p>
                    </div>
                  ))}
                </div>
              ) : null}
              {meta?.completeness_rules ? (
                <div className="timeline-completeness-legend">
                  {Object.entries(meta.completeness_rules).map(([key, value]) => (
                    <div key={key} className="timeline-completeness-item">
                      <span className={`timeline-health-chip completeness-${key}`}>{value?.label || key}</span>
                      <p>{value?.description || ""}</p>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
            <div className="chip-row">
              <span className="chip chip-connector">Connector stages: {summary?.connector_stage_count ?? 0}</span>
              <span className="chip chip-inferred">Inferred stages: {summary?.inferred_stage_count ?? 0}</span>
              <span className="chip chip-mock">Mocked stages: {summary?.mocked_stage_count ?? 0}</span>
              <span className="chip chip-muted">Query: {query.trim() || "all requirements"}</span>
            </div>
          </section>

          <section className="panel timeline-controls-panel">
            <div className="timeline-controls-copy">
              <strong>Operational triage</strong>
              <p>Prioritize weak delivery chains, incomplete evidence, or mocked stages without leaving the timeline view.</p>
            </div>
            <div className="timeline-controls-group">
              <label className="timeline-control-field">
                <span>Filter</span>
              <select value={recordFilter} onChange={(event) => setRecordFilter(event.target.value)}>
                <option value="all">All requirements</option>
                <option value="weak-only">Weak or incomplete only</option>
                <option value="connector-gaps">Connector gaps</option>
                <option value="mock-heavy">Uses mocked stages</option>
                <option value="fully-traceable">Fully traceable only</option>
                <option value="delivery-ready">Delivery evidence verified</option>
              </select>
            </label>
            <label className="timeline-control-field">
              <span>Sort</span>
              <select value={sortMode} onChange={(event) => setSortMode(event.target.value)}>
                <option value="weakest-traceability">Weakest traceability</option>
                <option value="most-complete">Most complete</option>
                <option value="most-mocked">Most mocked</option>
                <option value="latest-activity">Latest activity</option>
                <option value="delivery-evidence">Delivery evidence strength</option>
              </select>
            </label>
          </div>
        </section>

          {error ? <section className="panel error-panel">{error}</section> : null}

          {displayedRecords.length ? (
            <div className="timeline-record-list">
              {displayedRecords.map((record) => (
                <article key={record.issue_id} className="timeline-record-card">
                  <div className="timeline-record-header">
                    <div>
                      <p className="link-label">{record.issue_id}</p>
                      <h3>{record.title}</h3>
                      <div className={`timeline-record-provenance provenance-${getRequirementProvenance(record)}`}>
                        <span className={`timeline-source-tag ${getRequirementProvenance(record)}`}>
                          {formatRequirementProvenanceLabel(record)}
                        </span>
                        <p>{formatRequirementProvenanceCopy(record)}</p>
                      </div>
                    </div>
                    <div className="timeline-record-summary">
                      <StatusPill value={record.delivery_stage} />
                      <span>{record.readiness?.label || "Unknown readiness"}</span>
                      <span>{record.commit_count} linked commits</span>
                      <span>{formatTraceabilityStrength(record.quality?.traceability_strength)}</span>
                      <span>{record.quality?.completeness_pct ?? 0}% completeness</span>
                      <span>{formatDeliveryEvidenceStrength(record.quality?.delivery_evidence_strength)}</span>
                      <span>{formatFreshnessLabel(record.quality?.freshness)}</span>
                      <span>Last activity {formatDate(record.latest_activity_at)}</span>
                    </div>
                  </div>

                  <div className="chip-row timeline-meta-row">
                    <span className="chip chip-muted">Status {record.status}</span>
                    <span className="chip chip-muted">Priority {record.priority}</span>
                    <span className="chip chip-muted">Project {record.project_key}</span>
                    <span className={`chip chip-readiness readiness-${record.readiness?.code || "unknown"}`}>{record.readiness?.label || "Unknown readiness"}</span>
                    <span className={`chip chip-traceability traceability-${record.quality?.traceability_strength || "unknown"}`}>{formatTraceabilityStrength(record.quality?.traceability_strength)}</span>
                    <span className="chip chip-connector">Connector {record.source_breakdown?.connector ?? 0}</span>
                    <span className="chip chip-inferred">Inferred {record.source_breakdown?.inferred ?? 0}</span>
                    <span className="chip chip-mock">Mock {record.source_breakdown?.mock ?? 0}</span>
                    {(record.pull_request?.quality?.is_partial_connector || record.ci?.quality?.is_partial_connector || record.deployment?.quality?.is_partial_connector) ? (
                      <span className="chip chip-warning">Connector details still incomplete</span>
                    ) : null}
                    {(record.pull_request?.quality?.weak_evidence || record.ci?.quality?.weak_evidence || record.deployment?.quality?.weak_evidence) ? (
                      <span className="chip chip-warning">Inferred evidence is limited</span>
                    ) : null}
                    {record.quality?.missing_downstream_evidence ? <span className="chip chip-warning">Downstream delivery evidence is still missing</span> : null}
                  </div>

                  <div className="timeline-operational-strip">
                    <OperationalSignal label="Readiness" value={record.readiness?.label || "Unknown"} tone={record.readiness?.code || "unknown"} />
                    <OperationalSignal label="Delivery evidence" value={formatDeliveryEvidenceStrength(record.quality?.delivery_evidence_strength)} tone={record.quality?.delivery_evidence_strength || "unknown"} />
                    <OperationalSignal label="Weakest point" value={formatWeakestStage(record.quality?.weakest_stage)} tone={(record.quality?.weakest_stage?.source || "unknown")} />
                    <OperationalSignal label="Blocking gap" value={formatBlockingGap(record.readiness?.blocking_gap)} tone={record.readiness?.blocking_gap ? "warning" : "connector"} />
                    <OperationalSignal label="Downstream coverage" value={`${record.quality?.downstream_coverage_pct ?? 0}% visible`} tone="neutral" />
                  </div>

                  {record.quality?.weakest_stage?.reason ? <p className="timeline-operational-note">{record.quality.weakest_stage.reason}</p> : null}

                  <div className="timeline-stage-grid">
                    <StageCard
                      title="Requirement"
                      status={record.requirement?.status}
                      source={record.requirement?.source}
                      details={[
                        buildDetail("Owner", record.requirement?.owner ?? "Unassigned"),
                        buildDetail("Created", formatDate(record.requirement?.created_at)),
                        buildDetail("Updated", formatDate(record.requirement?.updated_at)),
                      ]}
                    />

                    <section className="timeline-stage-card">
                      <div className="timeline-stage-header">
                        <div>
                          <p className="link-label">Commits</p>
                          <h4>Linked engineering work</h4>
                        </div>
                        <span className="timeline-source-tag telemetry">telemetry</span>
                      </div>

                      {(record.commits ?? []).length ? (
                        <div className="timeline-commit-list">
                          {[...(record.commits ?? [])]
                            .sort((left, right) => new Date(right.timestamp || 0) - new Date(left.timestamp || 0))
                            .slice(0, 4)
                            .map((commit) => (
                              <article key={commit.commit_id} className="timeline-commit-item">
                                <div className="timeline-commit-topline">
                                  <strong>{shortCommitId(commit.commit_id)}</strong>
                                  <span>{commit.author || "Unknown contributor"}</span>
                                </div>
                                <p>{commit.message || "Commit without message"}</p>
                                <div className="timeline-commit-meta">
                                  <span>{commit.repository_name || "Unknown repository"}</span>
                                  <span>{commit.branch || "No branch"}</span>
                                  <span>{formatDate(commit.timestamp)}</span>
                                </div>
                              </article>
                            ))}
                        </div>
                      ) : (
                        <p className="empty-state">No commits linked yet.</p>
                      )}
                    </section>

                    <StageCard
                      title="Pull Request"
                      status={record.pull_request?.status}
                      source={record.pull_request?.source}
                      stageKind="pull_request"
                      provenance={record.pull_request?.provenance}
                      details={[
                        buildDetail("State", record.pull_request?.state || record.pull_request?.status),
                        buildDetail("Number", record.pull_request?.number ? `#${record.pull_request.number}` : ""),
                        buildDetail("PR", record.pull_request?.summary),
                        buildDetail("Title", record.pull_request?.title),
                        buildDetail("Author", record.pull_request?.author),
                        (record.pull_request?.reviewers ?? []).length
                          ? buildDetail("Reviewers", (record.pull_request.reviewers ?? []).join(", "))
                          : null,
                        buildDetail("Branch", record.pull_request?.branch),
                        buildDetail("Repository", record.pull_request?.repository_name),
                        buildDetail("Created", formatDateOrEmpty(record.pull_request?.created_at)),
                        buildDetail("Updated", formatDateOrEmpty(record.pull_request?.updated_at)),
                        buildDetail("Merged", formatDateOrEmpty(record.pull_request?.merged_at)),
                      ]}
                      linkLabel={record.pull_request?.url ? formatStageLinkLabel("Pull Request", record.pull_request?.url) : ""}
                      host={formatUrlHost(record.pull_request?.url)}
                      url={record.pull_request?.url}
                      evidence={record.pull_request?.evidence}
                      provenanceDetail={record.pull_request?.provenance_detail}
                      quality={record.pull_request?.quality}
                      note={record.pull_request?.note}
                    />

                    <StageCard
                      title="CI"
                      status={record.ci?.status}
                      source={record.ci?.source}
                      stageKind="ci"
                      provenance={record.ci?.provenance}
                      details={[
                        buildDetail("Status", record.ci?.status),
                        buildDetail("Summary", record.ci?.summary),
                        buildDetail("Workflow", record.ci?.workflow),
                        buildDetail("Run ID", record.ci?.run_id),
                        buildDetail("Runtime", record.ci?.duration_minutes ? `${record.ci.duration_minutes} min` : ""),
                        buildDetail("Started", formatDateOrEmpty(record.ci?.started_at)),
                        buildDetail("Completed", formatDateOrEmpty(record.ci?.completed_at)),
                      ]}
                      linkLabel={record.ci?.url ? formatStageLinkLabel("CI", record.ci?.url) : ""}
                      host={formatUrlHost(record.ci?.url)}
                      url={record.ci?.url}
                      evidence={record.ci?.evidence}
                      provenanceDetail={record.ci?.provenance_detail}
                      quality={record.ci?.quality}
                      note={record.ci?.note}
                    />

                    <StageCard
                      title="Deployment"
                      status={record.deployment?.status}
                      source={record.deployment?.source}
                      stageKind="deployment"
                      provenance={record.deployment?.provenance}
                      details={[
                        buildDetail("Status", record.deployment?.status),
                        buildDetail("Summary", record.deployment?.summary),
                        buildDetail("Environment", record.deployment?.environment),
                        buildDetail("Target / platform", record.deployment?.target),
                        buildDetail("Version", record.deployment?.version),
                        buildDetail("Released", formatDateOrEmpty(record.deployment?.deployed_at)),
                        buildDetail("Updated", formatDateOrEmpty(record.deployment?.updated_at)),
                      ]}
                      linkLabel={record.deployment?.url ? formatStageLinkLabel("Deployment", record.deployment?.url) : ""}
                      host={formatUrlHost(record.deployment?.url)}
                      url={record.deployment?.url}
                      evidence={record.deployment?.evidence}
                      provenanceDetail={record.deployment?.provenance_detail}
                      quality={record.deployment?.quality}
                      note={record.deployment?.note}
                    />
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <section className="panel">No delivery timeline records match the current filters.</section>
          )}
        </>
      )}
    </section>
  );
}

function SummaryCard({ label, value, tone = "neutral", caption = "", emphasis = "default" }) {
  return (
    <article className={`mini-stat timeline-summary-card tone-${tone} emphasis-${emphasis}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {caption ? <p>{caption}</p> : null}
    </article>
  );
}

function OperationalSignal({ label, value, tone = "neutral" }) {
  return (
    <div className={`timeline-operational-signal tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StageCard({ title, status, source, stageKind = "", provenance = null, details = [], note = "", evidence = [], url = "", linkLabel = "", provenanceDetail = "", host = "", quality = null }) {
  return (
    <section className={`timeline-stage-card source-${source || "unknown"}`}>
      <div className="timeline-stage-header">
        <div>
          <p className="link-label">{title}</p>
          <h4>{title}</h4>
        </div>
        <div className="timeline-stage-badges">
          <StatusPill value={status} />
          <div className="timeline-stage-badge-row">
            <span className={`timeline-source-tag ${source || "unknown"}`}>{provenance?.label || formatSourceLabel(source)}</span>
            <span className={`timeline-trust-tag trust-${source || "unknown"}`}>{formatTrustLabel(source, provenance?.trust)}</span>
          </div>
        </div>
      </div>

      <p className="timeline-provenance-copy">{formatProvenanceDetail(source, note, provenanceDetail)}</p>

      <div className="timeline-stage-lens-row">
        <span className={`timeline-stage-lens lens-${source || "unknown"}`}>{formatSignalLens(source, quality)}</span>
        {stageKind ? <span className="timeline-stage-lens lens-stage">{formatMeasuredFieldsLabel(stageKind)}</span> : null}
      </div>

      {quality ? (
        <div className="timeline-stage-health-row">
          <span className={`timeline-health-chip completeness-${quality.completeness_label || "minimal"}`}>
            {quality.completeness_pct ?? 0}% {quality.completeness_title || quality.completeness_label || "minimal"}
          </span>
          <span className={`timeline-health-chip confidence-${quality.confidence || "unknown"}`}>
            {formatConfidenceLabel(quality.confidence)}
          </span>
          {quality.is_partial_connector ? <span className="timeline-health-chip connector-partial">connector gap</span> : null}
          {quality.weak_evidence ? <span className="timeline-health-chip evidence-weak">limited evidence</span> : null}
          {quality.is_mock_fallback ? <span className="timeline-health-chip mock-fallback">placeholder stage</span> : null}
        </div>
      ) : null}

      <div className="timeline-stage-details">
        {details.filter(Boolean).map((detail) => (
          <div key={`${detail.label}-${detail.value}`} className="timeline-detail-row">
            <span className="timeline-detail-label">{detail.label}</span>
            <span className="timeline-detail-value">{detail.value}</span>
          </div>
        ))}
      </div>

      {evidence?.length ? (
        <div className="timeline-evidence-row">
          {evidence.slice(0, 3).map((item) => (
            <span key={item} className="timeline-evidence-chip">
              {item}
            </span>
          ))}
        </div>
      ) : null}

      {url ? (
        <div className="timeline-stage-actions">
          {host ? <span className="timeline-stage-host">{host}</span> : null}
          <a className="timeline-stage-link" href={url} target="_blank" rel="noreferrer">
            {linkLabel || "Open source record"}
          </a>
        </div>
      ) : null}

      {note ? <p className="feedback-note">{note}</p> : null}
    </section>
  );
}

function buildDetail(label, value) {
  if (!value) {
    return null;
  }

  return { label, value };
}

function formatProvenanceDetail(source, note, provenanceDetail) {
  if (provenanceDetail) {
    return provenanceDetail;
  }
  if (source === "connector") {
    return "Connector-backed stage";
  }
  if (source === "inferred") {
    return "Derived from linked activity";
  }
  if (source === "mock") {
    return "Showcase placeholder";
  }
  return note || "Stage provenance unavailable";
}

function StatusPill({ value }) {
  const normalized = String(value || "unknown")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  return <span className={`timeline-status-pill status-${normalized || "unknown"}`}>{value || "unknown"}</span>;
}

function shortCommitId(value) {
  return String(value || "N/A").slice(0, 8);
}

function formatSourceLabel(value) {
  if (value === "connector") {
    return "connector";
  }
  if (value === "inferred") {
    return "inferred";
  }
  if (value === "mock") {
    return "mock";
  }
  if (value === "mixed") {
    return "mixed";
  }
  return value || "unknown";
}

function formatTrustLabel(source, trust) {
  if (trust === "high") {
    return "high trust";
  }
  if (trust === "medium" || trust === "derived") {
    return "derived";
  }
  if (trust === "low" || trust === "placeholder") {
    return "placeholder";
  }
  if (trust === "blended") {
    return "blended";
  }
  if (source === "jira") {
    return "tracked";
  }
  if (source === "connector") {
    return "high trust";
  }
  if (source === "inferred") {
    return "derived";
  }
  if (source === "mock") {
    return "placeholder";
  }
  if (source === "mixed") {
    return "blended";
  }
  return "unknown";
}

function formatConfidenceLabel(value) {
  if (value === "high") {
    return "high confidence";
  }
  if (value === "medium") {
    return "medium confidence";
  }
  if (value === "low") {
    return "low confidence";
  }
  return "unknown confidence";
}

function formatSignalLens(source, quality) {
  if (source === "connector" && quality?.is_partial_connector) {
    return "Connector-backed with inferred field fill";
  }
  if (source === "connector") {
    return "Direct connector record";
  }
  if (source === "inferred") {
    return "Derived from linked activity";
  }
  if (source === "mock") {
    return "Placeholder fallback";
  }
  if (source === "mixed") {
    return "Mixed provenance";
  }
  return "Signal source unavailable";
}

function formatMeasuredFieldsLabel(stageKind) {
  if (stageKind === "pull_request") {
    return "Fields: number, author, reviewers, branch, timestamps";
  }
  if (stageKind === "ci") {
    return "Fields: workflow, run, state, timing, duration";
  }
  if (stageKind === "deployment") {
    return "Fields: env, target, release, state, deployed time";
  }
  return "Stage fields";
}

function formatDownstreamEvidenceLabel(value) {
  if (value === "verified") {
    return "Verified downstream evidence";
  }
  if (value === "derived") {
    return "Derived downstream evidence";
  }
  if (value === "missing") {
    return "Downstream evidence missing";
  }
  return "Downstream evidence unknown";
}

function formatDeliveryEvidenceStrength(value) {
  if (value === "verified") {
    return "Verified delivery evidence";
  }
  if (value === "partial") {
    return "Partial delivery evidence";
  }
  if (value === "weak") {
    return "Weak delivery evidence";
  }
  return "Delivery evidence missing";
}

function formatTraceabilityStrength(value) {
  if (value === "strong") {
    return "Strong traceability";
  }
  if (value === "moderate") {
    return "Moderate traceability";
  }
  if (value === "weak") {
    return "Weak traceability";
  }
  return "Traceability missing";
}

function formatWeakestStage(stage) {
  if (!stage?.label) {
    return "Unavailable";
  }
  return `${stage.label} (${stage.completeness_label || "missing"})`;
}

function formatBlockingGap(value) {
  if (value === "review") {
    return "Review evidence missing";
  }
  if (value === "pipeline") {
    return "Pipeline evidence missing";
  }
  if (value === "deployment") {
    return "Deployment evidence missing";
  }
  return "No immediate gap";
}

function isWeakRecord(record) {
  return (
    ["weak", "missing"].includes(record?.quality?.traceability_strength) ||
    (record?.quality?.completeness_pct ?? 0) < 70 ||
    record?.quality?.missing_downstream_evidence ||
    (record?.quality?.mock_stage_count ?? 0) > 0
  );
}

function compareRecords(left, right, sortMode) {
  if (sortMode === "most-complete") {
    return compareNumbers(right?.quality?.completeness_pct, left?.quality?.completeness_pct)
      || compareNumbers(right?.quality?.connector_stage_count, left?.quality?.connector_stage_count)
      || compareDates(right?.latest_activity_at, left?.latest_activity_at);
  }
  if (sortMode === "most-mocked") {
    return compareNumbers(right?.quality?.mock_stage_count, left?.quality?.mock_stage_count)
      || compareTraceability(left?.quality?.traceability_strength, right?.quality?.traceability_strength)
      || compareDates(right?.latest_activity_at, left?.latest_activity_at);
  }
  if (sortMode === "latest-activity") {
    return compareDates(right?.latest_activity_at, left?.latest_activity_at);
  }

  if (sortMode === "delivery-evidence") {
    return (
      compareDeliveryEvidence(left?.quality?.delivery_evidence_strength, right?.quality?.delivery_evidence_strength) ||
      compareTraceability(left?.quality?.traceability_strength, right?.quality?.traceability_strength) ||
      compareDates(right?.latest_activity_at, left?.latest_activity_at)
    );
  }

  return compareTraceability(left?.quality?.traceability_strength, right?.quality?.traceability_strength)
    || compareWeakestStage(left?.quality?.weakest_stage, right?.quality?.weakest_stage)
    || compareNumbers(left?.quality?.completeness_pct, right?.quality?.completeness_pct)
    || compareNumbers(right?.quality?.mock_stage_count, left?.quality?.mock_stage_count)
    || compareDates(right?.latest_activity_at, left?.latest_activity_at);
}

function compareDeliveryEvidence(left, right) {
  const rank = { missing: 0, weak: 1, partial: 2, verified: 3 };
  return (rank[left] ?? -1) - (rank[right] ?? -1);
}

function compareTraceability(left, right) {
  const rank = { missing: 0, weak: 1, moderate: 2, strong: 3 };
  return (rank[left] ?? -1) - (rank[right] ?? -1);
}

function compareWeakestStage(left, right) {
  const completenessRank = { missing: 0, minimal: 1, partial: 2, complete: 3 };
  const stageRank = { deployment: 0, ci: 1, pull_request: 2 };
  return (completenessRank[left?.completeness_label] ?? -1) - (completenessRank[right?.completeness_label] ?? -1)
    || (stageRank[left?.key] ?? 3) - (stageRank[right?.key] ?? 3);
}

function compareNumbers(left, right) {
  return Number(left ?? 0) - Number(right ?? 0);
}

function compareDates(left, right) {
  return new Date(left || 0).getTime() - new Date(right || 0).getTime();
}

function getRequirementProvenance(record) {
  return record?.provenance?.rollup || record?.provenance_rollup || "unknown";
}

function formatRequirementProvenanceLabel(record) {
  if (record?.provenance?.label) {
    return record.provenance.label;
  }
  const source = getRequirementProvenance(record);
  if (source === "connector") {
    return "connector-backed";
  }
  if (source === "inferred") {
    return "inferred-only";
  }
  if (source === "mock") {
    return "mock-backed";
  }
  if (source === "mixed") {
    return "mixed-source";
  }
  return "unknown";
}

function formatRequirementProvenanceCopy(record) {
  if (record?.provenance?.description) {
    const counts = record?.provenance?.counts || record?.source_breakdown || {};
    const connector = counts.connector ?? 0;
    const inferred = counts.inferred ?? 0;
    const mock = counts.mock ?? 0;

    if (record?.provenance?.rollup === "connector") {
      return `${record.provenance.description} ${connector} connector-backed stages.`;
    }
    if (record?.provenance?.rollup === "inferred") {
      return `${record.provenance.description} ${inferred} inferred stages.`;
    }
    if (record?.provenance?.rollup === "mock") {
      return `${record.provenance.description} ${mock} placeholder stages.`;
    }
    if (record?.provenance?.rollup === "mixed") {
      return `${record.provenance.description} ${connector} connector, ${inferred} inferred, ${mock} mock stages.`;
    }
  }

  const source = getRequirementProvenance(record);
  const breakdown = record?.source_breakdown || {};
  const connector = breakdown.connector ?? 0;
  const inferred = breakdown.inferred ?? 0;
  const mock = breakdown.mock ?? 0;

  if (source === "connector") {
    return `${connector} connector-backed delivery stages.`;
  }
  if (source === "inferred") {
    return `${inferred} stages inferred from linked activity.`;
  }
  if (source === "mock") {
    return `${mock} showcase placeholders remain because no delivery signals were found.`;
  }
  if (source === "mixed") {
    return `${connector} connector, ${inferred} inferred, ${mock} mock stages.`;
  }
  return "Stage provenance unavailable.";
}

function formatStageLinkLabel(stageName, url) {
  try {
    const hostname = new URL(url).hostname.replace(/^www\./, "");
    return `${stageName} record on ${hostname}`;
  } catch {
    return `Open ${stageName} record`;
  }
}

function formatUrlHost(url) {
  if (!url) {
    return "";
  }

  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

function formatDate(value) {
  if (!value) {
    return "N/A";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "N/A";
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

function formatDateOrEmpty(value) {
  if (!value) {
    return "";
  }
  return formatDate(value);
}

function formatFreshnessLabel(value) {
  if (value === "fresh") {
    return "Fresh activity";
  }
  if (value === "active") {
    return "Active timeline";
  }
  if (value === "stale") {
    return "Stale activity";
  }
  return "Freshness unknown";
}

export default DeliveryTimelineSection;
