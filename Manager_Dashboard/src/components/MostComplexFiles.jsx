import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "https://jkwubrrronkyfpmdlvwd.supabase.co";
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || import.meta.env.VITE_SUPABASE_KEY || "";

const supabase = createClient(supabaseUrl, supabaseKey);

export default function MostComplexFiles() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all"); // all, python, javascript, other

  useEffect(() => {
    fetchComplexFiles();
  }, [filter]);

  const fetchComplexFiles = async () => {
    setLoading(true);
    
    try {
      let query = supabase
        .from("file_complexity_snapshots")
        .select("*")
        .order("risk_score", { ascending: false })
        .limit(20);

      if (filter !== "all") {
        if (filter === "python") {
          query = query.eq("language", "python");
        } else if (filter === "javascript") {
          query = query.in("language", ["javascript", "typescript"]);
        } else {
          query = query.not("language", "in", "(python,javascript,typescript)");
        }
      }

      const { data, error } = await query;

      if (error) {
        console.error("Error fetching complex files:", error);
        return;
      }

      setFiles(data || []);
    } catch (e) {
      console.error("Error:", e);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score) => {
    if (score > 70) return "#dc2626";
    if (score > 50) return "#ea580c";
    if (score > 30) return "#ca8a04";
    return "#16a34a";
  };

  const getRiskBg = (score) => {
    if (score > 70) return "#fef2f2";
    if (score > 50) return "#fff7ed";
    if (score > 30) return "#fefce8";
    return "#f0fdf4";
  };

  const getLanguageIcon = (lang) => {
    switch (lang?.toLowerCase()) {
      case "python": return "🐍";
      case "javascript": return "📜";
      case "typescript": return "📘";
      case "java": return "☕";
      case "go": return "🐹";
      case "cpp": case "c": return "⚙️";
      default: return "📄";
    }
  };

  if (loading) {
    return <div style={{ padding: "1rem", textAlign: "center", color: "#6b7280" }}>Loading...</div>;
  }

  return (
    <div style={{ 
      backgroundColor: "white", 
      borderRadius: "8px", 
      boxShadow: "0 1px 3px rgba(0,0,0,0.1)", 
      padding: "1.5rem" 
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#1f2937" }}>
          Most Complex Files ({files.length})
        </h3>
        
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{
            padding: "0.375rem 0.75rem",
            fontSize: "0.875rem",
            borderRadius: "4px",
            border: "1px solid #e5e7eb",
            backgroundColor: "white"
          }}
        >
          <option value="all">All Languages</option>
          <option value="python">Python</option>
          <option value="javascript">JavaScript/TypeScript</option>
          <option value="other">Other</option>
        </select>
      </div>

      {files.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {files.map((file, idx) => (
            <div
              key={`${file.file_path}-${idx}`}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.75rem",
                backgroundColor: getRiskBg(file.risk_score),
                borderRadius: "6px",
                border: `1px solid ${getRiskColor(file.risk_score)}20`
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ fontSize: "1rem" }}>{getLanguageIcon(file.language)}</span>
                  <span style={{ 
                    fontSize: "0.875rem", 
                    fontWeight: "500",
                    color: "#1f2937",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap"
                  }}>
                    {file.file_path?.split('/').pop()}
                  </span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "0.25rem" }}>
                  {file.file_path}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "0.75rem", color: "#9ca3af" }}>
                    {file.lines_of_code} lines
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#6b7280" }}>
                    {file.function_count} functions
                  </div>
                </div>

                <div
                  style={{
                    padding: "0.25rem 0.75rem",
                    backgroundColor: getRiskColor(file.risk_score),
                    color: "white",
                    borderRadius: "4px",
                    fontSize: "0.875rem",
                    fontWeight: "600",
                    minWidth: "50px",
                    textAlign: "center"
                  }}
                >
                  {file.risk_score?.toFixed(0) || 0}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ textAlign: "center", padding: "2rem", color: "#6b7280" }}>
          No files found for the selected filter.
        </div>
      )}
    </div>
  );
}
