"use client";

import React, { useEffect, useState } from "react";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

interface ProjectSuggestion {
  project_id: string;
  project_name: string;
  address: string;
  confidence: number;
  match_reason: string;
}

interface AIProjectSuggestionsProps {
  ticketId: string;
  ticketDestination: string;
  onSelectProject: (projectId: string) => void;
  disabled?: boolean;
}

export default function AIProjectSuggestions({
  ticketId,
  ticketDestination,
  onSelectProject,
  disabled = false,
}: AIProjectSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<ProjectSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const fetchSuggestions = async () => {
      if (!ticketId || disabled) return;

      setLoading(true);
      setError(null);

      try {
        const token = getAccessToken();
        const tenantId = getTenantId();
        const baseUrl = getApiBaseUrl();

        const headers: HeadersInit = {
          "Content-Type": "application/json",
        };
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (tenantId) headers["X-Tenant-ID"] = tenantId;

        const res = await fetch(
          `${baseUrl}/api/ai/tickets/${ticketId}/project-suggestions?top_n=5`,
          { headers }
        );

        if (!res.ok) {
          throw new Error("Failed to fetch suggestions");
        }

        const data = await res.json();
        setSuggestions(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error loading suggestions");
      } finally {
        setLoading(false);
      }
    };

    fetchSuggestions();
  }, [ticketId, disabled]);

  if (disabled || !ticketDestination) {
    return null;
  }

  const confidenceColor = (score: number) => {
    if (score >= 0.9) return "#10b981"; // green
    if (score >= 0.75) return "#f59e0b"; // amber
    return "#ef4444"; // red
  };

  const confidenceLabel = (score: number) => {
    if (score >= 0.9) return "Excellent match";
    if (score >= 0.8) return "Good match";
    if (score >= 0.7) return "Fair match";
    return "Possible match";
  };

  return (
    <div
      style={{
        marginTop: "16px",
        padding: "12px",
        backgroundColor: "#f0fdf4",
        border: "1px solid #86efac",
        borderRadius: "8px",
      }}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: "100%",
          textAlign: "left",
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: "0",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          fontWeight: "600",
          color: "#166534",
          fontSize: "14px",
        }}
        title="Click to view AI-suggested projects for this ticket location"
      >
        <span style={{ fontSize: "18px" }}>🤖</span>
        AI Project Suggestions
        {loading && <span style={{ fontSize: "12px", marginLeft: "auto" }}>Loading...</span>}
        {!loading && (
          <span style={{ fontSize: "12px", marginLeft: "auto", opacity: "0.7" }}>
            {expanded ? "▼" : "▶"}
          </span>
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div style={{ marginTop: "12px" }}>
          {error && (
            <p style={{ color: "#dc2626", fontSize: "12px", margin: "0" }}>
              ⚠️ {error}
            </p>
          )}

          {!loading && suggestions.length === 0 && !error && (
            <p style={{ color: "#666", fontSize: "13px", margin: "0" }}>
              No project suggestions found for destination: {ticketDestination}
            </p>
          )}

          {suggestions.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {suggestions.map((suggestion, index) => (
                <button
                  key={suggestion.project_id}
                  onClick={() => onSelectProject(suggestion.project_id)}
                  style={{
                    padding: "10px 12px",
                    backgroundColor: "#white",
                    border: `2px solid ${confidenceColor(suggestion.confidence)}`,
                    borderRadius: "6px",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "all 200ms",
                    fontSize: "13px",
                  }}
                  onMouseEnter={(e) => {
                    (e.target as HTMLButtonElement).style.backgroundColor = "#ecfdf5";
                    (e.target as HTMLButtonElement).style.boxShadow =
                      "0 4px 12px rgba(16,185,129,0.2)";
                  }}
                  onMouseLeave={(e) => {
                    (e.target as HTMLButtonElement).style.backgroundColor = "white";
                    (e.target as HTMLButtonElement).style.boxShadow = "none";
                  }}
                  title={`Assign to ${suggestion.project_name}`}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", marginBottom: "4px" }}>
                    <strong>{index + 1}. {suggestion.project_name}</strong>
                    <span
                      style={{
                        padding: "2px 8px",
                        backgroundColor: confidenceColor(suggestion.confidence),
                        color: "white",
                        borderRadius: "12px",
                        fontSize: "11px",
                        fontWeight: "600",
                      }}
                    >
                      {Math.round(suggestion.confidence * 100)}%
                    </span>
                  </div>
                  <div style={{ fontSize: "12px", color: "#666" }}>
                    📍 {suggestion.address}
                  </div>
                  <div style={{ fontSize: "11px", color: "#888", marginTop: "4px" }}>
                    {confidenceLabel(suggestion.confidence)}: {suggestion.match_reason}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
