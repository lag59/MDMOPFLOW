"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";
import { getCurrentRoleAccess } from "@/lib/roleAccess";
import { ROLE_WORKSPACES, type RoleKey } from "@/lib/roles";

import styles from "./page.module.css";

type Summary = {
  projects: number;
  active_projects: number;
  tickets: number;
  open_tickets: number;
  estimates: number;
  draft_estimates: number;
  awarded_estimates: number;
  intake_items: number;
  intake_pending_review: number;
};

type Project = { id: string; project_name: string; status: string; contract_amount: string | null };
type Ticket = { id: string; ticket_number: string; material: string; status: string; created_at: string };
type Estimate = { id: string; estimate_name: string; status: string; bid_due_date: string | null };

type RoleExperience = {
  title: string;
  subtitle: string;
  moduleLinks: Array<{ label: string; href: string }>;
  quickActions: Array<{ label: string; href: string }>;
  kpiOrder: Array<keyof Summary>;
};

type RoleExperienceApiResponse = {
  role_key: string;
  role_label: string;
  kpi_order: string[];
  modules: Array<{ label: string; href: string }>;
  quick_actions: Array<{ label: string; href: string }>;
  alerts: string[];
};

const KPI_META: Record<keyof Summary, { label: string; href: string; color: string; sub: (summary: Summary) => string }> = {
  projects: { label: "Projects", href: "/projects", color: "#0f766e", sub: (s) => `${s.active_projects} active` },
  active_projects: { label: "Active Projects", href: "/project-manager", color: "#16a34a", sub: (s) => `${s.projects} total` },
  tickets: { label: "Tickets", href: "/tickets", color: "#2563eb", sub: (s) => `${s.open_tickets} open` },
  open_tickets: { label: "Open Tickets", href: "/ticket-manager", color: "#1d4ed8", sub: (s) => `${s.tickets} total` },
  estimates: { label: "Estimates", href: "/estimator", color: "#d97706", sub: (s) => `${s.awarded_estimates} awarded` },
  draft_estimates: { label: "Draft Estimates", href: "/estimator", color: "#f59e0b", sub: (s) => `${s.estimates} total` },
  awarded_estimates: { label: "Awarded Estimates", href: "/estimator", color: "#b45309", sub: (s) => `${s.estimates} total` },
  intake_items: { label: "Intake Items", href: "/intake", color: "#7c3aed", sub: (s) => `${s.intake_pending_review} need review` },
  intake_pending_review: { label: "Intake Pending Review", href: "/intake", color: "#6d28d9", sub: (s) => `${s.intake_items} total` },
};

