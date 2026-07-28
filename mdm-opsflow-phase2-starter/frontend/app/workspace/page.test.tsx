import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import WorkspacePage from "./page";

vi.mock("@/components/AppShell", () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe("Workspace resource explorer", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("opsflow_locale", "en");
    window.localStorage.setItem("opsflow_access_token", "token");
    window.localStorage.setItem("opsflow_tenant_id", "tenant-1");
    vi.restoreAllMocks();
  });

  it("shows preview records and creates a new resource from the workspace form", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.endsWith("/api/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              platform_role: "platform_super_admin",
              memberships: [{ role_name: "owner" }],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ id: "p1", project_name: "Northwind", project_number: "P-100" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/daily-field-reports")) {
        if (init?.method === "POST") {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                id: "dr-1",
                report_number: "R-001",
                project_id: "p1",
                report_date: "2026-07-28",
                reporting_supervisor: "Avery",
                status: "draft",
              }),
              { status: 201, headers: { "Content-Type": "application/json" } }
            )
          );
        }

        return Promise.resolve(
          new Response(JSON.stringify([]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/customers")) {
        if (init?.method === "POST") {
          return Promise.resolve(
            new Response(JSON.stringify({ id: "c2", name: "Northwind Builders" }), {
              status: 201,
              headers: { "Content-Type": "application/json" },
            })
          );
        }

        if (init?.method === "PATCH") {
          return Promise.resolve(
            new Response(JSON.stringify({ id: "c2", name: "Northwind Builders Updated" }), {
              status: 200,
              headers: { "Content-Type": "application/json" },
            })
          );
        }

        if (init?.method === "DELETE") {
          return Promise.resolve(new Response(null, { status: 204 }));
        }

        return Promise.resolve(
          new Response(JSON.stringify([{ id: "c1", name: "Acme Civil" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/employees")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ id: "e1", name: "Avery Chen" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/equipment")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ id: "eq1", unit_number: "EQ-100" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/trucks")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ id: "t1", unit_number: "TRK-01" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/materials")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ id: "m1", name: "Concrete Mix" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
    });

    const user = userEvent.setup();
    render(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText("Platform resources")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /customers/i }));

    expect(await screen.findByText("Acme Civil")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Customers name"), "Northwind Builders");
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(screen.getByText("Customers created.")).toBeInTheDocument();
    });

    await user.click(screen.getAllByRole("button", { name: "Edit" })[0]);
    await user.clear(screen.getByLabelText("Customers edit"));
    await user.type(screen.getByLabelText("Customers edit"), "Northwind Builders Updated");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getByText("Customers updated.")).toBeInTheDocument();
    });

    await user.click(screen.getAllByRole("button", { name: "Delete" })[0]);

    await waitFor(() => {
      expect(screen.getByText("Customers deleted.")).toBeInTheDocument();
    });
  });

  it("creates a daily field report from the workspace form", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.endsWith("/api/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              platform_role: "platform_super_admin",
              memberships: [{ role_name: "owner" }],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ id: "p1", project_name: "Northwind", project_number: "P-100" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/daily-field-reports")) {
        if (init?.method === "POST") {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                id: "dr-1",
                report_number: "R-001",
                project_id: "p1",
                report_date: "2026-07-28",
                reporting_supervisor: "Avery",
                status: "draft",
              }),
              { status: 201, headers: { "Content-Type": "application/json" } }
            )
          );
        }

        return Promise.resolve(
          new Response(JSON.stringify([{ id: "dr-1", report_number: "R-001", reporting_supervisor: "Avery", status: "draft" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
    });

    const user = userEvent.setup();
    render(<WorkspacePage />);

    const reportForm = await screen.findByRole("button", { name: /create report/i });
    await user.type(screen.getByLabelText("Company"), "Northwind Civil");
    await user.type(screen.getByLabelText("Supervisor"), "Avery Chen");
    await user.type(screen.getByLabelText("Work performed"), "Completed excavation");
    await user.type(screen.getByLabelText("Work planned for tomorrow"), "Pour foundation");
    await user.click(reportForm);

    expect(await screen.findByText("Daily report created.")).toBeInTheDocument();
    expect(await screen.findByText(/R-001/i)).toBeInTheDocument();
  });

  it("routes a single AI prompt into the report, customer, and material flows", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.endsWith("/api/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              platform_role: "platform_super_admin",
              memberships: [{ role_name: "owner" }],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ id: "p1", project_name: "Northwind", project_number: "P-100" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/customers") && init?.method === "POST") {
        return Promise.resolve(
          new Response(JSON.stringify({ id: "c1", name: "Northwind Civil" }), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/materials") && init?.method === "POST") {
        return Promise.resolve(
          new Response(JSON.stringify({ id: "m1", name: "Concrete Mix" }), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/daily-field-reports") && init?.method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "dr-2",
              report_number: "R-002",
              project_id: "p1",
              report_date: "2026-07-28",
              reporting_supervisor: "Avery Chen",
              status: "draft",
            }),
            { status: 201, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/daily-field-reports")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ id: "dr-2", report_number: "R-002", reporting_supervisor: "Avery Chen", status: "draft" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
    });

    const user = userEvent.setup();
    render(<WorkspacePage />);

    const assistantInput = await screen.findByLabelText(/ai routing assistant/i);
    await user.type(assistantInput, "Company: Northwind Civil\nSupervisor: Avery Chen\nMaterial: Concrete Mix\nWork: Completed excavation\nPlan: Pour foundation");
    await user.click(screen.getByRole("button", { name: /route once/i }));

    await waitFor(() => {
      expect(screen.getByText(/captured once and routed/i)).toBeInTheDocument();
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/api/ai/workflow/route"),
      expect.objectContaining({ method: "POST" })
    );
  });
});
