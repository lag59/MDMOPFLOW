"use client";

import React from "react";
import { useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken } from "@/lib/auth";
import { ReplayTokenState, ReplayTokenStateAlerts, fetchReplayTokenStateAlerts, fetchReplayTokenStateEnvelope } from "@/lib/replayTokens";

type SortValue = "-issued_at" | "+issued_at";

export default function IntakePage() {
  const [items, setItems] = useState<ReplayTokenState[]>([]);
  const [sort, setSort] = useState<SortValue>("-issued_at");
  const [limit, setLimit] = useState<number>(10);
  const [hasMore, setHasMore] = useState(false);
  const [nextCursorIssuedAt, setNextCursorIssuedAt] = useState<string | null>(null);
  const [nextCursorTokenId, setNextCursorTokenId] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<ReplayTokenStateAlerts | null>(null);
  const [staleThresholdMinutes, setStaleThresholdMinutes] = useState<number>(60);
  const [staleCountThreshold, setStaleCountThreshold] = useState<number>(10);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    void refreshAll();
  }, []);

  const byState = useMemo(() => {
    const counts = { issued: 0, consumed: 0, revoked: 0, expired: 0 };
    for (const item of items) {
      counts[item.state] += 1;
    }
    return counts;
  }, [items]);

  async function refreshAll(): Promise<void> {
    setLoading(true);
    setError("");
    try {
      const [listEnvelope, alertsPayload] = await Promise.all([
        fetchReplayTokenStateEnvelope({ limit, sort }),
        fetchReplayTokenStateAlerts({
          staleThresholdMinutes,
          staleActiveThresholdCount: staleCountThreshold,
        }),
      ]);
      setItems(listEnvelope.items);
      setHasMore(listEnvelope.has_more);
      setNextCursorIssuedAt(listEnvelope.next_cursor_issued_at);
      setNextCursorTokenId(listEnvelope.next_cursor_token_id);
      setAlerts(alertsPayload);
    } catch {
      setError("Unable to load replay token observability data.");
    } finally {
      setLoading(false);
    }
  }

  async function loadMore(): Promise<void> {
    if (!hasMore || !nextCursorIssuedAt || !nextCursorTokenId) {
      return;
    }

    setLoadingMore(true);
    setError("");
    try {
      const nextPage = await fetchReplayTokenStateEnvelope({
        limit,
        sort,
        cursorIssuedAt: nextCursorIssuedAt,
        cursorTokenId: nextCursorTokenId,
      });
      setItems((prev) => [...prev, ...nextPage.items]);
      setHasMore(nextPage.has_more);
      setNextCursorIssuedAt(nextPage.next_cursor_issued_at);
      setNextCursorTokenId(nextPage.next_cursor_token_id);
    } catch {
      setError("Unable to load the next page of replay token states.");
    } finally {
      setLoadingMore(false);
    }
  }

  async function applyControls(): Promise<void> {
    await refreshAll();
  }

  return (
    <AppShell titleKey="intake.title">
      <div className="card">
        <h3>Replay token operations</h3>
        <p>
          This view uses the envelope and alerts APIs to monitor replay-export token health, paging, and
          stale active-token thresholds.
        </p>
      </div>

      <div className="grid">
        <div className="card">
          Total tokens
          <div className="metric">{alerts?.total_tokens ?? "-"}</div>
          <div className="metric-note">Current alert window in UTC</div>
        </div>
        <div className="card">
          Active older than threshold
          <div className="metric">{alerts?.active_tokens_older_than_threshold ?? "-"}</div>
          <div className="metric-note">
            Threshold {alerts?.stale_threshold_minutes ?? staleThresholdMinutes}m /
            {" "}
            {alerts?.stale_active_threshold_count ?? staleCountThreshold}
          </div>
        </div>
        <div className="card">
          Consumed / revoked ratio
          <div className="metric">
            {alerts?.consumed_to_revoked_ratio === null || alerts?.consumed_to_revoked_ratio === undefined
              ? "n/a"
              : alerts.consumed_to_revoked_ratio.toFixed(2)}
          </div>
          <div className="metric-note">Operational churn indicator</div>
        </div>
        <div className="card">
          List state mix
          <div className="metric">
            {byState.issued}/{byState.consumed}/{byState.revoked}/{byState.expired}
          </div>
          <div className="metric-note">issued / consumed / revoked / expired</div>
        </div>
      </div>

      <div className="card">
        <div className="section-header">
          <h3>Controls</h3>
          <button onClick={() => void applyControls()} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        <div className="form-grid replay-controls-grid">
          <label>
            Sort
            <select value={sort} onChange={(e) => setSort(e.target.value as SortValue)}>
              <option value="-issued_at">Newest first</option>
              <option value="+issued_at">Oldest first</option>
            </select>
          </label>
          <label>
            Page size
            <select value={String(limit)} onChange={(e) => setLimit(Number(e.target.value))}>
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
            </select>
          </label>
          <label>
            Stale threshold (minutes)
            <input
              type="number"
              min={1}
              max={10080}
              value={staleThresholdMinutes}
              onChange={(e) => setStaleThresholdMinutes(Number(e.target.value || 1))}
            />
          </label>
          <label>
            Stale count threshold
            <input
              type="number"
              min={1}
              max={10000}
              value={staleCountThreshold}
              onChange={(e) => setStaleCountThreshold(Number(e.target.value || 1))}
            />
          </label>
        </div>
      </div>

      {alerts?.active_tokens_older_than_threshold_exceeded ? (
        <div className="card warning-card">
          <strong>Threshold exceeded</strong>
          <p>
            {alerts.active_tokens_older_than_threshold} active tokens are older than
            {" "}
            {alerts.stale_threshold_minutes} minutes.
          </p>
        </div>
      ) : null}

      {error ? <div className="card danger-card">{error}</div> : null}

      <div className="card">
        <div className="section-header">
          <h3>Token state feed</h3>
          <span className="metric-note">Timezone: {alerts?.window_effective_timezone || "UTC"}</span>
        </div>

        {loading ? (
          <p>Loading replay token states...</p>
        ) : items.length === 0 ? (
          <p>No replay export tokens were found for the current scope.</p>
        ) : (
          <div className="token-state-table-wrap">
            <table className="token-state-table">
              <thead>
                <tr>
                  <th>Token</th>
                  <th>State</th>
                  <th>Issued at</th>
                  <th>Expires at</th>
                  <th>Output</th>
                  <th>Latest activity</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.token_id}>
                    <td className="mono-cell">{item.token_id}</td>
                    <td>
                      <span className={`status-pill status-${item.state}`}>{item.state}</span>
                    </td>
                    <td>{new Date(item.issued_at).toLocaleString()}</td>
                    <td>{new Date(item.expires_at).toLocaleString()}</td>
                    <td>{item.output || "n/a"}</td>
                    <td>{new Date(item.latest_activity_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="replay-pagination-row">
          <div className="metric-note">
            Cursor: {nextCursorIssuedAt || "none"}
            {nextCursorTokenId ? ` / ${nextCursorTokenId}` : ""}
          </div>
          <button onClick={() => void loadMore()} disabled={!hasMore || loadingMore || loading}>
            {loadingMore ? "Loading more..." : hasMore ? "Load more" : "No more rows"}
          </button>
        </div>
      </div>
    </AppShell>
  );
}
