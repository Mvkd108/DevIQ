import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export default function NoveltyFeaturesSection() {
  const [burnoutData, setBurnoutData] = useState(null);
  const [atRiskData, setAtRiskData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  // Collapsible sections state
  const [showBurnoutDetails, setShowBurnoutDetails] = useState(false);
  const [showDeliveryDetails, setShowDeliveryDetails] = useState(false);
  const [expandedRequirement, setExpandedRequirement] = useState(null);

  useEffect(() => {
    fetchNoveltyData();
  }, []);

  const fetchNoveltyData = async () => {
    setLoading(true);
    setError("");
    
    try {
      const statusRes = await fetch(`${API_BASE_URL}/api/novelty-features/status`);
      const status = await statusRes.json();
      
      if (!status.burnout_detection?.available && !status.predictive_delivery?.available) {
        setError("Features not available.");
        setLoading(false);
        return;
      }

      const teamId = localStorage.getItem("teamId") || "team-001";
      
      if (status.burnout_detection?.available) {
        const burnoutRes = await fetch(`${API_BASE_URL}/api/teams/${teamId}/burnout-summary`);
        if (burnoutRes.ok) {
          setBurnoutData(await burnoutRes.json());
        }
      }

      if (status.predictive_delivery?.available) {
        const projectId = localStorage.getItem("projectId") || "project-001";
        const atRiskRes = await fetch(`${API_BASE_URL}/api/projects/${projectId}/at-risk-requirements?threshold=60`);
        if (atRiskRes.ok) {
          setAtRiskData(await atRiskRes.json());
        }
      }
    } catch (err) {
      setError("Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const getRiskStatus = (level) => {
    switch (level) {
      case "critical": return { color: "#dc2626", bg: "#fef2f2", text: "Critical Action Required" };
      case "high": return { color: "#ea580c", bg: "#fff7ed", text: "Attention Needed" };
      case "moderate": return { color: "#ca8a04", bg: "#fefce8", text: "Monitor" };
      case "low": return { color: "#16a34a", bg: "#f0fdf4", text: "Healthy" };
      default: return { color: "#6b7280", bg: "#f3f4f6", text: "Unknown" };
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "#6b7280" }}>
        Loading team health data...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "1.5rem", color: "#dc2626", textAlign: "center" }}>
        <p>{error}</p>
        <button 
          onClick={fetchNoveltyData}
          style={{
            marginTop: "0.5rem",
            padding: "0.5rem 1rem",
            backgroundColor: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "0.875rem"
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1200px", margin: "0 auto" }}>
      <h2 style={{ marginBottom: "1.5rem", fontSize: "1.25rem", fontWeight: "600", color: "#1f2937" }}>
        Team Health Overview
      </h2>

      {/* Executive Summary Cards */}
      <div style={{ 
        display: "grid", 
        gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", 
        gap: "1rem",
        marginBottom: "2rem"
      }}>
        {/* Team Burnout Card */}
        <div style={{
          backgroundColor: "white",
          borderRadius: "8px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          padding: "1.25rem",
          cursor: "pointer",
          transition: "box-shadow 0.2s",
        }} onClick={() => setShowBurnoutDetails(!showBurnoutDetails)}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
            <div>
              <div style={{ fontSize: "0.875rem", color: "#6b7280", marginBottom: "0.25rem" }}>
                Team Burnout Risk
              </div>
              <div style={{ fontSize: "1.75rem", fontWeight: "700", color: "#1f2937" }}>
                {burnoutData?.needing_attention_count || 0} of {burnoutData?.member_count || 0}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: "0.25rem" }}>
                members need attention
              </div>
            </div>
            <div style={{
              padding: "0.5rem 0.75rem",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: "600",
              backgroundColor: burnoutData?.needing_attention_count > 0 ? "#fef3c7" : "#f0fdf4",
              color: burnoutData?.needing_attention_count > 0 ? "#92400e" : "#166534",
            }}>
              {burnoutData?.needing_attention_count > 0 ? "Review Required" : "All Clear"}
            </div>
          </div>
          
          {/* Mini distribution bar */}
          <div style={{ display: "flex", height: "4px", borderRadius: "2px", overflow: "hidden", marginTop: "0.75rem" }}>
            <div style={{ flex: burnoutData?.distribution?.low || 1, backgroundColor: "#16a34a" }} />
            <div style={{ flex: burnoutData?.distribution?.moderate || 0, backgroundColor: "#ca8a04" }} />
            <div style={{ flex: burnoutData?.distribution?.high || 0, backgroundColor: "#ea580c" }} />
            <div style={{ flex: burnoutData?.distribution?.critical || 0, backgroundColor: "#dc2626" }} />
          </div>
          
          <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <span>{showBurnoutDetails ? "▼" : "▶"}</span>
            Click to {showBurnoutDetails ? "hide" : "view"} details
          </div>
        </div>

        {/* Delivery Risk Card */}
        <div style={{
          backgroundColor: "white",
          borderRadius: "8px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          padding: "1.25rem",
          cursor: "pointer",
        }} onClick={() => setShowDeliveryDetails(!showDeliveryDetails)}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
            <div>
              <div style={{ fontSize: "0.875rem", color: "#6b7280", marginBottom: "0.25rem" }}>
                Delivery At Risk
              </div>
              <div style={{ fontSize: "1.75rem", fontWeight: "700", color: "#1f2937" }}>
                {atRiskData?.count || 0}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: "0.25rem" }}>
                requirements may miss deadline
              </div>
            </div>
            <div style={{
              padding: "0.5rem 0.75rem",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: "600",
              backgroundColor: (atRiskData?.count || 0) > 0 ? "#fef2f2" : "#f0fdf4",
              color: (atRiskData?.count || 0) > 0 ? "#991b1b" : "#166534",
            }}>
              {(atRiskData?.count || 0) > 0 ? "Intervention Needed" : "On Track"}
            </div>
          </div>
          
          {(atRiskData?.count || 0) > 0 && (
            <div style={{ 
              display: "flex", 
              gap: "0.5rem", 
              marginTop: "0.75rem",
              flexWrap: "wrap"
            }}>
              {atRiskData?.requirements?.slice(0, 3).map((req, idx) => (
                <span key={idx} style={{
                  padding: "0.25rem 0.5rem",
                  fontSize: "0.75rem",
                  backgroundColor: req.risk_level === "critical" ? "#fef2f2" : req.risk_level === "high" ? "#fff7ed" : "#fefce8",
                  color: req.risk_level === "critical" ? "#991b1b" : req.risk_level === "high" ? "#9a3412" : "#854d0e",
                  borderRadius: "4px",
                }}>
                  {req.id}
                </span>
              ))}
              {(atRiskData?.count || 0) > 3 && (
                <span style={{
                  padding: "0.25rem 0.5rem",
                  fontSize: "0.75rem",
                  backgroundColor: "#f3f4f6",
                  color: "#6b7280",
                  borderRadius: "4px",
                }}>
                  +{(atRiskData?.count || 0) - 3} more
                </span>
              )}
            </div>
          )}
          
          <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: "0.75rem", display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <span>{showDeliveryDetails ? "▼" : "▶"}</span>
            Click to {showDeliveryDetails ? "hide" : "view"} details
          </div>
        </div>
      </div>

      {/* Expandable Burnout Details */}
      {showBurnoutDetails && burnoutData && (
        <div style={{
          backgroundColor: "white",
          borderRadius: "8px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          padding: "1.5rem",
          marginBottom: "1.5rem",
        }}>
          <h3 style={{ fontSize: "1rem", fontWeight: "600", marginBottom: "1rem", color: "#1f2937" }}>
            Burnout Risk Distribution
          </h3>
          
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
            {[
              { label: "Low Risk", value: burnoutData.distribution?.low || 0, color: "#16a34a", bg: "#f0fdf4" },
              { label: "Moderate", value: burnoutData.distribution?.moderate || 0, color: "#ca8a04", bg: "#fefce8" },
              { label: "High Risk", value: burnoutData.distribution?.high || 0, color: "#ea580c", bg: "#fff7ed" },
              { label: "Critical", value: burnoutData.distribution?.critical || 0, color: "#dc2626", bg: "#fef2f2" }
            ].map((item) => (
              <div 
                key={item.label}
                style={{
                  padding: "1rem",
                  backgroundColor: item.bg,
                  borderRadius: "6px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "1.5rem", fontWeight: "700", color: item.color }}>
                  {item.value}
                </div>
                <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "0.25rem" }}>
                  {item.label}
                </div>
              </div>
            ))}
          </div>

          {burnoutData.needing_attention_count > 0 && (
            <div style={{
              padding: "0.75rem 1rem",
              backgroundColor: "#fef3c7",
              borderRadius: "6px",
              fontSize: "0.875rem",
              color: "#92400e",
            }}>
              <strong>Action Required:</strong> {burnoutData.needing_attention_count} team member(s) need 1-on-1 check-ins this week.
            </div>
          )}

          <div style={{
            padding: "0.75rem",
            backgroundColor: "#f3f4f6",
            borderRadius: "6px",
            fontSize: "0.75rem",
            color: "#6b7280",
            marginTop: "1rem",
          }}>
            Individual scores visible in manager dashboard only. Team view shows aggregate data for privacy.
          </div>
        </div>
      )}

      {/* Expandable Delivery Details */}
      {showDeliveryDetails && atRiskData && (
        <div style={{
          backgroundColor: "white",
          borderRadius: "8px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          padding: "1.5rem",
          marginBottom: "1.5rem",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#1f2937" }}>
              Requirements At Risk ({atRiskData.count})
            </h3>
            <span style={{ fontSize: "0.75rem", color: "#9ca3af" }}>
              Threshold: {atRiskData.threshold}% probability
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {atRiskData.requirements?.map((req) => {
              const isExpanded = expandedRequirement === req.id;
              const status = getRiskStatus(req.risk_level);
              
              return (
                <div 
                  key={req.id}
                  style={{
                    border: "1px solid #e5e7eb",
                    borderRadius: "6px",
                    overflow: "hidden",
                  }}
                >
                  {/* Summary Row - Always Visible */}
                  <div 
                    onClick={() => setExpandedRequirement(isExpanded ? null : req.id)}
                    style={{
                      padding: "0.75rem 1rem",
                      display: "flex",
                      alignItems: "center",
                      gap: "1rem",
                      cursor: "pointer",
                      backgroundColor: isExpanded ? "#f9fafb" : "white",
                    }}
                  >
                    <span style={{ fontSize: "0.75rem" }}>{isExpanded ? "▼" : "▶"}</span>
                    
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: "500", fontSize: "0.875rem", color: "#1f2937" }}>
                        {req.title}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#9ca3af" }}>
                        {req.id}
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <div style={{
                        padding: "0.25rem 0.75rem",
                        borderRadius: "9999px",
                        fontSize: "0.75rem",
                        fontWeight: "600",
                        backgroundColor: status.bg,
                        color: status.color,
                      }}>
                        {req.probability}% on-time
                      </div>
                      
                      {req.predicted_delay_days > 0 && (
                        <div style={{
                          fontSize: "0.75rem",
                          color: "#dc2626",
                          fontWeight: "500",
                        }}>
                          +{req.predicted_delay_days}d
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div style={{
                      padding: "1rem",
                      backgroundColor: "#f9fafb",
                      borderTop: "1px solid #e5e7eb",
                    }}>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem", marginBottom: "1rem" }}>
                        <div>
                          <div style={{ fontSize: "0.75rem", color: "#6b7280", marginBottom: "0.25rem" }}>
                            Primary Risk Factor
                          </div>
                          <div style={{ fontSize: "0.875rem", color: "#1f2937" }}>
                            {req.primary_risk}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: "0.75rem", color: "#6b7280", marginBottom: "0.25rem" }}>
                            Risk Level
                          </div>
                          <div style={{
                            fontSize: "0.875rem",
                            fontWeight: "500",
                            color: status.color,
                            textTransform: "capitalize",
                          }}>
                            {req.risk_level}
                          </div>
                        </div>
                      </div>

                      <div style={{
                        padding: "0.75rem",
                        backgroundColor: "white",
                        borderRadius: "4px",
                        fontSize: "0.875rem",
                        color: "#4b5563",
                      }}>
                        <strong>Suggested Action:</strong> Review scope and resources for this requirement. Consider parallelizing work or adjusting timeline with stakeholders.
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {atRiskData.count === 0 && (
            <div style={{ textAlign: "center", padding: "2rem", color: "#6b7280" }}>
              All requirements on track for delivery.
            </div>
          )}
        </div>
      )}

      {/* Quick Actions Section */}
      <div style={{
        backgroundColor: "#f9fafb",
        borderRadius: "8px",
        padding: "1rem 1.5rem",
      }}>
        <h3 style={{ fontSize: "0.875rem", fontWeight: "600", color: "#6b7280", marginBottom: "0.75rem" }}>
          Recommended Actions
        </h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {burnoutData?.needing_attention_count > 0 && (
            <button style={{
              padding: "0.5rem 1rem",
              fontSize: "0.875rem",
              backgroundColor: "white",
              border: "1px solid #e5e7eb",
              borderRadius: "6px",
              cursor: "pointer",
              color: "#374151",
            }}>
              Schedule {burnoutData.needing_attention_count} check-ins
            </button>
          )}
          {(atRiskData?.count || 0) > 0 && (
            <button style={{
              padding: "0.5rem 1rem",
              fontSize: "0.875rem",
              backgroundColor: "white",
              border: "1px solid #e5e7eb",
              borderRadius: "6px",
              cursor: "pointer",
              color: "#374151",
            }}>
              Review at-risk requirements
            </button>
          )}
          <button style={{
            padding: "0.5rem 1rem",
            fontSize: "0.875rem",
            backgroundColor: "white",
            border: "1px solid #e5e7eb",
            borderRadius: "6px",
            cursor: "pointer",
            color: "#374151",
          }}>
            Export weekly report
          </button>
        </div>
      </div>
    </div>
  );
}
