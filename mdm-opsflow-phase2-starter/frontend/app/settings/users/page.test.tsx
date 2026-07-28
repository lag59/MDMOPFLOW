import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import UserSettingsPage from "./page";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: unknown }) => <a href={href}>{children}</a>,
}));

describe("User settings assignment flow", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("opsflow_locale", "en");
    window.localStorage.setItem("opsflow_access_token", "token");
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
    await user.selectOptions(screen.getByLabelText("Role"), "project_manager");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getByText("User assigned to company.")).toBeInTheDocument();
      expect(screen.getByText("Member User (member@acme.com)")).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(5);
    const assignCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");

    expect(assignCall?.[1]).toMatchObject({
      method: "POST",
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "X-Tenant-ID": "tenant-1",
      }),
    });
    expect(String((assignCall?.[1] as RequestInit | undefined)?.body)).toContain('"role_name":"project_manager"');
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
});
