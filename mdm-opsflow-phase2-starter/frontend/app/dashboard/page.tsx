"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

type Summary = {
  projects: number; active_projects: number;
  tickets: number; open_tickets: number;
  estimates: number; draft_estimates: number; awarded_estimates: number;
  intake_items: number; intake_pending_review: number;
};

type Project = { id: string; project_name: string; status: string; contract_amount: string | null };
type Ticket = { id: string; ticket_number: string; material: string; status: string; created_at: string };
type Estimate = { id: string; estimate_name: string; status: string; bid_due_date: string | null };

const STATUS_DOT: Record<string, string> = {
  active: "#16a34a", planning: "#2563eb", on_hold: "#d97706", complete: "#7c3aed", cancelled: "#dc2626",
};

const fmt = (n: string | number | null | undefined) =>
  !n || n === "0" ? "—" : Number(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const api = getApiBaseUrl();
  const token = getAccessToken();
  const tenant = getTenantId();

  useEffect(() => {
    if (!token) { window.location.href = "/login"; return; }
    const h = { Authorization: `Bearer ${token}`, "X-Tenant-ID": tenant };

    Promise.all([
      fetch(`${api}/api/projects`, { headers: h }).then(r => r.ok ? r.json() : []),
      fetch(`${api}/api/tickets`, { headers: h }).then(r => r.ok ? r.json() : []),
      fetch(`${api}/api/estimates`, { headers: h }).then(r => r.ok ? r.json() : []),
      fetch(`${api}/api/intake/items`, { headers: h }).then(r => r.ok ? r.json() : []),
    ]).then(([p, t, e, i]) => {
      setProjects(p);
      setTickets(t);
      setEstimates(e);
      setSummary({
        projects: p.length,
        active_projects: p.filter((x: Project) => x.status === "active").length,
        tickets: t.length,
        open_tickets: t.filter((x: Ticket) => x.status !== "closed").length,
        estimates: e.length,
        draft_estimates: e.filter((x: Estimate) => x.status === "Draft Estimate").length,
        awarded_estimates: e.filter((x: Estimate) => x.status === "Awarded" || x.status === "Converted to Project").length,
        intake_items: Array.isArray(i) ? i.length : (i?.items?.length ?? 0),
        intake_pending_review: Array.isArray(i)
          ? i.filter((x: { status?: string }) => x.status === "pending_review").length
          : 0,
      });
      setLoading(false);
    }).catch(() => {
      setError("Some dashboard data could not be loaded. Please refresh.");
      setLoading(false);
    });
  }, []);

  const recentProjects = projects.slice(0, 5);
  const recentTickets  = tickets.slice(0, 6);
  const activeEstimates = estimates.filter(e =>
    !["Archived","Not Awarded","Converted to Project"].includes(e.status)
  ).slice(0, 5);

  return (
    <AppShell titleKey="dashboard.title">
      <div className="card" style={{ marginBottom: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <p className="muted" style={{ margin: 0 }}>Quick actions to jump into daily work.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link href="/daily-production" className="link-button">Daily reports</Link>
            <Link href="/ticket-manager" className="link-button">Assign tickets</Link>
            <Link href="/modules" className="link-button">All modules</Link>
          </div>
        </div>
      </div>

      {loading ? (
        <p className="muted">Loading dashboard…</p>
      ) : error ? (
        <div className="card" style={{ borderColor: "#fecaca", background: "#fef2f2" }}>
          <p style={{ margin: 0, color: "#991b1b", fontWeight: 600 }}>{error}</p>
        </div>
      ) : (
        <>
          {/* ── KPI row */}
          <div className="grid" style={{ gridTemplateColumns: "repeat(4,1fr)" }}>
            {[
              { label: "Active Projects",   value: summary?.active_projects ?? 0,  sub: `${summary?.projects ?? 0} total`,   color: "#16a34a", href: "/project-manager" },
              { label: "Open Tickets",      value: summary?.open_tickets ?? 0,      sub: `${summary?.tickets ?? 0} total`,    color: "#2563eb", href: "/tickets" },
              { label: "Active Estimates",  value: summary?.estimates ?? 0,         sub: `${summary?.awarded_estimates ?? 0} awarded`, color: "#d97706", href: "/estimator" },
              { label: "Intake Queue",      value: summary?.intake_items ?? 0,      sub: `${summary?.intake_pending_review ?? 0} need review`, color: "#7c3aed", href: "/intake" },
            ].map(m => (
              <Link key={m.label} href={m.href} style={{ textDecoration: "none" }}>
                <div className="card" style={{ cursor: "pointer", transition: "box-shadow 0.15s" }}
                  onMouseEnter={e => (e.currentTarget.style.boxShadow = "0 6px 20px rgba(15,23,42,0.12)")}
                  onMouseLeave={e => (e.currentTarget.style.boxShadow = "")}>
                  <div className="metric-note">{m.label}</div>
                  <div className="metric" style={{ color: m.color }}>{m.value}</div>
                  <div className="metric-note">{m.sub}</div>
                </div>
              </Link>
            ))}
          </div>

          {/* ── Two-column body */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>

            {/* Recent projects */}
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <h3 style={{ margin: 0, fontSize: 14 }}>Recent Projects</h3>
                <Link href="/project-manager" style={{ fontSize: 12, color: "#f97316", fontWeight: 600 }}>View all →</Link>
              </div>
              {recentProjects.length === 0 ? <p className="muted" style={{ fontSize: 13 }}>No projects yet.</p> : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {recentProjects.map(p => (
                    <div key={p.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{p.project_name}</div>
                        <div style={{ fontSize: 11, color: "#64748b", marginTop: 1 }}>{fmt(p.contract_amount)}</div>
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, textTransform: "capitalize",
                        background: (STATUS_DOT[p.status] ?? "#64748b") + "22",
                        color: STATUS_DOT[p.status] ?? "#64748b" }}>{p.status.replace("_"," ")}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Active estimates */}
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <h3 style={{ margin: 0, fontSize: 14 }}>Active Estimates</h3>
                <Link href="/estimator" style={{ fontSize: 12, color: "#f97316", fontWeight: 600 }}>View all →</Link>
              </div>
              {activeEstimates.length === 0 ? <p className="muted" style={{ fontSize: 13 }}>No estimates yet.</p> : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {activeEstimates.map(e => (
                    <div key={e.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{e.estimate_name}</div>
                        {e.bid_due_date && <div style={{ fontSize: 11, color: "#64748b", marginTop: 1 }}>Due {e.bid_due_date}</div>}
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
                        background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" }}>{e.status}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent tickets */}
            <div className="card" style={{ gridColumn: "1 / -1" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <h3 style={{ margin: 0, fontSize: 14 }}>Recent Tickets</h3>
                <Link href="/tickets" style={{ fontSize: 12, color: "#f97316", fontWeight: 600 }}>View all →</Link>
              </div>
              {recentTickets.length === 0 ? <p className="muted" style={{ fontSize: 13 }}>No tickets yet.</p> : (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                        {["Ticket #","Material","Status","Date"].map(h => (
                          <th key={h} style={{ padding: "6px 10px", textAlign: "left", fontSize: 11, fontWeight: 700,
                            textTransform: "uppercase", letterSpacing: "0.04em", color: "#64748b" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {recentTickets.map(t => (
                        <tr key={t.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                          <td style={{ padding: "7px 10px", fontWeight: 600 }}>{t.ticket_number}</td>
                          <td style={{ padding: "7px 10px" }}>{t.material}</td>
                          <td style={{ padding: "7px 10px" }}>
                            <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 999,
                              background: "#f1f5f9", color: "#475569" }}>{t.status}</span>
                          </td>
                          <td style={{ padding: "7px 10px", color: "#64748b" }}>{t.created_at?.slice(0,10)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </AppShell>
  );
}
