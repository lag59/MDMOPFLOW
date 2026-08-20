import { describe, expect, it } from "vitest";

import { buildModuleDetailHref, getModuleDetail, getVisibleWorkspacesForRole, toModuleSlug } from "./modules";

describe("module metadata helpers", () => {
  it("slugifies labels and builds role-scoped module detail links", () => {
    expect(toModuleSlug("Executive Dashboard")).toBe("executive-dashboard");
    expect(buildModuleDetailHref("company_owner", "Executive Dashboard")).toBe(
      "/modules/company_owner/executive-dashboard"
    );
  });

  it("resolves module detail metadata for known role/module combinations", () => {
    const detail = getModuleDetail("dispatcher", "dispatch-board");
    expect(detail).not.toBeNull();
    expect(detail?.moduleLabel).toBe("Dispatch Board");
    expect(detail?.route.href).toBe("/ticket-manager");
    expect(detail?.route.status).toBe("live");
  });

  it("returns richer action metadata for company-owner executive dashboard", () => {
    const detail = getModuleDetail("company_owner", "executive-dashboard");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open Executive Dashboard");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Portfolio KPIs");
  });

  it("returns richer action metadata for executive KPI board", () => {
    const detail = getModuleDetail("executive", "kpi-board");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open KPI Board");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Operational throughput");
  });

  it("returns richer action metadata for project manager projects module", () => {
    const detail = getModuleDetail("project_manager", "projects");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open Projects Workspace");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Active jobs");
  });

  it("returns richer action metadata for dispatcher dispatch board", () => {
    const detail = getModuleDetail("dispatcher", "dispatch-board");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open Dispatch Board");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Unassigned tickets");
  });

  it("returns richer action metadata for accounting AP module", () => {
    const detail = getModuleDetail("accounting", "ap");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open AP View");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Payables exposure");
  });

  it("returns richer action metadata for fleet manager fleet module", () => {
    const detail = getModuleDetail("fleet_manager", "fleet");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open Fleet Overview");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Fleet assets");
  });

  it("resolves the field supervisor workspace modules as live route entries", () => {
    const safety = getModuleDetail("field_supervisor", "safety");
    const production = getModuleDetail("field_supervisor", "production");
    const crew = getModuleDetail("field_supervisor", "crew");
    const dailyReports = getModuleDetail("field_supervisor", "daily-field-reports");

    expect(safety).not.toBeNull();
    expect(safety?.route.status).toBe("live");
    expect(safety?.route.href).toBe("/modules/field_supervisor/safety");
    expect(production?.route.href).toBe("/modules/field_supervisor/production");
    expect(crew?.route.href).toBe("/modules/field_supervisor/crew");
    expect(dailyReports?.route.href).toBe("/field-supervisor");
  });

  it("returns richer action metadata for safety manager incidents module", () => {
    const detail = getModuleDetail("safety_manager", "incidents");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open Incident Queue");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Incident intake");
  });

  it("returns richer action metadata for administrator user admin module", () => {
    const detail = getModuleDetail("administrator", "user-admin");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open User Admin");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Tenant memberships");
  });

  it("returns richer action metadata for estimator takeoff module", () => {
    const detail = getModuleDetail("estimator", "takeoff");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open Takeoff Workspace");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Quantity takeoff");
  });

  it("returns richer action metadata for customer project snapshot module", () => {
    const detail = getModuleDetail("customer", "project-snapshot");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open Project Snapshot");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Project status");
  });

  it("returns richer action metadata for vendor purchase orders module", () => {
    const detail = getModuleDetail("vendor", "purchase-orders");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open Purchase Orders");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Project procurement");
  });

  it("returns richer action metadata for payroll timecards module", () => {
    const detail = getModuleDetail("payroll", "timecards");
    expect(detail).not.toBeNull();
    expect(detail?.route.primaryActionLabel).toBe("Open Timecards View");
    expect(detail?.route.actionLinks?.length).toBeGreaterThanOrEqual(3);
    expect(detail?.route.focusAreas).toContain("Employee roster");
  });

  it("returns null for unknown role or module slugs", () => {
    expect(getModuleDetail("unknown", "dispatch-board")).toBeNull();
    expect(getModuleDetail("dispatcher", "not-a-real-module")).toBeNull();
  });

  it("filters visible module workspaces to the roles assigned to the user", () => {
    const estimatorVisible = getVisibleWorkspacesForRole(["estimator"], false);
    expect(estimatorVisible).toHaveLength(1);
    expect(estimatorVisible[0].key).toBe("estimator");

    const multiRoleVisible = getVisibleWorkspacesForRole(["project_manager", "estimator"], false);
    expect(multiRoleVisible.map((workspace) => workspace.key)).toEqual(["project_manager", "estimator"]);
  });

  it("returns full workspace catalog for super admins", () => {
    const allVisible = getVisibleWorkspacesForRole(["project_manager"], true);
    expect(allVisible.length).toBeGreaterThan(1);
  });
});
