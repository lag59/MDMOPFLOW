"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import React, { useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getModuleDetail } from "@/lib/modules";
import { fetchReplayTokenStateAlerts, type ReplayTokenStateAlerts } from "@/lib/replayTokens";
import { getApiBaseUrl } from "@/lib/i18n";
import { listMaterialDensityPresets, listTickets, type MaterialDensityPreset, type Ticket } from "@/lib/tickets";

type Project = {
  id: string;
  project_name: string;
  project_number: string;
  status: string;
};

type WorkspaceResource = {
  id: string;
  name?: string;
  unit_number?: string;
};

type AdminOverview = {
  tenants: number;
  users: number;
  projects: number;
};

type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  title: string;
  platform_role: "platform_super_admin" | "user";
  is_active: boolean;
};

type ServiceInsights = {
  tickets: number;
  intake_items: number;
  intake_needs_review: number;
  extractions_pending_review: number;
  extractions_review_submitted: number;
  unresolved_extraction_issues: number;
  integration_events_pending: number;
  integration_events_failed: number;
  opportunities: string[];
};

type TenantUserMembership = {
  user_id: string;
  email: string;
  display_name: string;
  title: string;
  role_name: string;
  status: string;
};

type ProjectProfitability = {
  project_id: string;
  project_name: string;
  status: string;
  actual_revenue: number;
  actual_cost: number;
  gross_profit: number;
  profit_margin: number;
  cost_overrun: boolean;
  revenue_shortfall: boolean;
  ticket_count: number;
};

