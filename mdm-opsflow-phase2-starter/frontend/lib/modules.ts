import { ROLE_WORKSPACES, type RoleKey } from "@/lib/roles";

export type ModuleStatus = "live" | "bridge";

export type ModuleRouteConfig = {
  href: string;
  status: ModuleStatus;
  helperText: string;
  primaryActionLabel?: string;
  actionLinks?: Array<{
    label: string;
    href: string;
  }>;
  focusAreas?: string[];
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
  "Executive Dashboard": {
    href: "/dashboard",
    status: "live",
    helperText: "Portfolio-level ops dashboard",
    primaryActionLabel: "Open Executive Dashboard",
    actionLinks: [
      { label: "Open executive dashboard", href: "/dashboard" },
      { label: "Review project portfolio", href: "/projects" },
      { label: "Inspect ticket flow", href: "/tickets" },
    ],
    focusAreas: ["Portfolio KPIs", "Margin pressure", "AI action cards", "Operational exceptions"],
  },
  Portfolio: {
    href: "/projects",
    status: "bridge",
    helperText: "Use projects as current portfolio view",
    primaryActionLabel: "Open Portfolio View",
    actionLinks: [
      { label: "View active projects", href: "/projects" },
      { label: "Open modules dashboard", href: "/dashboard" },
      { label: "Review assigned tickets", href: "/ticket-manager" },
    ],
    focusAreas: ["Active job mix", "At-risk projects", "Revenue tracked", "Profitability follow-up"],
  },
  Forecasting: {
    href: "/projects",
    status: "bridge",
    helperText: "Use project metrics for forecast tracking",
    primaryActionLabel: "Open Forecast Inputs",
    actionLinks: [
      { label: "Review project metrics", href: "/projects" },
      { label: "Open executive dashboard", href: "/dashboard" },
      { label: "Inspect production tickets", href: "/projects" },
    ],
    focusAreas: ["Planned vs actual", "Production variance", "Schedule drift", "Final cost forecast"],
  },
  Approvals: {
    href: "/intake",
    status: "bridge",
    helperText: "Use intake review approvals",
    primaryActionLabel: "Open Approval Queue",
    actionLinks: [
      { label: "Open intake approvals", href: "/intake" },
      { label: "Review extraction queue", href: "/extraction-queue" },
      { label: "Open ticket assignment", href: "/ticket-manager" },
    ],
    focusAreas: ["Pending approvals", "OCR review backlog", "Exception routing", "Audit visibility"],
  },

  "KPI Board": {
    href: "/dashboard",
    status: "live",
    helperText: "Cross-project KPI board",
    primaryActionLabel: "Open KPI Board",
    actionLinks: [
      { label: "Open KPI dashboard", href: "/dashboard" },
      { label: "Review revenue drivers", href: "/projects" },
      { label: "Inspect ticket throughput", href: "/tickets" },
    ],
    focusAreas: ["Operational throughput", "Revenue tracked", "Approval bottlenecks", "At-risk jobs"],
  },
  Revenue: {
    href: "/projects",
    status: "bridge",
    helperText: "Revenue view is in project metrics",
    primaryActionLabel: "Open Revenue View",
    actionLinks: [
      { label: "Open project revenue", href: "/projects" },
      { label: "Review project tickets", href: "/tickets" },
      { label: "Check executive dashboard", href: "/dashboard" },
    ],
    focusAreas: ["Revenue tracked", "Ticket-backed billing", "Shortfall watchlist", "Project mix"],
  },
  "Burn Rate": {
    href: "/projects",
    status: "bridge",
    helperText: "Burn is tracked in project profitability",
    primaryActionLabel: "Open Burn Rate View",
    actionLinks: [
      { label: "Open profitability metrics", href: "/projects" },
      { label: "Review assignment load", href: "/ticket-manager" },
      { label: "Check production tickets", href: "/tickets" },
    ],
    focusAreas: ["Cost overrun flags", "Margin erosion", "Load volume", "Cash burn pressure"],
  },
  "Risk Radar": {
    href: "/intake",
    status: "bridge",
    helperText: "Use intake and review queues for active risk",
    primaryActionLabel: "Open Risk Radar",
    actionLinks: [
      { label: "Open intake alerts", href: "/intake" },
      { label: "Review extraction exceptions", href: "/extraction-queue" },
      { label: "Check at-risk projects", href: "/projects" },
    ],
    focusAreas: ["Stale approvals", "Extraction issues", "Unassigned tickets", "Portfolio exceptions"],
  },

  Projects: {
    href: "/projects",
    status: "live",
    helperText: "Projects module",
    primaryActionLabel: "Open Projects Workspace",
    actionLinks: [
      { label: "Open project list", href: "/projects" },
      { label: "Create new project", href: "/projects/new" },
      { label: "Review assigned tickets", href: "/ticket-manager" },
    ],
    focusAreas: ["Active jobs", "Project status", "Profitability", "Assigned ticket flow"],
  },
  Schedule: {
    href: "/daily-production",
    status: "bridge",
    helperText: "Foreman/superintendent daily production workflow",
    primaryActionLabel: "Open Daily Production Form",
    actionLinks: [
      { label: "Open daily production form", href: "/daily-production" },
      { label: "Open mechanic/material queue", href: "/daily-production/queue" },
      { label: "Review project tickets", href: "/tickets" },
      { label: "Open dispatch assignment", href: "/ticket-manager" },
    ],
    focusAreas: ["Labor hours", "Machine hours", "Material usage", "Queue-ready issue reporting"],
  },
  RFIs: {
    href: "/projects",
    status: "bridge",
    helperText: "Tracked under project operations for now",
    primaryActionLabel: "Open RFI Follow-up",
    actionLinks: [
      { label: "Open project detail", href: "/projects" },
      { label: "Review intake exceptions", href: "/intake" },
      { label: "Check document review", href: "/extraction-queue" },
    ],
    focusAreas: ["Open clarifications", "Field blockers", "Document review", "Cross-team follow-up"],
  },
  Submittals: {
    href: "/projects",
    status: "bridge",
    helperText: "Tracked under project operations for now",
    primaryActionLabel: "Open Submittal Tracking",
    actionLinks: [
      { label: "Open project detail", href: "/projects" },
      { label: "Review extracted documents", href: "/extraction-queue" },
      { label: "Open intake workflow", href: "/intake" },
    ],
    focusAreas: ["Pending documents", "Approval routing", "Field dependencies", "Delivery readiness"],
  },
  "Change Orders": {
    href: "/projects",
    status: "bridge",
    helperText: "Tracked under project operations for now",
    primaryActionLabel: "Open Change Order Watchlist",
    actionLinks: [
      { label: "Open project profitability", href: "/projects" },
      { label: "Review risk signals", href: "/modules/executive/risk-radar" },
      { label: "Check production tickets", href: "/tickets" },
    ],
    focusAreas: ["Scope variance", "Cost overrun risk", "Delay impacts", "Owner-facing follow-up"],
  },

  Takeoff: {
    href: "/tickets",
    status: "bridge",
    helperText: "Use ticket extraction + calculator",
    primaryActionLabel: "Open Takeoff Workspace",
    actionLinks: [
      { label: "Open ticket calculator", href: "/tickets" },
      { label: "Review material presets", href: "/tickets" },
      { label: "Open project pipeline", href: "/projects" },
    ],
    focusAreas: ["Quantity takeoff", "Material presets", "Load assumptions", "OCR-backed field capture"],
  },
  "Estimate Versions": {
    href: "/tickets",
    status: "bridge",
    helperText: "Use ticket workflow revisions",
    primaryActionLabel: "Open Estimate Versions",
    actionLinks: [
      { label: "Open ticket workspace", href: "/tickets" },
      { label: "Review project profitability", href: "/projects" },
      { label: "Open modules dashboard", href: "/dashboard" },
    ],
    focusAreas: ["Revision tracking", "Calculation outputs", "Material density changes", "Cost scenario checks"],
  },
  "Bid Pipeline": {
    href: "/projects",
    status: "bridge",
    helperText: "Use projects as active pipeline",
    primaryActionLabel: "Open Bid Pipeline",
    actionLinks: [
      { label: "Open projects pipeline", href: "/projects" },
      { label: "Review takeoff inputs", href: "/tickets" },
      { label: "Open executive dashboard", href: "/dashboard" },
    ],
    focusAreas: ["Pipeline jobs", "Bid assumptions", "Revenue outlook", "Estimate readiness"],
  },
  "Win/Loss": {
    href: "/dashboard",
    status: "bridge",
    helperText: "Use KPI dashboard summaries",
    primaryActionLabel: "Open Win/Loss View",
    actionLinks: [
      { label: "Open dashboard", href: "/dashboard" },
      { label: "Review project outcomes", href: "/projects" },
      { label: "Open estimate inputs", href: "/tickets" },
    ],
    focusAreas: ["Estimate outcomes", "Margin realization", "Pipeline conversion", "Bid performance"],
  },

  "Dispatch Board": {
    href: "/ticket-manager",
    status: "live",
    helperText: "Ticket-to-project dispatch",
    primaryActionLabel: "Open Dispatch Board",
    actionLinks: [
      { label: "Open assignment board", href: "/ticket-manager" },
      { label: "Review ticket intake", href: "/tickets" },
      { label: "Inspect project loads", href: "/projects" },
    ],
    focusAreas: ["Unassigned tickets", "Driver load", "Truck allocation", "Project assignment"],
  },
  "Crew Calendar": {
    href: "/ticket-manager",
    status: "bridge",
    helperText: "Use dispatch assignments",
    primaryActionLabel: "Open Crew Calendar",
    actionLinks: [
      { label: "Open dispatch board", href: "/ticket-manager" },
      { label: "Review active tickets", href: "/tickets" },
      { label: "Open projects", href: "/projects" },
    ],
    focusAreas: ["Crew load", "Driver schedule", "Assignment balance", "Field coverage"],
  },
  "Route Planning": {
    href: "/ticket-manager",
    status: "bridge",
    helperText: "Use dispatch routing assignments",
    primaryActionLabel: "Open Route Planning",
    actionLinks: [
      { label: "Open assignment board", href: "/ticket-manager" },
      { label: "Review ticket destinations", href: "/tickets" },
      { label: "Open project tickets", href: "/projects" },
    ],
    focusAreas: ["Destination clusters", "Truck routing", "Assigned destinations", "Unassigned loads"],
  },
  Utilization: {
    href: "/ticket-manager",
    status: "bridge",
    helperText: "Use assignment load and ticket counts",
    primaryActionLabel: "Open Utilization View",
    actionLinks: [
      { label: "Open dispatch board", href: "/ticket-manager" },
      { label: "Review ticket throughput", href: "/tickets" },
      { label: "Open projects", href: "/projects" },
    ],
    focusAreas: ["Assigned volume", "Truck usage", "Driver coverage", "Idle capacity"],
  },

  AP: {
    href: "/projects",
    status: "bridge",
    helperText: "Use project cost views",
    primaryActionLabel: "Open AP View",
    actionLinks: [
      { label: "Open project costs", href: "/projects" },
      { label: "Review fuel and haul costs", href: "/tickets" },
      { label: "Check project dashboards", href: "/projects" },
    ],
    focusAreas: ["Payables exposure", "Project cost review", "Fuel costs", "Overrun flags"],
  },
  AR: {
    href: "/projects",
    status: "bridge",
    helperText: "Use project revenue views",
    primaryActionLabel: "Open AR View",
    actionLinks: [
      { label: "Open project revenue", href: "/projects" },
      { label: "Review ticket revenue", href: "/tickets" },
      { label: "Check profitability", href: "/projects" },
    ],
    focusAreas: ["Receivables tracked", "Revenue shortfalls", "Ticket-backed billing", "Project collections"],
  },
  Invoices: {
    href: "/tickets",
    status: "bridge",
    helperText: "Use ticket revenue + cost records",
    primaryActionLabel: "Open Invoice Workspace",
    actionLinks: [
      { label: "Open ticket workspace", href: "/tickets" },
      { label: "Review assigned tickets", href: "/ticket-manager" },
      { label: "Open project tickets", href: "/projects" },
    ],
    focusAreas: ["Invoice-ready tickets", "Revenue records", "Missing assignments", "Delivery-backed billing"],
  },
  "Job Cost Ledger": {
    href: "/projects",
    status: "bridge",
    helperText: "Project profitability ledger",
    primaryActionLabel: "Open Job Cost Ledger",
    actionLinks: [
      { label: "Open profitability ledger", href: "/projects" },
      { label: "Review project dashboard", href: "/projects" },
      { label: "Inspect ticket costs", href: "/tickets" },
    ],
    focusAreas: ["Actual cost", "Gross profit", "Margin drift", "Per-project ledger"],
  },

  Timecards: {
    href: "/workspace",
    status: "bridge",
    helperText: "Use workspace resource records",
    primaryActionLabel: "Open Timecards View",
    actionLinks: [
      { label: "Open employee workspace", href: "/workspace" },
      { label: "Review project work", href: "/projects" },
      { label: "Open ticket records", href: "/tickets" },
    ],
    focusAreas: ["Employee roster", "Recorded work", "Daily activity", "Payroll readiness"],
  },
  Overtime: {
    href: "/workspace",
    status: "bridge",
    helperText: "Use workspace labor records",
    primaryActionLabel: "Open Overtime View",
    actionLinks: [
      { label: "Open employee workspace", href: "/workspace" },
      { label: "Review active jobs", href: "/projects" },
      { label: "Check dispatch load", href: "/ticket-manager" },
    ],
    focusAreas: ["Labor pressure", "Assignment load", "Employee utilization", "Hours follow-up"],
  },
  "Payroll Runs": {
    href: "/workspace",
    status: "bridge",
    helperText: "Use workspace reporting tools",
    primaryActionLabel: "Open Payroll Runs",
    actionLinks: [
      { label: "Open employee workspace", href: "/workspace" },
      { label: "Review job cost context", href: "/projects" },
      { label: "Open admin controls", href: "/settings/users" },
    ],
    focusAreas: ["Payroll cycle prep", "Employee count", "Project context", "Run readiness"],
  },
  "Labor Cost Allocation": {
    href: "/projects",
    status: "bridge",
    helperText: "Use project profitability metrics",
    primaryActionLabel: "Open Labor Cost Allocation",
    actionLinks: [
      { label: "Open project profitability", href: "/projects" },
      { label: "Review employee roster", href: "/workspace" },
      { label: "Check ticket activity", href: "/tickets" },
    ],
    focusAreas: ["Labor-to-job mapping", "Cost context", "Project allocation", "Margin impact"],
  },

  Incidents: {
    href: "/intake",
    status: "bridge",
    helperText: "Use intake + review issue tracking",
    primaryActionLabel: "Open Incident Queue",
    actionLinks: [
      { label: "Open intake alerts", href: "/intake" },
      { label: "Review extraction issues", href: "/extraction-queue" },
      { label: "Check active projects", href: "/projects" },
    ],
    focusAreas: ["Incident intake", "High-risk exceptions", "Delayed reviews", "Field escalation"],
  },
  Inspections: {
    href: "/intake",
    status: "bridge",
    helperText: "Use intake processing queues",
    primaryActionLabel: "Open Inspection View",
    actionLinks: [
      { label: "Open intake workflow", href: "/intake" },
      { label: "Review project dashboards", href: "/projects" },
      { label: "Open dispatch board", href: "/ticket-manager" },
    ],
    focusAreas: ["Inspection backlog", "Project attention", "Site coverage", "Field readiness"],
  },
  "Toolbox Talks": {
    href: "/workspace",
    status: "bridge",
    helperText: "Use workspace records and reports",
    primaryActionLabel: "Open Toolbox Talk View",
    actionLinks: [
      { label: "Open workspace", href: "/workspace" },
      { label: "Open active projects", href: "/projects" },
      { label: "Review safety issues", href: "/intake" },
    ],
    focusAreas: ["Crew communication", "Field reminders", "Active jobs", "Safety follow-up"],
  },
  "Corrective Actions": {
    href: "/intake",
    status: "bridge",
    helperText: "Use intake review actions",
    primaryActionLabel: "Open Corrective Actions",
    actionLinks: [
      { label: "Open intake approvals", href: "/intake" },
      { label: "Review extraction exceptions", href: "/extraction-queue" },
      { label: "Check project risk", href: "/projects" },
    ],
    focusAreas: ["Open actions", "Stale approvals", "Field issues", "Risk resolution"],
  },

  Fleet: {
    href: "/workspace",
    status: "bridge",
    helperText: "Use truck/material ticket activity",
    primaryActionLabel: "Open Fleet Overview",
    actionLinks: [
      { label: "Open equipment workspace", href: "/workspace" },
      { label: "Review truck tickets", href: "/tickets" },
      { label: "Open dispatch board", href: "/ticket-manager" },
    ],
    focusAreas: ["Fleet assets", "Truck activity", "Fuel signals", "Dispatch coverage"],
  },
  Maintenance: {
    href: "/workspace",
    status: "bridge",
    helperText: "Use equipment resources",
    primaryActionLabel: "Open Maintenance View",
    actionLinks: [
      { label: "Open equipment workspace", href: "/workspace" },
      { label: "Review truck assignments", href: "/ticket-manager" },
      { label: "Open fleet overview", href: "/modules/fleet_manager/fleet" },
    ],
    focusAreas: ["Equipment list", "Maintenance follow-up", "Idle assets", "Field readiness"],
  },
  Fuel: {
    href: "/tickets",
    status: "bridge",
    helperText: "Use ticket fuel cost tracking",
    primaryActionLabel: "Open Fuel Tracking",
    actionLinks: [
      { label: "Open ticket costs", href: "/tickets" },
      { label: "Review dispatch board", href: "/ticket-manager" },
      { label: "Open fleet workspace", href: "/workspace" },
    ],
    focusAreas: ["Fuel cost tracked", "Truck fuel patterns", "High-cost loads", "Ticket-linked fuel usage"],
  },
  "Work Orders": {
    href: "/workspace",
    status: "bridge",
    helperText: "Use workspace operations records",
    primaryActionLabel: "Open Work Orders",
    actionLinks: [
      { label: "Open equipment workspace", href: "/workspace" },
      { label: "Review fleet overview", href: "/modules/fleet_manager/fleet" },
      { label: "Inspect dispatch activity", href: "/ticket-manager" },
    ],
    focusAreas: ["Open equipment issues", "Asset attention list", "Truck usage", "Operations follow-up"],
  },

  "User Admin": {
    href: "/settings/users",
    status: "live",
    helperText: "Tenant user administration",
    primaryActionLabel: "Open User Admin",
    actionLinks: [
      { label: "Open tenant users", href: "/settings/users" },
      { label: "Open platform admin", href: "/platform-admin" },
      { label: "Review module catalog", href: "/modules" },
    ],
    focusAreas: ["Tenant memberships", "Role assignment", "Function access", "User status"],
  },
  "Role Policies": {
    href: "/settings/users",
    status: "bridge",
    helperText: "Role governance controls",
    primaryActionLabel: "Open Role Policies",
    actionLinks: [
      { label: "Open user permissions", href: "/settings/users" },
      { label: "Open platform admin", href: "/platform-admin" },
      { label: "Review admin modules", href: "/modules/administrator/user-admin" },
    ],
    focusAreas: ["Permission catalog", "Overrides", "Role governance", "Access control"],
  },
  "Audit Logs": {
    href: "/platform-admin",
    status: "bridge",
    helperText: "Use replay token and intake audits",
    primaryActionLabel: "Open Audit View",
    actionLinks: [
      { label: "Open platform insights", href: "/platform-admin" },
      { label: "Review intake operations", href: "/intake" },
      { label: "Open extraction queue", href: "/extraction-queue" },
    ],
    focusAreas: ["Operational exceptions", "Failed integrations", "Review backlog", "Admin follow-up"],
  },
  Integrations: {
    href: "/platform-admin",
    status: "bridge",
    helperText: "Platform integration controls",
    primaryActionLabel: "Open Integrations View",
    actionLinks: [
      { label: "Open service insights", href: "/platform-admin" },
      { label: "Review intake queue", href: "/intake" },
      { label: "Open extraction queue", href: "/extraction-queue" },
    ],
    focusAreas: ["Integration failures", "Pending events", "Platform opportunities", "Service health"],
  },

  "Project Snapshot": {
    href: "/projects",
    status: "live",
    helperText: "Customer project overview",
    primaryActionLabel: "Open Project Snapshot",
    actionLinks: [
      { label: "Open project portfolio", href: "/projects" },
      { label: "Review project documents", href: "/extraction-queue" },
      { label: "Check billing status", href: "/modules/customer/billing-status" },
    ],
    focusAreas: ["Project status", "Revenue snapshot", "Ticket activity", "Customer visibility"],
  },
  Milestones: {
    href: "/projects",
    status: "bridge",
    helperText: "Use project timelines and status",
    primaryActionLabel: "Open Milestones View",
    actionLinks: [
      { label: "Open project snapshot", href: "/projects" },
      { label: "Review project dashboard", href: "/projects" },
      { label: "Inspect assigned tickets", href: "/projects" },
    ],
    focusAreas: ["Active milestones", "Status tracking", "Project progress", "Delivery readiness"],
  },
  Documents: {
    href: "/extraction-queue",
    status: "live",
    helperText: "Document extraction and review",
    primaryActionLabel: "Open Documents View",
    actionLinks: [
      { label: "Open document queue", href: "/extraction-queue" },
      { label: "Review intake records", href: "/intake" },
      { label: "Open project snapshot", href: "/projects" },
    ],
    focusAreas: ["Shared documents", "Review status", "Uploaded records", "Project context"],
  },
  "Billing Status": {
    href: "/projects",
    status: "bridge",
    helperText: "Use project revenue and costs",
    primaryActionLabel: "Open Billing Status",
    actionLinks: [
      { label: "Open project billing", href: "/projects" },
      { label: "Review project tickets", href: "/tickets" },
      { label: "Open project snapshot", href: "/projects" },
    ],
    focusAreas: ["Revenue tracked", "Margin snapshot", "Ticket-backed billing", "Project financial status"],
  },

  "Purchase Orders": {
    href: "/projects",
    status: "bridge",
    helperText: "Use project procurement tracking",
    primaryActionLabel: "Open Purchase Orders",
    actionLinks: [
      { label: "Open project procurement", href: "/projects" },
      { label: "Review delivery tickets", href: "/tickets" },
      { label: "Check compliance docs", href: "/modules/vendor/compliance-docs" },
    ],
    focusAreas: ["Project procurement", "Open deliveries", "Vendor workload", "Order follow-up"],
  },
  "Invoice Submit": {
    href: "/tickets",
    status: "bridge",
    helperText: "Use ticket-based invoice records",
    primaryActionLabel: "Open Invoice Submit",
    actionLinks: [
      { label: "Open ticket billing", href: "/tickets" },
      { label: "Review project costs", href: "/projects" },
      { label: "Open delivery tracking", href: "/modules/vendor/delivery-tracking" },
    ],
    focusAreas: ["Invoice-ready records", "Ticket-backed billing", "Revenue lines", "Submission follow-up"],
  },
  "Delivery Tracking": {
    href: "/ticket-manager",
    status: "bridge",
    helperText: "Use dispatch assignment tracking",
    primaryActionLabel: "Open Delivery Tracking",
    actionLinks: [
      { label: "Open dispatch assignments", href: "/ticket-manager" },
      { label: "Review delivery tickets", href: "/tickets" },
      { label: "Open project deliveries", href: "/projects" },
    ],
    focusAreas: ["Assigned deliveries", "Destination visibility", "Truck movement", "Project drop-offs"],
  },
  "Compliance Docs": {
    href: "/extraction-queue",
    status: "live",
    helperText: "Use extraction review queue",
    primaryActionLabel: "Open Compliance Docs",
    actionLinks: [
      { label: "Open document review", href: "/extraction-queue" },
      { label: "Review intake uploads", href: "/intake" },
      { label: "Open vendor deliveries", href: "/modules/vendor/delivery-tracking" },
    ],
    focusAreas: ["Document completeness", "Review backlog", "Vendor upload status", "Compliance follow-up"],
  },
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

export function getVisibleWorkspacesForRole(roleKey: RoleKey, isSuperAdmin: boolean) {
  if (isSuperAdmin) {
    return ROLE_WORKSPACES;
  }

  const currentRoleWorkspace = ROLE_WORKSPACES.find((workspace) => workspace.key === roleKey);
  const otherWorkspaces = ROLE_WORKSPACES.filter((workspace) => workspace.key !== roleKey);

  return currentRoleWorkspace ? [currentRoleWorkspace, ...otherWorkspaces] : ROLE_WORKSPACES;
}
