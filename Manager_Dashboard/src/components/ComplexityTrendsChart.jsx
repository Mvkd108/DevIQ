import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "https://jkwubrrronkyfpmdlvwd.supabase.co";
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || import.meta.env.VITE_SUPABASE_KEY || "";

const supabase = createClient(supabaseUrl, supabaseKey);

export default function ComplexityTrendsChart() {
  const [trendData, setTrendData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState("4weeks"); // 1week, 4weeks, 3months

  useEffect(() => {
    fetchTrendData();
  }, [timeRange]);

  const fetchTrendData = async () => {
    setLoading(true);
    
    try {
      // Calculate date range
      const now = new Date();
      let startDate;
      switch (timeRange) {
        case "1week":
          startDate = new Date(now - 7 * 24 * 60 * 60 * 1000);
          break;
        case "4weeks":
          startDate = new Date(now - 28 * 24 * 60 * 60 * 1000);
          break;
        case "3months":
          startDate = new Date(now - 90 * 24 * 60 * 60 * 1000);
          break;
        default:
          startDate = new Date(now - 28 * 24 * 60 * 60 * 1000);
      }

      // Fetch complexity data over time
      const { data, error } = await supabase
        .from("commit_complexity_analysis")
        .select("timestamp, max_file_complexity, architectural_impact, author")
        .gte("timestamp", startDate.toISOString())
        .order("timestamp", { ascending: true });

      if (error) {
        console.error("Error fetching trend data:", error);
        return;
      }

      // Aggregate by day
      const dailyData = aggregateByDay(data || []);
      setTrendData(dailyData);
      
    } catch (e) {
      console.error("Error:", e);
    } finally {
      setLoading(false);
    }
  };

  const aggregateByDay = (commits) => {
    const grouped = {};
    
    commits.forEach(commit => {
      const date = new Date(commit.timestamp).toLocaleDateString();
      if (!grouped[date]) {
        grouped[date] = {
          date,
          totalComplexity: 0,
          count: 0,
          maxComplexity: 0,
          criticalCount: 0,
          highCount: 0
        };
      }
      
      grouped[date].totalComplexity += commit.max_file_complexity || 0;
      grouped[date].count += 1;
      grouped[date].maxComplexity = Math.max(grouped[date].maxComplexity, commit.max_file_complexity || 0);
      
      if (commit.architectural_impact === "critical") {
        grouped[date].criticalCount += 1;
      } else if (commit.architectural_impact === "high") {
        grouped[date].highCount += 1;
      }
    });
    
    return Object.values(grouped).map(day => ({
      ...day,
      avgComplexity: day.count > 0 ? day.totalComplexity / day.count : 0
    }));
  };

  // Calculate max for scaling
  const maxAvgComplexity = Math.max(...trendData.map(d => d.avgComplexity), 1);
  const maxCritical = Math.max(...trendData.map(d => d.criticalCount + d.highCount), 1);

  if (loading) {
    return <div style={{ padding: "1rem", textAlign: "center", color: "#6b7280" }}>Loading trends...</div>;
  }

  if (trendData.length === 0) {
    return <div style={{ padding: "1rem", textAlign: "center", color: "#6b7280" }}>No trend data available</div>;
  }

  return (
    <div style={{ padding: "1.5rem", backgroundColor: "white", borderRadius: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#1f2937" }}>
          Complexity Trends
        </h3>
        
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {["1week", "4weeks", "3months"].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              style={{
                padding: "0.375rem 0.75rem",
                fontSize: "0.75rem",
                borderRadius: "4px",
                border: "none",
                cursor: "pointer",
                backgroundColor: timeRange === range ? "#3b82f6" : "#f3f4f6",
                color: timeRange === range ? "white" : "#4b5563"
              }}
            >
              {range === "1week" ? "1 Week" : range === "4weeks" ? "4 Weeks" : "3 Months"}
            </button>
          ))}
        </div>
      </div>

      {/* Simple bar chart */}
      <div style={{ display: "flex", alignItems: "flex-end", gap: "2px", height: "200px", padding: "0 0 30px 0", position: "relative" }}>
        {trendData.map((day, idx) => (
          <div
            key={day.date}
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "2px",
              position: "relative"
            }}
          >
            {/* Average complexity bar */}
            <div
              style={{
                width: "100%",
                height: `${(day.avgComplexity / maxAvgComplexity) * 150}px`,
                backgroundColor: day.avgComplexity > 50 ? "#fca5a5" : day.avgComplexity > 30 ? "#fcd34d" : "#86efac",
                borderRadius: "2px 2px 0 0",
                minHeight: "4px",
                transition: "all 0.3s ease"
              }}
              title={`Avg Complexity: ${day.avgComplexity.toFixed(1)}`}
            />
            
            {/* Critical/High impact indicator */}
            {(day.criticalCount > 0 || day.highCount > 0) && (
              <div
                style={{
                  width: "100%",
                  height: `${((day.criticalCount + day.highCount) / maxCritical) * 40}px`,
                  backgroundColor: day.criticalCount > 0 ? "#dc2626" : "#ea580c",
                  borderRadius: "2px",
                  minHeight: "2px"
                }}
                title={`Critical: ${day.criticalCount}, High: ${day.highCount}`}
              />
            )}
            
            {/* Date label (show every 3rd label to avoid crowding) */}
            {idx % 3 === 0 && (
              <div
                style={{
                  position: "absolute",
                  bottom: "-25px",
                  fontSize: "0.65rem",
                  color: "#9ca3af",
                  transform: "rotate(-45deg)",
                  transformOrigin: "left center",
                  whiteSpace: "nowrap"
                }}
              >
                {new Date(day.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div style={{ display: "flex", gap: "1.5rem", marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid #e5e7eb" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div style={{ width: "12px", height: "12px", backgroundColor: "#86efac", borderRadius: "2px" }} />
          <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>Low Complexity (&lt;30)</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div style={{ width: "12px", height: "12px", backgroundColor: "#fcd34d", borderRadius: "2px" }} />
          <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>Medium (30-50)</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div style={{ width: "12px", height: "12px", backgroundColor: "#fca5a5", borderRadius: "2px" }} />
          <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>High (&gt;50)</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div style={{ width: "12px", height: "12px", backgroundColor: "#dc2626", borderRadius: "2px" }} />
          <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>Critical Commits</span>
        </div>
      </div>
    </div>
  );
}