export default function ModuleDetailPage() {
  const params = useParams();
  const role = String(params?.role || "");
  const moduleSlug = String(params?.module || "");
  const detail = getModuleDetail(role, moduleSlug);
  const [projects, setProjects] = useState<Project[]>([]);
  const [profitability, setProfitability] = useState<Map<string, ProjectProfitability>>(new Map());
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [alerts, setAlerts] = useState<ReplayTokenStateAlerts | null>(null);
  const [equipment, setEquipment] = useState<WorkspaceResource[]>([]);
  const [trucks, setTrucks] = useState<WorkspaceResource[]>([]);
  const [employees, setEmployees] = useState<WorkspaceResource[]>([]);
  const [adminOverview, setAdminOverview] = useState<AdminOverview | null>(null);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [serviceInsights, setServiceInsights] = useState<ServiceInsights | null>(null);
  const [tenantUsers, setTenantUsers] = useState<TenantUserMembership[]>([]);
  const [permissionCatalog, setPermissionCatalog] = useState<string[]>([]);
  const [materialPresets, setMaterialPresets] = useState<MaterialDensityPreset[]>([]);
  const [insightsLoading, setInsightsLoading] = useState(false);

  useEffect(() => {
    if (!detail || !["company_owner", "executive", "project_manager", "estimator", "dispatcher", "accounting", "payroll", "fleet_manager", "safety_manager", "administrator", "customer", "vendor"].includes(detail.roleKey)) {
      return;
    }

    const token = getAccessToken();
    if (!token) {
      return;
    }

    const headers = {
      Authorization: `Bearer ${token}`,
      "X-Tenant-ID": getTenantId(),
    };

    const loadInsights = async () => {
      setInsightsLoading(true);
      try {
        const projectRes = await fetch(`${getApiBaseUrl()}/api/projects`, { headers });
        const projectData = (projectRes.ok ? await projectRes.json() : []) as Project[];
        setProjects(projectData);

        const profitEntries = await Promise.all(
          projectData.map(async (project) => {
            try {
              const response = await fetch(`${getApiBaseUrl()}/api/projects/${project.id}/profitability`, { headers });
              if (!response.ok) {
                return null;
              }
              const data = (await response.json()) as ProjectProfitability;
              return [project.id, data] as const;
            } catch {
              return null;
            }
          })
        );

        setProfitability(new Map(profitEntries.filter((entry): entry is readonly [string, ProjectProfitability] => entry !== null)));

        try {
          const [ticketData, alertData, equipmentData, truckData, employeeData, tenantUserData, permissionCatalogData, overviewData, adminUserData, serviceInsightsData, materialPresetData] = await Promise.all([
            listTickets(),
            fetchReplayTokenStateAlerts({ staleThresholdMinutes: 60, staleActiveThresholdCount: 10 }),
            fetch(`${getApiBaseUrl()}/api/equipment`, { headers }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/trucks`, { headers }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/employees`, { headers }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/tenant-users`, { headers }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/tenant-users/permissions/catalog`, { headers }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/admin/overview`, { headers: { Authorization: `Bearer ${token}` } }).then((res) => (res.ok ? res.json() : null)),
            fetch(`${getApiBaseUrl()}/api/admin/users`, { headers: { Authorization: `Bearer ${token}` } }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/admin/service-insights`, { headers: { Authorization: `Bearer ${token}` } }).then((res) => (res.ok ? res.json() : null)),
            listMaterialDensityPresets().catch(() => []),
          ]);
          setTickets(ticketData);
          setAlerts(alertData);
          setEquipment(equipmentData as WorkspaceResource[]);
          setTrucks(truckData as WorkspaceResource[]);
          setEmployees(employeeData as WorkspaceResource[]);
          setTenantUsers(tenantUserData as TenantUserMembership[]);
          setPermissionCatalog(permissionCatalogData as string[]);
          setAdminOverview(overviewData as AdminOverview | null);
          setAdminUsers(adminUserData as AdminUser[]);
          setServiceInsights(serviceInsightsData as ServiceInsights | null);
          setMaterialPresets(materialPresetData as MaterialDensityPreset[]);
        } catch {
          setTickets([]);
          setAlerts(null);
          setEquipment([]);
          setTrucks([]);
          setEmployees([]);
          setTenantUsers([]);
          setPermissionCatalog([]);
          setAdminOverview(null);
          setAdminUsers([]);
          setServiceInsights(null);
          setMaterialPresets([]);
        }
      } finally {
        setInsightsLoading(false);
      }
    };

    loadInsights();
  }, [detail?.moduleSlug, detail?.roleKey]);

  const ownerSummary = useMemo(() => {
    const profitabilityItems = Array.from(profitability.values());
    const activeProjects = projects.filter((project) => project.status === "active").length;
    const atRiskProjects = profitabilityItems.filter((item) => item.cost_overrun || item.revenue_shortfall);
    const totalRevenue = profitabilityItems.reduce((acc, item) => acc + Number(item.actual_revenue || 0), 0);
    const totalMargin = profitabilityItems.reduce((acc, item) => acc + Number(item.gross_profit || 0), 0);
    const assignedTickets = tickets.filter((ticket) => !!ticket.project_id).length;

    return {
      activeProjects,
      atRiskProjects,
      totalRevenue,
      totalMargin,
      assignedTickets,
      flaggedApprovals: alerts?.active_tokens_older_than_threshold ?? 0,
      approvalPressure: alerts?.active_tokens_older_than_threshold_exceeded ?? false,
      topAtRiskProjects: atRiskProjects.slice(0, 5),
      unassignedTickets: tickets.filter((ticket) => !ticket.project_id).slice(0, 5),
    };
  }, [alerts, profitability, projects, tickets]);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);

  const renderCompanyOwnerContent = () => {
    if (!detail || !["company_owner", "executive", "project_manager", "estimator", "dispatcher", "accounting", "payroll", "fleet_manager", "safety_manager", "administrator", "customer", "vendor"].includes(detail.roleKey)) {
      return null;
    }

    if (insightsLoading) {
      return (
        <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading portfolio signals...
        </section>
      );
    }

    if (detail.moduleSlug === "executive-dashboard") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active projects</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.activeProjects}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">At-risk projects</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Approval backlog</div><div className="mt-2 text-3xl font-bold text-red-600">{ownerSummary.flaggedApprovals}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Executive signals</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p>Assigned tickets in circulation: {ownerSummary.assignedTickets}</p>
              <p>Gross margin tracked: {formatCurrency(ownerSummary.totalMargin)}</p>
              <p>{ownerSummary.approvalPressure ? "Approval pressure is elevated due to stale review tokens." : "Approval queue is within threshold."}</p>
            </div>
          </div>
        </section>
      );
    }

    if (detail.moduleSlug === "portfolio") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Portfolio projects</h2>
          <div className="mt-4 space-y-3">
            {projects.slice(0, 6).map((project) => {
              const projectProfitability = profitability.get(project.id);
              return (
                <div key={project.id} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{project.project_name}</div>
                      <div className="text-sm text-slate-500">{project.project_number} • {project.status}</div>
                    </div>
                    <Link href={`/projects/${project.id}`} className="text-sm font-semibold text-blue-700 hover:underline">Open project</Link>
                  </div>
                  <div className="mt-3 grid gap-3 text-sm text-slate-700 md:grid-cols-3">
                    <div>Revenue: {formatCurrency(Number(projectProfitability?.actual_revenue || 0))}</div>
                    <div>Margin: {Number(projectProfitability?.profit_margin || 0).toFixed(1)}%</div>
                    <div>Tickets: {projectProfitability?.ticket_count || 0}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      );
    }

    if (detail.moduleSlug === "forecasting") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Forecast watchlist</h2>
          <div className="mt-4 space-y-3">
            {ownerSummary.topAtRiskProjects.length === 0 ? (
              <p className="text-sm text-slate-600">No at-risk projects are currently flagged by profitability signals.</p>
            ) : (
              ownerSummary.topAtRiskProjects.map((item) => (
                <div key={item.project_id} className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-slate-800">
                  <div className="font-semibold">{item.project_name}</div>
                  <div className="mt-1">Margin: {Number(item.profit_margin || 0).toFixed(1)}% • Revenue: {formatCurrency(Number(item.actual_revenue || 0))}</div>
                  <div className="mt-1">{item.cost_overrun ? "Cost overrun flagged" : ""}{item.cost_overrun && item.revenue_shortfall ? " • " : ""}{item.revenue_shortfall ? "Revenue shortfall flagged" : ""}</div>
                </div>
              ))
            )}
          </div>
        </section>
      );
    }

    if (detail.moduleSlug === "approvals") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Approval backlog</h2>
            <div className="mt-3 text-3xl font-bold text-slate-900">{ownerSummary.flaggedApprovals}</div>
            <p className="mt-2 text-sm text-slate-600">Items exceeding the replay-token alert threshold.</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Unassigned ticket follow-up</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              {ownerSummary.unassignedTickets.length === 0 ? (
                <p>No unassigned tickets currently need owner attention.</p>
              ) : (
                ownerSummary.unassignedTickets.map((ticket) => (
                  <div key={ticket.id} className="rounded-md border border-slate-200 px-3 py-2">
                    {ticket.ticket_number || "Untitled ticket"} • {ticket.material || "Unspecified material"}
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "executive" && detail.moduleSlug === "kpi-board") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Gross margin</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(ownerSummary.totalMargin)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Assigned tickets</div><div className="mt-2 text-3xl font-bold text-blue-700">{ownerSummary.assignedTickets}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Risk flags</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Executive KPI summary</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p>Active projects: {ownerSummary.activeProjects}</p>
              <p>Approval backlog above threshold: {ownerSummary.flaggedApprovals}</p>
              <p>Projects with profitability warnings: {ownerSummary.topAtRiskProjects.length}</p>
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "executive" && detail.moduleSlug === "revenue") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Revenue watchlist</h2>
          <div className="mt-4 space-y-3">
            {Array.from(profitability.values()).slice(0, 6).map((item) => (
              <div key={item.project_id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{item.project_name}</div>
                    <div className="text-sm text-slate-500">{item.status}</div>
                  </div>
                  <div className="text-right text-sm text-slate-700">
                    <div>Revenue: {formatCurrency(Number(item.actual_revenue || 0))}</div>
                    <div>Tickets: {item.ticket_count}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "executive" && detail.moduleSlug === "burn-rate") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Burn rate signals</h2>
          <div className="mt-4 space-y-3">
            {ownerSummary.topAtRiskProjects.length === 0 ? (
              <p className="text-sm text-slate-600">No burn-rate exceptions are currently flagged.</p>
            ) : (
              ownerSummary.topAtRiskProjects.map((item) => (
                <div key={item.project_id} className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-slate-800">
                  <div className="font-semibold">{item.project_name}</div>
                  <div className="mt-1">Gross profit: {formatCurrency(Number(item.gross_profit || 0))}</div>
                  <div className="mt-1">Margin: {Number(item.profit_margin || 0).toFixed(1)}%</div>
                </div>
              ))
            )}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "executive" && detail.moduleSlug === "risk-radar") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Operational risk</h2>
            <div className="mt-3 text-3xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div>
            <p className="mt-2 text-sm text-slate-600">Projects currently flagged by profitability warnings.</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Workflow risk</h2>
            <div className="mt-3 text-3xl font-bold text-red-600">{ownerSummary.flaggedApprovals + ownerSummary.unassignedTickets.length}</div>
            <p className="mt-2 text-sm text-slate-600">Combined stale approval and unassigned ticket follow-up count.</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "project_manager" && detail.moduleSlug === "projects") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active jobs</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.activeProjects}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Assigned tickets</div><div className="mt-2 text-3xl font-bold text-blue-700">{ownerSummary.assignedTickets}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">At-risk jobs</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Project execution board</h2>
            <div className="mt-4 space-y-3">
              {projects.slice(0, 6).map((project) => {
                const projectProfitability = profitability.get(project.id);
                return (
                  <div key={project.id} className="rounded-lg border border-slate-200 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{project.project_name}</div>
                        <div className="text-sm text-slate-500">{project.project_number} • {project.status}</div>
                      </div>
                      <div className="flex gap-3 text-sm">
                        <Link href={`/projects/${project.id}`} className="font-semibold text-blue-700 hover:underline">Details</Link>
                        <Link href={`/projects/${project.id}/dashboard`} className="font-semibold text-blue-700 hover:underline">Dashboard</Link>
                      </div>
                    </div>
                    <div className="mt-3 grid gap-3 text-sm text-slate-700 md:grid-cols-3">
                      <div>Margin: {Number(projectProfitability?.profit_margin || 0).toFixed(1)}%</div>
                      <div>Tickets: {projectProfitability?.ticket_count || 0}</div>
                      <div>Revenue: {formatCurrency(Number(projectProfitability?.actual_revenue || 0))}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "project_manager" && detail.moduleSlug === "schedule") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Schedule pressure view</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
              <div className="font-semibold text-slate-900">Execution load</div>
              <p className="mt-2">Assigned tickets in play: {ownerSummary.assignedTickets}</p>
              <p>Unassigned tickets needing dispatch: {ownerSummary.unassignedTickets.length}</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
              <div className="font-semibold text-slate-900">Projects needing attention</div>
              <p className="mt-2">At-risk projects: {ownerSummary.topAtRiskProjects.length}</p>
              <p>Approval backlog: {ownerSummary.flaggedApprovals}</p>
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "project_manager" && detail.moduleSlug === "rfis") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">RFI follow-up board</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-700">
            <p>Use intake exceptions and document review to track unresolved project clarifications.</p>
            <p>Approval backlog currently flagged: {ownerSummary.flaggedApprovals}</p>
            <p>Unassigned tickets that may indicate missing field direction: {ownerSummary.unassignedTickets.length}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "project_manager" && detail.moduleSlug === "submittals") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Submittal readiness</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2 text-sm text-slate-700">
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="font-semibold text-slate-900">Document intake</div>
              <p className="mt-2">Approval backlog above threshold: {ownerSummary.flaggedApprovals}</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="font-semibold text-slate-900">Project readiness</div>
              <p className="mt-2">Active jobs ready for document follow-up: {ownerSummary.activeProjects}</p>
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "project_manager" && detail.moduleSlug === "change-orders") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Change order watchlist</h2>
          <div className="mt-4 space-y-3">
            {ownerSummary.topAtRiskProjects.length === 0 ? (
              <p className="text-sm text-slate-600">No current change-order risk signals are flagged.</p>
            ) : (
              ownerSummary.topAtRiskProjects.map((item) => (
                <div key={item.project_id} className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-slate-800">
                  <div className="font-semibold">{item.project_name}</div>
                  <div className="mt-1">Margin: {Number(item.profit_margin || 0).toFixed(1)}%</div>
                  <div className="mt-1">Revenue: {formatCurrency(Number(item.actual_revenue || 0))}</div>
                </div>
              ))
            )}
          </div>
        </section>
      );
    }

    const driverCounts = tickets.reduce<Map<string, number>>((acc, ticket) => {
      const key = (ticket.driver || "Unassigned driver").trim() || "Unassigned driver";
      acc.set(key, (acc.get(key) || 0) + 1);
      return acc;
    }, new Map());
    const truckCounts = tickets.reduce<Map<string, number>>((acc, ticket) => {
      const key = (ticket.truck || "Unassigned truck").trim() || "Unassigned truck";
      acc.set(key, (acc.get(key) || 0) + 1);
      return acc;
    }, new Map());
    const topDrivers = Array.from(driverCounts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 4);
    const topTrucks = Array.from(truckCounts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 4);
    const profitabilityItems = Array.from(profitability.values());
    const totalActualCost = profitabilityItems.reduce((acc, item) => acc + Number(item.actual_cost || 0), 0);
    const totalGrossProfit = profitabilityItems.reduce((acc, item) => acc + Number(item.gross_profit || 0), 0);
    const totalFuelCost = tickets.reduce((acc, ticket) => acc + Number(ticket.fuel_cost || 0), 0);
    const revenueReadyTickets = tickets.filter((ticket) => Number(ticket.revenue || 0) > 0).length;
    const equipmentCount = equipment.length;
    const truckCount = trucks.length;
    const activeTenantUsers = tenantUsers.filter((user) => user.status === "active").length;
    const distinctMaterials = Array.from(new Set(tickets.map((ticket) => ticket.material.trim()).filter(Boolean)));
    const presetCoverage = distinctMaterials.filter((material) => materialPresets.some((preset) => preset.material_name.trim().toLowerCase() === material.toLowerCase())).length;
    const employeeCount = employees.length;

    if (detail.roleKey === "dispatcher" && detail.moduleSlug === "dispatch-board") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Unassigned tickets</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.unassignedTickets.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Assigned tickets</div><div className="mt-2 text-3xl font-bold text-green-600">{ownerSummary.assignedTickets}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active projects</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.activeProjects}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Dispatch backlog</div><div className="mt-2 text-3xl font-bold text-red-600">{ownerSummary.flaggedApprovals}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Dispatch board</h2>
            <div className="mt-4 space-y-3">
              {tickets.slice(0, 6).map((ticket) => (
                <div key={ticket.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{ticket.ticket_number || "Untitled ticket"}</div>
                      <div>{ticket.material || "Unknown material"} • {ticket.destination || "No destination"}</div>
                    </div>
                    <div className="text-right">
                      <div>Driver: {ticket.driver || "Unassigned"}</div>
                      <div>Truck: {ticket.truck || "Unassigned"}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "dispatcher" && detail.moduleSlug === "crew-calendar") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Driver load</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              {topDrivers.map(([driver, count]) => (
                <div key={driver} className="rounded-md border border-slate-200 px-3 py-2">{driver}: {count} ticket(s)</div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Crew coverage</h2>
            <p className="mt-3 text-sm text-slate-700">Use current driver and truck assignments to balance dispatch load across field crews.</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "dispatcher" && detail.moduleSlug === "route-planning") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Route planning signals</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-700">
            <p>Unassigned loads needing route planning: {ownerSummary.unassignedTickets.length}</p>
            <p>Assigned loads currently in motion: {ownerSummary.assignedTickets}</p>
            <p>Projects currently receiving loads: {ownerSummary.activeProjects}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "dispatcher" && detail.moduleSlug === "utilization") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Truck utilization</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              {topTrucks.map(([truck, count]) => (
                <div key={truck} className="rounded-md border border-slate-200 px-3 py-2">{truck}: {count} ticket(s)</div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Capacity view</h2>
            <p className="mt-3 text-sm text-slate-700">Assigned vs unassigned ticket volume provides the current dispatch utilization snapshot.</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "accounting" && detail.moduleSlug === "ap") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Actual cost</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(totalActualCost)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Fuel cost tracked</div><div className="mt-2 text-3xl font-bold text-red-600">{formatCurrency(totalFuelCost)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Overrun projects</div><div className="mt-2 text-3xl font-bold text-amber-600">{profitabilityItems.filter((item) => item.cost_overrun).length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tracked jobs</div><div className="mt-2 text-3xl font-bold text-slate-900">{profitabilityItems.length}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "accounting" && detail.moduleSlug === "ar") {
      return (
        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-3xl font-bold text-green-600">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue shortfalls</div><div className="mt-2 text-3xl font-bold text-amber-600">{profitabilityItems.filter((item) => item.revenue_shortfall).length}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Invoice-ready tickets</div><div className="mt-2 text-3xl font-bold text-slate-900">{revenueReadyTickets}</div></div>
        </section>
      );
    }

    if (detail.roleKey === "accounting" && detail.moduleSlug === "invoices") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Invoice-ready ticket flow</h2>
          <div className="mt-4 space-y-3">
            {tickets.slice(0, 6).map((ticket) => (
              <div key={ticket.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{ticket.ticket_number || "Untitled ticket"}</div>
                    <div>{ticket.material || "Unknown material"} • {ticket.driver || "No driver"}</div>
                  </div>
                  <div className="text-right">
                    <div>Revenue: {formatCurrency(Number(ticket.revenue || 0))}</div>
                    <div>Fuel: {formatCurrency(Number(ticket.fuel_cost || 0))}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "accounting" && detail.moduleSlug === "job-cost-ledger") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Job cost ledger</h2>
          <div className="mt-4 space-y-3">
            {profitabilityItems.slice(0, 6).map((item) => (
              <div key={item.project_id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{item.project_name}</div>
                    <div>{item.status}</div>
                  </div>
                  <div className="text-right">
                    <div>Cost: {formatCurrency(Number(item.actual_cost || 0))}</div>
                    <div>Profit: {formatCurrency(Number(item.gross_profit || 0))}</div>
                  </div>
                </div>
              </div>
            ))}
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-800">
              Total gross profit tracked: {formatCurrency(totalGrossProfit)}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "fleet_manager" && detail.moduleSlug === "fleet") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Equipment assets</div><div className="mt-2 text-3xl font-bold text-slate-900">{equipmentCount}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Truck units</div><div className="mt-2 text-3xl font-bold text-blue-700">{truckCount}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Assigned tickets</div><div className="mt-2 text-3xl font-bold text-green-600">{ownerSummary.assignedTickets}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Fuel tracked</div><div className="mt-2 text-3xl font-bold text-red-600">{formatCurrency(totalFuelCost)}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Fleet activity</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2 text-sm text-slate-700">
              <div>
                <div className="font-semibold text-slate-900">Equipment roster</div>
                <div className="mt-2 space-y-2">
                  {equipment.slice(0, 4).map((item) => (
                    <div key={item.id} className="rounded-md border border-slate-200 px-3 py-2">{item.name || item.unit_number || item.id}</div>
                  ))}
                </div>
              </div>
              <div>
                <div className="font-semibold text-slate-900">Truck roster</div>
                <div className="mt-2 space-y-2">
                  {trucks.slice(0, 4).map((item) => (
                    <div key={item.id} className="rounded-md border border-slate-200 px-3 py-2">{item.unit_number || item.name || item.id}</div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "fleet_manager" && detail.moduleSlug === "maintenance") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Maintenance attention</h2>
            <p className="mt-3 text-sm text-slate-700">Equipment assets currently tracked: {equipmentCount}</p>
            <p className="mt-1 text-sm text-slate-700">Truck units currently tracked: {truckCount}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Dispatch impact</h2>
            <p className="mt-3 text-sm text-slate-700">Assigned tickets depending on fleet readiness: {ownerSummary.assignedTickets}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "fleet_manager" && detail.moduleSlug === "fuel") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Fuel tracking</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Fuel tracked</div><div className="mt-2 text-2xl font-bold text-red-600">{formatCurrency(totalFuelCost)}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tickets with revenue</div><div className="mt-2 text-2xl font-bold text-slate-900">{revenueReadyTickets}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Truck units</div><div className="mt-2 text-2xl font-bold text-blue-700">{truckCount}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "fleet_manager" && detail.moduleSlug === "work-orders") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Work order queue</h2>
          <div className="mt-4 space-y-2 text-sm text-slate-700">
            <p>Use the equipment and truck rosters as the current work-order source list.</p>
            <p>Fleet-linked dispatch load: {ownerSummary.assignedTickets} assigned tickets.</p>
            <p>Assets currently in the system: {equipmentCount + truckCount}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "safety_manager" && detail.moduleSlug === "incidents") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Incident backlog</div><div className="mt-2 text-3xl font-bold text-red-600">{ownerSummary.flaggedApprovals}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">At-risk projects</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Unassigned tickets</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.unassignedTickets.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active jobs</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.activeProjects}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Incident watchlist</h2>
            <div className="mt-4 space-y-3">
              {ownerSummary.topAtRiskProjects.length === 0 ? (
                <p className="text-sm text-slate-600">No high-risk projects are currently flagged.</p>
              ) : (
                ownerSummary.topAtRiskProjects.map((item) => (
                  <div key={item.project_id} className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-slate-800">
                    <div className="font-semibold">{item.project_name}</div>
                    <div className="mt-1">Margin: {Number(item.profit_margin || 0).toFixed(1)}%</div>
                    <div className="mt-1">Ticket volume: {item.ticket_count}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "safety_manager" && detail.moduleSlug === "inspections") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Inspection pressure</h2>
            <p className="mt-3 text-sm text-slate-700">Stale approval items needing review: {ownerSummary.flaggedApprovals}</p>
            <p className="mt-1 text-sm text-slate-700">Projects with elevated operational risk: {ownerSummary.topAtRiskProjects.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Field coverage</h2>
            <p className="mt-3 text-sm text-slate-700">Assigned tickets currently tied to active work: {ownerSummary.assignedTickets}</p>
            <p className="mt-1 text-sm text-slate-700">Active jobs needing inspection oversight: {ownerSummary.activeProjects}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "safety_manager" && detail.moduleSlug === "toolbox-talks") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Toolbox talk coordination</h2>
          <div className="mt-4 space-y-2 text-sm text-slate-700">
            <p>Active crews inferred from assigned tickets: {ownerSummary.assignedTickets}</p>
            <p>Projects currently active: {ownerSummary.activeProjects}</p>
            <p>Open safety follow-up signals: {ownerSummary.flaggedApprovals + ownerSummary.topAtRiskProjects.length}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "safety_manager" && detail.moduleSlug === "corrective-actions") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Corrective actions queue</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Open actions</div><div className="mt-2 text-2xl font-bold text-red-600">{ownerSummary.flaggedApprovals}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Risk jobs</div><div className="mt-2 text-2xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Unresolved workflow items</div><div className="mt-2 text-2xl font-bold text-slate-900">{ownerSummary.unassignedTickets.length}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "administrator" && detail.moduleSlug === "user-admin") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tenant users</div><div className="mt-2 text-3xl font-bold text-slate-900">{tenantUsers.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active users</div><div className="mt-2 text-3xl font-bold text-green-600">{activeTenantUsers}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Platform users</div><div className="mt-2 text-3xl font-bold text-blue-700">{adminOverview?.users ?? adminUsers.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Permission catalog</div><div className="mt-2 text-3xl font-bold text-slate-900">{permissionCatalog.length}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">User access queue</h2>
            <div className="mt-4 space-y-2 text-sm text-slate-700">
              {tenantUsers.slice(0, 5).map((user) => (
                <div key={user.user_id} className="rounded-md border border-slate-200 px-3 py-2">{user.display_name || user.email} • {user.role_name} • {user.status}</div>
              ))}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "administrator" && detail.moduleSlug === "role-policies") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Role governance</h2>
            <p className="mt-3 text-sm text-slate-700">Function catalog entries: {permissionCatalog.length}</p>
            <p className="mt-1 text-sm text-slate-700">Tenant members under role control: {tenantUsers.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Platform scope</h2>
            <p className="mt-3 text-sm text-slate-700">Tenants in overview: {adminOverview?.tenants ?? 0}</p>
            <p className="mt-1 text-sm text-slate-700">Projects in overview: {adminOverview?.projects ?? projects.length}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "administrator" && detail.moduleSlug === "audit-logs") {
      return (
        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Failed integrations</div><div className="mt-2 text-3xl font-bold text-red-600">{serviceInsights?.integration_events_failed ?? 0}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Extraction issues</div><div className="mt-2 text-3xl font-bold text-amber-600">{serviceInsights?.unresolved_extraction_issues ?? 0}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Intake review backlog</div><div className="mt-2 text-3xl font-bold text-slate-900">{serviceInsights?.intake_needs_review ?? 0}</div></div>
        </section>
      );
    }

    if (detail.roleKey === "administrator" && detail.moduleSlug === "integrations") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Integration health</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Pending events</div><div className="mt-2 text-2xl font-bold text-slate-900">{serviceInsights?.integration_events_pending ?? 0}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Failed events</div><div className="mt-2 text-2xl font-bold text-red-600">{serviceInsights?.integration_events_failed ?? 0}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Improvement opportunities</div><div className="mt-2 text-2xl font-bold text-blue-700">{serviceInsights?.opportunities.length ?? 0}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "estimator" && detail.moduleSlug === "takeoff") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Ticket records</div><div className="mt-2 text-3xl font-bold text-slate-900">{tickets.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Material presets</div><div className="mt-2 text-3xl font-bold text-blue-700">{materialPresets.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Material coverage</div><div className="mt-2 text-3xl font-bold text-green-600">{presetCoverage}/{distinctMaterials.length || 0}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Takeoff inputs</h2>
            <div className="mt-4 space-y-2 text-sm text-slate-700">
              {materialPresets.slice(0, 5).map((preset) => (
                <div key={preset.id} className="rounded-md border border-slate-200 px-3 py-2">{preset.material_name} • density {preset.density_tons_per_cubic_yard}</div>
              ))}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "estimator" && detail.moduleSlug === "estimate-versions") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Estimate version signals</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Preset library</div><div className="mt-2 text-2xl font-bold text-slate-900">{materialPresets.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Distinct materials</div><div className="mt-2 text-2xl font-bold text-blue-700">{distinctMaterials.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">At-risk jobs</div><div className="mt-2 text-2xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "estimator" && detail.moduleSlug === "bid-pipeline") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Bid pipeline</h2>
          <div className="mt-4 space-y-3">
            {projects.slice(0, 6).map((project) => {
              const projectProfitability = profitability.get(project.id);
              return (
                <div key={project.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{project.project_name}</div>
                      <div>{project.project_number} • {project.status}</div>
                    </div>
                    <div className="text-right">
                      <div>Revenue: {formatCurrency(Number(projectProfitability?.actual_revenue || 0))}</div>
                      <div>Margin: {Number(projectProfitability?.profit_margin || 0).toFixed(1)}%</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "estimator" && detail.moduleSlug === "win-loss") {
      return (
        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tracked jobs</div><div className="mt-2 text-3xl font-bold text-slate-900">{projects.length}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">At-risk jobs</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Gross profit tracked</div><div className="mt-2 text-3xl font-bold text-green-600">{formatCurrency(totalGrossProfit)}</div></div>
        </section>
      );
    }

    if (detail.roleKey === "customer" && detail.moduleSlug === "project-snapshot") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tracked projects</div><div className="mt-2 text-3xl font-bold text-slate-900">{projects.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active projects</div><div className="mt-2 text-3xl font-bold text-blue-700">{ownerSummary.activeProjects}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Project revenue</div><div className="mt-2 text-3xl font-bold text-green-600">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Project tickets</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.assignedTickets}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Customer project snapshot</h2>
            <div className="mt-4 space-y-3">
              {projects.slice(0, 5).map((project) => {
                const projectProfitability = profitability.get(project.id);
                return (
                  <div key={project.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{project.project_name}</div>
                        <div>{project.project_number} • {project.status}</div>
                      </div>
                      <div className="text-right">
                        <div>Revenue: {formatCurrency(Number(projectProfitability?.actual_revenue || 0))}</div>
                        <div>Tickets: {projectProfitability?.ticket_count || 0}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "customer" && detail.moduleSlug === "milestones") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Milestone progress</h2>
            <p className="mt-3 text-sm text-slate-700">Active projects currently visible: {ownerSummary.activeProjects}</p>
            <p className="mt-1 text-sm text-slate-700">Projects needing attention: {ownerSummary.topAtRiskProjects.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Delivery readiness</h2>
            <p className="mt-3 text-sm text-slate-700">Assigned project tickets in circulation: {ownerSummary.assignedTickets}</p>
            <p className="mt-1 text-sm text-slate-700">Review backlog that may affect milestones: {ownerSummary.flaggedApprovals}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "customer" && detail.moduleSlug === "documents") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Document visibility</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Review backlog</div><div className="mt-2 text-2xl font-bold text-amber-600">{ownerSummary.flaggedApprovals}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tracked projects</div><div className="mt-2 text-2xl font-bold text-slate-900">{projects.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Ticket records</div><div className="mt-2 text-2xl font-bold text-blue-700">{tickets.length}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "customer" && detail.moduleSlug === "billing-status") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Billing status</h2>
          <div className="mt-4 space-y-3">
            {Array.from(profitability.values()).slice(0, 5).map((item) => (
              <div key={item.project_id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{item.project_name}</div>
                    <div>{item.status}</div>
                  </div>
                  <div className="text-right">
                    <div>Revenue: {formatCurrency(Number(item.actual_revenue || 0))}</div>
                    <div>Margin: {Number(item.profit_margin || 0).toFixed(1)}%</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "vendor" && detail.moduleSlug === "purchase-orders") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tracked projects</div><div className="mt-2 text-3xl font-bold text-slate-900">{projects.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Assigned deliveries</div><div className="mt-2 text-3xl font-bold text-blue-700">{ownerSummary.assignedTickets}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Open review items</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.flaggedApprovals}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-3xl font-bold text-green-600">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Purchase order context</h2>
            <div className="mt-4 space-y-3">
              {projects.slice(0, 5).map((project) => (
                <div key={project.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                  <div className="font-semibold text-slate-900">{project.project_name}</div>
                  <div>{project.project_number} • {project.status}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "vendor" && detail.moduleSlug === "invoice-submit") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Invoice submit queue</h2>
          <div className="mt-4 space-y-3">
            {tickets.slice(0, 5).map((ticket) => (
              <div key={ticket.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{ticket.ticket_number || "Untitled ticket"}</div>
                    <div>{ticket.material || "Unknown material"} • {ticket.destination || "No destination"}</div>
                  </div>
                  <div className="text-right">
                    <div>Revenue: {formatCurrency(Number(ticket.revenue || 0))}</div>
                    <div>Status: {ticket.status}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "vendor" && detail.moduleSlug === "delivery-tracking") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Delivery tracking</h2>
            <p className="mt-3 text-sm text-slate-700">Assigned project tickets: {ownerSummary.assignedTickets}</p>
            <p className="mt-1 text-sm text-slate-700">Unassigned deliveries: {ownerSummary.unassignedTickets.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Project drop-offs</h2>
            <p className="mt-3 text-sm text-slate-700">Active projects receiving loads: {ownerSummary.activeProjects}</p>
            <p className="mt-1 text-sm text-slate-700">Review backlog affecting delivery flow: {ownerSummary.flaggedApprovals}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "vendor" && detail.moduleSlug === "compliance-docs") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Compliance document status</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Review backlog</div><div className="mt-2 text-2xl font-bold text-amber-600">{ownerSummary.flaggedApprovals}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Ticket records</div><div className="mt-2 text-2xl font-bold text-slate-900">{tickets.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tracked projects</div><div className="mt-2 text-2xl font-bold text-blue-700">{projects.length}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "payroll" && detail.moduleSlug === "timecards") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Employees</div><div className="mt-2 text-3xl font-bold text-slate-900">{employeeCount}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active projects</div><div className="mt-2 text-3xl font-bold text-blue-700">{ownerSummary.activeProjects}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Assigned tickets</div><div className="mt-2 text-3xl font-bold text-green-600">{ownerSummary.assignedTickets}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Jobs tracked</div><div className="mt-2 text-3xl font-bold text-slate-900">{projects.length}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Timecard roster</h2>
            <div className="mt-4 space-y-2 text-sm text-slate-700">
              {employees.slice(0, 5).map((employee) => (
                <div key={employee.id} className="rounded-md border border-slate-200 px-3 py-2">{employee.name || employee.unit_number || employee.id}</div>
              ))}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "payroll" && detail.moduleSlug === "overtime") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Overtime pressure</h2>
            <p className="mt-3 text-sm text-slate-700">Assigned tickets suggesting active field load: {ownerSummary.assignedTickets}</p>
            <p className="mt-1 text-sm text-slate-700">At-risk jobs requiring closer labor review: {ownerSummary.topAtRiskProjects.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Workload context</h2>
            <p className="mt-3 text-sm text-slate-700">Employees currently tracked: {employeeCount}</p>
            <p className="mt-1 text-sm text-slate-700">Active jobs in the tenant: {ownerSummary.activeProjects}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "payroll" && detail.moduleSlug === "payroll-runs") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Payroll run readiness</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Employee roster</div><div className="mt-2 text-2xl font-bold text-slate-900">{employeeCount}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tracked projects</div><div className="mt-2 text-2xl font-bold text-blue-700">{projects.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-2xl font-bold text-green-600">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "payroll" && detail.moduleSlug === "labor-cost-allocation") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Labor cost allocation</h2>
          <div className="mt-4 space-y-3">
            {Array.from(profitability.values()).slice(0, 5).map((item) => (
              <div key={item.project_id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{item.project_name}</div>
                    <div>{item.status}</div>
                  </div>
                  <div className="text-right">
                    <div>Cost: {formatCurrency(Number(item.actual_cost || 0))}</div>
                    <div>Margin: {Number(item.profit_margin || 0).toFixed(1)}%</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    return null;
  };

  if (!detail) {
    return (
      <AppShell titleKey="modules.title">
        <div className="space-y-4 p-6">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <h2 className="text-lg font-semibold text-red-900">Module route not found</h2>
            <p className="mt-1 text-sm text-red-800">The requested role/module combination does not exist in the current module catalog.</p>
          </div>
          <Link href="/modules" className="inline-flex text-sm font-semibold text-blue-700 hover:text-blue-900 hover:underline">
            Back to Modules
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell titleKey="modules.title">
      <div className="space-y-6 p-6">
        <div className="mb-2">
          <Link href="/modules" className="inline-flex text-sm font-semibold text-blue-700 hover:text-blue-900 hover:underline">
            Back to Modules
          </Link>
        </div>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{detail.roleLabel}</span>
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                detail.route.status === "live" ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"
              }`}
            >
              {detail.route.status === "live" ? "Live Module" : "Bridge Module"}
            </span>
          </div>

          <h1 className="text-3xl font-bold text-slate-900">{detail.moduleLabel}</h1>
          <p className="mt-2 text-sm text-slate-600">{detail.roleSummary}</p>
          <p className="mt-2 text-sm text-slate-700">{detail.route.helperText}</p>

          {detail.route.focusAreas?.length ? (
            <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Focus areas</h2>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {detail.route.focusAreas.map((item) => (
                  <div key={item} className="rounded-md bg-white px-3 py-2 text-sm text-slate-700 shadow-sm">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {detail.route.actionLinks?.length ? (
            <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Recommended actions</h2>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {detail.route.actionLinks.map((action) => (
                  <Link
                    key={`${detail.moduleSlug}-${action.label}`}
                    href={action.href}
                    className="rounded-lg border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-800 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800"
                  >
                    {action.label}
                  </Link>
                ))}
              </div>
            </div>
          ) : null}

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link
              href={detail.route.href}
              className="inline-flex items-center rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
            >
              {detail.route.primaryActionLabel || "Open Module Workspace"}
            </Link>
            <Link
              href="/modules"
              className="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              Browse Other Modules
            </Link>
          </div>
        </section>

        {renderCompanyOwnerContent()}
      </div>
    </AppShell>
  );
}
