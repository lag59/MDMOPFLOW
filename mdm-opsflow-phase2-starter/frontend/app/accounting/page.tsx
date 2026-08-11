"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

type Project = { id: string; project_name: string; project_number: string; contract_amount: string | null; status: string };
type Ticket  = { id: string; ticket_number: string; project_id: string | null; material: string; quantity: string; unit: string; unit_price: string | null; total_price: string | null; status: string; };
type Invoice = { invoice_number: string; project_id: string; project_name: string; total_amount: string; line_items: { ticket_number: string; material: string; quantity: string; unit: string; unit_price: string; line_total: string }[]; };
type GenerateForm = { project_id: string; rate_per_ton: string; rate_per_load: string; };

const fmt = (n: string | number | null | undefined) =>
  !n || n === "0" ? "—" : Number(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });

export default function AccountingPage() {
  const [projects, setProjects]     = useState<Project[]>([]);
  const [tickets, setTickets]       = useState<Ticket[]>([]);
  const [invoice, setInvoice]       = useState<Invoice | null>(null);
  const [generating, setGenerating] = useState(false);
  const [msg, setMsg]               = useState<{ text: string; ok: boolean } | null>(null);
  const [form, setForm]             = useState<GenerateForm>({ project_id: "", rate_per_ton: "85", rate_per_load: "0" });
  const [loading, setLoading]       = useState(true);

  const api = getApiBaseUrl();
  const token = getAccessToken();
  const tenant = getTenantId();

  function headers() {
    return { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "X-Tenant-ID": tenant };
  }

  useEffect(() => {
    if (!token) { window.location.href = "/login"; return; }
    Promise.all([
      fetch(`${api}/api/projects`, { headers: headers() }).then(r => r.ok ? r.json() : []),
      fetch(`${api}/api/tickets`, { headers: headers() }).then(r => r.ok ? r.json() : []),
    ]).then(([p, t]) => { setProjects(p); setTickets(t); setLoading(false); });
  }, []);

  async function generateInvoice(e: React.FormEvent) {
    e.preventDefault();
    if (!form.project_id) { setMsg({ text: "Select a project.", ok: false }); return; }
    setGenerating(true); setMsg(null); setInvoice(null);
    const r = await fetch(`${api}/api/invoices/generate`, {
      method: "POST", headers: headers(),
      body: JSON.stringify({
        project_id: form.project_id,
        rate_per_ton: Number(form.rate_per_ton) || null,
        rate_per_load: Number(form.rate_per_load) || null,
      }),
    });
    setGenerating(false);
    if (r.ok) {
      setInvoice(await r.json());
      setMsg({ text: "Invoice generated.", ok: true });
    } else {
      const d = await r.json().catch(() => null);
      setMsg({ text: d?.detail || "Invoice generation failed.", ok: false });
    }
  }

  const totalTicketRevenue = tickets.reduce((s, t) => s + Number(t.total_price || 0), 0);
  const approvedTickets    = tickets.filter(t => t.status === "approved");
  const pendingTickets     = tickets.filter(t => t.status !== "approved" && t.status !== "closed");

  return (
    <AppShell titleKey="nav.accounting">
      {loading ? <p className="muted">Loading…</p> : (
        <>
          {/* Metrics */}
          <div className="grid" style={{ gridTemplateColumns: "repeat(4,1fr)", marginBottom: 20 }}>
            {[
              { label: "Total Ticket Revenue", value: fmt(totalTicketRevenue), color: "#16a34a" },
              { label: "Approved Tickets",      value: approvedTickets.length,  color: "#2563eb" },
              { label: "Pending Tickets",       value: pendingTickets.length,   color: "#d97706" },
              { label: "Active Projects",       value: projects.filter(p => p.status === "active").length, color: "#7c3aed" },
            ].map(m => (
              <div className="card" key={m.label}>
                <div className="metric-note">{m.label}</div>
                <div className="metric" style={{ color: m.color, fontSize: 22 }}>{m.value}</div>
              </div>
            ))}
          </div>

          {msg && (
            <div style={{ marginBottom: 14, padding: "9px 14px", borderRadius: 8, fontSize: 13,
              background: msg.ok ? "#dcfce7" : "#fee2e2", color: msg.ok ? "#166534" : "#991b1b" }}>
              {msg.text}
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {/* Invoice generator */}
            <div className="card">
              <h3 style={{ marginTop: 0, fontSize: 14 }}>Generate Invoice</h3>
              <form onSubmit={generateInvoice}>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                    Project
                    <select value={form.project_id} onChange={e => setForm(p => ({ ...p, project_id: e.target.value }))}>
                      <option value="">— select project —</option>
                      {projects.map(proj => <option key={proj.id} value={proj.id}>{proj.project_name} ({proj.project_number})</option>)}
                    </select>
                  </label>
                  <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                    Rate per Ton ($)
                    <input type="number" min="0" step="0.01" value={form.rate_per_ton}
                      onChange={e => setForm(p => ({ ...p, rate_per_ton: e.target.value }))} />
                  </label>
                  <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                    Rate per Load ($)
                    <input type="number" min="0" step="0.01" value={form.rate_per_load}
                      onChange={e => setForm(p => ({ ...p, rate_per_load: e.target.value }))} />
                  </label>
                  <button type="submit" disabled={generating}>{generating ? "Generating…" : "Generate Invoice"}</button>
                </div>
              </form>

              {/* Invoice preview */}
              {invoice && (
                <div style={{ marginTop: 16, borderTop: "1px solid #e2e8f0", paddingTop: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>Invoice #{invoice.invoice_number}</div>
                      <div className="muted" style={{ fontSize: 12 }}>{invoice.project_name}</div>
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: "#16a34a" }}>{fmt(invoice.total_amount)}</div>
                  </div>
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid #e2e8f0" }}>
                          {["Ticket","Material","Qty","Unit","Rate","Total"].map(h => (
                            <th key={h} style={{ padding: "5px 8px", textAlign: "left", fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(invoice.line_items || []).map((li, i) => (
                          <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                            <td style={{ padding: "5px 8px" }}>{li.ticket_number}</td>
                            <td style={{ padding: "5px 8px" }}>{li.material}</td>
                            <td style={{ padding: "5px 8px" }}>{li.quantity}</td>
                            <td style={{ padding: "5px 8px" }}>{li.unit}</td>
                            <td style={{ padding: "5px 8px" }}>{fmt(li.unit_price)}</td>
                            <td style={{ padding: "5px 8px", fontWeight: 600 }}>{fmt(li.line_total)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            {/* Ticket billing summary */}
            <div className="card">
              <h3 style={{ marginTop: 0, fontSize: 14 }}>Ticket Billing Summary</h3>
              {tickets.length === 0 ? <p className="muted" style={{ fontSize: 13 }}>No tickets yet.</p> : (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                        {["Ticket #","Material","Qty","Unit","Status"].map(h => (
                          <th key={h} style={{ padding: "7px 8px", textAlign: "left", fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {tickets.slice(0, 20).map(t => (
                        <tr key={t.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                          <td style={{ padding: "7px 8px", fontWeight: 600 }}>{t.ticket_number}</td>
                          <td style={{ padding: "7px 8px" }}>{t.material}</td>
                          <td style={{ padding: "7px 8px" }}>{t.quantity}</td>
                          <td style={{ padding: "7px 8px" }}>{t.unit}</td>
                          <td style={{ padding: "7px 8px" }}>
                            <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 999,
                              background: t.status === "approved" ? "#dcfce7" : "#f1f5f9",
                              color: t.status === "approved" ? "#166534" : "#475569" }}>{t.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Project contract overview */}
            <div className="card" style={{ gridColumn: "1/-1" }}>
              <h3 style={{ marginTop: 0, fontSize: 14 }}>Project Contract Overview</h3>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                      {["Project","Number","Status","Contract Value","Budget","Variance"].map(h => (
                        <th key={h} style={{ padding: "7px 10px", textAlign: "left", fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {projects.map(p => {
                      const variance = p.contract_amount && p.budget
                        ? Number(p.contract_amount) - Number(p.budget) : null;
                      return (
                        <tr key={p.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                          <td style={{ padding: "8px 10px", fontWeight: 600 }}>{p.project_name}</td>
                          <td style={{ padding: "8px 10px" }}>{p.project_number}</td>
                          <td style={{ padding: "8px 10px" }}>
                            <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 999, textTransform: "capitalize",
                              background: p.status === "active" ? "#dcfce7" : "#f1f5f9",
                              color: p.status === "active" ? "#166534" : "#475569" }}>{p.status.replace("_"," ")}</span>
                          </td>
                          <td style={{ padding: "8px 10px" }}>{fmt(p.contract_amount)}</td>
                          <td style={{ padding: "8px 10px" }}>{fmt(p.budget)}</td>
                          <td style={{ padding: "8px 10px", fontWeight: 600,
                            color: variance == null ? "#94a3b8" : variance >= 0 ? "#16a34a" : "#dc2626" }}>
                            {variance == null ? "—" : fmt(variance)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </AppShell>
  );
}
