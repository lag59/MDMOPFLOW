"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";
import type { Estimate, CreateEstimatePayload, EstimatorBidPipelineItem } from "@/lib/estimator";

// ── helpers ─────────────────────────────────────────────────────────────────

const fmt = (n: string | number | null | undefined) =>
  n == null || n === "" ? "—" : Number(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const STATUS_COLORS: Record<string, string> = {
  "Draft Estimate":         "#64748b",
  "Pending Review":         "#d97706",
  "Submitted":              "#2563eb",
  "Under Review":           "#7c3aed",
  "Awarded":                "#16a34a",
  "Not Awarded":            "#dc2626",
  "Converted to Project":   "#0891b2",
  "Archived":               "#94a3b8",
};

const STATUS_FLOW: Record<string, string | null> = {
  "Draft Estimate":       "Pending Review",
  "Pending Review":       "Submitted",
  "Submitted":            "Under Review",
  "Under Review":         "Awarded",
  "Awarded":              "Converted to Project",
  "Converted to Project": null,
  "Not Awarded":          null,
  "Archived":             null,
};

const BLANK: Omit<CreateEstimatePayload, "estimate_name" | "estimate_number"> = {
  customer_name: "", project_name: "", project_address: "",
  project_type: "Heavy civil", bid_due_date: "", estimator_name: "",
  project_manager_name: "", contract_type: "Lump sum", estimate_type: "Detailed",
  currency: "USD", target_margin_percent: "15",
  default_overhead_percent: "8", default_contingency_percent: "5", notes: "",
};

// Fields that can be AI-suggested in the create form
type AiSuggestableKey = "target_margin_percent" | "default_overhead_percent" | "default_contingency_percent" | "estimate_type" | "contract_type";

type AiAssistResult = {
  ai_generated: boolean;
  disclaimer: string;
  suggestions: Partial<Record<AiSuggestableKey, string>> & {
    suggested_line_items?: { description: string; category: string; unit: string; quantity: string; unit_cost: string }[];
    rationale?: string;
  };
};

// ── component ────────────────────────────────────────────────────────────────

export default function EstimatorPage() {
  const [estimates, setEstimates]     = useState<Estimate[]>([]);
  const [bids, setBids]               = useState<EstimatorBidPipelineItem[]>([]);
  const [selected, setSelected]       = useState<Estimate | null>(null);
  const [showCreate, setShowCreate]   = useState(false);
  const [saving, setSaving]           = useState(false);
  const [msg, setMsg]                 = useState<{ text: string; ok: boolean } | null>(null);

  // AI assist state
  const [aiRunning, setAiRunning]     = useState(false);
  const [aiResult, setAiResult]       = useState<AiAssistResult | null>(null);
  // Tracks which form fields were filled by AI (vs user-typed)
  const [aiFilledFields, setAiFilledFields] = useState<Set<string>>(new Set());

  const [form, setForm] = useState<CreateEstimatePayload>({
    estimate_name: "", estimate_number: "", ...BLANK,
  });

  // Staged AI line items (user can accept/reject individually)
  const [pendingAiItems, setPendingAiItems] = useState<AiAssistResult["suggestions"]["suggested_line_items"]>([]);

  const api    = getApiBaseUrl();
  const token  = getAccessToken();
  const tenant = getTenantId();

  function headers() {
    return { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "X-Tenant-ID": tenant };
  }

  async function loadEstimates() {
    const r = await fetch(`${api}/api/estimates`, { headers: headers() });
    if (r.ok) setEstimates(await r.json());
  }

  async function loadBids() {
    const r = await fetch(`${api}/api/estimator/bid-pipeline`, { headers: headers() });
    if (r.ok) setBids(await r.json());
  }

  useEffect(() => {
    if (!token) { window.location.href = "/login"; return; }
    loadEstimates();
    loadBids();
  }, []);

  // ── summary counts
  const counts = {
    draft:     estimates.filter(e => e.status === "Draft Estimate").length,
    submitted: estimates.filter(e => e.status === "Submitted").length,
    awarded:   estimates.filter(e => e.status === "Awarded").length,
    converted: estimates.filter(e => e.status === "Converted to Project").length,
  };

  // ── AI assist: requires estimate to exist first, so we create a stub then call ai-assist
  async function runAiAssist() {
    if (!form.estimate_name.trim() || !form.estimate_number.trim()) {
      setMsg({ text: "Enter an estimate name and number before running AI Assist.", ok: false });
      return;
    }
    setAiRunning(true);
    setMsg(null);
    setAiResult(null);

    // Create a temporary stub estimate so the backend has context to work with
    const createRes = await fetch(`${api}/api/estimates`, {
      method: "POST", headers: headers(),
      body: JSON.stringify({ ...form, status: "Draft Estimate" }),
    });
    if (!createRes.ok) {
      const d = await createRes.json().catch(() => null);
      setMsg({ text: d?.detail || "Could not create estimate for AI assist.", ok: false });
      setAiRunning(false);
      return;
    }
    const created: Estimate = await createRes.json();
    setEstimates(prev => [created, ...prev]);

    // Call AI assist
    const aiRes = await fetch(`${api}/api/estimates/${created.id}/ai-assist`, {
      method: "POST", headers: headers(),
    });
    setAiRunning(false);

    if (!aiRes.ok) {
      setSelected(created);
      setShowCreate(false);
      setMsg({ text: "Estimate created. AI assist unavailable — fill in the remaining fields.", ok: true });
      return;
    }

    const result: AiAssistResult = await aiRes.json();
    setAiResult(result);

    // Apply AI suggestions to form fields, track which were AI-filled
    const aiKeys: AiSuggestableKey[] = ["target_margin_percent","default_overhead_percent","default_contingency_percent","estimate_type","contract_type"];
    const filled = new Set<string>();
    const updates: Partial<CreateEstimatePayload> = {};
    for (const key of aiKeys) {
      const val = result.suggestions[key];
      if (val && !form[key as keyof CreateEstimatePayload]) {
        updates[key as keyof CreateEstimatePayload] = val as string;
        filled.add(key);
      }
    }
    if (Object.keys(updates).length > 0) {
      setForm(prev => ({ ...prev, ...updates }));
      setAiFilledFields(filled);
    }
    if (result.suggestions.suggested_line_items?.length) {
      setPendingAiItems(result.suggestions.suggested_line_items);
    }

    setSelected(created);
    setShowCreate(false);
    setMsg({ text: "Estimate created. AI suggestions applied — review each highlighted field before saving.", ok: true });
  }

  // When user edits an AI-filled field, clear its AI badge
  function handleFormChange(key: keyof CreateEstimatePayload, value: string) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (aiFilledFields.has(key as string)) {
      setAiFilledFields(prev => { const s = new Set(prev); s.delete(key as string); return s; });
    }
  }

  // Accept a pending AI line item — save it to the selected estimate
  async function acceptAiLineItem(
    item: NonNullable<AiAssistResult["suggestions"]["suggested_line_items"]>[number],
    index: number,
    estimateId: string,
  ) {
    const r = await fetch(`${api}/api/estimates/${estimateId}/items`, {
      method: "POST", headers: headers(),
      body: JSON.stringify({
        description: item.description,
        category: item.category,
        unit: item.unit,
        quantity: item.quantity,
        unit_cost: item.unit_cost,
        total_cost: String(Number(item.quantity) * Number(item.unit_cost)),
      }),
    });
    if (r.ok) {
      setPendingAiItems(prev => prev?.filter((_, i) => i !== index));
      setMsg({ text: `"${item.description}" added to estimate.`, ok: true });
    }
  }

  // ── create estimate (manual, no AI)
  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.estimate_name.trim() || !form.estimate_number.trim()) {
      setMsg({ text: "Estimate name and number are required.", ok: false });
      return;
    }
    setSaving(true);
    setMsg(null);
    const r = await fetch(`${api}/api/estimates`, {
      method: "POST", headers: headers(), body: JSON.stringify({ ...form, status: "Draft Estimate" }),
    });
    setSaving(false);
    if (r.ok) {
      const created: Estimate = await r.json();
      setEstimates(prev => [created, ...prev]);
      setShowCreate(false);
      setForm({ estimate_name: "", estimate_number: "", ...BLANK });
      setAiFilledFields(new Set());
      setSelected(created);
      setMsg({ text: "Estimate created.", ok: true });
    } else {
      const d = await r.json().catch(() => null);
      setMsg({ text: d?.detail || "Failed to create estimate.", ok: false });
    }
  }

  // ── advance status
  async function advanceStatus(est: Estimate) {
    const next = STATUS_FLOW[est.status];
    if (!next) return;
    setMsg(null);
    const r = await fetch(`${api}/api/estimates/${est.id}`, {
      method: "PATCH", headers: headers(), body: JSON.stringify({ status: next }),
    });
    if (r.ok) {
      const updated: Estimate = await r.json();
      setEstimates(prev => prev.map(e => e.id === updated.id ? updated : e));
      setSelected(updated);
      setMsg({ text: `Status updated to "${next}".`, ok: true });
    } else {
      const d = await r.json().catch(() => null);
      setMsg({ text: d?.detail || "Status update failed.", ok: false });
    }
  }

  async function markNotAwarded(est: Estimate) {
    setMsg(null);
    const r = await fetch(`${api}/api/estimates/${est.id}`, {
      method: "PATCH", headers: headers(), body: JSON.stringify({ status: "Not Awarded" }),
    });
    if (r.ok) {
      const updated: Estimate = await r.json();
      setEstimates(prev => prev.map(e => e.id === updated.id ? updated : e));
      setSelected(updated);
      setMsg({ text: "Marked as Not Awarded.", ok: true });
    } else {
      setMsg({ text: "Failed to update status.", ok: false });
    }
  }

  const pill = (status: string) => (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 999,
      fontSize: 11, fontWeight: 700,
      background: STATUS_COLORS[status] ? STATUS_COLORS[status] + "22" : "#f1f5f9",
      color: STATUS_COLORS[status] ?? "#475569",
      border: `1px solid ${STATUS_COLORS[status] ?? "#cbd5e1"}`,
    }}>{status}</span>
  );

  // AI badge shown next to AI-filled fields
  const AiBadge = () => (
    <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4,
      background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe", marginLeft: 6 }}>
      AI suggested — verify before saving
    </span>
  );

  return (
    <AppShell titleKey="nav.estimator">
      {/* ── Summary metrics */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(4,1fr)", marginBottom: 20 }}>
        {[
          { label: "Draft",     value: counts.draft,     color: "#64748b" },
          { label: "Submitted", value: counts.submitted,  color: "#2563eb" },
          { label: "Awarded",   value: counts.awarded,    color: "#16a34a" },
          { label: "Converted", value: counts.converted,  color: "#0891b2" },
        ].map(m => (
          <div className="card" key={m.label}>
            <div className="metric-note">{m.label} Estimates</div>
            <div className="metric" style={{ color: m.color }}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* ── Feedback banner */}
      {msg && (
        <div style={{ marginBottom: 14, padding: "9px 14px", borderRadius: 8, fontSize: 13,
          background: msg.ok ? "#dcfce7" : "#fee2e2", color: msg.ok ? "#166534" : "#991b1b" }}>
          {msg.text}
        </div>
      )}

      {/* ── AI disclaimer banner when AI results are present */}
      {aiResult && (
        <div style={{ marginBottom: 14, padding: "10px 14px", borderRadius: 8, fontSize: 13,
          background: aiResult.ai_generated ? "#eff6ff" : "#fefce8",
          color: aiResult.ai_generated ? "#1e3a8a" : "#713f12",
          border: `1px solid ${aiResult.ai_generated ? "#bfdbfe" : "#fde68a"}`,
          display: "flex", gap: 10, alignItems: "flex-start" }}>
          <span style={{ fontSize: 16 }}>{aiResult.ai_generated ? "🤖" : "⚠️"}</span>
          <div>
            <strong>{aiResult.ai_generated ? "AI-generated suggestions" : "Template defaults — not AI"}</strong>
            <div style={{ marginTop: 2 }}>{aiResult.disclaimer}</div>
            {aiResult.suggestions.rationale && (
              <div style={{ marginTop: 4, fontStyle: "italic" }}>{aiResult.suggestions.rationale}</div>
            )}
          </div>
          <button className="btn-ghost" style={{ marginLeft: "auto", fontSize: 11, padding: "2px 8px" }}
            onClick={() => setAiResult(null)}>Dismiss</button>
        </div>
      )}

      {/* ── Main layout: list + detail */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>

        {/* Left: estimates list */}
        <div className="card" style={{ flex: "0 0 300px", minWidth: 260 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: 15 }}>Estimates ({estimates.length})</h3>
            <button onClick={() => { setShowCreate(true); setSelected(null); setMsg(null); setAiResult(null); setPendingAiItems([]); }} style={{ fontSize: 12, padding: "5px 10px" }}>
              + New
            </button>
          </div>
          <div className="list" style={{ maxHeight: 560, overflowY: "auto", marginTop: 0 }}>
            {estimates.length === 0 && <p className="muted" style={{ fontSize: 13 }}>No estimates yet.</p>}
            {estimates.map(est => (
              <div key={est.id} className="list-item"
                onClick={() => { setSelected(est); setShowCreate(false); setMsg(null); setAiResult(null); setPendingAiItems([]); }}
                style={{ cursor: "pointer",
                  background: selected?.id === est.id ? "rgba(249,115,22,0.06)" : undefined,
                  borderLeft: selected?.id === est.id ? "3px solid #f97316" : "3px solid transparent",
                  padding: "9px 12px" }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{est.estimate_name}</div>
                <div className="muted" style={{ fontSize: 11 }}>{est.estimate_number} · {est.customer_name || "—"}</div>
                <div style={{ marginTop: 4 }}>{pill(est.status)}</div>
                {est.bid_due_date && (
                  <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>Due {est.bid_due_date}</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right: detail / create panel */}
        <div className="card" style={{ flex: 1 }}>

          {/* Create form */}
          {showCreate && (
            <form onSubmit={handleCreate}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h3 style={{ margin: 0 }}>New Estimate</h3>
                <div style={{ display: "flex", gap: 8 }}>
                  <button type="button" onClick={runAiAssist} disabled={aiRunning}
                    style={{ fontSize: 12, padding: "5px 12px", background: "linear-gradient(135deg,#2563eb,#1d4ed8)" }}>
                    {aiRunning ? "AI thinking…" : "🤖 AI Assist"}
                  </button>
                  <button type="button" className="btn-ghost" onClick={() => setShowCreate(false)} style={{ fontSize: 12 }}>✕ Cancel</button>
                </div>
              </div>

              {/* AI Assist explainer */}
              <div style={{ marginBottom: 14, padding: "8px 12px", borderRadius: 8, fontSize: 12,
                background: "#f0fdf4", color: "#166534", border: "1px solid #bbf7d0" }}>
                Enter a <strong>name</strong>, <strong>number</strong>, and optionally a customer or project type, then click <strong>🤖 AI Assist</strong>. 
                AI will pre-fill suggested values. Fields filled by AI will be clearly labelled — you can edit any of them freely before saving.
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {([
                  ["Estimate Name *",    "estimate_name",           "text"],
                  ["Estimate Number *",  "estimate_number",         "text"],
                  ["Customer Name",      "customer_name",           "text"],
                  ["Project Name",       "project_name",            "text"],
                  ["Project Address",    "project_address",         "text"],
                  ["Bid Due Date",       "bid_due_date",            "date"],
                  ["Estimator",         "estimator_name",           "text"],
                  ["Project Manager",   "project_manager_name",     "text"],
                ] as [string, keyof CreateEstimatePayload, string][]).map(([label, key, type]) => (
                  <label key={key} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                    {label}
                    <input type={type} value={(form[key] as string) ?? ""}
                      onChange={e => handleFormChange(key, e.target.value)} />
                  </label>
                ))}

                {/* AI-suggestable fields */}
                {([
                  ["Target Margin %",   "target_margin_percent",    "number"],
                  ["Overhead %",        "default_overhead_percent", "number"],
                  ["Contingency %",     "default_contingency_percent","number"],
                ] as [string, AiSuggestableKey, string][]).map(([label, key, type]) => (
                  <label key={key} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                    <span>{label}{aiFilledFields.has(key) && <AiBadge />}</span>
                    <input type={type}
                      style={{ borderColor: aiFilledFields.has(key) ? "#93c5fd" : undefined,
                               background: aiFilledFields.has(key) ? "#eff6ff" : undefined }}
                      value={(form[key] as string) ?? ""}
                      onChange={e => handleFormChange(key, e.target.value)} />
                  </label>
                ))}

                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  <span>Project Type</span>
                  <select value={form.project_type} onChange={e => handleFormChange("project_type", e.target.value)}>
                    {["Heavy civil","Site development","Excavation","Grading","Underground utilities","Hauling","Demolition","Paving","Landscaping","General construction","Other"].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>

                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  <span>Contract Type{aiFilledFields.has("contract_type") && <AiBadge />}</span>
                  <select
                    style={{ borderColor: aiFilledFields.has("contract_type") ? "#93c5fd" : undefined,
                             background: aiFilledFields.has("contract_type") ? "#eff6ff" : undefined }}
                    value={form.contract_type}
                    onChange={e => handleFormChange("contract_type", e.target.value)}>
                    {["Lump sum","Unit price","Cost plus","Time and materials","GMP","Design-build"].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>

                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  <span>Estimate Type{aiFilledFields.has("estimate_type") && <AiBadge />}</span>
                  <select
                    style={{ borderColor: aiFilledFields.has("estimate_type") ? "#93c5fd" : undefined,
                             background: aiFilledFields.has("estimate_type") ? "#eff6ff" : undefined }}
                    value={form.estimate_type}
                    onChange={e => handleFormChange("estimate_type", e.target.value)}>
                    {["Conceptual","Preliminary","Budgetary","Detailed","Bid","Change-order estimate"].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>
              </div>

              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, marginTop: 12 }}>
                Notes
                <textarea rows={3} value={form.notes} onChange={e => handleFormChange("notes", e.target.value)} />
              </label>

              <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
                <button type="submit" disabled={saving}>{saving ? "Saving…" : "Create Estimate"}</button>
                <button type="button" className="btn-ghost" onClick={() => setShowCreate(false)}>Cancel</button>
              </div>
            </form>
          )}

          {/* Detail panel */}
          {!showCreate && selected && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                <div>
                  <h3 style={{ margin: 0, marginBottom: 2 }}>{selected.estimate_name}</h3>
                  <div className="muted" style={{ fontSize: 12 }}>{selected.estimate_number} · {selected.customer_name || "—"}</div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  {pill(selected.status)}
                  {STATUS_FLOW[selected.status] && (
                    <button onClick={() => advanceStatus(selected)} style={{ fontSize: 12, padding: "5px 12px" }}>
                      Advance → {STATUS_FLOW[selected.status]}
                    </button>
                  )}
                  {["Submitted","Under Review","Awarded"].includes(selected.status) && (
                    <button onClick={() => markNotAwarded(selected)} className="btn-danger" style={{ fontSize: 12, padding: "5px 12px" }}>
                      Not Awarded
                    </button>
                  )}
                </div>
              </div>

              {/* Status progress bar */}
              <div style={{ marginTop: 16, display: "flex", gap: 4, flexWrap: "wrap" }}>
                {Object.keys(STATUS_FLOW).filter(s => !["Not Awarded","Archived"].includes(s)).map(s => {
                  const statuses = ["Draft Estimate","Pending Review","Submitted","Under Review","Awarded","Converted to Project"];
                  const current  = statuses.indexOf(selected.status);
                  const idx      = statuses.indexOf(s);
                  const done     = idx <= current;
                  return (
                    <div key={s} style={{ fontSize: 10, fontWeight: done ? 700 : 400,
                      padding: "3px 8px", borderRadius: 4,
                      background: done ? (STATUS_COLORS[s] + "22") : "#f1f5f9",
                      color: done ? STATUS_COLORS[s] : "#94a3b8",
                      border: `1px solid ${done ? STATUS_COLORS[s] : "#e2e8f0"}` }}>
                      {s}
                    </div>
                  );
                })}
              </div>

              {/* Details grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 20, borderTop: "1px solid #e2e8f0", paddingTop: 16 }}>
                {[
                  ["Project",        selected.project_name],
                  ["Customer",       selected.customer_name],
                  ["Project Type",   selected.project_type],
                  ["Contract",       selected.contract_type],
                  ["Estimate Type",  selected.estimate_type],
                  ["Bid Due Date",   selected.bid_due_date],
                  ["Estimator",      selected.estimator_name],
                  ["Project Mgr",    selected.project_manager_name],
                  ["Target Margin",  selected.target_margin_percent ? `${selected.target_margin_percent}%` : "—"],
                  ["Overhead",       selected.default_overhead_percent ? `${selected.default_overhead_percent}%` : "—"],
                  ["Contingency",    selected.default_contingency_percent ? `${selected.default_contingency_percent}%` : "—"],
                  ["Created",        selected.created_at?.slice(0,10)],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#64748b" }}>{label}</div>
                    <div style={{ fontSize: 13, marginTop: 2 }}>{value || "—"}</div>
                  </div>
                ))}
              </div>

              {selected.notes && (
                <div style={{ marginTop: 16, padding: "10px 14px", background: "#f8fafc", borderRadius: 8, fontSize: 13 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>Notes</div>
                  {selected.notes}
                </div>
              )}

              {/* Pending AI line items */}
              {pendingAiItems && pendingAiItems.length > 0 && (
                <div style={{ marginTop: 20, borderTop: "1px solid #e2e8f0", paddingTop: 16 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <h4 style={{ margin: 0 }}>🤖 AI-suggested line items</h4>
                    <span style={{ fontSize: 11, color: "#1d4ed8" }}>These were NOT saved yet — accept each one individually</span>
                  </div>
                  <div style={{ fontSize: 12, color: "#92400e", background: "#fefce8", border: "1px solid #fde68a",
                    borderRadius: 6, padding: "6px 10px", marginBottom: 8 }}>
                    ⚠️ These line items were suggested by AI based on the project type. Verify quantities and costs against your actual scope before accepting.
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {pendingAiItems.map((item, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px",
                        border: "1px solid #bfdbfe", borderRadius: 8, background: "#eff6ff", fontSize: 13 }}>
                        <div style={{ flex: 1 }}>
                          <strong>{item.description}</strong>
                          <span className="muted" style={{ marginLeft: 8 }}>{item.category} · {item.quantity} {item.unit} @ {fmt(item.unit_cost)}/each</span>
                        </div>
                        <button onClick={() => acceptAiLineItem(item, i, selected.id)}
                          style={{ fontSize: 11, padding: "3px 10px", background: "linear-gradient(135deg,#16a34a,#15803d)" }}>
                          Accept
                        </button>
                        <button className="btn-ghost" onClick={() => setPendingAiItems(prev => prev?.filter((_,idx) => idx !== i))}
                          style={{ fontSize: 11, padding: "3px 8px" }}>
                          Dismiss
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {!showCreate && !selected && (
            <p className="muted" style={{ marginTop: 0 }}>Select an estimate from the list, or click <strong>+ New</strong> to create one.</p>
          )}
        </div>
      </div>

      {/* ── Bid Pipeline */}
      {bids.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Bid Pipeline</h3>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", textAlign: "left" }}>
                  {["Bid #","Customer","Stage","Bid Amount","Probability","Due Date","Status"].map(h => (
                    <th key={h} style={{ padding: "8px 12px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "#64748b" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bids.map(bid => (
                  <tr key={bid.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "9px 12px", fontWeight: 600 }}>{bid.bid_number}</td>
                    <td style={{ padding: "9px 12px" }}>{bid.customer_name}</td>
                    <td style={{ padding: "9px 12px" }}>{bid.stage}</td>
                    <td style={{ padding: "9px 12px" }}>{fmt(bid.bid_amount)}</td>
                    <td style={{ padding: "9px 12px" }}>{bid.probability_percent ? `${bid.probability_percent}%` : "—"}</td>
                    <td style={{ padding: "9px 12px" }}>{bid.due_date ?? "—"}</td>
                    <td style={{ padding: "9px 12px" }}>{bid.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppShell>
  );
}

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";
import type { Estimate, CreateEstimatePayload, EstimatorBidPipelineItem } from "@/lib/estimator";

// ── types ────────────────────────────────────────────────────────────────────

type EstimateItem = {
  id: string;
  item_number: string;
  cost_code: string;
  description: string;
  quantity: string;
  unit_of_measure: string;
  unit_cost: string;
  total_cost: string;
  notes: string;
};

type NewItemDraft = {
  item_number: string;
  cost_code: string;
  description: string;
  quantity: string;
  unit_of_measure: string;
  unit_cost: string;
  notes: string;
};

const fmt = (n: string | number | null | undefined) =>
  n == null || n === "" ? "—" : Number(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const STATUS_COLORS: Record<string, string> = {
  "Draft Estimate":         "#64748b",
  "Pending Review":         "#d97706",
  "Submitted":              "#2563eb",
  "Under Review":           "#7c3aed",
  "Awarded":                "#16a34a",
  "Not Awarded":            "#dc2626",
  "Converted to Project":   "#0891b2",
  "Archived":               "#94a3b8",
};

const STATUS_FLOW: Record<string, string | null> = {
  "Draft Estimate":       "Pending Review",
  "Pending Review":       "Submitted",
  "Submitted":            "Under Review",
  "Under Review":         "Awarded",
  "Awarded":              "Converted to Project",
  "Converted to Project": null,
  "Not Awarded":          null,
  "Archived":             null,
};

const BLANK: Omit<CreateEstimatePayload, "estimate_name" | "estimate_number"> = {
  customer_name: "", project_name: "", project_address: "",
  project_type: "Heavy civil", bid_due_date: "", estimator_name: "",
  project_manager_name: "", contract_type: "Lump sum", estimate_type: "Detailed",
  currency: "USD", target_margin_percent: "15",
  default_overhead_percent: "8", default_contingency_percent: "5", notes: "",
};

// ── component ────────────────────────────────────────────────────────────────

export default function EstimatorPage() {
  const [estimates, setEstimates]     = useState<Estimate[]>([]);
  const [bids, setBids]               = useState<EstimatorBidPipelineItem[]>([]);
  const [selected, setSelected]       = useState<Estimate | null>(null);
  const [items, setItems]             = useState<EstimateItem[]>([]);
  const [showCreate, setShowCreate]   = useState(false);
  const [saving, setSaving]           = useState(false);
  const [addingItem, setAddingItem]   = useState(false);
  const [itemSaving, setItemSaving]   = useState(false);
  const [msg, setMsg]                 = useState<{ text: string; ok: boolean } | null>(null);

  const BLANK_ITEM: NewItemDraft = {
    item_number: "", cost_code: "", description: "", quantity: "1",
    unit_of_measure: "LS", unit_cost: "0", notes: "",
  };
  const [newItem, setNewItem] = useState<NewItemDraft>(BLANK_ITEM);

  const [form, setForm] = useState<CreateEstimatePayload>({
    estimate_name: "", estimate_number: "", ...BLANK,
  });

  const api    = getApiBaseUrl();
  const token  = getAccessToken();
  const tenant = getTenantId();

  function headers() {
    return { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "X-Tenant-ID": tenant };
  }

  async function loadEstimates() {
    const r = await fetch(`${api}/api/estimates`, { headers: headers() });
    if (r.ok) setEstimates(await r.json());
  }

  async function loadBids() {
    const r = await fetch(`${api}/api/estimator/bid-pipeline`, { headers: headers() });
    if (r.ok) setBids(await r.json());
  }

  async function loadItems(estimateId: string) {
    const r = await fetch(`${api}/api/estimates/${estimateId}/items`, { headers: headers() });
    if (r.ok) setItems(await r.json());
    else setItems([]);
  }

  useEffect(() => {
    if (!token) { window.location.href = "/login"; return; }
    loadEstimates();
    loadBids();
  }, []);

  // ── totals
  const totalCost = items.reduce((s, i) => s + Number(i.total_cost || 0), 0);
  const overhead = totalCost * (Number(selected?.default_overhead_percent || 0) / 100);
  const contingency = totalCost * (Number(selected?.default_contingency_percent || 0) / 100);
  const margin = (totalCost + overhead + contingency) * (Number(selected?.target_margin_percent || 0) / 100);
  const grandTotal = totalCost + overhead + contingency + margin;

  // ── save line item
  async function saveItem(e: React.FormEvent) {
    e.preventDefault();
    if (!selected || !newItem.description.trim()) {
      setMsg({ text: "Description is required.", ok: false });
      return;
    }
    setItemSaving(true);
    setMsg(null);
    const qty = Number(newItem.quantity) || 0;
    const uc  = Number(newItem.unit_cost) || 0;
    const r = await fetch(`${api}/api/estimates/${selected.id}/items`, {
      method: "POST", headers: headers(),
      body: JSON.stringify({
        item_number: newItem.item_number,
        cost_code: newItem.cost_code,
        description: newItem.description,
        quantity: String(qty),
        unit_of_measure: newItem.unit_of_measure,
        unit_cost: String(uc),
        total_cost: String(qty * uc),
        notes: newItem.notes,
      }),
    });
    setItemSaving(false);
    if (r.ok) {
      await loadItems(selected.id);
      setNewItem(BLANK_ITEM);
      setAddingItem(false);
      setMsg({ text: "Line item added.", ok: true });
    } else {
      const d = await r.json().catch(() => null);
      setMsg({ text: d?.detail || "Failed to add item.", ok: false });
    }
  }

  // ── create estimate
  const counts = {
    draft:     estimates.filter(e => e.status === "Draft Estimate").length,
    submitted: estimates.filter(e => e.status === "Submitted").length,
    awarded:   estimates.filter(e => e.status === "Awarded").length,
    converted: estimates.filter(e => e.status === "Converted to Project").length,
  };

  // ── create estimate
  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.estimate_name.trim() || !form.estimate_number.trim()) {
      setMsg({ text: "Estimate name and number are required.", ok: false });
      return;
    }
    setSaving(true);
    setMsg(null);
    const r = await fetch(`${api}/api/estimates`, {
      method: "POST", headers: headers(), body: JSON.stringify({ ...form, status: "Draft Estimate" }),
    });
    setSaving(false);
    if (r.ok) {
      const created: Estimate = await r.json();
      setEstimates(prev => [created, ...prev]);
      setShowCreate(false);
      setForm({ estimate_name: "", estimate_number: "", ...BLANK });
      setSelected(created);
      setMsg({ text: "Estimate created.", ok: true });
    } else {
      const d = await r.json().catch(() => null);
      setMsg({ text: d?.detail || "Failed to create estimate.", ok: false });
    }
  }

  // ── advance status
  async function advanceStatus(est: Estimate) {
    const next = STATUS_FLOW[est.status];
    if (!next) return;
    setMsg(null);
    const r = await fetch(`${api}/api/estimates/${est.id}`, {
      method: "PATCH", headers: headers(), body: JSON.stringify({ status: next }),
    });
    if (r.ok) {
      const updated: Estimate = await r.json();
      setEstimates(prev => prev.map(e => e.id === updated.id ? updated : e));
      setSelected(updated);
      setMsg({ text: `Status updated to "${next}".`, ok: true });
    } else {
      const d = await r.json().catch(() => null);
      setMsg({ text: d?.detail || "Status update failed.", ok: false });
    }
  }

  // ── mark not awarded
  async function markNotAwarded(est: Estimate) {
    setMsg(null);
    const r = await fetch(`${api}/api/estimates/${est.id}`, {
      method: "PATCH", headers: headers(), body: JSON.stringify({ status: "Not Awarded" }),
    });
    if (r.ok) {
      const updated: Estimate = await r.json();
      setEstimates(prev => prev.map(e => e.id === updated.id ? updated : e));
      setSelected(updated);
      setMsg({ text: "Marked as Not Awarded.", ok: true });
    } else {
      setMsg({ text: "Failed to update status.", ok: false });
    }
  }

  const pill = (status: string) => (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 999,
      fontSize: 11, fontWeight: 700,
      background: STATUS_COLORS[status] ? STATUS_COLORS[status] + "22" : "#f1f5f9",
      color: STATUS_COLORS[status] ?? "#475569",
      border: `1px solid ${STATUS_COLORS[status] ?? "#cbd5e1"}`,
    }}>{status}</span>
  );

  return (
    <AppShell titleKey="nav.estimator">
      {/* ── Summary metrics */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(4,1fr)", marginBottom: 20 }}>
        {[
          { label: "Draft",     value: counts.draft,     color: "#64748b" },
          { label: "Submitted", value: counts.submitted,  color: "#2563eb" },
          { label: "Awarded",   value: counts.awarded,    color: "#16a34a" },
          { label: "Converted", value: counts.converted,  color: "#0891b2" },
        ].map(m => (
          <div className="card" key={m.label}>
            <div className="metric-note">{m.label} Estimates</div>
            <div className="metric" style={{ color: m.color }}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* ── Feedback banner */}
      {msg && (
        <div style={{ marginBottom: 14, padding: "9px 14px", borderRadius: 8, fontSize: 13,
          background: msg.ok ? "#dcfce7" : "#fee2e2", color: msg.ok ? "#166534" : "#991b1b" }}>
          {msg.text}
        </div>
      )}

      {/* ── Main layout: list + detail */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>

        {/* Left: estimates list */}
        <div className="card" style={{ flex: "0 0 300px", minWidth: 260 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: 15 }}>Estimates ({estimates.length})</h3>
            <button onClick={() => { setShowCreate(true); setSelected(null); setMsg(null); }} style={{ fontSize: 12, padding: "5px 10px" }}>
              + New
            </button>
          </div>
          <div className="list" style={{ maxHeight: 560, overflowY: "auto", marginTop: 0 }}>
            {estimates.length === 0 && <p className="muted" style={{ fontSize: 13 }}>No estimates yet.</p>}
            {estimates.map(est => (
              <div key={est.id} className="list-item"
                onClick={() => {
                  setSelected(est); setShowCreate(false); setMsg(null);
                  setAddingItem(false); setNewItem(BLANK_ITEM);
                  loadItems(est.id);
                }}
                style={{ cursor: "pointer",
                  background: selected?.id === est.id ? "rgba(249,115,22,0.06)" : undefined,
                  borderLeft: selected?.id === est.id ? "3px solid #f97316" : "3px solid transparent",
                  padding: "9px 12px" }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{est.estimate_name}</div>
                <div className="muted" style={{ fontSize: 11 }}>{est.estimate_number} · {est.customer_name || "—"}</div>
                <div style={{ marginTop: 4 }}>{pill(est.status)}</div>
                {est.bid_due_date && (
                  <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>Due {est.bid_due_date}</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right: detail / create panel */}
        <div className="card" style={{ flex: 1 }}>

          {/* Create form */}
          {showCreate && (
            <form onSubmit={handleCreate}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h3 style={{ margin: 0 }}>New Estimate</h3>
                <button type="button" className="btn-ghost" onClick={() => setShowCreate(false)} style={{ fontSize: 12 }}>✕ Cancel</button>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {([
                  ["Estimate Name *",    "estimate_name",           "text"],
                  ["Estimate Number *",  "estimate_number",         "text"],
                  ["Customer Name",      "customer_name",           "text"],
                  ["Project Name",       "project_name",            "text"],
                  ["Project Address",    "project_address",         "text"],
                  ["Bid Due Date",       "bid_due_date",            "date"],
                  ["Estimator",         "estimator_name",           "text"],
                  ["Project Manager",   "project_manager_name",     "text"],
                  ["Target Margin %",   "target_margin_percent",    "number"],
                  ["Overhead %",        "default_overhead_percent", "number"],
                  ["Contingency %",     "default_contingency_percent","number"],
                ] as [string, keyof CreateEstimatePayload, string][]).map(([label, key, type]) => (
                  <label key={key} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                    {label}
                    <input type={type} value={(form[key] as string) ?? ""}
                      onChange={e => setForm(prev => ({ ...prev, [key]: e.target.value }))} />
                  </label>
                ))}
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Project Type
                  <select value={form.project_type} onChange={e => setForm(prev => ({ ...prev, project_type: e.target.value }))}>
                    {["Heavy civil","Site development","Excavation","Grading","Underground utilities","Hauling","Demolition","Paving","Landscaping","General construction","Other"].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Contract Type
                  <select value={form.contract_type} onChange={e => setForm(prev => ({ ...prev, contract_type: e.target.value }))}>
                    {["Lump sum","Unit price","Cost plus","Time and materials","GMP","Design-build"].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>
              </div>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, marginTop: 12 }}>
                Notes
                <textarea rows={3} value={form.notes} onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))} />
              </label>
              <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
                <button type="submit" disabled={saving}>{saving ? "Saving…" : "Create Estimate"}</button>
                <button type="button" className="btn-ghost" onClick={() => setShowCreate(false)}>Cancel</button>
              </div>
            </form>
          )}

          {/* Detail panel */}
          {!showCreate && selected && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                <div>
                  <h3 style={{ margin: 0, marginBottom: 2 }}>{selected.estimate_name}</h3>
                  <div className="muted" style={{ fontSize: 12 }}>{selected.estimate_number} · {selected.customer_name || "—"}</div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  {pill(selected.status)}
                  {STATUS_FLOW[selected.status] && (
                    <button onClick={() => advanceStatus(selected)} style={{ fontSize: 12, padding: "5px 12px" }}>
                      Advance → {STATUS_FLOW[selected.status]}
                    </button>
                  )}
                  {["Submitted","Under Review","Awarded"].includes(selected.status) && (
                    <button onClick={() => markNotAwarded(selected)} className="btn-danger" style={{ fontSize: 12, padding: "5px 12px" }}>
                      Not Awarded
                    </button>
                  )}
                </div>
              </div>

              {/* Status progress bar */}
              <div style={{ marginTop: 16, display: "flex", gap: 4, flexWrap: "wrap" }}>
                {Object.keys(STATUS_FLOW).filter(s => !["Not Awarded","Archived"].includes(s)).map(s => {
                  const statuses = ["Draft Estimate","Pending Review","Submitted","Under Review","Awarded","Converted to Project"];
                  const current  = statuses.indexOf(selected.status);
                  const idx      = statuses.indexOf(s);
                  const done     = idx <= current;
                  return (
                    <div key={s} style={{ fontSize: 10, fontWeight: done ? 700 : 400,
                      padding: "3px 8px", borderRadius: 4,
                      background: done ? (STATUS_COLORS[s] + "22") : "#f1f5f9",
                      color: done ? STATUS_COLORS[s] : "#94a3b8",
                      border: `1px solid ${done ? STATUS_COLORS[s] : "#e2e8f0"}` }}>
                      {s}
                    </div>
                  );
                })}
              </div>

              {/* Details grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 20, borderTop: "1px solid #e2e8f0", paddingTop: 16 }}>
                {[
                  ["Project",        selected.project_name],
                  ["Customer",       selected.customer_name],
                  ["Project Type",   selected.project_type],
                  ["Contract",       selected.contract_type],
                  ["Estimate Type",  selected.estimate_type],
                  ["Bid Due Date",   selected.bid_due_date],
                  ["Estimator",      selected.estimator_name],
                  ["Project Mgr",    selected.project_manager_name],
                  ["Target Margin",  selected.target_margin_percent ? `${selected.target_margin_percent}%` : "—"],
                  ["Overhead",       selected.default_overhead_percent ? `${selected.default_overhead_percent}%` : "—"],
                  ["Contingency",    selected.default_contingency_percent ? `${selected.default_contingency_percent}%` : "—"],
                  ["Created",        selected.created_at?.slice(0,10)],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#64748b" }}>{label}</div>
                    <div style={{ fontSize: 13, marginTop: 2 }}>{value || "—"}</div>
                  </div>
                ))}
              </div>

              {selected.notes && (
                <div style={{ marginTop: 16, padding: "10px 14px", background: "#f8fafc", borderRadius: 8, fontSize: 13 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>Notes</div>
                  {selected.notes}
                </div>
              )}

              {/* ── Line items */}
              <div style={{ marginTop: 20, borderTop: "1px solid #e2e8f0", paddingTop: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                  <h4 style={{ margin: 0 }}>Line Items ({items.length})</h4>
                  {!selected.is_locked && (
                    <button onClick={() => setAddingItem(a => !a)} style={{ fontSize: 12, padding: "5px 10px" }}>
                      {addingItem ? "✕ Cancel" : "+ Add Item"}
                    </button>
                  )}
                </div>

                {/* Add item form */}
                {addingItem && (
                  <form onSubmit={saveItem} style={{ background: "#f8fafc", borderRadius: 8, padding: 14, marginBottom: 12 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                      {([
                        ["Item #",      "item_number",     "text"],
                        ["Cost Code",   "cost_code",       "text"],
                        ["Description *","description",    "text"],
                        ["Qty",         "quantity",        "number"],
                        ["Unit",        "unit_of_measure", "text"],
                        ["Unit Cost $", "unit_cost",       "number"],
                      ] as [string, keyof NewItemDraft, string][]).map(([label, key, type]) => (
                        <label key={key} style={{ display: "flex", flexDirection: "column", gap: 3, fontSize: 12 }}>
                          {label}
                          <input type={type} value={newItem[key]}
                            onChange={e => setNewItem(prev => ({ ...prev, [key]: e.target.value }))}
                            style={{ padding: "6px 8px", fontSize: 12 }} />
                        </label>
                      ))}
                    </div>
                    <div style={{ marginTop: 8, display: "flex", gap: 6, alignItems: "center" }}>
                      <span style={{ fontSize: 12, color: "#64748b" }}>
                        Total: {fmt(Number(newItem.quantity) * Number(newItem.unit_cost))}
                      </span>
                      <button type="submit" disabled={itemSaving} style={{ fontSize: 12, padding: "5px 10px", marginLeft: "auto" }}>
                        {itemSaving ? "Saving…" : "Add"}
                      </button>
                    </div>
                  </form>
                )}

                {/* Items table */}
                {items.length > 0 ? (
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                      <thead>
                        <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                          {["#","Cost Code","Description","Qty","Unit","Unit Cost","Total"].map(h => (
                            <th key={h} style={{ padding: "6px 10px", textAlign: "left", fontWeight: 700, fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {items.map(item => (
                          <tr key={item.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                            <td style={{ padding: "7px 10px" }}>{item.item_number || "—"}</td>
                            <td style={{ padding: "7px 10px", color: "#64748b" }}>{item.cost_code || "—"}</td>
                            <td style={{ padding: "7px 10px", fontWeight: 500 }}>{item.description}</td>
                            <td style={{ padding: "7px 10px" }}>{Number(item.quantity).toLocaleString()}</td>
                            <td style={{ padding: "7px 10px" }}>{item.unit_of_measure}</td>
                            <td style={{ padding: "7px 10px" }}>{fmt(item.unit_cost)}</td>
                            <td style={{ padding: "7px 10px", fontWeight: 600 }}>{fmt(item.total_cost)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="muted" style={{ fontSize: 13 }}>No line items yet. Click + Add Item to begin.</p>
                )}

                {/* Cost summary */}
                {(items.length > 0 || selected) && (
                  <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 8 }}>
                    {[
                      { label: "Direct Cost",  value: totalCost,   color: "#0f172a" },
                      { label: `Overhead (${selected?.default_overhead_percent ?? 0}%)`, value: overhead, color: "#475569" },
                      { label: `Contingency (${selected?.default_contingency_percent ?? 0}%)`, value: contingency, color: "#d97706" },
                      { label: `Margin (${selected?.target_margin_percent ?? 0}%)`, value: margin, color: "#16a34a" },
                      { label: "Grand Total",  value: grandTotal,  color: "#f97316" },
                    ].map(m => (
                      <div key={m.label} style={{ padding: "10px 12px", background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0" }}>
                        <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "#94a3b8" }}>{m.label}</div>
                        <div style={{ fontSize: 15, fontWeight: 800, marginTop: 4, color: m.color }}>{fmt(m.value)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
          {!showCreate && !selected && (
            <p className="muted" style={{ marginTop: 0 }}>Select an estimate from the list, or click <strong>+ New</strong> to create one.</p>
          )}
        </div>
      </div>

      {/* ── Bid Pipeline */}
      {bids.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Bid Pipeline</h3>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", textAlign: "left" }}>
                  {["Bid #","Customer","Stage","Bid Amount","Probability","Due Date","Status"].map(h => (
                    <th key={h} style={{ padding: "8px 12px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "#64748b" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bids.map(bid => (
                  <tr key={bid.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "9px 12px", fontWeight: 600 }}>{bid.bid_number}</td>
                    <td style={{ padding: "9px 12px" }}>{bid.customer_name}</td>
                    <td style={{ padding: "9px 12px" }}>{bid.stage}</td>
                    <td style={{ padding: "9px 12px" }}>{fmt(bid.bid_amount)}</td>
                    <td style={{ padding: "9px 12px" }}>{bid.probability_percent ? `${bid.probability_percent}%` : "—"}</td>
                    <td style={{ padding: "9px 12px" }}>{bid.due_date ?? "—"}</td>
                    <td style={{ padding: "9px 12px" }}>{bid.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppShell>
  );
}
