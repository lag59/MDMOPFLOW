export type RoleKey =
  | "company_owner"
  | "executive"
  | "project_manager"
  | "estimator"
  | "dispatcher"
  | "accounting"
  | "payroll"
  | "safety_manager"
  | "fleet_manager"
  | "administrator"
  | "customer"
  | "vendor";

export type RoleWorkspace = {
  key: RoleKey;
  label: string;
  summary: string;
  modules: string[];
};

export const ROLE_WORKSPACES: RoleWorkspace[] = [
  {
    key: "company_owner",
    label: "Company Owner",
    summary: "Portfolio visibility, risk, and margin oversight.",
    modules: ["Executive Dashboard", "Portfolio", "Forecasting", "Approvals"],
  },
  {
    key: "executive",
    label: "Executive",
    summary: "Operational and financial KPI review across projects.",
    modules: ["KPI Board", "Revenue", "Burn Rate", "Risk Radar"],
  },
  {
    key: "project_manager",
    label: "Project Manager",
    summary: "Plan, execute, and track active construction jobs.",
    modules: ["Projects", "Schedule", "RFIs", "Submittals", "Change Orders"],
  },
  {
    key: "estimator",
    label: "Estimator",
    summary: "Build and revise estimates from bid through handoff.",
    modules: ["Takeoff", "Estimate Versions", "Bid Pipeline", "Win/Loss"],
  },
  {
    key: "dispatcher",
    label: "Dispatcher",
    summary: "Assign crews and equipment to active work.",
    modules: ["Dispatch Board", "Crew Calendar", "Route Planning", "Utilization"],
  },
  {
    key: "accounting",
    label: "Accounting",
    summary: "Control AP/AR, invoices, and job cost reporting.",
    modules: ["AP", "AR", "Invoices", "Job Cost Ledger"],
  },
  {
    key: "payroll",
    label: "Payroll",
    summary: "Validate labor time and process payroll cycles.",
    modules: ["Timecards", "Overtime", "Payroll Runs", "Labor Cost Allocation"],
  },
  {
    key: "safety_manager",
    label: "Safety Manager",
    summary: "Track incidents and maintain compliance programs.",
    modules: ["Incidents", "Inspections", "Toolbox Talks", "Corrective Actions"],
  },
  {
    key: "fleet_manager",
    label: "Fleet Manager",
    summary: "Manage equipment health, downtime, and maintenance.",
    modules: ["Fleet", "Maintenance", "Fuel", "Work Orders"],
  },
  {
    key: "administrator",
    label: "Administrator",
    summary: "Configure users, roles, modules, and integrations.",
    modules: ["User Admin", "Role Policies", "Audit Logs", "Integrations"],
  },
  {
    key: "customer",
    label: "Customer",
    summary: "Review project status and shared deliverables.",
    modules: ["Project Snapshot", "Milestones", "Documents", "Billing Status"],
  },
  {
    key: "vendor",
    label: "Vendor",
    summary: "Submit invoices and track fulfillment for assigned work.",
    modules: ["Purchase Orders", "Invoice Submit", "Delivery Tracking", "Compliance Docs"],
  },
];

export function mapBackendRole(platformRole: string, membershipRoleName: string | undefined): RoleKey {
  if (platformRole === "platform_super_admin") {
    return "administrator";
  }

  const role = (membershipRoleName || "").toLowerCase();
  if (role.includes("owner")) {
    return "company_owner";
  }
  if (role.includes("exec")) {
    return "executive";
  }
  if (role.includes("estimate")) {
    return "estimator";
  }
  if (role.includes("dispatch")) {
    return "dispatcher";
  }
  if (role.includes("account")) {
    return "accounting";
  }
  if (role.includes("payroll")) {
    return "payroll";
  }
  if (role.includes("safety")) {
    return "safety_manager";
  }
  if (role.includes("fleet")) {
    return "fleet_manager";
  }
  if (role.includes("admin")) {
    return "administrator";
  }
  if (role.includes("customer")) {
    return "customer";
  }
  if (role.includes("vendor")) {
    return "vendor";
  }

  return "project_manager";
}
