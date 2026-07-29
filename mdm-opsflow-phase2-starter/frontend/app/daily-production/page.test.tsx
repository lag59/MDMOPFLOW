import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DailyProductionPage from "./page";

vi.mock("@/components/AppShell", () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/lib/auth", () => ({
  getAccessToken: () => "token",
  getTenantId: () => "tenant-1",
}));

vi.mock("@/lib/i18n", () => ({
  getApiBaseUrl: () => "http://localhost",
}));

const createTicketMock = vi.fn();
const listTicketsMock = vi.fn();

vi.mock("@/lib/tickets", () => ({
  createTicket: (...args: unknown[]) => createTicketMock(...args),
  listTickets: (...args: unknown[]) => listTicketsMock(...args),
}));

describe("Daily production report", () => {
  beforeEach(() => {
    createTicketMock.mockReset();
    createTicketMock.mockResolvedValue({ id: "t1", ticket_number: "T-1" });
    listTicketsMock.mockReset();
    listTicketsMock.mockResolvedValue([]);
    vi.restoreAllMocks();
  });

  it("includes visitors, delays, photos, production, and safety sections in the saved report", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

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
              JSON.stringify({ id: "dr-1", report_number: "DR-001" }),
              { status: 201, headers: { "Content-Type": "application/json" } }
            )
          );
        }

        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
    });

    const user = userEvent.setup();
    render(<DailyProductionPage />);

    await screen.findByRole("option", { name: /Northwind/i });
    await user.selectOptions(screen.getByLabelText(/project/i), "p1");
    await user.type(screen.getByLabelText(/foreman\/superintendent/i), "Avery Chen");
    await user.click(screen.getByRole("button", { name: /add visitor/i }));
    await user.type(screen.getByLabelText(/visitor name/i), "Taylor Rivera");
    await user.type(screen.getByLabelText(/visitor company/i), "City of Example");
    await user.click(screen.getByRole("button", { name: /add delay/i }));
    await user.type(screen.getByLabelText(/delay category/i), "Weather");
    await user.type(screen.getByLabelText(/delay description/i), "Heavy rain slowed grading");
    await user.click(screen.getByRole("button", { name: /add photo/i }));
    await user.type(screen.getByLabelText(/photo description/i), "Excavation progress");
    await user.click(screen.getByRole("button", { name: /add production/i }));
    await user.type(screen.getByLabelText(/bid item/i), "Excavation");
    await user.click(screen.getByRole("button", { name: /add safety observation/i }));
    await user.type(screen.getByLabelText(/safety observation type/i), "Hazard");

    await user.click(screen.getByRole("button", { name: /save daily production/i }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalled();
    });

    const reportCall = fetchSpy.mock.calls.find(([input]) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      return url.endsWith("/api/daily-field-reports");
    });

    expect(reportCall).toBeDefined();
    const body = JSON.parse((reportCall?.[1] as RequestInit).body as string);
    expect(body.visitors).toHaveLength(1);
    expect(body.delays).toHaveLength(1);
    expect(body.photos).toHaveLength(1);
    expect(body.production_quantities).toHaveLength(1);
    expect(body.safety_observations).toHaveLength(1);
  });
});