const ROLE_EXPERIENCES: Record<RoleKey, RoleExperience> = {
  estimator: {
    title: "Estimator Command Center",
    subtitle: "Prioritize estimate throughput, bid pipeline progression, and review readiness.",
    moduleLinks: [
      { label: "Takeoff", href: "/modules/estimator/takeoff" },
      { label: "Estimate Versions", href: "/modules/estimator/estimate-versions" },
      { label: "Bid Pipeline", href: "/modules/estimator/bid-pipeline" },
      { label: "Win/Loss", href: "/modules/estimator/win-loss" },
    ],
    quickActions: [
      { label: "Open estimator workspace", href: "/estimator" },
      { label: "Review ticket inputs", href: "/tickets" },
      { label: "View projects", href: "/projects" },
    ],
    kpiOrder: ["estimates", "draft_estimates", "awarded_estimates", "intake_pending_review"],
  },
  dispatcher: {
    title: "Dispatcher Operations",
    subtitle: "Balance dispatch load, truck assignment, and unresolved ticket flow.",
    moduleLinks: [
      { label: "Dispatch Board", href: "/modules/dispatcher/dispatch-board" },
      { label: "Crew Calendar", href: "/modules/dispatcher/crew-calendar" },
      { label: "Route Planning", href: "/modules/dispatcher/route-planning" },
      { label: "Utilization", href: "/modules/dispatcher/utilization" },
    ],
    quickActions: [
      { label: "Assign tickets", href: "/ticket-manager" },
      { label: "Review active tickets", href: "/tickets" },
      { label: "Open projects", href: "/projects" },
    ],
    kpiOrder: ["open_tickets", "tickets", "active_projects", "intake_pending_review"],
  },
  fleet_manager: {
    title: "Fleet Readiness",
    subtitle: "Track fleet workload, issue pressure, and throughput from field operations.",
    moduleLinks: [
      { label: "Fleet", href: "/modules/fleet_manager/fleet" },
      { label: "Maintenance", href: "/modules/fleet_manager/maintenance" },
      { label: "Fuel", href: "/modules/fleet_manager/fuel" },
      { label: "Work Orders", href: "/modules/fleet_manager/work-orders" },
    ],
    quickActions: [
      { label: "Open workspace assets", href: "/workspace" },
      { label: "Check dispatch board", href: "/ticket-manager" },
      { label: "Inspect tickets", href: "/tickets" },
    ],
    kpiOrder: ["open_tickets", "tickets", "intake_pending_review", "projects"],
  },
  safety_manager: {
    title: "Safety and Compliance",
    subtitle: "Monitor incidents, pending reviews, and operational risk signals.",
    moduleLinks: [
      { label: "Incidents", href: "/modules/safety_manager/incidents" },
      { label: "Inspections", href: "/modules/safety_manager/inspections" },
      { label: "Toolbox Talks", href: "/modules/safety_manager/toolbox-talks" },
      { label: "Corrective Actions", href: "/modules/safety_manager/corrective-actions" },
    ],
    quickActions: [
      { label: "Open intake queue", href: "/intake" },
      { label: "Review extraction issues", href: "/extraction-queue" },
      { label: "Open projects", href: "/projects" },
    ],
    kpiOrder: ["intake_pending_review", "intake_items", "open_tickets", "active_projects"],
  },
  accounting: {
    title: "Accounting Control Tower",
    subtitle: "Track AR/AP workload, invoice readiness, and project-financial signals.",
    moduleLinks: [
      { label: "AP", href: "/modules/accounting/ap" },
      { label: "AR", href: "/modules/accounting/ar" },
      { label: "Invoices", href: "/modules/accounting/invoices" },
      { label: "Job Cost Ledger", href: "/modules/accounting/job-cost-ledger" },
    ],
    quickActions: [
      { label: "Open projects", href: "/projects" },
      { label: "Review tickets", href: "/tickets" },
      { label: "Open estimator", href: "/estimator" },
    ],
    kpiOrder: ["awarded_estimates", "open_tickets", "tickets", "active_projects"],
  },
  executive: {
    title: "Executive Portfolio View",
    subtitle: "Review cross-project KPIs, operational pressure, and delivery risk.",
    moduleLinks: [
      { label: "KPI Board", href: "/modules/executive/kpi-board" },
      { label: "Revenue", href: "/modules/executive/revenue" },
      { label: "Burn Rate", href: "/modules/executive/burn-rate" },
      { label: "Risk Radar", href: "/modules/executive/risk-radar" },
    ],
    quickActions: [
      { label: "Open projects", href: "/projects" },
      { label: "Review tickets", href: "/tickets" },
      { label: "View all modules", href: "/modules" },
    ],
    kpiOrder: ["active_projects", "projects", "open_tickets", "intake_pending_review"],
  },
  company_owner: {
    title: "Owner Portfolio View",
    subtitle: "Track company-level performance, job health, and operational exceptions.",
    moduleLinks: [
      { label: "Executive Dashboard", href: "/modules/company_owner/executive-dashboard" },
      { label: "Portfolio", href: "/modules/company_owner/portfolio" },
      { label: "Forecasting", href: "/modules/company_owner/forecasting" },
      { label: "Approvals", href: "/modules/company_owner/approvals" },
    ],
    quickActions: [
      { label: "Open projects", href: "/projects" },
      { label: "Review intake", href: "/intake" },
      { label: "View modules", href: "/modules" },
    ],
    kpiOrder: ["active_projects", "open_tickets", "awarded_estimates", "intake_pending_review"],
  },
  project_manager: {
    title: "Project Execution Dashboard",
    subtitle: "Keep active jobs, schedule pressure, and ticket throughput under control.",
    moduleLinks: [
      { label: "Projects", href: "/modules/project_manager/projects" },
      { label: "Schedule", href: "/modules/project_manager/schedule" },
      { label: "RFIs", href: "/modules/project_manager/rfis" },
      { label: "Change Orders", href: "/modules/project_manager/change-orders" },
    ],
    quickActions: [
      { label: "Create project", href: "/projects/new" },
      { label: "Open dispatch board", href: "/ticket-manager" },
      { label: "Open daily production", href: "/daily-production" },
    ],
    kpiOrder: ["active_projects", "open_tickets", "tickets", "intake_pending_review"],
  },
  field_supervisor: {
    title: "Field Supervisor Operations",
    subtitle: "Prioritize daily production, field issues, and active site execution.",
    moduleLinks: [
      { label: "Daily Field Reports", href: "/field-supervisor" },
      { label: "Safety", href: "/modules/field_supervisor/safety" },
      { label: "Production", href: "/modules/field_supervisor/production" },
      { label: "Crew", href: "/modules/field_supervisor/crew" },
    ],
    quickActions: [
      { label: "Submit daily report", href: "/daily-production" },
      { label: "Open ticket queue", href: "/tickets" },
      { label: "Open projects", href: "/projects" },
    ],
    kpiOrder: ["open_tickets", "tickets", "intake_pending_review", "active_projects"],
  },
  payroll: {
    title: "Payroll Operations",
    subtitle: "Monitor labor-related operational flow and payroll preparation workload.",
    moduleLinks: [
      { label: "Timecards", href: "/modules/payroll/timecards" },
      { label: "Overtime", href: "/modules/payroll/overtime" },
      { label: "Payroll Runs", href: "/modules/payroll/payroll-runs" },
      { label: "Labor Cost Allocation", href: "/modules/payroll/labor-cost-allocation" },
    ],
    quickActions: [
      { label: "Open workspace", href: "/workspace" },
      { label: "Review projects", href: "/projects" },
      { label: "Open tickets", href: "/tickets" },
    ],
    kpiOrder: ["active_projects", "tickets", "open_tickets", "intake_items"],
  },
  administrator: {
    title: "Administrator Operations",
    subtitle: "Oversee user access, platform integrations, and operational diagnostics.",
    moduleLinks: [
      { label: "User Admin", href: "/modules/administrator/user-admin" },
      { label: "Role Policies", href: "/modules/administrator/role-policies" },
      { label: "Audit Logs", href: "/modules/administrator/audit-logs" },
      { label: "Integrations", href: "/modules/administrator/integrations" },
    ],
    quickActions: [
      { label: "Open user settings", href: "/settings/users" },
      { label: "Open platform admin", href: "/platform-admin" },
      { label: "View modules", href: "/modules" },
    ],
    kpiOrder: ["projects", "active_projects", "tickets", "intake_pending_review"],
  },
  customer: {
    title: "Customer Project Visibility",
    subtitle: "Track customer-visible project progress, documents, and billing posture.",
    moduleLinks: [
      { label: "Project Snapshot", href: "/modules/customer/project-snapshot" },
      { label: "Milestones", href: "/modules/customer/milestones" },
      { label: "Documents", href: "/modules/customer/documents" },
      { label: "Billing Status", href: "/modules/customer/billing-status" },
    ],
    quickActions: [
      { label: "Open projects", href: "/projects" },
      { label: "View documents", href: "/extraction-queue" },
      { label: "View modules", href: "/modules" },
    ],
    kpiOrder: ["active_projects", "projects", "tickets", "intake_pending_review"],
  },
  vendor: {
    title: "Vendor Fulfillment Dashboard",
    subtitle: "Track procurement, delivery activity, and compliance records for assigned work.",
    moduleLinks: [
      { label: "Purchase Orders", href: "/modules/vendor/purchase-orders" },
      { label: "Invoice Submit", href: "/modules/vendor/invoice-submit" },
      { label: "Delivery Tracking", href: "/modules/vendor/delivery-tracking" },
      { label: "Compliance Docs", href: "/modules/vendor/compliance-docs" },
    ],
    quickActions: [
      { label: "Open vendor workspace", href: "/vendor" },
      { label: "Review projects", href: "/projects" },
      { label: "View modules", href: "/modules" },
    ],
    kpiOrder: ["tickets", "open_tickets", "projects", "intake_pending_review"],
  },
};

