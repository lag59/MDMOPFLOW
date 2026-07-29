import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as roleAccess from "@/lib/roleAccess";

import ModuleDetailPage from "./page";

const mockParams = {
  role: "company_owner",
  module: "executive-dashboard",
};

vi.mock("@/components/AppShell", () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));

vi.mock("next/navigation", () => ({
  useParams: () => mockParams,
}));

vi.mock("@/lib/auth", () => ({
  getAccessToken: () => "token",
  getTenantId: () => "tenant-1",
}));

vi.mock("@/lib/i18n", () => ({
  getApiBaseUrl: () => "http://api.test",
}));

vi.mock("@/lib/roleAccess", () => ({
  getCurrentRoleAccess: vi.fn(async () => ({ roleKey: mockParams.role, isSuperAdmin: false })),
  canAccessModuleRole: vi.fn((context: { roleKey: string; isSuperAdmin: boolean } | null, routeRoleKey: string) => {
    if (!context) {
      return false;
    }
    return context.isSuperAdmin || context.roleKey === routeRoleKey;
  }),
}));

vi.mock("@/lib/tickets", () => ({
  listTickets: vi.fn(async () => [
    {
      id: "ticket-1",
      tenant_id: "tenant-1",
      intake_item_id: null,
      project_id: "project-1",
      ticket_number: "TCK-101",
      truck: "Unit 1",
      driver: "Driver A",
      material: "Aggregate",
      origin: "Pit",
      destination: "Jobsite",
      load_time: null,
      unload_time: null,
      miles: null,
      weight: null,
      volume_yards: null,
      tons: null,
      fuel_cost: null,
      revenue: null,
      status: "draft",
      notes: "",
      created_by: "user-1",
      created_at: "2026-07-28T00:00:00Z",
      updated_at: "2026-07-28T00:00:00Z",
    },
  ]),
  listMaterialDensityPresets: vi.fn(async () => [
    {
      id: "preset-1",
      tenant_id: "tenant-1",
      material_name: "Aggregate",
      density_tons_per_cubic_yard: "1.50",
      created_by: "user-1",
      created_at: "2026-07-28T00:00:00Z",
      updated_at: "2026-07-28T00:00:00Z",
    },
  ]),
}));

vi.mock("@/lib/replayTokens", () => ({
  fetchReplayTokenStateAlerts: vi.fn(async () => ({
    as_of: "2026-07-28T00:00:00Z",
    stale_threshold_minutes: 60,
    stale_active_threshold_count: 10,
    window_start_issued_at: null,
    window_end_issued_at: null,
    window_effective_timezone: "UTC",
    total_tokens: 12,
    active_tokens: 4,
    active_tokens_older_than_threshold: 3,
    active_tokens_older_than_threshold_exceeded: true,
    consumed_tokens: 5,
    revoked_tokens: 1,
    consumed_to_revoked_ratio: 5,
  })),
}));

vi.mock("@/lib/vendor", () => ({
  listVendorPurchaseOrders: vi.fn(async () => [
    {
      id: "po-1",
      tenant_id: "tenant-1",
      project_id: "project-1",
      po_number: "PO-1001",
      vendor_name: "Acme Materials",
      description: "Aggregate delivery",
      status: "open",
      total_amount: "12500.00",
      created_by: "user-1",
      created_at: "2026-07-28T00:00:00Z",
      updated_at: "2026-07-28T00:00:00Z",
    },
  ]),
  listVendorInvoiceSubmissions: vi.fn(async () => [
    {
      id: "inv-1",
      tenant_id: "tenant-1",
      project_id: "project-1",
      purchase_order_id: "po-1",
      invoice_number: "INV-501",
      vendor_name: "Acme Materials",
      amount: "6400.00",
      status: "submitted",
      notes: "First half",
      created_by: "user-1",
      created_at: "2026-07-28T00:00:00Z",
      updated_at: "2026-07-28T00:00:00Z",
    },
  ]),
  listVendorDeliveryRecords: vi.fn(async () => [
    {
      id: "del-1",
      tenant_id: "tenant-1",
      project_id: "project-1",
      purchase_order_id: "po-1",
      ticket_number: "TCK-DEL-01",
      vendor_name: "Acme Materials",
      destination: "North Yard",
      status: "delivered",
      received_at: "2026-07-28T10:00:00Z",
      created_by: "user-1",
      created_at: "2026-07-28T00:00:00Z",
      updated_at: "2026-07-28T00:00:00Z",
    },
  ]),
  listVendorComplianceDocuments: vi.fn(async () => [
    {
      id: "doc-1",
      tenant_id: "tenant-1",
      project_id: "project-1",
      document_name: "Insurance Certificate",
      vendor_name: "Acme Materials",
      status: "current",
      expires_at: "2026-12-31T00:00:00Z",
      notes: "Annual renewal",
      created_by: "user-1",
      created_at: "2026-07-28T00:00:00Z",
      updated_at: "2026-07-28T00:00:00Z",
    },
  ]),
}));

