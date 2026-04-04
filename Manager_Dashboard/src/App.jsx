import { useEffect, useMemo, useState } from "react";
import DeliveryTimelineSection from "./components/DeliveryTimelineSection";
import KnowledgeRiskSection from "./components/KnowledgeRiskSection";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const REFRESH_INTERVAL_MS = 30000; // 30s for manager view

function App() {
  const [events, setEvents] = useState([]);
  const [issues, setIssues] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [health, setHealth] = useState(null);
  const [deliveryTimeline, setDeliveryTimeline] = useState([]);
  const [deliveryTimelineSummary, setDeliveryTimelineSummary] = useState(null);
  const [deliveryTimelineLoading, setDeliveryTimelineLoading] = useState(true);
  const [deliveryTimelineError, setDeliveryTimelineError] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastRefreshedAt, setLastRefreshedAt] = useState(null);
  const [activeTab, setActiveTab] = useState("risk"); // risk | delivery | team

  // Load dashboard data
  async function loadDashboard() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dashboard`);
      if (!response.ok) throw new Error(`Backend error: ${response.status}`);
      const payload = await response.json();
      setEvents(payload.events ?? []);
      setIssues(payload.issues ?? []);
      setAnalytics(payload.analytics ?? null);
      setLastRefreshedAt(new Date());
      setError("");
    } catch (fetchError) {
      setError(fetchError.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  async function loadDeliveryTimeline() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/delivery-timeline`);
      if (!response.ok) throw new Error(`Timeline error: ${response.status}`);
      const payload = await response.json();
      setDeliveryTimeline(payload.records ?? []);
      setDeliveryTimelineSummary(payload.summary ?? null);
      setDeliveryTimelineError("");
    } catch (err) {
      setDeliveryTimelineError(err.message);
    } finally {
      setDeliveryTimelineLoading(false);
    }
  }

  async function loadHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/health`);
      if (!response.ok) throw new Error(`Health error: ${response.status}`);
      const payload = await response.json();
      setHealth(payload);
    } catch {
      setHealth(null);
    }
  }

  useEffect(() => {
    loadDashboard();
    loadDeliveryTimeline();
    loadHealth();
    const interval = setInterval(() => {
      loadDashboard();
      loadDeliveryTimeline({ background: true });
      loadHealth();
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  // Risk calculations
  const riskMetrics = useMemo(() => {
    const knowledgeRisks = analytics?.knowledge_risks ?? [];
    const highRiskModules = knowledgeRisks.filter(r => 
      r.mitigation_priority === "urgent" || r.mitigation_priority === "critical"
    );
    const urgentReviews = knowledgeRisks.filter(r => r.review_urgency === "urgent").length;
    const backupNeeded = knowledgeRisks.filter(r => r.backup_gap_pct > 30).length;
    
    // Delivery risk from timeline
    const weakTraceability = deliveryTimelineSummary?.weak_traceability_requirements ?? 0;
    const missingDeployment = deliveryTimelineSummary?.requirements_missing_deployment_visibility ?? 0;
    const mockedStages = deliveryTimelineSummary?.requirements_with_mocked_stages ?? 0;
    
    return {
      highRiskModules: highRiskModules.length,
      urgentReviews,
      backupNeeded,
      weakTraceability,
      missingDeployment,
      mockedStages,
      totalAtRisk: highRiskModules.length + weakTraceability + missingDeployment,
    };
  }, [analytics, deliveryTimelineSummary]);

  // Interventions derived from data
  const interventions = useMemo(() => {
    const list = [];
    
    // Knowledge continuity interventions
    const knowledgeRisks = analytics?.knowledge_risks ?? [];
    const urgentGaps = knowledgeRisks.filter(r => r.review_urgency === "urgent").slice(0, 2);
    urgentGaps.forEach(risk => {
      list.push({
        type: "continuity",
        priority: "high",
        target: risk.module,
        action: risk.recommended_backup_action || "Assign backup owner",
        reason: risk.manager_summary || "Knowledge concentration risk",
        owner: risk.top_contributor,
      });
    });
    
    // Delivery interventions
    if (deliveryTimelineSummary?.weak_traceability_requirements > 0) {
      list.push({
        type: "delivery",
        priority: "medium",
        target: "Delivery Pipeline",
        action: "Strengthen traceability on weak requirements",
        reason: `${deliveryTimelineSummary.weak_traceability_requirements} requirements have weak delivery chain`,
        owner: "Tech Lead",
      });
    }
    
    // Team health interventions from burnout data
    const burnoutRisks = analytics?.burnout_risk_summary ?? {};
    if (burnoutRisks.high_risk_count > 0) {
      list.push({
        type: "wellness",
        priority: "high",
        target: "Team Health",
        action: "Schedule 1:1s with at-risk developers",
        reason: `${burnoutRisks.high_risk_count} developers showing burnout signals`,
        owner: "Engineering Manager",
      });
    }
    
    return list.slice(0, 5); // Cap at 5 interventions
  }, [analytics, deliveryTimelineSummary]);

  // Team health metrics
  const teamHealth = useMemo(() => {
    const burnoutSummary = analytics?.burnout_risk_summary ?? {};
    const developerMetrics = analytics?.developer_metrics ?? [];
    
    const overloaded = developerMetrics.filter(d => d.workload_share_pct > 35).length;
    const highImpact = developerMetrics.filter(d => d.impact_score > 80).length;
    
    return {
      burnoutRisk: burnoutSummary.high_risk_count ?? 0,
      moderateBurnout: burnoutSummary.moderate_risk_count ?? 0,
      overloaded,
      highImpact,
      totalDevelopers: developerMetrics.length,
    };
  }, [analytics]);

  // Backend status for header
  const backendHealthy = health?.ready === true;
  const operatingMode = health?.operating_mode || "unknown";

  if (loading) {
    return (
      <div className="page-shell">
        <header className="topbar">
          <div className="brand-block">
            <p className="brand-kicker">DevIQ Manager</p>
            <h1>Engineering Risk Dashboard</h1>
          </div>
        </header>
        <main className="page-content">
          <div className="loading-center">Loading risk intelligence...</div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-shell">
        <header className="topbar">
          <div className="brand-block">
            <p className="brand-kicker">DevIQ Manager</p>
            <h1>Engineering Risk Dashboard</h1>
          </div>
        </header>
        <main className="page-content">
          <div className="error-panel">{error}</div>
          <div className="setup-hint">
            Backend target: {API_BASE_URL}
            <br />
            Ensure the FastAPI service is running on port 8000
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="page-shell">
      {/* Compact Header */}
      <header className="topbar compact">
        <div className="brand-block">
          <p className="brand-kicker">DevIQ Manager</p>
          <h1>Engineering Risk Dashboard</h1>
        </div>
        
        <div className="header-status">
          <span className={`status-pill ${backendHealthy ? "healthy" : "degraded"}`}>
            {backendHealthy ? "● Live" : "● Degraded"}
          </span>
          <span className="mode-pill">{operatingMode}</span>
          <span className="refresh-time">{formatTime(lastRefreshedAt)}</span>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="tab-nav">
        <button 
          className={activeTab === "risk" ? "tab active" : "tab"}
          onClick={() => setActiveTab("risk")}
        >
          Risk Overview
          {riskMetrics.totalAtRisk > 0 && (
            <span className="tab-badge alert">{riskMetrics.totalAtRisk}</span>
          )}
        </button>
        <button 
          className={activeTab === "delivery" ? "tab active" : "tab"}
          onClick={() => setActiveTab("delivery")}
        >
          Delivery Forecast
        </button>
        <button 
          className={activeTab === "team" ? "tab active" : "tab"}
          onClick={() => setActiveTab("team")}
        >
          Team Health
          {teamHealth.burnoutRisk > 0 && (
            <span className="tab-badge warning">{teamHealth.burnoutRisk}</span>
          )}
        </button>
      </nav>

      <main className="page-content compact">
        {/* RISK OVERVIEW TAB */}
        {activeTab === "risk" && (
          <>
            {/* Risk Summary Cards */}
            <section className="risk-summary-grid">
              <RiskCard 
                label="Critical Risks"
                value={riskMetrics.highRiskModules}
                trend={riskMetrics.highRiskModules > 0 ? "needs-attention" : "stable"}
                detail="High-priority knowledge gaps"
              />
              <RiskCard 
                label="Weak Traceability"
                value={riskMetrics.weakTraceability}
                trend={riskMetrics.weakTraceability > 5 ? "warning" : "stable"}
                detail="Requirements with thin delivery chain"
              />
              <RiskCard 
                label="Missing Deployment"
                value={riskMetrics.missingDeployment}
                trend={riskMetrics.missingDeployment > 3 ? "warning" : "stable"}
                detail="No deployment visibility"
              />
              <RiskCard 
                label="Backup Gaps"
                value={riskMetrics.backupNeeded}
                trend={riskMetrics.backupNeeded > 2 ? "needs-attention" : "stable"}
                detail="Modules needing backup owners"
              />
            </section>

            {/* Interventions Panel */}
            <section className="interventions-panel">
              <div className="panel-header">
                <h2>Recommended Interventions</h2>
                <span className="intervention-count">{interventions.length} actions</span>
              </div>
              <div className="intervention-list">
                {interventions.length === 0 ? (
                  <p className="empty-intervention">No critical interventions needed. Monitor continuing.</p>
                ) : (
                  interventions.map((item, idx) => (
                    <div key={idx} className={`intervention-card priority-${item.priority}`}>
                      <div className="intervention-header">
                        <span className={`type-badge ${item.type}`}>{item.type}</span>
                        <span className="priority-badge">{item.priority}</span>
                      </div>
                      <div className="intervention-body">
                        <strong className="intervention-action">{item.action}</strong>
                        <p className="intervention-target">Target: {item.target} {item.owner && `• Owner: ${item.owner}`}</p>
                        <p className="intervention-reason">{item.reason}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            {/* Knowledge Risk Summary (Compact) */}
            <section className="compact-panel">
              <div className="panel-header">
                <h2>Knowledge Continuity</h2>
              </div>
              <KnowledgeRiskSection analytics={analytics} compact />
            </section>
          </>
        )}

        {/* DELIVERY FORECAST TAB */}
        {activeTab === "delivery" && (
          <>
            {/* Delivery Status Summary */}
            <section className="delivery-summary-grid">
              <StatCard 
                label="Requirements Tracked" 
                value={deliveryTimelineSummary?.requirements_total ?? deliveryTimeline.length} 
              />
              <StatCard 
                label="Connector-Backed" 
                value={deliveryTimelineSummary?.connector_backed_requirements ?? 0}
                tone="positive"
              />
              <StatCard 
                label="Live Deployments" 
                value={deliveryTimelineSummary?.deployments_live ?? 0}
                tone={deliveryTimelineSummary?.deployments_live > 0 ? "positive" : "warning"}
              />
              <StatCard 
                label="CI Passing" 
                value={deliveryTimelineSummary?.ci_passing ?? 0}
                tone={deliveryTimelineSummary?.ci_passing > 0 ? "positive" : "neutral"}
              />
            </section>

            {/* Risk Breakdown */}
            <section className="delivery-risk-grid">
              <MiniStat 
                label="Weak Traceability" 
                value={deliveryTimelineSummary?.weak_traceability_requirements ?? 0}
                alert={deliveryTimelineSummary?.weak_traceability_requirements > 0}
              />
              <MiniStat 
                label="Mocked Stages" 
                value={deliveryTimelineSummary?.requirements_with_mocked_stages ?? 0}
                alert={deliveryTimelineSummary?.requirements_with_mocked_stages > 5}
              />
              <MiniStat 
                label="Missing Review" 
                value={deliveryTimelineSummary?.requirements_missing_review_visibility ?? 0}
              />
              <MiniStat 
                label="Missing Pipeline" 
                value={deliveryTimelineSummary?.requirements_missing_pipeline_visibility ?? 0}
              />
              <MiniStat 
                label="Missing Deployment" 
                value={deliveryTimelineSummary?.requirements_missing_deployment_visibility ?? 0}
              />
              <MiniStat 
                label="Inferred Only" 
                value={deliveryTimelineSummary?.inferred_only_requirements ?? 0}
              />
            </section>

            {/* Timeline Section */}
            <DeliveryTimelineSection
              records={deliveryTimeline}
              summary={deliveryTimelineSummary}
              loading={deliveryTimelineLoading}
              error={deliveryTimelineError}
              compact
            />
          </>
        )}

        {/* TEAM HEALTH TAB */}
        {activeTab === "team" && (
          <>
            {/* Team Health Summary */}
            <section className="health-summary-grid">
              <HealthCard 
                label="High Burnout Risk" 
                value={teamHealth.burnoutRisk}
                status={teamHealth.burnoutRisk > 0 ? "critical" : "healthy"}
                detail="Immediate intervention needed"
              />
              <HealthCard 
                label="Moderate Risk" 
                value={teamHealth.moderateBurnout}
                status={teamHealth.moderateBurnout > 2 ? "warning" : "healthy"}
                detail="Schedule check-ins"
              />
              <HealthCard 
                label="Overloaded" 
                value={teamHealth.overloaded}
                status={teamHealth.overloaded > 2 ? "warning" : "healthy"}
                detail="Workload share > 35%"
              />
              <HealthCard 
                label="High Impact" 
                value={teamHealth.highImpact}
                status="neutral"
                detail="Impact score > 80"
              />
            </section>

            {/* Developer Metrics Table (Condensed) */}
            <section className="compact-panel">
              <div className="panel-header">
                <h2>Developer Workload</h2>
              </div>
              <div className="dev-table">
                <div className="dev-table-header">
                  <span>Developer</span>
                  <span>Impact</span>
                  <span>Workload %</span>
                  <span>Status</span>
                </div>
                {(analytics?.developer_metrics ?? []).slice(0, 8).map(dev => (
                  <div key={dev.developer} className="dev-table-row">
                    <span className="dev-name">{dev.developer}</span>
                    <span className={`dev-score ${dev.impact_score > 80 ? "high" : ""}`}>
                      {dev.impact_score.toFixed(1)}
                    </span>
                    <span className={`dev-score ${dev.workload_share_pct > 35 ? "alert" : ""}`}>
                      {dev.workload_share_pct.toFixed(1)}%
                    </span>
                    <span className={`dev-status ${getDevStatus(dev)}`}>
                      {getDevStatusLabel(dev)}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {/* Burnout Alert Details */}
            {teamHealth.burnoutRisk > 0 && (
              <section className="alert-panel">
                <div className="alert-header">
                  <span className="alert-icon">⚠️</span>
                  <h3>Burnout Risk Detected</h3>
                </div>
                <p>{teamHealth.burnoutRisk} developer(s) showing critical burnout signals.</p>
                <div className="alert-actions">
                  <button className="action-btn primary">Schedule 1:1s</button>
                  <button className="action-btn secondary">Rebalance Workload</button>
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}

// Helper Components
function RiskCard({ label, value, trend, detail }) {
  return (
    <article className={`risk-card trend-${trend}`}>
      <span className="risk-label">{label}</span>
      <strong className="risk-value">{value}</strong>
      <span className="risk-detail">{detail}</span>
    </article>
  );
}

function HealthCard({ label, value, status, detail }) {
  return (
    <article className={`health-card status-${status}`}>
      <span className="health-label">{label}</span>
      <strong className="health-value">{value}</strong>
      <span className="health-detail">{detail}</span>
    </article>
  );
}

function StatCard({ label, value, tone = "neutral" }) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
    </article>
  );
}

function MiniStat({ label, value, alert = false }) {
  return (
    <article className={`mini-stat ${alert ? "alert" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function getDevStatus(dev) {
  if (dev.workload_share_pct > 35) return "overloaded";
  if (dev.impact_score > 80 && dev.workload_share_pct > 25) return "high-exposure";
  return "normal";
}

function getDevStatusLabel(dev) {
  if (dev.workload_share_pct > 35) return "Overloaded";
  if (dev.impact_score > 80 && dev.workload_share_pct > 25) return "High Exposure";
  return "Balanced";
}

function formatTime(date) {
  if (!date) return "--:--";
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default App;
