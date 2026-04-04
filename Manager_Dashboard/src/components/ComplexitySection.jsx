import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import ComplexityTrendsChart from "./ComplexityTrendsChart";
import MostComplexFiles from "./MostComplexFiles";

// Initialize Supabase client directly (bypasses Render backend)
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "https://jkwubrrronkyfpmdlvwd.supabase.co";
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || import.meta.env.VITE_SUPABASE_KEY || "";

const supabase = createClient(supabaseUrl, supabaseKey);

export default function ComplexitySection() {
  const [repoOverview, setRepoOverview] = useState(null);
  const [highComplexityCommits, setHighComplexityCommits] = useState([]);
  const [developerTrends, setDeveloperTrends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedCommit, setExpandedCommit] = useState(null);
  const [fileDetails, setFileDetails] = useState({}); // Store file-level metrics

  useEffect(() => {
    fetchComplexityData();
  }, []);

  // Fetch file-level details when expanding a commit
  const fetchFileDetails = async (commitId) => {
    if (fileDetails[commitId]) return; // Already loaded

    try {
      const { data, error } = await supabase
        .from("file_complexity_snapshots")
        .select("*")
        .eq("commit_id", commitId);

      if (error) {
        console.error("Error fetching file details:", error);
        return;
      }

      setFileDetails(prev => ({ ...prev, [commitId]: data || [] }));
    } catch (e) {
      console.error("Error:", e);
    }
  };

  const handleExpandCommit = (commitId) => {
    if (expandedCommit === commitId) {
      setExpandedCommit(null);
    } else {
      setExpandedCommit(commitId);
      fetchFileDetails(commitId);
    }
  };

  useEffect(() => {
    fetchComplexityData();
  }, []);

  const fetchComplexityData = async () => {
    setLoading(true);
    setError("");

    try {
      // Fetch repository overview
      const { data: overview, error: overviewError } = await supabase
        .from("repository_complexity_overview")
        .select("*")
        .limit(1)
        .single();

      if (overviewError && overviewError.code !== "PGRST116") {
        console.log("Overview error:", overviewError);
      }
      
      if (overview) {
        setRepoOverview(overview);
      }

      // Fetch high complexity commits
      const { data: highRisk, error: highRiskError } = await supabase
        .from("high_complexity_commits")
        .select("*")
        .limit(10);

      if (highRiskError) {
        console.log("High complexity error:", highRiskError);
      } else {
        setHighComplexityCommits(highRisk || []);
      }

      // Fetch developer trends
      const { data: trends, error: trendsError } = await supabase
        .from("developer_complexity_trends")
        .select("*")
        .limit(10);

      if (trendsError) {
        console.log("Trends error:", trendsError);
      } else {
        setDeveloperTrends(trends || []);
      }

    } catch (err) {
      console.error("Error fetching complexity data:", err);
      setError("Failed to load complexity data");
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score) => {
    if (score > 70) return "#dc2626"; // red
    if (score > 50) return "#ea580c"; // orange
    if (score > 30) return "#ca8a04"; // yellow
    return "#16a34a"; // green
  };

  const getRiskBg = (score) => {
    if (score > 70) return "#fef2f2";
    if (score > 50) return "#fff7ed";
    if (score > 30) return "#fefce8";
    return "#f0fdf4";
  };

  const getImpactColor = (impact) => {
    switch (impact) {
      case "critical": return "#dc2626";
      case "high": return "#ea580c";
      case "medium": return "#ca8a04";
      default: return "#16a34a";
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "#6b7280" }}>
        Loading code complexity data...
      </div>
    );
  }

  if (error && !repoOverview && highComplexityCommits.length === 0) {
    return (
      <div style={{ padding: "1.5rem", color: "#6b7280", textAlign: "center" }}>
        <p>Complexity analysis data not available.</p>
        <p style={{ fontSize: "0.875rem", marginTop: "0.5rem" }}>
          Run: <code>python run_complexity_analysis.py</code> to generate data.
        </p>
        <button 
          onClick={fetchComplexityData}
          style={{
            marginTop: "1rem",
            padding: "0.5rem 1rem",
            backgroundColor: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer"
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1200px", margin: "0 auto" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: "600", color: "#1f2937", marginBottom: "0.5rem" }}>
          Code Complexity Analysis
        </h2>
        <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>
          AST-based complexity metrics and architectural impact assessment
        </p>
      </div>

      {/* Repository Health Overview */}
      {repoOverview && (
        <div style={{
          backgroundColor: "white",
          borderRadius: "8px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          padding: "1.5rem",
          marginBottom: "1.5rem"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#1f2937" }}>
              Repository: {repoOverview.repository_name}
            </h3>
            <div style={{
              padding: "0.5rem 1rem",
              borderRadius: "9999px",
              fontSize: "0.875rem",
              fontWeight: "600",
              backgroundColor: repoOverview.avg_max_complexity > 50 ? "#fef2f2" : "#f0fdf4",
              color: repoOverview.avg_max_complexity > 50 ? "#dc2626" : "#16a34a"
            }}>
              Health Score: {Math.max(0, 100 - repoOverview.avg_max_complexity).toFixed(0)}/100
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "1rem" }}>
            <div style={{ textAlign: "center", padding: "1rem", backgroundColor: "#f9fafb", borderRadius: "6px" }}>
              <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#1f2937" }}>
                {repoOverview.total_commits_analyzed || 0}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "0.25rem" }}>
                Commits Analyzed
              </div>
            </div>

            <div style={{ textAlign: "center", padding: "1rem", backgroundColor: "#f9fafb", borderRadius: "6px" }}>
              <div style={{ fontSize: "1.5rem", fontWeight: "700", color: getRiskColor(repoOverview.avg_max_complexity) }}>
                {repoOverview.avg_max_complexity?.toFixed(1) || 0}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "0.25rem" }}>
                Avg Complexity
              </div>
            </div>

            <div style={{ textAlign: "center", padding: "1rem", backgroundColor: repoOverview.critical_commits > 0 ? "#fef2f2" : "#f0fdf4", borderRadius: "6px" }}>
              <div style={{ fontSize: "1.5rem", fontWeight: "700", color: repoOverview.critical_commits > 0 ? "#dc2626" : "#16a34a" }}>
                {repoOverview.critical_commits || 0}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "0.25rem" }}>
                Critical Commits
              </div>
            </div>

            <div style={{ textAlign: "center", padding: "1rem", backgroundColor: "#f9fafb", borderRadius: "6px" }}>
              <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#1f2937" }}>
                {repoOverview.contributing_developers || 0}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "0.25rem" }}>
                Developers
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Complexity Trends Chart */}
      <ComplexityTrendsChart />

      {/* High Complexity Commits */}
      <div style={{
        backgroundColor: "white",
        borderRadius: "8px",
        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        padding: "1.5rem",
        marginBottom: "1.5rem"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#1f2937" }}>
            High Complexity Commits ({highComplexityCommits.length})
          </h3>
          {highComplexityCommits.length > 0 && (
            <span style={{ fontSize: "0.75rem", color: "#9ca3af" }}>
              Click to expand details
            </span>
          )}
        </div>

        {highComplexityCommits.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {highComplexityCommits.map((commit) => {
              const isExpanded = expandedCommit === commit.commit_id;
              const riskScore = commit.max_file_complexity || 0;

              return (
                <div
                  key={commit.commit_id}
                  style={{
                    border: "1px solid #e5e7eb",
                    borderRadius: "6px",
                    overflow: "hidden",
                    backgroundColor: isExpanded ? "#f9fafb" : "white"
                  }}
                >
                  {/* Summary Row */}
                  <div
                    onClick={() => handleExpandCommit(commit.commit_id)}
                    style={{
                      padding: "0.75rem 1rem",
                      cursor: "pointer",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <span style={{ fontSize: "0.75rem", color: "#9ca3af" }}>
                        {isExpanded ? "▼" : "▶"}
                      </span>
                      <div>
                        <div style={{ fontFamily: "monospace", fontSize: "0.85rem", color: "#1f2937" }}>
                          {commit.commit_id?.slice(0, 8)}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "#6b7280" }}>
                          by {commit.author}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <span style={{
                        padding: "0.25rem 0.75rem",
                        borderRadius: "4px",
                        fontSize: "0.75rem",
                        fontWeight: "600",
                        backgroundColor: getRiskBg(riskScore),
                        color: getRiskColor(riskScore)
                      }}>
                        Risk: {riskScore.toFixed(0)}
                      </span>
                      <span style={{
                        padding: "0.25rem 0.75rem",
                        borderRadius: "4px",
                        fontSize: "0.75rem",
                        fontWeight: "600",
                        backgroundColor: "#f3f4f6",
                        color: getImpactColor(commit.architectural_impact)
                      }}>
                        {commit.architectural_impact}
                      </span>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div style={{
                      padding: "1rem",
                      borderTop: "1px solid #e5e7eb",
                      backgroundColor: "white"
                    }}>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem", marginBottom: "1rem" }}>
                        <div>
                          <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginBottom: "0.25rem" }}>
                            Files Changed
                          </div>
                          <div style={{ fontSize: "0.875rem", fontWeight: "500" }}>
                            {commit.files_changed || "Unknown"}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginBottom: "0.25rem" }}>
                            Complexity Trend
                          </div>
                          <div style={{ fontSize: "0.875rem", fontWeight: "500" }}>
                            {commit.complexity_trend}
                          </div>
                        </div>
                      </div>

                      {/* File-level Complexity Details */}
                      {fileDetails[commit.commit_id] && fileDetails[commit.commit_id].length > 0 && (
                        <div style={{ marginBottom: "1rem" }}>
                          <div style={{ 
                            fontSize: "0.75rem", 
                            color: "#9ca3af", 
                            marginBottom: "0.5rem",
                            fontWeight: "600",
                            textTransform: "uppercase",
                            letterSpacing: "0.05em"
                          }}>
                            File-level Complexity ({fileDetails[commit.commit_id].length} files)
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                            {fileDetails[commit.commit_id].map((file, idx) => (
                              <div
                                key={idx}
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "center",
                                  padding: "0.5rem 0.75rem",
                                  backgroundColor: getRiskBg(file.risk_score),
                                  borderRadius: "4px",
                                  border: `1px solid ${getRiskColor(file.risk_score)}20`
                                }}
                              >
                                <div style={{ flex: 1, minWidth: 0 }}>
                                  <div style={{ 
                                    fontSize: "0.8rem", 
                                    fontWeight: "500",
                                    color: "#1f2937",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap"
                                  }}>
                                    {file.file_path?.split('/').pop()}
                                  </div>
                                  <div style={{ fontSize: "0.7rem", color: "#6b7280" }}>
                                    {file.language} • {file.lines_of_code} lines
                                  </div>
                                </div>
                                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                                  <span style={{
                                    fontSize: "0.75rem",
                                    padding: "0.125rem 0.5rem",
                                    backgroundColor: "white",
                                    borderRadius: "3px",
                                    color: getRiskColor(file.risk_score),
                                    fontWeight: "600"
                                  }}>
                                    CC: {file.cyclomatic_complexity}
                                  </span>
                                  <span style={{
                                    fontSize: "0.75rem",
                                    padding: "0.125rem 0.5rem",
                                    backgroundColor: getRiskColor(file.risk_score),
                                    color: "white",
                                    borderRadius: "3px",
                                    fontWeight: "600"
                                  }}>
                                    Risk: {file.risk_score?.toFixed(0) || 0}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div style={{
                        padding: "0.75rem",
                        backgroundColor: riskScore > 50 ? "#fef2f2" : "#f0fdf4",
                        borderRadius: "4px",
                        fontSize: "0.875rem",
                        color: riskScore > 50 ? "#991b1b" : "#166534"
                      }}>
                        {riskScore > 50
                          ? "[WARNING] This commit introduces significant complexity. Code review recommended."
                          : "[OK] Complexity is within acceptable range."
                        }
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: "2rem", color: "#6b7280" }}>
            No high complexity commits found.
          </div>
        )}
      </div>

      {/* Most Complex Files */}
      <MostComplexFiles />

      {/* Developer Trends */}
      {developerTrends.length > 0 && (
        <div style={{
          backgroundColor: "white",
          borderRadius: "8px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          padding: "1.5rem"
        }}>
          <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#1f2937", marginBottom: "1rem" }}>
            Developer Complexity Trends
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {developerTrends.slice(0, 5).map((trend, idx) => (
              <div
                key={`${trend.author}-${trend.week}-${idx}`}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "0.75rem 1rem",
                  backgroundColor: "#f9fafb",
                  borderRadius: "6px"
                }}
              >
                <div>
                  <div style={{ fontWeight: "500", fontSize: "0.875rem", color: "#1f2937" }}>
                    {trend.author}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#9ca3af" }}>
                    Week of {new Date(trend.week).toLocaleDateString()}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "#1f2937" }}>
                      {trend.commit_count}
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "#9ca3af" }}>commits</div>
                  </div>

                  <div style={{
                    textAlign: "center",
                    padding: "0.25rem 0.5rem",
                    backgroundColor: trend.avg_complexity_delta > 0 ? "#fef2f2" : "#f0fdf4",
                    borderRadius: "4px"
                  }}>
                    <div style={{
                      fontSize: "0.875rem",
                      fontWeight: "600",
                      color: trend.avg_complexity_delta > 0 ? "#dc2626" : "#16a34a"
                    }}>
                      {trend.avg_complexity_delta > 0 ? "+" : ""}{trend.avg_complexity_delta?.toFixed(1) || 0}
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "#9ca3af" }}>complexity</div>
                  </div>

                  {trend.high_impact_commits > 0 && (
                    <div style={{
                      textAlign: "center",
                      padding: "0.25rem 0.5rem",
                      backgroundColor: "#fef2f2",
                      borderRadius: "4px"
                    }}>
                      <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "#dc2626" }}>
                        {trend.high_impact_commits}
                      </div>
                      <div style={{ fontSize: "0.7rem", color: "#9ca3af" }}>high impact</div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{
        marginTop: "2rem",
        padding: "1rem",
        backgroundColor: "#f9fafb",
        borderRadius: "6px",
        fontSize: "0.75rem",
        color: "#6b7280"
      }}>
        <strong>How it works:</strong> Complexity is calculated locally using AST parsing (Python) 
        and heuristics (other languages). Risk scores range from 0-100 based on cyclomatic complexity, 
        cognitive complexity, and nesting depth. Data is stored in Supabase and fetched directly by the dashboard 
        without processing on Render.
      </div>
    </div>
  );
}
