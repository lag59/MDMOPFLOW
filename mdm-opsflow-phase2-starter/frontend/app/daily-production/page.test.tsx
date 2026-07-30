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
const uploadTicketFilesForExtractionMock = vi.fn();

vi.mock("@/lib/tickets", () => ({
  createTicket: (...args: unknown[]) => createTicketMock(...args),
  listTickets: (...args: unknown[]) => listTicketsMock(...args),
  uploadTicketFilesForExtraction: (...args: unknown[]) => uploadTicketFilesForExtractionMock(...args),
}));

describe("Daily production report", () => {
  beforeEach(() => {
    createTicketMock.mockReset();
    createTicketMock.mockResolvedValue({ id: "t1", ticket_number: "T-1" });
    listTicketsMock.mockReset();
    listTicketsMock.mockResolvedValue([]);
    uploadTicketFilesForExtractionMock.mockReset();
    uploadTicketFilesForExtractionMock.mockResolvedValue({ items: [] });
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

  it("scans a document with OCR and applies extracted values into editable report fields", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.endsWith("/api/projects")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ id: "p1", project_name: "Northwind", project_number: "P-100" }]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }));
    });

    uploadTicketFilesForExtractionMock.mockResolvedValue({
      items: [
        {
          filename: "ticket-a.txt",
          original_filename: "ticket-a.txt",
          mime_type: "text/plain",
          file_size_bytes: 128,
          extracted_summary: "Ticket T-220: Crushed Stone 42 tons",
          extracted_text_preview: "Ticket # T-220\nMaterial: Crushed Stone\nTons: 42\nDriver: Jordan Lee",
          extraction_confidence: 0.94,
          review_required: false,
          extracted_entities: {
            ticket_number: "T-220",
            material_name: "Crushed Stone",
            tons: "42",
            driver: "Jordan Lee",
          },
          calculator_prefill: {
            material_name: "Crushed Stone",
            gross_weight_lbs: null,
            tare_weight_lbs: null,
            net_weight_lbs: null,
            number_of_loads: null,
          },
          created_ticket_id: null,
          duplicate_ticket_id: null,
        },
      ],
    });

    const user = userEvent.setup();
    render(<DailyProductionPage />);

    const fileInput = screen.getByLabelText(/upload ticket or delivery scan/i);
    const file = new File(["Ticket # T-220"], "ticket-a.txt", { type: "text/plain" });
    await user.upload(fileInput, file);

    await user.click(screen.getByRole("button", { name: /scan with ocr/i }));

    expect(await screen.findByText("ticket-a.txt")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /apply to form/i }));

    await waitFor(() => {
      expect(screen.getByDisplayValue("Crushed Stone")).toBeInTheDocument();
      expect(screen.getByLabelText(/foreman\/superintendent/i)).toHaveValue("Jordan Lee");
      expect(screen.getByText(/Applied extracted values from ticket-a.txt/i)).toBeInTheDocument();
    });
  });
});
