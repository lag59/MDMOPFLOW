"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

type Project = { id: string; project_name: string; project_number: string; customer: string; status: string; contract_amount: string | null; budget: string | null; start_date: string | null; end_date: string | null; };
type Estimate = { id: string; estimate_name: string; estimate_number: string; status: string; target_margin_percent: string; bid_due_date: string | null; };
type Ticket = { id: string; ticket_number: string; material: string; quantity: string; unit: string; status: string; };
type TeamMember = { user_id: string; email: string; display_name: string; title: string; role_name: string; status: string; };

const fmt = (n: string | number | null | undefined) =>
  !n || n === "0" ? "—" : Number(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function OwnerPage() {
  const [projects, setProjects]   = useState<Project[]>([]);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [tickets, setTickets]     = useState<Ticket[]>([]);
  const [team, setTeam]           = useState<TeamMember[]>([]);
  const [loading, setLoading]     = useState(true);

  const api = getApiBaseUrl();
  const token = getAccessToken();
  const tenant = getTenantId();

  useEffect(() => {
    if (!token) { window.location.href = "/login"; return; }
    const h = { Authorization: `Bearer ${token}`, "X-Tenant-ID": tenant };
    Promise.all([
      fetch(`${api}/api/projects`, { headers: h }).then(r => r.ok ? r.json() : []),
      fetch(`${api}/api/estimates`, { headers: h }).then(r => r.ok ? r.json() : []),
      fetch(`${api}/api/tickets`, { headers: h }).then(r => r.ok ? r.json() : []),
      fetch(`${api}/api/tenant-users`, { headers: h }).then(r => r.ok ? r.json() : []),
    ]).then(([p, e, t, tm]) => { setProjects(p); setEstimates(e); setTickets(t); setTeam(tm); setLoading(false); });
  }, []);

  const totalContractValue = projects.reduce((sum, p) => sum + Number(p.contract_amount || 0), 0);
  const totalBudget        = projects.reduce((sum, p) => sum + Number(p.budget || 0), 0);
  const activeProjects     = projects.filter(p => p.status === "active");
  const awardedEstimates   = estimates.filter(e => ["Awarded","Converted to Project"].includes(e.status));
  const openTickets        = tickets.filter(t => t.status !== "closed");

  const pill = (status: string, color: string) => (
    <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, textTransform: "capitalize",
      background: color + "22", color, border: `1px solid ${color}44` }}>
      {status.replace("_"," ")}
    </span>
  );

  return (
    <AppShell titleKey="nav.owner">
      {loading ? <p className="muted">Loading…</p> : (
        <>
          {/* Portfolio summary */}
          <div className="grid" style={{ gridTemplateColumns: "repeat(4,1fr)" }}>
            {[
              { label: "Total Contract Value", value: fmt(totalContractValue), color: "#16a34a" },
              { label: "Total Budget",          value: fmt(totalBudget),        color: "#2563eb" },
              { label: "Active Projects",       value: activeProjects.length,   color: "#f97316" },
              { label: "Awarded Bids",          value: awardedEstimates.length, color: "#7c3aed" },
            ].map(m => (
              <div className="card" key={m.label}>
                <div className="metric-note">{m.label}</div>
                <div className="metric" style={{ color: m.color, fontSize: 22 }}>{m.value}</div>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
            {/* Project portfolio */}
            <div className="card">
              <h3 style={{ marginTop: 0, fontSize: 14 }}>Project Portfolio</h3>
              {projects.length === 0 ? <p className="muted" style={{ fontSize: 13 }}>No projects yet.</p> : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {projects.map(p => (
                    <div key={p.id} style={{ padding: "8px 0", borderBottom: "1px solid #f1f5f9", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{p.project_name}</div>
                        <div style={{ fontSize: 11, color: "#64748b" }}>{p.customer || "—"} · {fmt(p.contract_amount)}</div>
                      </div>
                      {pill(p.status, p.status === "active" ? "#16a34a" : p.status === "planning" ? "#2563eb" : "#d97706")}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Bid performance */}
            <div className="card">
              <h3 style={{ marginTop: 0, fontSize: 14 }}>Bid Performance</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 12 }}>
                {[
                  ["Total Bids",    estimates.length,                                            "#64748b"],
                  ["Awarded",       awardedEstimates.length,                                     "#16a34a"],
                  ["In Progress",   estimates.filter(e => !["Awarded","Not Awarded","Archived","Converted to Project"].includes(e.status)).length, "#2563eb"],
                  ["Not Awarded",   estimates.filter(e => e.status === "Not Awarded").length,     "#dc2626"],
                ].map(([label, value, color]) => (
                  <div key={label as string} style={{ padding: "10px", borderRadius: 8, background: "#f8fafc", border: "1px solid #e2e8f0" }}>
                    <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>{label}</div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: color as string, marginTop: 2 }}>{value}</div>
                  </div>
                ))}
              </div>
              {estimates.slice(0,4).map(e => (
                <div key={e.id} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #f1f5f9", fontSize: 13 }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{e.estimate_name}</div>
                    {e.bid_due_date && <div style={{ fontSize: 11, color: "#64748b" }}>Due {e.bid_due_date}</div>}
                  </div>
                  <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
                    background: e.status === "Awarded" ? "#dcfce7" : "#f1f5f9",
                    color: e.status === "Awarded" ? "#166534" : "#475569" }}>{e.status}</span>
                </div>
              ))}
            </div>

            {/* Team */}
            <div className="card">
              <h3 style={{ marginTop: 0, fontSize: 14 }}>Team ({team.length})</h3>
              {team.length === 0 ? <p className="muted" style={{ fontSize: 13 }}>No team members yet.</p> : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {team.map(m => (
                    <div key={m.user_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid #f1f5f9" }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{m.display_name}</div>
                        <div style={{ fontSize: 11, color: "#64748b" }}>{m.email}</div>
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, background: "#f1f5f9", color: "#475569" }}>{m.role_name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Open tickets overview */}
            <div className="card">
              <h3 style={{ marginTop: 0, fontSize: 14 }}>Open Tickets ({openTickets.length})</h3>
              {openTickets.length === 0 ? <p className="muted" style={{ fontSize: 13 }}>No open tickets.</p> : (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {openTickets.slice(0, 6).map(t => (
                    <div key={t.id} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #f1f5f9", fontSize: 13 }}>
                      <div>
                        <span style={{ fontWeight: 600 }}>{t.ticket_number}</span>
                        <span style={{ color: "#64748b", marginLeft: 8 }}>{t.material} · {t.quantity} {t.unit}</span>
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 999, background: "#f1f5f9", color: "#475569" }}>{t.status}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </AppShell>
  );
}
