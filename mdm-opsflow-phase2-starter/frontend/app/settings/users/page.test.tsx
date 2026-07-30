import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import UserSettingsPage from "./page";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));

describe("User settings assignment flow", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("opsflow_locale", "en");
    window.localStorage.setItem("opsflow_access_token", "token");
    window.localStorage.setItem("opsflow_refresh_token", "refresh-token");
    window.localStorage.setItem("opsflow_tenant_id", "tenant-1");
    vi.restoreAllMocks();
  });

  it("assigns a user with selected role and refreshes tenant members", async () => {
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [{ tenant_id: "tenant-1", tenant_name: "Acme Civil" }],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(["owner", "executive", "project_manager", "estimator"]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            user_id: "u1",
            email: "member@acme.com",
            display_name: "Member User",
            title: "",
            role_name: "project_manager",
            status: "active",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              user_id: "u1",
              email: "member@acme.com",
              display_name: "Member User",
              title: "",
              role_name: "project_manager",
              status: "active",
            },
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    const user = userEvent.setup();
    render(<UserSettingsPage />);

    await user.type(screen.getByPlaceholderText("User email"), "member@acme.com");
    await user.type(screen.getByPlaceholderText("Display name"), "Member User");
    await user.type(screen.getByPlaceholderText("Job title"), "Project Engineer");
    await user.selectOptions(screen.getByLabelText("Role"), "project_manager");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getByText("User assigned to company. Temporary password: ChangeMe123!")).toBeInTheDocument();
      expect(screen.getByText("Member User (member@acme.com)")).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(6);
    const assignCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");

    expect(assignCall?.[1]).toMatchObject({
      method: "POST",
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "X-Tenant-ID": "tenant-1",
      }),
    });
    expect(String((assignCall?.[1] as RequestInit | undefined)?.body)).toContain('"role_name":"project_manager"');
    expect(String((assignCall?.[1] as RequestInit | undefined)?.body)).toContain('"display_name":"Member User"');
    expect(String((assignCall?.[1] as RequestInit | undefined)?.body)).toContain('"temporary_password":"ChangeMe123!"');
  });

  it("shows localized error when backend returns user not found", async () => {
    vi.spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [{ tenant_id: "tenant-1", tenant_name: "Acme Civil" }],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(["owner", "executive", "project_manager", "estimator"]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "User not found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        })
      );

    const user = userEvent.setup();
    render(<UserSettingsPage />);

    await user.type(screen.getByPlaceholderText("User email"), "missing@acme.com");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getByText("User not found.")).toBeInTheDocument();
    });
  });

  it("lets a super-admin pick a tenant before loading members", async () => {
    window.localStorage.removeItem("opsflow_tenant_id");

    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [
              { tenant_id: "tenant-a", tenant_name: "Acme Civil" },
              { tenant_id: "tenant-b", tenant_name: "North Ridge" },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(["owner", "executive", "project_manager", "estimator"]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(["owner", "executive", "project_manager", "estimator"]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

    const user = userEvent.setup();
    render(<UserSettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("You are managing users and function access for the selected tenant.")).toBeInTheDocument();
    });

    expect(fetchMock.mock.calls.some(([, init]) => {
      return init?.headers instanceof Headers
        ? init.headers.get("X-Tenant-ID") === "tenant-a"
        : (init?.headers as Record<string, string> | undefined)?.["X-Tenant-ID"] === "tenant-a";
    })).toBe(true);

    await user.selectOptions(screen.getByLabelText("Tenant"), "tenant-b");

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([, init]) => {
          return init?.headers instanceof Headers
            ? init.headers.get("X-Tenant-ID") === "tenant-b"
            : (init?.headers as Record<string, string> | undefined)?.["X-Tenant-ID"] === "tenant-b";
        })
      ).toBe(true);
    });
  });

  it("refreshes session and retries when saving function access returns 401", async () => {
    let putAttempts = 0;
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method || "GET";

      if (url.endsWith("/api/admin/tenant-service-summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ items: [{ tenant_id: "tenant-1", tenant_name: "Acme Civil" }] }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/tenant-users") && method === "GET") {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                user_id: "u1",
                email: "member@acme.com",
                display_name: "Member User",
                title: "",
                role_name: "project_manager",
                status: "active",
              },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/tenant-users/permissions/catalog")) {
        return Promise.resolve(
          new Response(JSON.stringify(["project_read", "project_write"]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/tenant-users/roles/catalog")) {
        return Promise.resolve(
          new Response(JSON.stringify(["owner", "executive", "project_manager", "estimator"]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/tenant-users/u1/permissions") && method === "GET") {
        const effectivePermissions = putAttempts > 0 ? ["project_read", "project_write"] : ["project_read"];
        const overrides = putAttempts > 0 ? [{ permission: "project_write", enabled: true }] : [];
        return Promise.resolve(
          new Response(
            JSON.stringify({
              user_id: "u1",
              email: "member@acme.com",
              role_name: "project_manager",
              base_permissions: ["project_read"],
              effective_permissions: effectivePermissions,
              overrides,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/tenant-users/u1/permissions") && method === "PUT") {
        putAttempts += 1;
        if (putAttempts === 1) {
          return Promise.resolve(
            new Response(JSON.stringify({ detail: "Invalid authentication" }), {
              status: 401,
              headers: { "Content-Type": "application/json" },
            })
          );
        }
        return Promise.resolve(
          new Response(
            JSON.stringify({
              user_id: "u1",
              email: "member@acme.com",
              role_name: "project_manager",
              base_permissions: ["project_read"],
              effective_permissions: ["project_read", "project_write"],
              overrides: [{ permission: "project_write", enabled: true }],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/auth/refresh") && method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              access_token: "new-access-token",
              refresh_token: "new-refresh-token",
              token_type: "bearer",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    const user = userEvent.setup();
    render(<UserSettingsPage />);

    await user.click(await screen.findByRole("button", { name: "Manage Functions" }));
    const checkboxes = await screen.findAllByRole("checkbox");
    await user.click(checkboxes[1]);
    await user.click(screen.getByRole("button", { name: "Save Function Access" }));

    await waitFor(() => {
      expect(screen.getByText("Function toggles updated.")).toBeInTheDocument();
    });

    const refreshCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/api/auth/refresh"));
    expect(refreshCall).toBeTruthy();
    expect(window.localStorage.getItem("opsflow_access_token")).toBe("new-access-token");
    expect(window.localStorage.getItem("opsflow_refresh_token")).toBe("new-refresh-token");
  });
});
