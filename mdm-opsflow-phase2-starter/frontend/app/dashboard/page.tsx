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
    }).catch(() => setLoading(false));
  }, []);

  const recentProjects = projects.slice(0, 5);
  const recentTickets  = tickets.slice(0, 6);
  const activeEstimates = estimates.filter(e =>
    !["Archived","Not Awarded","Converted to Project"].includes(e.status)
  ).slice(0, 5);

  return (
    <AppShell titleKey="dashboard.title">
      {loading ? (
        <p className="muted">Loading dashboard…</p>
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

type Project = {
  id: string;
  project_name: string;
  status: string;
};

export default function DashboardPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [projects, setProjects] = useState<Project[]>([]);
  const [alerts, setAlerts] = useState<ReplayTokenStateAlerts | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [densityPresets, setDensityPresets] = useState<MaterialDensityPreset[]>([]);

  useEffect(() => {
    setLocale(getLocale());
    const token = getAccessToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    fetch(`${getApiBaseUrl()}/api/projects`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-ID": getTenantId(),
      },
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setProjects(data));

    fetchReplayTokenStateAlerts({
      staleThresholdMinutes: 60,
      staleActiveThresholdCount: 10,
    })
      .then((data) => setAlerts(data))
      .catch(() => {
        setAlerts(null);
      });

    listTickets()
      .then((data) => setTickets(data))
      .catch(() => {
        setTickets([]);
      });

    listMaterialDensityPresets()
      .then((data) => setDensityPresets(data))
      .catch(() => {
        setDensityPresets([]);
      });
  }, []);

  const consumedRevokedRatio =
    alerts?.consumed_to_revoked_ratio === null || alerts?.consumed_to_revoked_ratio === undefined
      ? "n/a"
      : alerts.consumed_to_revoked_ratio.toFixed(2);

  const materialCounts = tickets.reduce<Record<string, number>>((acc, ticket) => {
    const material = ticket.material.trim();
    if (!material) {
      return acc;
    }
    acc[material] = (acc[material] || 0) + 1;
    return acc;
  }, {});

  const topMaterials = Object.entries(materialCounts)
    .sort((a, b) => {
      if (b[1] !== a[1]) {
        return b[1] - a[1];
      }
      return a[0].localeCompare(b[0]);
    })
    .slice(0, 3);

  const normalizedPresetMap = new Map(
    densityPresets.map((preset) => [preset.material_name.trim().toLowerCase(), preset.density_tons_per_cubic_yard])
  );
  const distinctMaterialCount = Object.keys(materialCounts).length;
  const effectivePresetCount = Object.keys(materialCounts).filter((name) => normalizedPresetMap.has(name.toLowerCase())).length;

  return (
    <AppShell titleKey="dashboard.title">
      <div className="card">
        <h3>{t(locale, "dashboard.welcome")}</h3>
        <p>{t(locale, "dashboard.subtitle")}</p>
      </div>
      <div className="grid">
        <div className="card">
          {t(locale, "dashboard.activeProjects")}
          <div className="metric">{projects.length}</div>
          <div className="metric-note">Across all active tenant jobs</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.documentsProcessed")}
          <div className="metric">{alerts?.total_tokens ?? "-"}</div>
          <div className="metric-note">Replay export tokens in current alert window</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.budgetHealth")}
          <div className="metric">{consumedRevokedRatio}</div>
          <div className="metric-note">Consumed to revoked token ratio</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.pendingReviews")}
          <div className="metric">{alerts?.active_tokens_older_than_threshold ?? "-"}</div>
          <div className="metric-note">Active tokens older than 60 minutes</div>
        </div>
        <div className="card">
          Material intelligence
          <div className="metric">{effectivePresetCount}/{distinctMaterialCount}</div>
          <div className="metric-note">materials currently covered by density presets</div>
          {topMaterials.length === 0 ? (
            <div className="metric-note">No ticket materials yet.</div>
          ) : (
            topMaterials.map(([material, count]) => {
              const density = normalizedPresetMap.get(material.toLowerCase()) || "n/a";
              return (
                <div className="metric-note" key={material}>
                  {material}: {count} ticket(s) | density {density}
                </div>
              );
            })
          )}
        </div>
      </div>

      {alerts?.active_tokens_older_than_threshold_exceeded ? (
        <div className="card warning-card">
          <strong>Replay token alert</strong>
          <p>
            Threshold exceeded: {alerts.active_tokens_older_than_threshold} active tokens older than
            {" "}
            {alerts.stale_threshold_minutes} minutes (limit {alerts.stale_active_threshold_count}).
          </p>
        </div>
      ) : null}

      <div className="stats-strip">
        <div className="mini-stat">
          <strong>$2.45M</strong>
          <span>Revenue MTD</span>
        </div>
        <div className="mini-stat">
          <strong>96%</strong>
          <span>Safety Compliance</span>
        </div>
        <div className="mini-stat">
          <strong>89%</strong>
          <span>Equipment Utilization</span>
        </div>
        <div className="mini-stat">
          <strong>14</strong>
          <span>AI Action Cards</span>
        </div>
      </div>
    </AppShell>
  );
}