vi.mock("@/lib/customerPortal", () => ({
  listCustomerPortalProjects: vi.fn(async () => [
    {
      project_id: "project-1",
      project_name: "North Yard",
      project_number: "P-100",
      status: "active",
      project_manager: "Jordan Lee",
      actual_revenue: "250000.00",
      ticket_count: 7,
      total_documents: 3,
      pending_review_documents: 1,
    },
  ]),
  getCustomerPortalBillingStatus: vi.fn(async () => ({
    project_id: "project-1",
    project_name: "North Yard",
    status: "active",
    actual_revenue: "250000.00",
    ticket_count: 7,
    total_tons: "10.00",
    total_cubic_yards: "8.00",
    revenue_shortfall: false,
  })),
  getCustomerPortalDocumentStatus: vi.fn(async () => ({
    project_id: "project-1",
    project_name: "North Yard",
    total_documents: 3,
    pending_review_documents: 1,
    latest_document_at: "2026-07-28T00:00:00Z",
  })),
}));

vi.mock("@/lib/estimator", () => ({
  listEstimatorTakeoffs: vi.fn(async () => [
    {
      id: "takeoff-1",
      tenant_id: "tenant-1",
      project_id: "project-1",
      takeoff_number: "TK-001",
      material_name: "Aggregate Base",
      quantity: "120.50",
      unit_of_measure: "cy",
      estimated_cost: "18750.00",
      status: "draft",
      notes: "Initial civil quantities",
      created_by: "user-1",
      created_at: "2026-07-28T00:00:00Z",
      updated_at: "2026-07-28T00:00:00Z",
    },
  ]),
  listEstimatorVersions: vi.fn(async () => [
    {
      id: "version-1",
      tenant_id: "tenant-1",
      project_id: "project-1",
      version_name: "Bid Rev A",
      revision_number: 1,
      estimated_revenue: "340000.00",
      estimated_cost: "278000.00",
      status: "submitted",
      notes: "First pricing pass",
      created_by: "user-1",
      created_at: "2026-07-28T00:00:00Z",
      updated_at: "2026-07-28T00:00:00Z",
    },
  ]),
  listEstimatorBidPipelineItems: vi.fn(async () => [
    {
      id: "bid-1",
      tenant_id: "tenant-1",
      project_id: "project-1",
      bid_number: "BID-9001",
      customer_name: "City Utilities",
      stage: "proposal",
      bid_amount: "340000.00",
      probability_percent: "62.50",
      due_date: "2026-08-15T00:00:00Z",
      status: "open",
      notes: "Pending clarifications",
      created_by: "user-1",
      created_at: "2026-07-28T00:00:00Z",
      updated_at: "2026-07-28T00:00:00Z",
    },
  ]),
  listEstimatorWinLossRecords: vi.fn(async () => [
    {
      id: "wl-1",
      tenant_id: "tenant-1",
      project_id: "project-1",
      bid_pipeline_item_id: "bid-1",
      outcome: "won",
      final_amount: "336500.00",
      decision_date: "2026-08-20T00:00:00Z",
      reason: "Strong schedule and safety plan",
      created_by: "user-1",
      created_at: "2026-07-28T00:00:00Z",
      updated_at: "2026-07-28T00:00:00Z",
    },
  ]),
  getEstimatorSummary: vi.fn(async () => ({
    takeoff_count: 1,
    version_count: 1,
    bid_pipeline_count: 1,
    wins: 1,
    losses: 0,
    pending: 0,
    win_rate_percent: "100.00",
  })),
}));

