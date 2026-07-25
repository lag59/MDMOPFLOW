import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import IntakePage from "./page";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: unknown }) => <a href={href}>{children}</a>,
}));

describe("Intake replay token observability page", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("opsflow_access_token", "token");
    window.localStorage.setItem("opsflow_tenant_id", "tenant-1");
    vi.restoreAllMocks();
  });

  it("loads envelope list plus alerts and supports cursor-based load more", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list") && !url.includes("cursor_issued_at")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  token_id: "tok-1",
                  tenant_id: "tenant-1",
                  state: "issued",
                  issued_at: "2026-07-25T18:00:00Z",
                  issued_by_user_id: "u-1",
                  consumed_at: null,
                  consumed_by_user_id: null,
                  revoked_at: null,
                  revoked_by_user_id: null,
                  expires_at: "2026-07-25T18:05:00Z",
                  latest_activity_at: "2026-07-25T18:00:00Z",
                  event_id: "evt-1",
                  output: "json",
                  export_limit: 100,
                },
              ],
              limit: 10,
              has_more: true,
              next_cursor_issued_at: "2026-07-25T18:00:00Z",
              next_cursor_token_id: "tok-1",
              sort: "-issued_at",
              window_start_issued_at: null,
              window_end_issued_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-states/alerts")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              as_of: "2026-07-25T18:10:00Z",
              stale_threshold_minutes: 60,
              stale_active_threshold_count: 10,
              window_start_issued_at: null,
              window_end_issued_at: null,
              window_effective_timezone: "UTC",
              total_tokens: 1,
              active_tokens: 1,
              active_tokens_older_than_threshold: 12,
              active_tokens_older_than_threshold_exceeded: true,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-states/list") && url.includes("cursor_issued_at")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  token_id: "tok-2",
                  tenant_id: "tenant-1",
                  state: "consumed",
                  issued_at: "2026-07-25T17:40:00Z",
                  issued_by_user_id: "u-1",
                  consumed_at: "2026-07-25T17:41:00Z",
                  consumed_by_user_id: "u-1",
                  revoked_at: null,
                  revoked_by_user_id: null,
                  expires_at: "2026-07-25T17:45:00Z",
                  latest_activity_at: "2026-07-25T17:41:00Z",
                  event_id: "evt-1",
                  output: "json",
                  export_limit: 100,
                },
              ],
              limit: 10,
              has_more: false,
              next_cursor_issued_at: null,
              next_cursor_token_id: null,
              sort: "-issued_at",
              window_start_issued_at: null,
              window_end_issued_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    const user = userEvent.setup();
    render(<IntakePage />);

    await waitFor(() => {
      expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      expect(screen.getByText("Threshold exceeded")).toBeInTheDocument();
      expect(screen.getByText("tok-1")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Load more" }));

    await waitFor(() => {
      expect(screen.getByText("tok-2")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "No more rows" })).toBeDisabled();
    });

    expect(fetchMock).toHaveBeenCalled();
  });
});
