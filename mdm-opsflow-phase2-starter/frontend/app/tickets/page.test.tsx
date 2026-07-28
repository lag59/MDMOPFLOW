import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import TicketsPage from "./page";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: unknown }) => <a href={href}>{children}</a>,
}));

describe("Tickets calculator workflow", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("opsflow_locale", "en");
    window.localStorage.setItem("opsflow_access_token", "token");
    window.localStorage.setItem("opsflow_tenant_id", "tenant-1");
    vi.restoreAllMocks();
  });

  it(
    "runs calculator, applies outputs, creates ticket, and patches selected ticket",
    async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method || "GET";

      if (url.includes("/api/tickets/material-density-presets") && method === "GET") {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                id: "p-1",
                tenant_id: "tenant-1",
                material_name: "Aggregate",
                density_tons_per_cubic_yard: "1.5000",
                created_by: "u-1",
                created_at: "2026-07-25T10:00:00Z",
                updated_at: "2026-07-25T10:00:00Z",
              },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/tickets") && method === "GET") {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                id: "t-1",
                tenant_id: "tenant-1",
                intake_item_id: null,
                project_id: null,
                ticket_number: "TCK-EXISTING",
                truck: "",
                driver: "",
                material: "Aggregate",
                origin: "",
                destination: "",
                load_time: null,
                unload_time: null,
                miles: null,
                weight: "22000.00",
                volume_yards: "7.33",
                tons: "11.00",
                fuel_cost: null,
                revenue: "137.50",
                status: "draft",
                notes: "",
                created_by: "u-1",
                created_at: "2026-07-25T10:00:00Z",
                updated_at: "2026-07-25T10:00:00Z",
              },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/tickets/quantity-calculation") && method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              net_weight_lbs: "22000.00",
              net_tons: "11.00",
              estimated_cubic_yards: "7.33",
              estimated_load_count: "4.00",
              tons_per_load: "2.75",
              cubic_yards_per_load: "1.83",
              cost_from_ton: "137.50",
              cost_from_cubic_yard: "131.94",
              cost_from_load: "260.00",
              selected_cost_method: "per_ton",
              selected_total_cost: "137.50",
              resolved_material_name: "Aggregate",
              resolved_density_source: "preset",
              assumptions: ["material_density_tons_per_cubic_yard resolved from tenant material preset"],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/tickets") && method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "t-2",
              tenant_id: "tenant-1",
              intake_item_id: null,
              project_id: null,
              ticket_number: "TCK-1001",
              truck: "",
              driver: "",
              material: "Aggregate",
              origin: "",
              destination: "",
              load_time: null,
              unload_time: null,
              miles: null,
              weight: "22000.00",
              volume_yards: "7.33",
              tons: "11.00",
              fuel_cost: null,
              revenue: "137.50",
              status: "draft",
              notes: "",
              created_by: "u-1",
              created_at: "2026-07-25T10:05:00Z",
              updated_at: "2026-07-25T10:05:00Z",
            }),
            { status: 201, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/tickets/t-1") && method === "PATCH") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "t-1",
              tenant_id: "tenant-1",
              intake_item_id: null,
              project_id: null,
              ticket_number: "TCK-EXISTING",
              truck: "",
              driver: "",
              material: "Aggregate",
              origin: "",
              destination: "",
              load_time: null,
              unload_time: null,
              miles: null,
              weight: "22000.00",
              volume_yards: "7.33",
              tons: "11.00",
              fuel_cost: null,
              revenue: "137.50",
              status: "draft",
              notes: "",
              created_by: "u-1",
              created_at: "2026-07-25T10:00:00Z",
              updated_at: "2026-07-25T10:10:00Z",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/api/tickets/t-1") && method === "DELETE") {
        return Promise.resolve(new Response(null, { status: 204 }));
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    const user = userEvent.setup();
    render(<TicketsPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Ticket quantity and cost calculator" })).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText("Material preset"), "p-1");
    await waitFor(() => {
      expect(screen.getByLabelText("Density (tons / cubic yard)")).toHaveValue(1.5);
    });

    const materialInputs = screen.getAllByLabelText("Material");
    await user.type(materialInputs[0], "Aggregate");
    const netWeightInputs = screen.getAllByLabelText("Net weight (lbs)");
    await user.type(netWeightInputs[0], "22000");
    await user.type(screen.getByLabelText("Rate per ton"), "12.5");

    await user.click(screen.getByRole("button", { name: "Run ticket calculation" }));

    await waitFor(() => {
      expect(screen.getByText(/Density source: preset/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Apply outputs to ticket form" }));

    await waitFor(() => {
      expect(screen.getByText("Calculation outputs applied to ticket form.")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Ticket number"), "TCK-1001");
    await user.click(screen.getByRole("button", { name: "Create ticket" }));

    await waitFor(() => {
      expect(screen.getByText("Ticket created with standardized calculation outputs.")).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText("Selected ticket for update"), "t-1");
    await user.click(screen.getByRole("button", { name: "Apply outputs to selected ticket" }));

    await waitFor(() => {
      expect(screen.getByText("Selected ticket updated with standardized outputs.")).toBeInTheDocument();
    });

    const createCall = fetchMock.mock.calls.find(([input, init]) => String(input).endsWith("/api/tickets") && (init?.method || "GET") === "POST");
    expect(createCall).toBeDefined();
    expect(String(createCall?.[1]?.body)).toContain('"tons":"11.00"');
    expect(String(createCall?.[1]?.body)).toContain('"volume_yards":"7.33"');

    const patchCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/tickets/t-1") && (init?.method || "GET") === "PATCH");
    expect(patchCall).toBeDefined();
    expect(String(patchCall?.[1]?.body)).toContain('"revenue":"137.50"');

    vi.spyOn(window, "confirm").mockReturnValue(true);
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await waitFor(() => {
      expect(screen.getByLabelText("Ticket number")).toHaveValue("TCK-EXISTING");
    });

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => {
      expect(screen.getByText("Deleted ticket TCK-EXISTING.")).toBeInTheDocument();
    });

    const deleteCall = fetchMock.mock.calls.find(([input, init]) =>
      String(input).includes("/api/tickets/t-1") && (init?.method || "GET") === "DELETE"
    );
    expect(deleteCall).toBeDefined();
    },
    10000
  );

  it("uploads ticket files and prefills calculator + form from extracted fields", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method || "GET";

      if (url.includes("/api/tickets/material-density-presets") && method === "GET") {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/tickets") && method === "GET") {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.includes("/api/tickets/upload-extract") && method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  filename: "ticket_upload.txt",
                  original_filename: "ticket_upload.txt",
                  mime_type: "text/plain",
                  file_size_bytes: 120,
                  extracted_summary: "Ticket TCK-902; Material Sand",
                  extraction_confidence: 0.82,
                  review_required: false,
                  extracted_entities: {
                    ticket_number: "TCK-902",
                    material: "Sand",
                    net_weight_lbs: "25000",
                  },
                  calculator_prefill: {
                    material_name: "Sand",
                    gross_weight_lbs: null,
                    tare_weight_lbs: null,
                    net_weight_lbs: "25000",
                    number_of_loads: 2,
                  },
                  created_ticket_id: null,
                  duplicate_ticket_id: null,
                },
              ],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    const user = userEvent.setup();
    render(<TicketsPage />);

    const fileInput = screen.getByLabelText("Ticket files") as HTMLInputElement;
    const file = new File(["Ticket # TCK-902"], "ticket_upload.txt", { type: "text/plain" });
    await user.upload(fileInput, file);

    await user.click(screen.getByRole("button", { name: "Upload and extract" }));

    await waitFor(() => {
      expect(screen.getByText("ticket_upload.txt")).toBeInTheDocument();
      expect(screen.getByDisplayValue("TCK-902")).toBeInTheDocument();
      expect(screen.getAllByDisplayValue("Sand").length).toBeGreaterThan(0);
      expect(screen.getByText(/high \(82%\)/i)).toBeInTheDocument();
    });
  });

  it("shows possible duplicates panel for near-match ticket numbers", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method || "GET";

      if (url.includes("/api/tickets/material-density-presets") && method === "GET") {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
      }

      if (url.endsWith("/api/tickets") && method === "GET") {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                id: "dup-1",
                tenant_id: "tenant-1",
                intake_item_id: null,
                project_id: null,
                ticket_number: "INV-62126",
                truck: "",
                driver: "",
                material: "Dirt",
                origin: "",
                destination: "",
                load_time: null,
                unload_time: null,
                miles: null,
                weight: "18000.00",
                volume_yards: "7.50",
                tons: "9.00",
                fuel_cost: null,
                revenue: "120.00",
                status: "draft",
                notes: "",
                created_by: "u-1",
                created_at: "2026-07-25T10:00:00Z",
                updated_at: "2026-07-25T10:00:00Z",
              },
            ]),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    const user = userEvent.setup();
    render(<TicketsPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Ticket form" })).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Ticket number"), "INV 62126");

    await waitFor(() => {
      expect(screen.getByText("Possible duplicates found before save:")).toBeInTheDocument();
      expect(screen.getByText("near match")).toBeInTheDocument();
      expect(screen.getAllByText("INV-62126").length).toBeGreaterThan(0);
    });

    await user.click(screen.getByRole("button", { name: "Load existing" }));
    await waitFor(() => {
      expect(screen.getByText("Loaded ticket INV-62126 into form.")).toBeInTheDocument();
      expect(screen.getByLabelText("Ticket number")).toHaveValue("INV-62126");
    });
  });
});