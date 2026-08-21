import { beforeEach, describe, expect, it, vi } from "vitest";

import { getDocumentIntakeConfig, routeDocumentForIntake } from "./documentIntake";

vi.mock("@/lib/i18n", () => ({
  getApiBaseUrl: () => "https://api.example.test",
}));

describe("document intake API client", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("opsflow_access_token", "token");
    window.localStorage.setItem("opsflow_refresh_token", "refresh-token");
    window.localStorage.setItem("opsflow_tenant_id", "tenant-1");
    vi.restoreAllMocks();
  });

  it("loads document intake config with tenant auth headers", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          auto_route_min_confidence: 0.72,
          auto_post_financial_or_ticket_min_confidence: 0.9,
          never_silent_overwrite: true,
          preserve_source_value: true,
          preserve_units: true,
          flag_cross_document_conflicts: true,
          require_tenant_scope: true,
          create_audit_event: true,
          routes: { haul_ticket: "Tickets > Hauling" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const config = await getDocumentIntakeConfig();

    expect(config.routes.haul_ticket).toBe("Tickets > Hauling");
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/api/document-intake/config",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({ Authorization: "Bearer token", "X-Tenant-ID": "tenant-1" }),
      })
    );
  });

  it("uploads a file for strict document routing and retries after refresh", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/document-intake") && fetchMock.mock.calls.filter(([calledUrl]) => String(calledUrl).endsWith("/api/document-intake")).length === 1) {
        return Promise.resolve(new Response(JSON.stringify({ detail: "Invalid authentication" }), { status: 401, headers: { "Content-Type": "application/json" } }));
      }
      if (url.endsWith("/api/auth/refresh")) {
        return Promise.resolve(new Response(JSON.stringify({ access_token: "fresh-token", refresh_token: "fresh-refresh" }), { status: 200, headers: { "Content-Type": "application/json" } }));
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            document_type: "haul_ticket",
            classification_confidence: 0.99,
            recommended_route: "Tickets > Hauling",
            project: { name: "North Ridge Commerce Park - Phase 2", number: null, match_confidence: 0 },
            vendor: { name: "Carolina Haul Services", document_number: "CH-004821" },
            extracted_fields: { ticket_number: "CH-004821", load_unit: "TON" },
            uncertain_fields: [],
            conflicts: [],
            requires_human_review: false,
            reason_for_review: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );
    });

    const result = await routeDocumentForIntake(new File(["HAUL TICKET"], "haul-ticket.txt", { type: "text/plain" }));

    expect(result.document_type).toBe("haul_ticket");
    expect(result.extracted_fields.load_unit).toBe("TON");
    expect(window.localStorage.getItem("opsflow_access_token")).toBe("fresh-token");
    const uploadCalls = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/document-intake"));
    expect(uploadCalls).toHaveLength(2);
    expect(uploadCalls[1][1]).toEqual(expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer fresh-token", "X-Tenant-ID": "tenant-1" }) }));
  });
});