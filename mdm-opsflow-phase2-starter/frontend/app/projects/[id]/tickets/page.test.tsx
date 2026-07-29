import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import ProjectTicketsPage from "./page";

vi.mock("@/components/AppShell", () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "project-1" }),
}));

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Project tickets page", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("opsflow_locale", "en");
    window.localStorage.setItem("opsflow_access_token", "token");
    window.localStorage.setItem("opsflow_tenant_id", "tenant-1");
    vi.restoreAllMocks();
  });

  it("falls back to /api/tickets and filters by project when project-ticket endpoint is unavailable", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects/project-1")) {
        return Promise.resolve(jsonResponse({ id: "project-1", project_name: "Northbound" }));
      }

      if (url.endsWith("/api/projects/project-1/tickets")) {
        return Promise.resolve(new Response("not found", { status: 404 }));
      }

      if (url.endsWith("/api/tickets")) {
        return Promise.resolve(
          jsonResponse([
            {
              id: "tk-1",
              ticket_number: "TCK-100",
              truck: "Unit 1",
              driver: "Alex",
              material: "Aggregate",
              origin: "Pit A",
              destination: "Site B",
              project_id: "project-1",
              status: "draft",
              revenue: 1000,
              fuel_cost: 100,
              tons: 10,
              volume_yards: 8,
              created_at: "2026-07-28T00:00:00Z",
            },
            {
              id: "tk-2",
              ticket_number: "TCK-101",
              truck: "Unit 2",
              driver: "Sam",
              material: "Sand",
              origin: "Yard",
              destination: "Site C",
              project_id: "project-2",
              status: "approved",
              revenue: 1200,
              fuel_cost: 140,
              tons: 12,
              volume_yards: 9,
              created_at: "2026-07-28T00:00:00Z",
            },
          ])
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ProjectTicketsPage />);

    await waitFor(() => {
      expect(screen.getByText("Northbound")).toBeInTheDocument();
      expect(screen.getByText("TCK-100")).toBeInTheDocument();
      expect(screen.queryByText("TCK-101")).not.toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/projects/project-1/tickets"),
      expect.any(Object)
    );
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/tickets"), expect.any(Object));
  });

  it("surfaces primary and fallback status codes when ticket fetch fails", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/projects/project-1")) {
        return Promise.resolve(jsonResponse({ id: "project-1", project_name: "Northbound" }));
      }

      if (url.endsWith("/api/projects/project-1/tickets")) {
        return Promise.resolve(new Response("forbidden", { status: 403 }));
      }

      if (url.endsWith("/api/tickets")) {
        return Promise.resolve(new Response("forbidden", { status: 403 }));
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    render(<ProjectTicketsPage />);

    await waitFor(() => {
      expect(screen.getByText("Error: Failed to fetch tickets (403 / fallback 403)")).toBeInTheDocument();
    });
  });
});