const STATUS_DOT: Record<string, string> = {
  active: "#16a34a",
  planning: "#2563eb",
  on_hold: "#d97706",
  complete: "#7c3aed",
  cancelled: "#dc2626",
};

const fmt = (n: string | number | null | undefined) =>
  !n || n === "0" ? "-" : Number(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const SHORT_KPI_META: Record<keyof Summary, { icon: string; suffix: string }> = {
  projects: { icon: "📁", suffix: "total projects" },
  active_projects: { icon: "🟢", suffix: "currently active" },
  tickets: { icon: "🎫", suffix: "total tickets" },
  open_tickets: { icon: "⚠️", suffix: "pending action" },
  estimates: { icon: "🧮", suffix: "this month" },
  draft_estimates: { icon: "📝", suffix: "in progress" },
  awarded_estimates: { icon: "🏆", suffix: "won bids" },
  intake_items: { icon: "📥", suffix: "documents tracked" },
  intake_pending_review: { icon: "🔎", suffix: "needs review" },
};

function toShortDate(value: string): string {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value.slice(0, 10);
  }
  return parsed.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [roleKey, setRoleKey] = useState<RoleKey>("project_manager");
  const [roleLabel, setRoleLabel] = useState("Project Manager");
  const [serverRoleExperience, setServerRoleExperience] = useState<RoleExperienceApiResponse | null>(null);

  const api = getApiBaseUrl();
  const token = getAccessToken();
  const tenant = getTenantId();

  useEffect(() => {
    document.body.classList.add("dashboard-shell");
    return () => {
      document.body.classList.remove("dashboard-shell");
    };
  }, []);

  useEffect(() => {
    if (!token) {
      window.location.href = "/login";
      return;
    }
    const h = { Authorization: `Bearer ${token}`, "X-Tenant-ID": tenant };

    Promise.all([
      getCurrentRoleAccess(),
      fetch(`${api}/api/projects`, { headers: h }).then((r) => (r.ok ? r.json() : [])),
      fetch(`${api}/api/tickets`, { headers: h }).then((r) => (r.ok ? r.json() : [])),
      fetch(`${api}/api/estimates`, { headers: h }).then((r) => (r.ok ? r.json() : [])),
      fetch(`${api}/api/intake/items`, { headers: h }).then((r) => (r.ok ? r.json() : [])),
      fetch(`${api}/api/dashboard/role-experience`, { headers: h }).then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([roleAccess, p, t, e, i, roleExperiencePayload]) => {
        const resolvedRole = roleAccess?.roleKey || "project_manager";
        const workspace = ROLE_WORKSPACES.find((entry) => entry.key === resolvedRole);
        setRoleKey(resolvedRole);
        setRoleLabel(workspace?.label || "Project Manager");
        setServerRoleExperience(roleExperiencePayload as RoleExperienceApiResponse | null);

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
          intake_pending_review: Array.isArray(i) ? i.filter((x: { status?: string }) => x.status === "pending_review").length : 0,
        });
        setLoading(false);
      })
      .catch(() => {
        setError("Some dashboard data could not be loaded. Please refresh.");
        setLoading(false);
      });
  }, [api, tenant, token]);

  const roleExperience = ROLE_EXPERIENCES[roleKey] || ROLE_EXPERIENCES.project_manager;
  const serverKpiOrder = (serverRoleExperience?.kpi_order || [])
    .filter((item): item is keyof Summary => item in KPI_META)
    .slice(0, 4);
  const effectiveKpiOrder = serverKpiOrder.length > 0 ? serverKpiOrder : roleExperience.kpiOrder;
  const effectiveModules = serverRoleExperience?.modules?.length ? serverRoleExperience.modules : roleExperience.moduleLinks;
  const effectiveQuickActions = serverRoleExperience?.quick_actions?.length ? serverRoleExperience.quick_actions : roleExperience.quickActions;

  const roleAlerts = (() => {
    if (serverRoleExperience?.alerts?.length) {
      return serverRoleExperience.alerts;
    }

    if (!summary) {
      return [];
    }

    const alerts: string[] = [];
    if (summary.intake_pending_review > 0) {
      alerts.push(`${summary.intake_pending_review} intake items require review.`);
    }
    if (summary.open_tickets > 0) {
      alerts.push(`${summary.open_tickets} tickets remain open.`);
    }
    if ((roleKey === "estimator" || roleKey === "executive" || roleKey === "company_owner") && summary.draft_estimates > 0) {
      alerts.push(`${summary.draft_estimates} estimates are still in draft.`);
    }
    if ((roleKey === "dispatcher" || roleKey === "fleet_manager") && summary.open_tickets > summary.active_projects * 3 && summary.active_projects > 0) {
      alerts.push("Dispatch load is high relative to active projects.");
    }
    if ((roleKey === "accounting" || roleKey === "executive" || roleKey === "company_owner") && summary.awarded_estimates > 0 && summary.open_tickets > 0) {
      alerts.push("Awarded estimates and open tickets indicate pending billing follow-through.");
    }

    return alerts.slice(0, 3);
  })();

  const recentProjects = projects.slice(0, 5);
  const recentTickets = tickets.slice(0, 6);
  const activeEstimates = estimates.filter((e) => !["Archived", "Not Awarded", "Converted to Project"].includes(e.status)).slice(0, 5);

  const topKpis = effectiveKpiOrder.slice(0, 4);
  const chartSeries = topKpis.map((key, idx) => {
    const value = Number(summary?.[key] ?? 0);
    return {
      key,
      x: idx,
      y: value,
      label: KPI_META[key].label,
    };
  });
  const maxY = Math.max(1, ...chartSeries.map((point) => point.y));
  const trendPath = chartSeries
    .map((point, index) => {
      const x = chartSeries.length > 1 ? (point.x / (chartSeries.length - 1)) * 100 : 0;
      const y = 100 - (point.y / maxY) * 82;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const chartHint = chartSeries.length > 0
    ? `${chartSeries[0].label} to ${chartSeries[chartSeries.length - 1].label}`
    : "No trend data";
  const weatherTemp = 82;
  const intakePressure = summary?.intake_pending_review ?? 0;
  const openTicketPressure = summary?.open_tickets ?? 0;
  const healthScore = Math.max(58, Math.min(96, 92 - intakePressure * 2 - Math.floor(openTicketPressure * 0.8)));

  return (
    <AppShell titleKey="dashboard.title">
      <div className={styles.surface}>
        <div className={styles.surfaceGlow} aria-hidden />

        <section className={styles.commandDeck}>
          <div className={styles.commandLeft}>
            <div className={styles.rolePill}>{serverRoleExperience?.role_label || roleLabel}</div>
            <h2 className={styles.commandTitle}>Welcome back, John 👋</h2>
            <p className={styles.commandSubtitle}>Here&apos;s what&apos;s happening with your projects today.</p>
            <p className={styles.workspaceTitle}>{roleExperience.title}</p>
          </div>

          <div className={styles.commandRight}>
            <label className={styles.commandSearch}>
              <span className={styles.commandSearchIcon} aria-hidden>⌕</span>
              <input placeholder="Search documents, tickets, vendors..." aria-label="Global search" />
            </label>
            <button type="button" className={styles.uploadButton}>Upload</button>
          </div>
        </section>

        {loading ? (
          <p className={styles.stateText}>Loading dashboard...</p>
        ) : error ? (
          <div className={styles.errorPanel}>
            <p className={styles.errorText}>{error}</p>
          </div>
        ) : (
          <>
            <section className={styles.kpiGrid}>
              {topKpis.map((kpiKey) => {
                const meta = KPI_META[kpiKey];
                const miniMeta = SHORT_KPI_META[kpiKey];
                return (
                  <Link key={kpiKey} href={meta.href} className={styles.kpiCard}>
                    <div className={styles.kpiCardTop}>
                      <span className={styles.kpiIcon} aria-hidden>{miniMeta.icon}</span>
                      <span className={styles.kpiLabel}>{meta.label}</span>
                    </div>
                    <div className={styles.kpiValue}>{summary?.[kpiKey] ?? 0}</div>
                    <div className={styles.kpiSubline}>{miniMeta.suffix}</div>
                  </Link>
                );
              })}
            </section>

            <section className={styles.contentGrid}>
              <div className={styles.mainColumn}>
                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <h3>Document Activity</h3>
                    <span>{chartHint}</span>
                  </div>
                  <div className={styles.chartWrap}>
                    <svg className={styles.chartSvg} viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Dashboard trend chart">
                      <defs>
                        <linearGradient id="trendStroke" x1="0" y1="0" x2="1" y2="0">
                          <stop offset="0%" stopColor="#3f8cff" />
                          <stop offset="100%" stopColor="#46d7a4" />
                        </linearGradient>
                      </defs>
                      <polyline
                        points="0,90 100,90"
                        fill="none"
                        stroke="rgba(126, 147, 194, 0.35)"
                        strokeWidth="0.8"
                        vectorEffect="non-scaling-stroke"
                      />
                      {trendPath ? (
                        <path
                          d={trendPath}
                          fill="none"
                          stroke="url(#trendStroke)"
                          strokeWidth="2"
                          vectorEffect="non-scaling-stroke"
                          strokeLinecap="round"
                        />
                      ) : null}
                    </svg>
                  </div>
                </article>

                <div className={styles.triplePanelGrid}>
                  <article className={styles.panel}>
                    <div className={styles.panelHeader}>
                      <h3>Role Modules</h3>
                      <Link href="/modules">View all</Link>
                    </div>
                    <ul className={styles.listStack}>
                      {effectiveModules.slice(0, 5).map((moduleLink) => (
                        <li key={moduleLink.label} className={styles.listRow}>
                          <Link href={moduleLink.href} className={styles.listPrimary}>{moduleLink.label}</Link>
                          <span className={styles.listMeta}>Open module</span>
                        </li>
                      ))}
                    </ul>
                  </article>

                  <article className={styles.panel}>
                    <div className={styles.panelHeader}>
                      <h3>Recent Documents</h3>
                      <Link href="/extraction-queue">View all</Link>
                    </div>
                    {recentTickets.length === 0 ? (
                      <p className={styles.emptyText}>No tickets yet.</p>
                    ) : (
                      <ul className={styles.listStack}>
                        {recentTickets.map((ticket) => (
                          <li key={ticket.id} className={styles.listRow}>
                            <div>
                              <div className={styles.listPrimary}>{ticket.ticket_number || "Unnumbered ticket"}</div>
                              <div className={styles.listMeta}>{ticket.material || "Material pending"}</div>
                            </div>
                            <span className={styles.badge}>{toShortDate(ticket.created_at)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </article>

                  <article className={styles.panel}>
                    <div className={styles.panelHeader}>
                      <h3>Activity Feed</h3>
                      <Link href="/tickets">View all</Link>
                    </div>
                    <ul className={styles.activityFeed}>
                      {recentTickets.slice(0, 3).map((ticket) => (
                        <li key={ticket.id}>
                          <span className={styles.activityIcon}>✓</span>
                          <div>
                            <strong>Ticket activity</strong>
                            <p>{ticket.ticket_number || "New ticket"} · {ticket.material || "Material pending"}</p>
                          </div>
                          <em>{toShortDate(ticket.created_at)}</em>
                        </li>
                      ))}
                      {activeEstimates.slice(0, 2).map((estimate) => (
                        <li key={estimate.id}>
                          <span className={styles.activityIcon}>↗</span>
                          <div>
                            <strong>Estimate updated</strong>
                            <p>{estimate.estimate_name}</p>
                          </div>
                          <em>{estimate.bid_due_date ? toShortDate(estimate.bid_due_date) : "Open"}</em>
                        </li>
                      ))}
                    </ul>
                  </article>
                </div>
              </div>

              <div className={styles.sideColumn}>
                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <h3>Estimate Snapshot</h3>
                    <Link href="/estimator">Open</Link>
                  </div>
                  <div className={styles.snapshotValue}>{fmt(recentProjects[0]?.contract_amount || null)}</div>
                  <p className={styles.snapshotCaption}>Top project value</p>
                  <ul className={styles.compactList}>
                    {activeEstimates.slice(0, 4).map((estimate) => (
                      <li key={estimate.id}>
                        <span>{estimate.estimate_name}</span>
                        <span>{estimate.status}</span>
                      </li>
                    ))}
                  </ul>
                </article>

                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <h3>Project Health</h3>
                    <span>Live</span>
                  </div>
                  <div className={styles.healthDialWrap}>
                    <div className={styles.healthDial}>
                      <span>{healthScore}</span>
                    </div>
                    <p>Portfolio health score based on open tickets and intake review pressure.</p>
                    </div>
                </article>

                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <h3>Quick Actions</h3>
                    <span>Launch</span>
                  </div>
                  <div className={styles.quickActions}>
                    {effectiveQuickActions.map((action) => (
                      <Link key={action.label} href={action.href} className={styles.quickActionLink}>
                        {action.label}
                      </Link>
                    ))}
                  </div>
                </article>

                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <h3>Recent Alerts</h3>
                    <span>{roleAlerts.length}</span>
                  </div>
                  {roleAlerts.length > 0 ? (
                    <ul className={styles.alertStack}>
                      {roleAlerts.map((alertText) => (
                        <li key={alertText}>{alertText}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className={styles.emptyText}>No active alerts.</p>
                  )}
                </article>

                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <h3>Weather</h3>
                    <span>Durham, NC</span>
                  </div>
                  <div className={styles.weatherNow}>{weatherTemp}°F</div>
                  <p className={styles.snapshotCaption}>Mostly sunny. Good conditions for field throughput.</p>
                  <div className={styles.weatherDays}>
                    {["Fri", "Sat", "Sun", "Mon", "Tue"].map((day, idx) => (
                      <div key={day}>
                        <span>{day}</span>
                        <strong>{80 + ((idx + 1) % 4)}°</strong>
                      </div>
                    ))}
                  </div>
                </article>
              </div>
            </section>

            <section className={styles.bottomPanels}>
              <article className={styles.panel}>
                <div className={styles.panelHeader}>
                  <h3>Project Pipeline</h3>
                  <Link href="/projects">View all</Link>
                </div>
                {recentProjects.length === 0 ? (
                  <p className={styles.emptyText}>No projects yet.</p>
                ) : (
                  <ul className={styles.listStack}>
                    {recentProjects.map((project) => (
                      <li key={project.id} className={styles.listRow}>
                        <div>
                          <div className={styles.listPrimary}>{project.project_name}</div>
                          <div className={styles.listMeta}>{fmt(project.contract_amount)}</div>
                        </div>
                        <span className={styles.statusDot} style={{ color: STATUS_DOT[project.status] ?? "#64748b" }}>
                          {project.status.replace("_", " ")}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </article>

              <article className={styles.panel}>
                <div className={styles.panelHeader}>
                  <h3>Open Tickets</h3>
                  <Link href="/tickets">View all</Link>
                </div>
                {recentTickets.length === 0 ? (
                  <p className={styles.emptyText}>No tickets yet.</p>
                ) : (
                  <div className={styles.tableWrap}>
                    <table className={styles.ticketsTable}>
                      <thead>
                        <tr>
                          <th>Ticket #</th>
                          <th>Material</th>
                          <th>Status</th>
                          <th>Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recentTickets.map((ticket) => (
                          <tr key={ticket.id}>
                            <td>{ticket.ticket_number || "-"}</td>
                            <td>{ticket.material || "-"}</td>
                            <td>{ticket.status}</td>
                            <td>{toShortDate(ticket.created_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </article>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
