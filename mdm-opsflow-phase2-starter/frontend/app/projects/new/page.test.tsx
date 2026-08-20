import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import NewProjectPage from "./page";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));

describe("New project document intake", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("opsflow_locale", "en");
    window.localStorage.setItem("opsflow_access_token", "token");
    window.localStorage.setItem("opsflow_tenant_id", "tenant-1");
    vi.restoreAllMocks();
  });

  it("creates a project, uploads documents to intake, and shows AI routing results", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method || "GET";

      if (url.endsWith("/api/projects") && method === "POST") {
        return Promise.resolve(
          new Response(JSON.stringify({ id: "project-1" }), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (url.endsWith("/api/intake/upload") && method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "intake-1",
              original_filename: "scale-ticket.txt",
              document_type: "ticket",
              extracted_summary: "Ticket HT-1001, net tons 23.67",
              ocr_status: "completed",
              ai_status: "completed",
              classification_confidence: 0.96,
              needs_review: false,
            }),
            { status: 201, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.endsWith("/api/intake/placement/suggest") && method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  item_id: "intake-1",
                  destination_label: "Tickets",
                  destination_href: "/tickets",
                  confidence: 0.94,
                  reason: "Gross, tare, net, and tons indicate a haul ticket.",
                  signal_source: "rules_engine",
                  document_intelligence: {
                    primary_document_type: "haul_ticket",
                    recommended_module: "tickets",
                    confidence: 0.96,
                    supporting_evidence: ["gross/tare/net present", "tons calculated"],
                    conflicting_evidence: [],
                  },
                },
              ],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } }));
    });

    const user = userEvent.setup();
    render(<NewProjectPage />);

    await user.type(screen.getByPlaceholderText("Project name"), "Route 12 Rehab");
    await user.type(screen.getByPlaceholderText("Project number"), "R12-001");
    await user.type(screen.getByPlaceholderText("Customer"), "County DOT");
    await user.type(screen.getByPlaceholderText("Project manager"), "Pat Manager");
    await user.upload(
      screen.getByLabelText("Attach project documents"),
      new File(["Gross 78440\nTare 31100\nNet 47340\nTons 23.67"], "scale-ticket.txt", { type: "text/plain" })
    );
    await user.click(screen.getByRole("button", { name: "Create project" }));

    await waitFor(() => {
      expect(screen.getByText("OCR / AI Document Routing")).toBeInTheDocument();
    });

    expect(screen.getByText("scale-ticket.txt")).toBeInTheDocument();
    expect(screen.getByText("Destination: Tickets")).toBeInTheDocument();
    expect(screen.getByText("Classification: 96% | Routing: 94%")).toBeInTheDocument();

    const uploadCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/api/intake/upload"));
    const formData = uploadCall?.[1]?.body as FormData;
    expect(formData.get("project_id")).toBe("project-1");
    expect(formData.get("file")).toBeInstanceOf(File);
  });
});
