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

// ── component ────────────────────────────────────────────────────────────────

export default function EstimatorPage() {
  const [estimates, setEstimates]     = useState<Estimate[]>([]);
  const [bids, setBids]               = useState<EstimatorBidPipelineItem[]>([]);
  const [selected, setSelected]       = useState<Estimate | null>(null);
  const [showCreate, setShowCreate]   = useState(false);
  const [saving, setSaving]           = useState(false);
  const [msg, setMsg]                 = useState<{ text: string; ok: boolean } | null>(null);

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
                onClick={() => { setSelected(est); setShowCreate(false); setMsg(null); }}
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
