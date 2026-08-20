import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import PlatformAdminPage from "./page";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));

describe("Platform admin tenant creation", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("opsflow_access_token", "token");
    window.localStorage.setItem("opsflow_refresh_token", "refresh-token");
    window.localStorage.setItem("opsflow_locale", "en");
    vi.restoreAllMocks();
  });

  it("refreshes an expired access token before denying super-admin access", async () => {
    window.localStorage.setItem("opsflow_tenant_id", "tenant-1");
    let meCalls = 0;
    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.endsWith("/api/auth/me")) {
        meCalls += 1;
        if (meCalls === 1) {
          return Promise.resolve(new Response(JSON.stringify({ detail: "Invalid authentication" }), { status: 401, headers: { "Content-Type": "application/json" } }));
        }
        return Promise.resolve(new Response(JSON.stringify({ platform_role: "PLATFORM_SUPER_ADMIN" }), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/auth/refresh")) {
        return Promise.resolve(new Response(JSON.stringify({ access_token: "fresh-token", refresh_token: "fresh-refresh" }), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/overview")) {
        return Promise.resolve(new Response(JSON.stringify({ tenants: 0, users: 0, projects: 0 }), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/service-insights")) {
        return Promise.resolve(new Response(JSON.stringify({ tickets: 0, intake_items: 0, intake_needs_review: 0, extractions_pending_review: 0, extractions_review_submitted: 0, unresolved_extraction_issues: 0, integration_events_pending: 0, integration_events_failed: 0, opportunities: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/users") || url.endsWith("/api/admin/roles/catalog")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/tenant-service-summary")) {
        return Promise.resolve(new Response(JSON.stringify({ items: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      return Promise.resolve(new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } }));
    });

    render(<PlatformAdminPage />);

    expect(await screen.findByRole("heading", { name: "Create Tenant" })).toBeInTheDocument();
    expect(window.localStorage.getItem("opsflow_access_token")).toBe("fresh-token");
  });

  it("creates and saves a tenant with owner access", async () => {
    let createdTenant: { tenant_id: string; tenant_name: string } | null = null;
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method || "GET";

      if (url.endsWith("/api/auth/me")) {
        return Promise.resolve(
          new Response(JSON.stringify({ platform_role: "platform_super_admin" }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/admin/overview")) {
        return Promise.resolve(new Response(JSON.stringify({ tenants: createdTenant ? 1 : 0, users: 1, projects: 0 }), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/service-insights")) {
        return Promise.resolve(new Response(JSON.stringify({ tickets: 0, intake_items: 0, intake_needs_review: 0, extractions_pending_review: 0, extractions_review_submitted: 0, unresolved_extraction_issues: 0, integration_events_pending: 0, integration_events_failed: 0, opportunities: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/users")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/tenant-service-summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: createdTenant ? [{ tenant_id: createdTenant.tenant_id, tenant_name: createdTenant.tenant_name }] : [],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/admin/roles/catalog")) {
        return Promise.resolve(new Response(JSON.stringify(["owner", "project_manager"]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/admin/tenants") && method === "POST") {
        createdTenant = { tenant_id: "tenant-1", tenant_name: "North Ridge Civil" };
        return Promise.resolve(
          new Response(JSON.stringify({ ...createdTenant, tenant_type: "production", is_test: false, created_by_automation: false }), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      return Promise.resolve(new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } }));
    });

    const user = userEvent.setup();
    render(<PlatformAdminPage />);

    await user.type(await screen.findByLabelText("Tenant name"), "North Ridge Civil");
    await user.clear(screen.getByLabelText("Company type"));
    await user.type(screen.getByLabelText("Company type"), "Heavy Civil");
    await user.type(screen.getByLabelText("Owner email"), "owner@northridge.com");
    await user.type(screen.getByLabelText("Owner name"), "North Ridge Owner");
    await user.clear(screen.getByLabelText("Owner temporary password"));
    await user.type(screen.getByLabelText("Owner temporary password"), "OwnerPass123!");
    await user.click(screen.getByRole("button", { name: "Create Tenant" }));

    await waitFor(() => {
      expect(screen.getByText('Tenant "North Ridge Civil" saved with owner access.')).toBeInTheDocument();
    });

    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/api/admin/tenants"))).toBe(true);
    expect(screen.getByLabelText("Saved tenant")).toHaveValue("tenant-1");
  });
});
