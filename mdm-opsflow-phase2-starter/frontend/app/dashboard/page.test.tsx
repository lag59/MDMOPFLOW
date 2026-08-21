import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "./page";

const roleState: { roleKey: string; roleKeys: string[]; isSuperAdmin: boolean } = {
  roleKey: "project_manager",
  roleKeys: ["project_manager"],
  isSuperAdmin: false,
};

vi.mock("@/components/AppShell", () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/lib/auth", () => ({
  getAccessToken: () => "token-123",
  getTenantId: () => "tenant-123",
}));

vi.mock("@/lib/i18n", () => ({
  getApiBaseUrl: () => "http://localhost:8000",
}));

vi.mock("@/lib/roleAccess", () => ({
  getCurrentRoleAccess: vi.fn(async () => roleState),
}));

describe("Dashboard role-aware experience", () => {
  beforeEach(() => {
    roleState.roleKey = "project_manager";
    roleState.roleKeys = ["project_manager"];
    roleState.isSuperAdmin = false;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.endsWith("/api/projects")) {
          return new Response(
            JSON.stringify([
              { id: "p-1", project_name: "Alpha", status: "active", contract_amount: "100000" },
              { id: "p-2", project_name: "Bravo", status: "planning", contract_amount: "25000" },
            ]),
            { status: 200 }
          );
        }

        if (url.endsWith("/api/tickets")) {
          return new Response(
            JSON.stringify([
              { id: "t-1", ticket_number: "TK-1", material: "Rock", status: "open", created_at: "2026-08-01T00:00:00Z" },
              { id: "t-2", ticket_number: "TK-2", material: "Sand", status: "closed", created_at: "2026-08-02T00:00:00Z" },
            ]),
            { status: 200 }
          );
        }

        if (url.endsWith("/api/estimates")) {
          return new Response(
            JSON.stringify([
              { id: "e-1", estimate_name: "Estimate A", status: "Draft Estimate", bid_due_date: "2026-08-15" },
              { id: "e-2", estimate_name: "Estimate B", status: "Awarded", bid_due_date: null },
            ]),
            { status: 200 }
          );
        }

        if (url.endsWith("/api/intake/items")) {
          return new Response(JSON.stringify([{ id: "i-1", status: "pending_review" }, { id: "i-2", status: "uploaded" }]), {
            status: 200,
          });
        }

        if (url.endsWith("/api/dashboard/role-experience")) {
          return new Response(
            JSON.stringify({
              role_key: roleState.roleKey,
              role_label: roleState.roleKey === "estimator" ? "Estimator" : "Dispatcher",
              kpi_order: roleState.roleKey === "estimator"
                ? ["estimates", "draft_estimates", "awarded_estimates", "intake_pending_review"]
                : ["open_tickets", "tickets", "active_projects", "intake_pending_review"],
              modules: roleState.roleKey === "estimator"
                ? [
                    { label: "Takeoff", href: "/modules/estimator/takeoff" },
                    { label: "Bid Pipeline", href: "/modules/estimator/bid-pipeline" },
                  ]
                : [
                    { label: "Dispatch Board", href: "/modules/dispatcher/dispatch-board" },
                    { label: "Route Planning", href: "/modules/dispatcher/route-planning" },
                  ],
              quick_actions: roleState.roleKey === "estimator"
                ? [
                    { label: "Open estimator workspace", href: "/estimator" },
                    { label: "Review ticket inputs", href: "/tickets" },
                  ]
                : [
                    { label: "Assign tickets", href: "/ticket-manager" },
                    { label: "Review active tickets", href: "/tickets" },
                  ],
              alerts: ["1 intake items require review."],
            }),
            { status: 200 }
          );
        }

        return new Response(JSON.stringify([]), { status: 200 });
      })
    );
  });

  it("renders estimator-focused modules and actions", async () => {
    roleState.roleKey = "estimator";
    roleState.roleKeys = ["estimator"];

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Estimator Command Center")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Role Modules" })).toBeInTheDocument();
      expect(screen.getByText("Bid Pipeline")).toBeInTheDocument();
      expect(screen.getByText("Open estimator workspace")).toBeInTheDocument();
      expect(screen.getByText("Draft Estimates")).toBeInTheDocument();
    });
  });

  it("renders dispatcher-focused modules and ticket KPIs", async () => {
    roleState.roleKey = "dispatcher";
    roleState.roleKeys = ["dispatcher"];

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Dispatcher Operations")).toBeInTheDocument();
      expect(screen.getByText("Dispatch Board")).toBeInTheDocument();
      expect(screen.getByText("Assign tickets")).toBeInTheDocument();
      expect(screen.getAllByText("Open Tickets").length).toBeGreaterThan(0);
    });
  });

  it("keeps rendering when a backend endpoint is unauthorized", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/estimates")) {
          return new Response(JSON.stringify({ detail: "Insufficient permissions" }), { status: 403 });
        }
        if (url.endsWith("/api/projects")) {
          return new Response(JSON.stringify([{ id: "p-1", project_name: "Alpha", status: "active", contract_amount: null }]), {
            status: 200,
          });
        }
        if (url.endsWith("/api/tickets")) {
          return new Response(JSON.stringify([]), { status: 200 });
        }
        if (url.endsWith("/api/intake/items")) {
          return new Response(JSON.stringify([]), { status: 200 });
        }
        if (url.endsWith("/api/dashboard/role-experience")) {
          return new Response(JSON.stringify({ detail: "Insufficient permissions" }), { status: 403 });
        }
        return new Response(JSON.stringify([]), { status: 200 });
      })
    );

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Project Execution Dashboard")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Project Pipeline" })).toBeInTheDocument();
    });
  });
});
