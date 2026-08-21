import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AppShell from "./AppShell";

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

vi.mock("@/lib/auth", () => ({
  clearSession: vi.fn(),
  getAccessToken: () => "access-token",
  getTenantId: () => "tenant-1",
  refreshSession: vi.fn(async () => true),
  setTenantId: vi.fn(),
}));

vi.mock("@/lib/i18n", () => ({
  getApiBaseUrl: () => "https://api.example.test",
  getLocale: () => "en",
  t: (_locale: string, key: string) => key,
}));

describe("AppShell AI Capture", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("routes one note through the shared AI workflow endpoint", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.endsWith("/api/auth/me")) {
        return Promise.resolve(new Response(JSON.stringify({ tenant_id: "tenant-1" }), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/ai/workflow/route")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              routed: true,
              processing_outcome: "created",
              created_count: 2,
              recognized_existing_count: 0,
              useful_details_count: 2,
              customer_created: true,
              material_created: true,
              report_created: false,
              customer_name: "Summit Peak Builders",
              material_name: "57 stone",
              report_number: null,
              message: "Captured once and routed to the right places.",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } }));
    });

    const user = userEvent.setup();
    render(<AppShell titleKey="dashboard.title"><div>Dashboard content</div></AppShell>);

    await user.click(screen.getByRole("button", { name: "AI Capture" }));
    await user.type(screen.getByPlaceholderText(/company: summit peak builders/i), "Company: Summit Peak Builders\nMaterial: 57 stone");
    await user.click(screen.getByRole("button", { name: "Route with AI" }));

    await waitFor(() => {
      expect(screen.getByText("Captured once and routed to the right places.")).toBeInTheDocument();
      expect(screen.getByText("Outcome: created")).toBeInTheDocument();
      expect(screen.getByText("Customer: Summit Peak Builders (created)")).toBeInTheDocument();
      expect(screen.getByText("Material: 57 stone (created)")).toBeInTheDocument();
    });

    const routeCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/api/ai/workflow/route"));
    expect(routeCall).toBeTruthy();
    expect(routeCall?.[1]?.headers).toMatchObject({
      Authorization: "Bearer access-token",
      "X-Tenant-ID": "tenant-1",
      "Content-Type": "application/json",
    });
    expect(JSON.parse(String(routeCall?.[1]?.body))).toEqual({ note: "Company: Summit Peak Builders\nMaterial: 57 stone" });
  });
});