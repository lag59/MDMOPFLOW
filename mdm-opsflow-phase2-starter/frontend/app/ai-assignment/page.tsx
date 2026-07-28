"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

interface Assignment {
  ticket_id: string;
  project_id: string;
  confidence: number;
  match_info: string;
}

export default function AIAssignmentPage() {
  const router = useRouter();
  const [confidenceThreshold, setConfidenceThreshold] = useState("0.75");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAutoAssign = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const token = getAccessToken();
      const tenantId = getTenantId();
      const baseUrl = getApiBaseUrl();

      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (tenantId) headers["X-Tenant-ID"] = tenantId;

      const threshold = parseFloat(confidenceThreshold);
      if (isNaN(threshold) || threshold < 0.5 || threshold > 1.0) {
        throw new Error("Confidence threshold must be between 0.5 and 1.0");
      }

      const res = await fetch(
        `${baseUrl}/api/ai/tickets/auto-assign?confidence_threshold=${threshold}`,
        {
          method: "POST",
          headers,
        }
      );

      if (!res.ok) {
        throw new Error("Failed to run auto-assignment");
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error running auto-assignment");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell titleKey="tickets.title">
      <div className="space-y-6 p-6">
        {/* Header */}
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: "bold", margin: "0 0 8px 0" }}>
            🤖 AI Ticket Assignment
          </h1>
          <p style={{ color: "#666", margin: "0", fontSize: "14px" }}>
            Automatically assign unassigned tickets to projects based on location matching
          </p>
        </div>

        {/* Configuration */}
        <div
          style={{
            padding: "16px",
            backgroundColor: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: "8px",
          }}
        >
          <label style={{ display: "block", marginBottom: "12px" }}>
            <span style={{ fontWeight: "600", display: "block", marginBottom: "8px" }}>
              Confidence Threshold (0.5 - 1.0)
            </span>
            <p style={{ fontSize: "12px", color: "#666", margin: "0 0 8px 0" }}>
              Higher values are more conservative (fewer assignments, higher quality). Lower values assign more
              tickets (more matches, potentially lower quality).
            </p>
            <input
              type="number"
              min="0.5"
              max="1.0"
              step="0.05"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                fontSize: "14px",
              }}
            />
            <div style={{ fontSize: "12px", color: "#888", marginTop: "8px" }}>
              <div>• 0.90+: Excellent matches only</div>
              <div>• 0.75: Good balance (default)</div>
              <div>• 0.50: Include all possible matches</div>
            </div>
          </label>

          <button
            onClick={handleAutoAssign}
            disabled={loading}
            style={{
              padding: "10px 20px",
              backgroundColor: loading ? "#cbd5e1" : "#0ea5e9",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: "14px",
              fontWeight: "600",
              transition: "all 200ms",
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                (e.target as HTMLButtonElement).style.backgroundColor = "#0284c7";
                (e.target as HTMLButtonElement).style.boxShadow = "0 4px 12px rgba(2,132,199,0.3)";
              }
            }}
            onMouseLeave={(e) => {
              if (!loading) {
                (e.target as HTMLButtonElement).style.backgroundColor = "#0ea5e9";
                (e.target as HTMLButtonElement).style.boxShadow = "none";
              }
            }}
          >
            {loading ? "🔄 Running Assignment..." : "▶️ Run AI Auto-Assignment"}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div
            style={{
              padding: "12px",
              backgroundColor: "#fee2e2",
              border: "1px solid #fecaca",
              borderRadius: "6px",
              color: "#991b1b",
              fontSize: "14px",
            }}
          >
            ⚠️ {error}
          </div>
        )}

        {/* Results Display */}
        {result && (
          <div
            style={{
              padding: "16px",
              backgroundColor: "#f0fdf4",
              border: "1px solid #86efac",
              borderRadius: "8px",
            }}
          >
            <h2 style={{ margin: "0 0 16px 0", fontSize: "18px", fontWeight: "bold" }}>
              ✅ Assignment Complete
            </h2>

            {/* Summary Stats */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: "12px",
                marginBottom: "16px",
              }}
            >
              <div
                style={{
                  padding: "12px",
                  backgroundColor: "white",
                  border: "1px solid #86efac",
                  borderRadius: "6px",
                }}
              >
                <div style={{ fontSize: "12px", color: "#666" }}>Total Unassigned</div>
                <div style={{ fontSize: "24px", fontWeight: "bold", color: "#059669" }}>
                  {result.total_unassigned}
                </div>
              </div>

              <div
                style={{
                  padding: "12px",
                  backgroundColor: "white",
                  border: "1px solid #86efac",
                  borderRadius: "6px",
                }}
              >
                <div style={{ fontSize: "12px", color: "#666" }}>Successfully Assigned</div>
                <div style={{ fontSize: "24px", fontWeight: "bold", color: "#10b981" }}>
                  {result.assigned}
                </div>
              </div>

              <div
                style={{
                  padding: "12px",
                  backgroundColor: "white",
                  border: "1px solid #86efac",
                  borderRadius: "6px",
                }}
              >
                <div style={{ fontSize: "12px", color: "#666" }}>No Destination</div>
                <div style={{ fontSize: "24px", fontWeight: "bold", color: "#6b7280" }}>
                  {result.skipped_no_destination}
                </div>
              </div>

              <div
                style={{
                  padding: "12px",
                  backgroundColor: "white",
                  border: "1px solid #86efac",
                  borderRadius: "6px",
                }}
              >
                <div style={{ fontSize: "12px", color: "#666" }}>Low Confidence</div>
                <div style={{ fontSize: "24px", fontWeight: "bold", color: "#f59e0b" }}>
                  {result.skipped_low_confidence}
                </div>
              </div>
            </div>

            {/* Assignment Details */}
            {result.assignments && result.assignments.length > 0 && (
              <div>
                <h3 style={{ margin: "0 0 12px 0", fontSize: "16px", fontWeight: "600" }}>
                  Assigned Tickets ({result.assignments.length})
                </h3>
                <div
                  style={{
                    maxHeight: "400px",
                    overflowY: "auto",
                    display: "grid",
                    gap: "8px",
                  }}
                >
                  {result.assignments.map((assignment: Assignment, idx: number) => (
                    <div
                      key={assignment.ticket_id}
                      style={{
                        padding: "10px",
                        backgroundColor: "white",
                        border: "1px solid #d1fae5",
                        borderRadius: "4px",
                        fontSize: "13px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
                        <strong>Ticket #{idx + 1}</strong>
                        <span
                          style={{
                            padding: "2px 8px",
                            backgroundColor: "#dcfce7",
                            color: "#166534",
                            borderRadius: "12px",
                            fontSize: "11px",
                          }}
                        >
                          {Math.round(assignment.confidence * 100)}% confidence
                        </span>
                      </div>
                      <div style={{ color: "#666", marginTop: "4px" }}>
                        {assignment.match_info}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
              <button
                onClick={() => router.push("/ticket-manager")}
                style={{
                  padding: "10px 20px",
                  backgroundColor: "#0ea5e9",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: "600",
                }}
              >
                📋 View Tickets
              </button>
              <button
                onClick={() => {
                  setResult(null);
                  setError(null);
                }}
                style={{
                  padding: "10px 20px",
                  backgroundColor: "#e5e7eb",
                  color: "#1f2937",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: "600",
                }}
              >
                ↻ Run Again
              </button>
            </div>
          </div>
        )}

        {/* Info Box */}
        <div
          style={{
            padding: "12px",
            backgroundColor: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: "6px",
            fontSize: "13px",
            color: "#1e40af",
          }}
        >
          <strong>ℹ️ How it works:</strong> The AI compares ticket destination locations with project addresses
          using fuzzy matching. Only tickets without an assigned project are processed. Assignments respect the
          confidence threshold you set above.
        </div>
      </div>
    </AppShell>
  );
}