describe("Company owner module detail page", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockParams.role = "company_owner";
    mockParams.module = "executive-dashboard";
  });

  it("renders live executive dashboard signals and actions", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: false,
              revenue_shortfall: true,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Executive Dashboard")).toBeInTheDocument();
      expect(screen.getByText("Open Executive Dashboard")).toBeInTheDocument();
      expect(screen.getByText("Portfolio KPIs")).toBeInTheDocument();
      expect(screen.getByText("Approval backlog")).toBeInTheDocument();
      expect(screen.getByText("Executive signals")).toBeInTheDocument();
      expect(screen.getByText("Review project portfolio")).toBeInTheDocument();
      expect(screen.getByText("$250K")).toBeInTheDocument();
    });
  });

  it("renders live executive KPI board signals and actions", async () => {
    mockParams.role = "executive";
    mockParams.module = "kpi-board";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
              { id: "project-2", project_name: "South Yard", project_number: "P-200", status: "active" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: false,
              revenue_shortfall: true,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-2/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-2",
              project_name: "South Yard",
              status: "active",
              actual_revenue: 125000,
              actual_cost: 95000,
              gross_profit: 30000,
              profit_margin: 24,
              cost_overrun: false,
              revenue_shortfall: false,
              ticket_count: 3,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("KPI Board")).toBeInTheDocument();
      expect(screen.getByText("Open KPI Board")).toBeInTheDocument();
      expect(screen.getByText("Operational throughput")).toBeInTheDocument();
      expect(screen.getByText("Executive KPI summary")).toBeInTheDocument();
      expect(screen.getAllByText("Revenue tracked").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Gross margin")).toBeInTheDocument();
      expect(screen.getByText("$375K")).toBeInTheDocument();
    });
  });

  it("renders live project manager projects workspace signals and actions", async () => {
    mockParams.role = "project_manager";
    mockParams.module = "projects";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
              { id: "project-2", project_name: "South Yard", project_number: "P-200", status: "planning" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: false,
              revenue_shortfall: true,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-2/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-2",
              project_name: "South Yard",
              status: "planning",
              actual_revenue: 100000,
              actual_cost: 85000,
              gross_profit: 15000,
              profit_margin: 15,
              cost_overrun: false,
              revenue_shortfall: false,
              ticket_count: 1,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Projects")).toBeInTheDocument();
      expect(screen.getByText("Open Projects Workspace")).toBeInTheDocument();
      expect(screen.getByText("Project execution board")).toBeInTheDocument();
      expect(screen.getByText("North Yard")).toBeInTheDocument();
      expect(screen.getByText("South Yard")).toBeInTheDocument();
      expect(screen.getByText("Create new project")).toBeInTheDocument();
      expect(screen.getByText("$350K")).toBeInTheDocument();
    });
  });

  it("renders live dispatcher dispatch board signals and actions", async () => {
    mockParams.role = "dispatcher";
    mockParams.module = "dispatch-board";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: false,
              revenue_shortfall: false,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Dispatch Board")).toBeInTheDocument();
      expect(screen.getByText("Open Dispatch Board")).toBeInTheDocument();
      expect(screen.getByText("Dispatch board")).toBeInTheDocument();
      expect(screen.getByText("TCK-101")).toBeInTheDocument();
      expect(screen.getByText("Driver: Driver A")).toBeInTheDocument();
      expect(screen.getByText("Truck: Unit 1")).toBeInTheDocument();
    });
  });

  it("renders live accounting AP signals and actions", async () => {
    mockParams.role = "accounting";
    mockParams.module = "ap";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: true,
              revenue_shortfall: false,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("AP")).toBeInTheDocument();
      expect(screen.getByText("Open AP View")).toBeInTheDocument();
      expect(screen.getByText("Actual cost")).toBeInTheDocument();
      expect(screen.getByText("Fuel cost tracked")).toBeInTheDocument();
      expect(screen.getByText("Overrun projects")).toBeInTheDocument();
      expect(screen.getByText("$210K")).toBeInTheDocument();
    });
  });

  it("renders live fleet manager fleet signals and actions", async () => {
    mockParams.role = "fleet_manager";
    mockParams.module = "fleet";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: false,
              revenue_shortfall: false,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/equipment")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "eq-1", name: "Excavator 320" },
              { id: "eq-2", name: "Dozer D6" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/trucks")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "trk-1", unit_number: "TRK-101" },
              { id: "trk-2", unit_number: "TRK-102" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Fleet")).toBeInTheDocument();
      expect(screen.getByText("Open Fleet Overview")).toBeInTheDocument();
      expect(screen.getByText("Equipment assets")).toBeInTheDocument();
      expect(screen.getByText("Truck units")).toBeInTheDocument();
      expect(screen.getByText("Excavator 320")).toBeInTheDocument();
      expect(screen.getByText("TRK-101")).toBeInTheDocument();
    });
  });

  it("renders live safety manager incident signals and actions", async () => {
    mockParams.role = "safety_manager";
    mockParams.module = "incidents";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: false,
              revenue_shortfall: true,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/equipment")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/trucks")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Incidents")).toBeInTheDocument();
      expect(screen.getByText("Open Incident Queue")).toBeInTheDocument();
      expect(screen.getByText("Incident backlog")).toBeInTheDocument();
      expect(screen.getByText("Incident watchlist")).toBeInTheDocument();
      expect(screen.getByText("North Yard")).toBeInTheDocument();
      expect(screen.getByText("At-risk projects")).toBeInTheDocument();
    });
  });

  it("renders live administrator user admin signals and actions", async () => {
    mockParams.role = "administrator";
    mockParams.module = "user-admin";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/equipment") || url.endsWith("/api/trucks")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/tenant-users")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                user_id: "u-1",
                email: "ops@example.com",
                display_name: "Ops Admin",
                title: "Administrator",
                role_name: "administrator",
                status: "active",
              },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/tenant-users/permissions/catalog")) {
        return Promise.resolve(
          new Response(JSON.stringify(["tickets_read", "tickets_write", "projects_read"]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/admin/overview")) {
        return Promise.resolve(
          new Response(JSON.stringify({ tenants: 2, users: 5, projects: 8 }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/admin/users")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ id: "admin-1", email: "admin@example.com", display_name: "Admin", title: "Platform Admin", platform_role: "platform_super_admin", is_active: true }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/admin/service-insights")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              tickets: 10,
              intake_items: 6,
              intake_needs_review: 2,
              extractions_pending_review: 3,
              extractions_review_submitted: 1,
              unresolved_extraction_issues: 1,
              integration_events_pending: 4,
              integration_events_failed: 1,
              opportunities: ["Reduce extraction review latency"],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("User Admin")).toBeInTheDocument();
      expect(screen.getByText("Open User Admin")).toBeInTheDocument();
      expect(screen.getByText("Tenant users")).toBeInTheDocument();
      expect(screen.getByText("Permission catalog")).toBeInTheDocument();
      expect(screen.getByText("User access queue")).toBeInTheDocument();
      expect(screen.getByText("Platform users")).toBeInTheDocument();
    });
  });

  it("renders live estimator takeoff signals and actions", async () => {
    mockParams.role = "estimator";
    mockParams.module = "takeoff";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: false,
              revenue_shortfall: false,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/equipment") || url.endsWith("/api/trucks") || url.endsWith("/api/tenant-users") || url.endsWith("/api/admin/users")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/tenant-users/permissions/catalog")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/overview") || url.endsWith("/api/admin/service-insights")) {
        return Promise.resolve(new Response(JSON.stringify(null), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Takeoff")).toBeInTheDocument();
      expect(screen.getByText("Open Takeoff Workspace")).toBeInTheDocument();
      expect(screen.getByText("Takeoff inputs")).toBeInTheDocument();
      expect(screen.getByText("Takeoffs")).toBeInTheDocument();
      expect(screen.getByText("Bid pipeline")).toBeInTheDocument();
      expect(screen.getByText("TK-001 • Aggregate Base • 120.50 cy")).toBeInTheDocument();
    });
  });

  it("renders live customer project snapshot signals and actions", async () => {
    mockParams.role = "customer";
    mockParams.module = "project-snapshot";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: false,
              revenue_shortfall: false,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/equipment") || url.endsWith("/api/trucks") || url.endsWith("/api/tenant-users") || url.endsWith("/api/admin/users")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/tenant-users/permissions/catalog")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/overview") || url.endsWith("/api/admin/service-insights")) {
        return Promise.resolve(new Response(JSON.stringify(null), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Project Snapshot")).toBeInTheDocument();
      expect(screen.getByText("Open Project Snapshot")).toBeInTheDocument();
      expect(screen.getByText("Customer project snapshot")).toBeInTheDocument();
      expect(screen.getByText("Tracked projects")).toBeInTheDocument();
      expect(screen.getByText("Project revenue")).toBeInTheDocument();
      expect(screen.getByText("North Yard")).toBeInTheDocument();
      expect(screen.getByText("Tickets: 7")).toBeInTheDocument();
    });
  });

  it("renders live vendor purchase order signals and actions", async () => {
    mockParams.role = "vendor";
    mockParams.module = "purchase-orders";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: false,
              revenue_shortfall: false,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/equipment") || url.endsWith("/api/trucks") || url.endsWith("/api/tenant-users") || url.endsWith("/api/admin/users")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/tenant-users/permissions/catalog")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/overview") || url.endsWith("/api/admin/service-insights")) {
        return Promise.resolve(new Response(JSON.stringify(null), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Purchase Orders")).toBeInTheDocument();
      expect(screen.getByText("Open Purchase Orders")).toBeInTheDocument();
      expect(screen.getByText("Purchase order context")).toBeInTheDocument();
      expect(screen.getByText("Purchase orders")).toBeInTheDocument();
      expect(screen.getByText("Submitted invoices")).toBeInTheDocument();
      expect(screen.getByText("PO-1001")).toBeInTheDocument();
    });
  });

  it("renders live payroll timecard signals and actions", async () => {
    mockParams.role = "payroll";
    mockParams.module = "timecards";

    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "project-1", project_name: "North Yard", project_number: "P-100", status: "active" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/projects/project-1/profitability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              project_id: "project-1",
              project_name: "North Yard",
              status: "active",
              actual_revenue: 250000,
              actual_cost: 210000,
              gross_profit: 40000,
              profit_margin: 16,
              cost_overrun: false,
              revenue_shortfall: false,
              ticket_count: 7,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/employees")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              { id: "emp-1", name: "Avery Chen" },
              { id: "emp-2", name: "Jordan Lee" },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/payroll/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              employee_count: 2,
              timecard_count: 1,
              payroll_run_count: 1,
              total_regular_hours: "8.00",
              total_overtime_hours: "2.00",
              total_double_time_hours: "0.00",
              by_project: [
                {
                  project_id: "project-1",
                  timecard_count: 1,
                  regular_hours: "8.00",
                  overtime_hours: "2.00",
                  double_time_hours: "0.00",
                },
              ],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/payroll/timecards")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                id: "tc-1",
                tenant_id: "tenant-1",
                employee_id: "emp-1",
                project_id: "project-1",
                work_date: "2026-07-28T00:00:00Z",
                regular_hours: "8.00",
                overtime_hours: "2.00",
                double_time_hours: "0.00",
                cost_code: "EARTH-100",
                work_description: "Haul and grading support",
                status: "submitted",
                created_by: "user-1",
                created_at: "2026-07-28T00:00:00Z",
                updated_at: "2026-07-28T00:00:00Z",
              },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/payroll/runs")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                id: "run-1",
                tenant_id: "tenant-1",
                run_number: "PR-2026-001",
                period_start: "2026-07-01T00:00:00Z",
                period_end: "2026-07-31T23:59:59Z",
                status: "draft",
                notes: "July payroll run",
                employee_count: 2,
                total_regular_hours: "8.00",
                total_overtime_hours: "2.00",
                total_double_time_hours: "0.00",
                created_by: "user-1",
                created_at: "2026-07-28T00:00:00Z",
                updated_at: "2026-07-28T00:00:00Z",
              },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/equipment") || url.endsWith("/api/trucks") || url.endsWith("/api/tenant-users") || url.endsWith("/api/admin/users")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/tenant-users/permissions/catalog")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/overview") || url.endsWith("/api/admin/service-insights")) {
        return Promise.resolve(new Response(JSON.stringify(null), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getAllByText("Timecards").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Open Timecards View")).toBeInTheDocument();
      expect(screen.getByText("Timecard roster")).toBeInTheDocument();
      expect(screen.getByText("Employees")).toBeInTheDocument();
      expect(screen.getByText(/Haul and grading support/)).toBeInTheDocument();
      expect(screen.getByText(/8.00h regular \/ 2.00h OT/)).toBeInTheDocument();
    });
  });

  it("shows module access denied when role does not match module route", async () => {
    mockParams.role = "payroll";
    mockParams.module = "timecards";

    vi.spyOn(roleAccess, "getCurrentRoleAccess").mockResolvedValue({
      roleKey: "dispatcher",
      isSuperAdmin: false,
    });

    vi.spyOn(global, "fetch").mockResolvedValue(new Response("not found", { status: 404 }));

    render(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Module access denied")).toBeInTheDocument();
      expect(screen.getByText("Back to Modules")).toBeInTheDocument();
    });
  });
});
