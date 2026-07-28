import { ROLE_WORKSPACES, type RoleKey } from "@/lib/roles";

export type ModuleStatus = "live" | "bridge";

export type ModuleRouteConfig = {
  href: string;
  status: ModuleStatus;
  helperText: string;
};

export type ModuleDetail = {
  roleKey: RoleKey;
  roleLabel: string;
  roleSummary: string;
  moduleLabel: string;
  moduleSlug: string;
  route: ModuleRouteConfig;
};

export const MODULE_ROUTE_MAP: Record<string, ModuleRouteConfig> = {
  "Executive Dashboard": { href: "/dashboard", status: "live", helperText: "Portfolio-level ops dashboard" },
  Portfolio: { href: "/projects", status: "bridge", helperText: "Use projects as current portfolio view" },
  Forecasting: { href: "/projects", status: "bridge", helperText: "Use project metrics for forecast tracking" },
  Approvals: { href: "/intake", status: "bridge", helperText: "Use intake review approvals" },

  "KPI Board": { href: "/dashboard", status: "live", helperText: "Cross-project KPI board" },
  Revenue: { href: "/projects", status: "bridge", helperText: "Revenue view is in project metrics" },
  "Burn Rate": { href: "/projects", status: "bridge", helperText: "Burn is tracked in project profitability" },
  "Risk Radar": { href: "/intake", status: "bridge", helperText: "Use intake and review queues for active risk" },

  Projects: { href: "/projects", status: "live", helperText: "Projects module" },
  Schedule: { href: "/projects", status: "bridge", helperText: "Use project timeline and ticket activity" },
  RFIs: { href: "/projects", status: "bridge", helperText: "Tracked under project operations for now" },
  Submittals: { href: "/projects", status: "bridge", helperText: "Tracked under project operations for now" },
  "Change Orders": { href: "/projects", status: "bridge", helperText: "Tracked under project operations for now" },

  Takeoff: { href: "/tickets", status: "bridge", helperText: "Use ticket extraction + calculator" },
  "Estimate Versions": { href: "/tickets", status: "bridge", helperText: "Use ticket workflow revisions" },
  "Bid Pipeline": { href: "/projects", status: "bridge", helperText: "Use projects as active pipeline" },
  "Win/Loss": { href: "/dashboard", status: "bridge", helperText: "Use KPI dashboard summaries" },

  "Dispatch Board": { href: "/ticket-manager", status: "live", helperText: "Ticket-to-project dispatch" },
  "Crew Calendar": { href: "/ticket-manager", status: "bridge", helperText: "Use dispatch assignments" },
  "Route Planning": { href: "/ticket-manager", status: "bridge", helperText: "Use dispatch routing assignments" },
  Utilization: { href: "/ticket-manager", status: "bridge", helperText: "Use assignment load and ticket counts" },

  AP: { href: "/projects", status: "bridge", helperText: "Use project cost views" },
  AR: { href: "/projects", status: "bridge", helperText: "Use project revenue views" },
  Invoices: { href: "/tickets", status: "bridge", helperText: "Use ticket revenue + cost records" },
  "Job Cost Ledger": { href: "/projects", status: "bridge", helperText: "Project profitability ledger" },

  Timecards: { href: "/workspace", status: "bridge", helperText: "Use workspace resource records" },
  Overtime: { href: "/workspace", status: "bridge", helperText: "Use workspace labor records" },
  "Payroll Runs": { href: "/workspace", status: "bridge", helperText: "Use workspace reporting tools" },
  "Labor Cost Allocation": { href: "/projects", status: "bridge", helperText: "Use project profitability metrics" },

  Incidents: { href: "/intake", status: "bridge", helperText: "Use intake + review issue tracking" },
  Inspections: { href: "/intake", status: "bridge", helperText: "Use intake processing queues" },
  "Toolbox Talks": { href: "/workspace", status: "bridge", helperText: "Use workspace records and reports" },
  "Corrective Actions": { href: "/intake", status: "bridge", helperText: "Use intake review actions" },

  Fleet: { href: "/tickets", status: "bridge", helperText: "Use truck/material ticket activity" },
  Maintenance: { href: "/workspace", status: "bridge", helperText: "Use equipment resources" },
  Fuel: { href: "/tickets", status: "bridge", helperText: "Use ticket fuel cost tracking" },
  "Work Orders": { href: "/workspace", status: "bridge", helperText: "Use workspace operations records" },

  "User Admin": { href: "/settings/users", status: "live", helperText: "Tenant user administration" },
  "Role Policies": { href: "/platform-admin", status: "bridge", helperText: "Role governance controls" },
  "Audit Logs": { href: "/intake", status: "bridge", helperText: "Use replay token and intake audits" },
  Integrations: { href: "/platform-admin", status: "bridge", helperText: "Platform integration controls" },

  "Project Snapshot": { href: "/projects", status: "live", helperText: "Customer project overview" },
  Milestones: { href: "/projects", status: "bridge", helperText: "Use project timelines and status" },
  Documents: { href: "/extraction-queue", status: "live", helperText: "Document extraction and review" },
  "Billing Status": { href: "/projects", status: "bridge", helperText: "Use project revenue and costs" },

  "Purchase Orders": { href: "/projects", status: "bridge", helperText: "Use project procurement tracking" },
  "Invoice Submit": { href: "/tickets", status: "bridge", helperText: "Use ticket-based invoice records" },
  "Delivery Tracking": { href: "/ticket-manager", status: "bridge", helperText: "Use dispatch assignment tracking" },
  "Compliance Docs": { href: "/extraction-queue", status: "live", helperText: "Use extraction review queue" },
};

export function toModuleSlug(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function buildModuleDetailHref(roleKey: RoleKey, moduleLabel: string): string {
  return `/modules/${roleKey}/${toModuleSlug(moduleLabel)}`;
}

export function getModuleDetail(roleKey: string, moduleSlug: string): ModuleDetail | null {
  const workspace = ROLE_WORKSPACES.find((entry) => entry.key === roleKey);
  if (!workspace) return null;

  const moduleLabel = workspace.modules.find((entry) => toModuleSlug(entry) === moduleSlug);
  if (!moduleLabel) return null;

  const route = MODULE_ROUTE_MAP[moduleLabel];
  if (!route) return null;

  return {
    roleKey: workspace.key,
    roleLabel: workspace.label,
    roleSummary: workspace.summary,
    moduleLabel,
    moduleSlug,
    route,
  };
}
