import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import IntakePage from "./page";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: unknown }) => <a href={href}>{children}</a>,
}));

describe("Intake replay token observability page", () => {
  beforeEach(() => {
    vi.useRealTimers();
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

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  id: "log-1",
                  tenant_id: "tenant-1",
                  action: "issue_replay_history_export_token",
                  resource_type: "replay_history_export_token",
                  resource_id: "tok-1",
                  details: "issued",
                  actor_user_id: "u-1",
                  created_by: "u-1",
                  created_at: "2026-07-25T18:00:00Z",
                  updated_at: "2026-07-25T18:00:00Z",
                },
              ],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 1,
              issued_count: 1,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: 0,
              revoke_rate_percent: 0,
              unique_actor_count: 1,
              latest_created_at: "2026-07-25T18:00:00Z",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  bucket_start_created_at: "2026-07-25T00:00:00Z",
                  issued_count: 1,
                  consumed_count: 0,
                  revoked_count: 0,
                  total_count: 1,
                },
              ],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
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
      expect(screen.getAllByText("tok-1").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("issue_replay_history_export_token")).toBeInTheDocument();
      expect(screen.getByText("Audit total")).toBeInTheDocument();
      expect(screen.getByText("1/0/0")).toBeInTheDocument();
      expect(screen.getByText("Consume / revoke rate")).toBeInTheDocument();
      expect(screen.getByText("0.0% / 0.0%")).toBeInTheDocument();
      expect(screen.getByText("Audit trend")).toBeInTheDocument();
      expect(screen.getByText("Total 1")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Load more" }));

    await waitFor(() => {
      expect(screen.getByText("tok-2")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "No more rows" })).toBeDisabled();
    });

    expect(fetchMock).toHaveBeenCalled();
  });

  it("loads additional audit rows with cursor_created_at and cursor_id", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list") && !url.includes("cursor_created_at")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  id: "log-1",
                  tenant_id: "tenant-1",
                  action: "issue_replay_history_export_token",
                  resource_type: "replay_history_export_token",
                  resource_id: "tok-1",
                  details: "issued",
                  actor_user_id: "u-1",
                  created_by: "u-1",
                  created_at: "2026-07-25T18:00:00Z",
                  updated_at: "2026-07-25T18:00:00Z",
                },
              ],
              limit: 10,
              has_more: true,
              next_cursor_created_at: "2026-07-25T18:00:00Z",
              next_cursor_id: "log-1",
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 2,
              issued_count: 1,
              consumed_count: 0,
              revoked_count: 1,
              consume_rate_percent: 0,
              revoke_rate_percent: 100,
              unique_actor_count: 2,
              latest_created_at: "2026-07-25T18:00:00Z",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list") && url.includes("cursor_created_at") && url.includes("cursor_id=log-1")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  id: "log-2",
                  tenant_id: "tenant-1",
                  action: "revoke_replay_history_export_token",
                  resource_type: "replay_history_export_token",
                  resource_id: "tok-2",
                  details: "revoked",
                  actor_user_id: "u-2",
                  created_by: "u-2",
                  created_at: "2026-07-25T17:59:00Z",
                  updated_at: "2026-07-25T17:59:00Z",
                },
              ],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
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
      expect(screen.getByText("tok-1")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Load more audit" })).toBeEnabled();
    });

    await user.click(screen.getByRole("button", { name: "Load more audit" }));

    await waitFor(() => {
      expect(screen.getByText("tok-2")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "No more audit rows" })).toBeDisabled();
    });

    const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
    const loadMoreAuditUrl = calledUrls.find((url) =>
      url.includes("/export-token-history/list") &&
      url.includes("cursor_created_at=2026-07-25T18%3A00%3A00Z") &&
      url.includes("cursor_id=log-1") &&
      url.includes("sort=-created_at")
    );
    expect(loadMoreAuditUrl).toBeTruthy();
  });

  it("applies stale-threshold and sort controls when refreshing", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_issued_at: null,
              next_cursor_token_id: null,
              sort: url.includes("sort=%2Bissued_at") ? "+issued_at" : "-issued_at",
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
              stale_threshold_minutes: url.includes("stale_threshold_minutes=15") ? 15 : 60,
              stale_active_threshold_count: url.includes("stale_active_threshold_count=3") ? 3 : 10,
              window_start_issued_at: null,
              window_end_issued_at: null,
              window_effective_timezone: "UTC",
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
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
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Refresh" })).toBeEnabled();
    });

    await user.selectOptions(screen.getByLabelText("Sort"), "+issued_at");
    const thresholdInput = screen.getByLabelText("Stale threshold (minutes)");
    const countInput = screen.getByLabelText("Stale count threshold");
    fireEvent.change(thresholdInput, { target: { value: "15" } });
    fireEvent.change(countInput, { target: { value: "3" } });
    await user.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
    const latestListUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-states/list"));
    const latestAlertsUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-states/alerts"));

    expect(latestListUrl).toBeTruthy();
    expect(latestAlertsUrl).toBeTruthy();
    expect(latestListUrl).toMatch(/sort=(%2Bissued_at|\+issued_at)/);
    expect(latestAlertsUrl).toContain("stale_threshold_minutes=15");
    expect(latestAlertsUrl).toContain("stale_active_threshold_count=3");
  });

  it("supports stale-token dry run and shows permission message on denied live revoke", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method || "GET";

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/revoke-active") && method === "POST") {
        const payload = JSON.parse(String(init?.body || "{}")) as { dry_run?: boolean };
        if (payload.dry_run) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                tenant_id: "tenant-1",
                dry_run: true,
                inspected_tokens: 20,
                candidate_count: 2,
                revoked_count: 0,
                skipped_consumed_count: 0,
                skipped_revoked_count: 0,
                skipped_expired_count: 0,
                candidate_token_ids: ["tok-a", "tok-b"],
                revoked_token_ids: [],
                revoked_at: "2026-07-25T18:10:00Z",
              }),
              { status: 200, headers: { "Content-Type": "application/json" } }
            )
          );
        }

        return Promise.resolve(
          new Response(
            JSON.stringify({ detail: "Live bulk token revocation requires intake_review permission" }),
            { status: 403, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    const user = userEvent.setup();
    render(<IntakePage />);

    await waitFor(() => {
      expect(screen.getByText("Replay token operations")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Preview revoke stale tokens" }));
    await waitFor(() => {
      expect(screen.getByText("Dry run found 2 candidate tokens.")).toBeInTheDocument();
      expect(screen.getByText("tok-a, tok-b")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Live revoke reason"), {
      target: { value: "Security incident token sweep" },
    });

    await user.click(screen.getByRole("button", { name: "Confirm live revoke" }));
    await waitFor(() => {
      expect(screen.getByText("Permission denied: Live bulk token revocation requires intake_review permission")).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalled();
  });

  it("requests a signed audit export token and starts the download", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method || "GET";

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token") && method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              token: "signed-token",
              download_url: "/api/intake/events/replay-history/export/download?token=signed-token",
              expires_at: "2026-07-25T18:15:00Z",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    const user = userEvent.setup();
    render(<IntakePage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Download audit export" })).toBeEnabled();
    });

    await user.click(screen.getByRole("button", { name: "Download audit export" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
      expect(openSpy).toHaveBeenCalledWith("/api/intake/events/replay-history/export/download?token=signed-token", "_self");
    });
  });

  it("applies audit filters when refreshing audit history", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
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
    });

    await user.selectOptions(screen.getByLabelText("Audit action"), "revoke_replay_history_export_token");
    await user.selectOptions(screen.getByLabelText("Audit sort"), "+created_at");
    fireEvent.change(screen.getByLabelText("Actor user ID"), { target: { value: "u-99" } });
    fireEvent.change(screen.getByLabelText("Token ID"), { target: { value: "tok-xyz" } });
    fireEvent.change(screen.getByLabelText("Start created at (UTC ISO)"), { target: { value: "2026-07-25T00:00:00Z" } });
    fireEvent.change(screen.getByLabelText("End created at (UTC ISO)"), { target: { value: "2026-07-26T00:00:00Z" } });

    await user.click(screen.getByRole("button", { name: "Refresh audit" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
    const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

    expect(latestAuditUrl).toBeTruthy();
    expect(latestAuditUrl).toContain("action=revoke_replay_history_export_token");
    expect(latestAuditUrl).toContain("sort=%2Bcreated_at");
    expect(latestAuditUrl).toContain("actor_user_id=u-99");
    expect(latestAuditUrl).toContain("token_id=tok-xyz");
    expect(latestAuditUrl).toContain("start_created_at=2026-07-25T00%3A00%3A00Z");
    expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00Z");
  });

  it("applies trend granularity when refreshing audit history", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: url.includes("granularity=hour") ? "hour" : "day",
              window_start_created_at: null,
              window_end_created_at: null,
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
    });

    await user.selectOptions(screen.getByLabelText("Trend granularity"), "hour");
    await user.click(screen.getByRole("button", { name: "Refresh audit" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
    const latestTrendUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/trends"));
    expect(latestTrendUrl).toBeTruthy();
    expect(latestTrendUrl).toContain("granularity=hour");
  });

  it("applies an audit window preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_1h");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-25T23%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-6-hours preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_6h");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-25T18%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-12-hours preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_12h");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-25T12%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-48-hours preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_48h");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-24T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-72-hours preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_72h");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-23T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-96-hours preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_96h");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-22T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-120-hours preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_120h");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-21T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-144-hours preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_144h");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-20T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-168-hours preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_168h");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-19T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-14-days preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_14d");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-12T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-21-days preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_21d");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-07-05T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-28-days preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_28d");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-06-28T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-60-days preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_60d");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-05-27T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-90-days preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_90d");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-04-27T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-180-days preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_180d");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2026-01-27T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-365-days preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_365d");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2025-07-26T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-730-days preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_730d");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2024-07-26T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("applies the last-1095-days preset when refreshing audit history", async () => {
    const nowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-26T00:00:00.000Z"));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/export-token-states/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
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
              total_tokens: 0,
              active_tokens: 0,
              active_tokens_older_than_threshold: 0,
              active_tokens_older_than_threshold_exceeded: false,
              consumed_tokens: 0,
              revoked_tokens: 0,
              consumed_to_revoked_ratio: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/list")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              limit: 10,
              has_more: false,
              next_cursor_created_at: null,
              next_cursor_id: null,
              sort: "-created_at",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/summary")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total_entries: 0,
              issued_count: 0,
              consumed_count: 0,
              revoked_count: 0,
              consume_rate_percent: null,
              revoke_rate_percent: null,
              unique_actor_count: 0,
              latest_created_at: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      if (url.includes("/export-token-history/trends")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              granularity: "day",
              window_start_created_at: null,
              window_end_created_at: null,
              window_effective_timezone: "UTC",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }

      return Promise.resolve(new Response("not found", { status: 404 }));
    });

    try {
      const user = userEvent.setup();
      render(<IntakePage />);

      await waitFor(() => {
        expect(screen.getByText("Replay token operations")).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("Audit window preset"), "last_1095d");
      await user.click(screen.getByRole("button", { name: "Refresh audit" }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      const calledUrls = fetchMock.mock.calls.map((entry) => String(entry[0]));
      const latestAuditUrl = [...calledUrls].reverse().find((url) => url.includes("/export-token-history/list"));

      expect(latestAuditUrl).toBeTruthy();
      expect(latestAuditUrl).toContain("start_created_at=2023-07-27T00%3A00%3A00.000Z");
      expect(latestAuditUrl).toContain("end_created_at=2026-07-26T00%3A00%3A00.000Z");
    } finally {
      nowSpy.mockRestore();
    }
  });
});
