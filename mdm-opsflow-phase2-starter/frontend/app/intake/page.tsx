"use client";

import React from "react";
import { useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken } from "@/lib/auth";
import {
  ReplayTokenApiError,
  ReplayTokenAuditEntry,
  ReplayTokenAuditSummary,
  ReplayTokenAuditTrend,
  ReplayTokenBulkRevokeActiveResponse,
  ReplayTokenState,
  ReplayTokenStateAlerts,
  createReplayTokenAuditExportToken,
  bulkRevokeActiveReplayTokens,
  fetchReplayTokenAuditHistoryPage,
  fetchReplayTokenAuditSummary,
  fetchReplayTokenAuditTrend,
  fetchReplayTokenStateAlerts,
  fetchReplayTokenStateEnvelope,
} from "@/lib/replayTokens";

type SortValue = "-issued_at" | "+issued_at";
type ReplayTokenAuditAction =
  | "all"
  | "issue_replay_history_export_token"
  | "consume_replay_history_export_token"
  | "revoke_replay_history_export_token";
type ReplayTokenAuditSort = "-created_at" | "+created_at";
type ReplayTokenAuditTrendGranularity = "day" | "hour";
type ReplayTokenAuditWindowPreset =
  | "all"
  | "last_1h"
  | "last_6h"
  | "last_12h"
  | "last_24h"
  | "last_48h"
  | "last_72h"
  | "last_96h"
  | "last_120h"
  | "last_144h"
  | "last_168h"
  | "last_7d"
  | "last_14d"
  | "last_21d"
  | "last_30d"
  | "custom";

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return `${value.toFixed(1)}%`;
}

function formatTrendLabel(value: string): string {
  return new Date(value).toLocaleString();
}

function formatTrendWindow(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "n/a";
}

function resolveAuditWindowPresetRange(
  preset: ReplayTokenAuditWindowPreset,
  nowMs: number = Date.now()
): { start: string; end: string } | null {
  if (preset === "all" || preset === "custom") {
    return null;
  }

  const endDate = new Date(nowMs);
  const end = endDate.toISOString();
  const start = new Date(endDate.getTime());
  if (preset === "last_1h") {
    start.setUTCHours(start.getUTCHours() - 1);
  } else if (preset === "last_6h") {
    start.setUTCHours(start.getUTCHours() - 6);
  } else if (preset === "last_12h") {
    start.setUTCHours(start.getUTCHours() - 12);
  } else if (preset === "last_24h") {
    start.setUTCHours(start.getUTCHours() - 24);
  } else if (preset === "last_48h") {
    start.setUTCHours(start.getUTCHours() - 48);
  } else if (preset === "last_72h") {
    start.setUTCHours(start.getUTCHours() - 72);
  } else if (preset === "last_96h") {
    start.setUTCHours(start.getUTCHours() - 96);
  } else if (preset === "last_120h") {
    start.setUTCHours(start.getUTCHours() - 120);
  } else if (preset === "last_144h") {
    start.setUTCHours(start.getUTCHours() - 144);
  } else if (preset === "last_168h") {
    start.setUTCHours(start.getUTCHours() - 168);
  } else if (preset === "last_7d") {
    start.setUTCDate(start.getUTCDate() - 7);
  } else if (preset === "last_14d") {
    start.setUTCDate(start.getUTCDate() - 14);
  } else if (preset === "last_21d") {
    start.setUTCDate(start.getUTCDate() - 21);
  } else {
    start.setUTCDate(start.getUTCDate() - 30);
  }

  return { start: start.toISOString(), end };
}

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
  const [revokeBusy, setRevokeBusy] = useState(false);
  const [auditLoading, setAuditLoading] = useState(false);
  const [revokePreview, setRevokePreview] = useState<ReplayTokenBulkRevokeActiveResponse | null>(null);
  const [revokeResult, setRevokeResult] = useState<string>("");
  const [liveRevokeReason, setLiveRevokeReason] = useState<string>("");
  const [auditEntries, setAuditEntries] = useState<ReplayTokenAuditEntry[]>([]);
  const [auditSummary, setAuditSummary] = useState<ReplayTokenAuditSummary | null>(null);
  const [auditTrend, setAuditTrend] = useState<ReplayTokenAuditTrend | null>(null);
  const [auditHasMore, setAuditHasMore] = useState(false);
  const [auditNextCursorCreatedAt, setAuditNextCursorCreatedAt] = useState<string | null>(null);
  const [auditNextCursorId, setAuditNextCursorId] = useState<string | null>(null);
  const [auditLoadingMore, setAuditLoadingMore] = useState(false);
  const [auditExportBusy, setAuditExportBusy] = useState(false);
  const [auditAction, setAuditAction] = useState<ReplayTokenAuditAction>("all");
  const [auditSort, setAuditSort] = useState<ReplayTokenAuditSort>("-created_at");
  const [auditTrendGranularity, setAuditTrendGranularity] = useState<ReplayTokenAuditTrendGranularity>("day");
  const [auditWindowPreset, setAuditWindowPreset] = useState<ReplayTokenAuditWindowPreset>("all");
  const [auditActorUserId, setAuditActorUserId] = useState<string>("");
  const [auditTokenId, setAuditTokenId] = useState<string>("");
  const [auditStartCreatedAt, setAuditStartCreatedAt] = useState<string>("");
  const [auditEndCreatedAt, setAuditEndCreatedAt] = useState<string>("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    void refreshAll();
    void refreshAudit();
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

  async function refreshAudit(): Promise<void> {
    setAuditLoading(true);
    try {
      const [page, summary, trend] = await Promise.all([
        fetchReplayTokenAuditHistoryPage({
          limit: 10,
          sort: auditSort,
          action: auditAction === "all" ? undefined : auditAction,
          actorUserId: auditActorUserId.trim() || undefined,
          tokenId: auditTokenId.trim() || undefined,
          startCreatedAt: auditStartCreatedAt || undefined,
          endCreatedAt: auditEndCreatedAt || undefined,
        }),
        fetchReplayTokenAuditSummary({
          action: auditAction === "all" ? undefined : auditAction,
          actorUserId: auditActorUserId.trim() || undefined,
          tokenId: auditTokenId.trim() || undefined,
          startCreatedAt: auditStartCreatedAt || undefined,
          endCreatedAt: auditEndCreatedAt || undefined,
        }),
        fetchReplayTokenAuditTrend({
          action: auditAction === "all" ? undefined : auditAction,
          actorUserId: auditActorUserId.trim() || undefined,
          tokenId: auditTokenId.trim() || undefined,
          startCreatedAt: auditStartCreatedAt || undefined,
          endCreatedAt: auditEndCreatedAt || undefined,
          granularity: auditTrendGranularity,
        }),
      ]);
      setAuditEntries(page.items);
      setAuditSummary(summary);
      setAuditTrend(trend);
      setAuditHasMore(page.has_more);
      setAuditNextCursorCreatedAt(page.next_cursor_created_at);
      setAuditNextCursorId(page.next_cursor_id);
    } catch {
      setAuditEntries([]);
      setAuditSummary(null);
      setAuditTrend(null);
      setAuditHasMore(false);
      setAuditNextCursorCreatedAt(null);
      setAuditNextCursorId(null);
    } finally {
      setAuditLoading(false);
    }
  }

  async function loadMoreAudit(): Promise<void> {
    if (!auditHasMore || !auditNextCursorCreatedAt || !auditNextCursorId) {
      return;
    }

    setAuditLoadingMore(true);
    try {
      const page = await fetchReplayTokenAuditHistoryPage({
        limit: 10,
        sort: auditSort,
        action: auditAction === "all" ? undefined : auditAction,
        actorUserId: auditActorUserId.trim() || undefined,
        tokenId: auditTokenId.trim() || undefined,
        startCreatedAt: auditStartCreatedAt || undefined,
        endCreatedAt: auditEndCreatedAt || undefined,
        cursorCreatedAt: auditNextCursorCreatedAt,
        cursorId: auditNextCursorId,
      });
      setAuditEntries((prev) => [...prev, ...page.items]);
      setAuditHasMore(page.has_more);
      setAuditNextCursorCreatedAt(page.next_cursor_created_at);
      setAuditNextCursorId(page.next_cursor_id);
    } catch {
      setError("Unable to load more replay token audit entries.");
    } finally {
      setAuditLoadingMore(false);
    }
  }

  async function downloadAuditExport(): Promise<void> {
    setAuditExportBusy(true);
    setError("");
    try {
      const response = await createReplayTokenAuditExportToken({
        startCreatedAt: auditStartCreatedAt || undefined,
        endCreatedAt: auditEndCreatedAt || undefined,
        output: "csv",
        limit: 500,
      });
      window.open(response.download_url, "_self");
    } catch {
      setError("Unable to start replay token audit download.");
    } finally {
      setAuditExportBusy(false);
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
    setRevokePreview(null);
    setRevokeResult("");
    await refreshAll();
    await refreshAudit();
  }

  function applyAuditWindowPreset(preset: ReplayTokenAuditWindowPreset): void {
    setAuditWindowPreset(preset);
    const range = resolveAuditWindowPresetRange(preset);
    if (range) {
      setAuditStartCreatedAt(range.start);
      setAuditEndCreatedAt(range.end);
      return;
    }

    if (preset === "all") {
      setAuditStartCreatedAt("");
      setAuditEndCreatedAt("");
    }
  }

  function getIssuedBeforeCutoffIso(): string {
    const cutoff = new Date(Date.now() - staleThresholdMinutes * 60 * 1000);
    return cutoff.toISOString();
  }

  async function previewRevokeStaleTokens(): Promise<void> {
    setRevokeBusy(true);
    setError("");
    setRevokeResult("");
    try {
      const response = await bulkRevokeActiveReplayTokens({
        limit: 500,
        issuedBefore: getIssuedBeforeCutoffIso(),
        reason: "UI stale token cleanup preview",
        dryRun: true,
      });
      setRevokePreview(response);
      setRevokeResult(`Dry run found ${response.candidate_count} candidate tokens.`);
    } catch {
      setError("Unable to preview stale token revocation.");
    } finally {
      setRevokeBusy(false);
    }
  }

  async function runLiveRevoke(): Promise<void> {
    setRevokeBusy(true);
    setError("");
    setRevokeResult("");
    try {
      const response = await bulkRevokeActiveReplayTokens({
        limit: 500,
        issuedBefore: getIssuedBeforeCutoffIso(),
        reason: liveRevokeReason.trim(),
        dryRun: false,
      });
      setRevokePreview(response);
      setRevokeResult(`Live revoke completed: ${response.revoked_count} token(s) revoked.`);
      await refreshAll();
      await refreshAudit();
    } catch (err) {
      if (err instanceof ReplayTokenApiError && err.status === 403) {
        setError(`Permission denied: ${err.detail}`);
      } else {
        setError("Unable to run live stale token revocation.");
      }
    } finally {
      setRevokeBusy(false);
    }
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

      <div className="card">
        <div className="section-header">
          <h3>Stale token actions</h3>
        </div>
        <p className="metric-note">
          Cutoff uses current stale threshold. Dry run first, then confirm live revoke when candidates exist.
        </p>
        <div className="replay-action-row">
          <button onClick={() => void previewRevokeStaleTokens()} disabled={revokeBusy || loading}>
            {revokeBusy ? "Working..." : "Preview revoke stale tokens"}
          </button>
          <button
            onClick={() => void runLiveRevoke()}
            disabled={
              revokeBusy ||
              loading ||
              !revokePreview ||
              revokePreview.candidate_count < 1 ||
              !liveRevokeReason.trim()
            }
          >
            Confirm live revoke
          </button>
        </div>
        <div className="form-grid">
          <label>
            Live revoke reason
            <input
              type="text"
              value={liveRevokeReason}
              onChange={(e) => setLiveRevokeReason(e.target.value)}
              placeholder="Required for live revoke (for example: security incident token sweep)"
            />
          </label>
        </div>
        {revokePreview ? (
          <div className="list">
            <div className="list-item">
              <strong>Preview summary</strong>
              <span>Inspected: {revokePreview.inspected_tokens}</span>
              <span>Candidates: {revokePreview.candidate_count}</span>
              <span>Would revoke: {revokePreview.revoked_count}</span>
            </div>
            {revokePreview.candidate_token_ids.length > 0 ? (
              <div className="list-item">
                <strong>Candidate token IDs</strong>
                <span className="mono-cell">{revokePreview.candidate_token_ids.join(", ")}</span>
              </div>
            ) : null}
          </div>
        ) : null}
        {revokeResult ? <p>{revokeResult}</p> : null}
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

      <div className="card">
        <div className="section-header">
          <h3>Audit trail</h3>
          <div className="replay-action-row">
            <button onClick={() => void refreshAudit()} disabled={auditLoading}>
              {auditLoading ? "Refreshing..." : "Refresh audit"}
            </button>
            <button onClick={() => void downloadAuditExport()} disabled={auditLoading || auditExportBusy}>
              {auditExportBusy ? "Preparing download..." : "Download audit export"}
            </button>
          </div>
        </div>
        <div className="grid">
          <div className="card">
            Audit total
            <div className="metric">{auditSummary?.total_entries ?? "-"}</div>
            <div className="metric-note">Rows matching current filters</div>
          </div>
          <div className="card">
            Issue / consume / revoke
            <div className="metric">
              {auditSummary
                ? `${auditSummary.issued_count}/${auditSummary.consumed_count}/${auditSummary.revoked_count}`
                : "-"}
            </div>
            <div className="metric-note">Action counts for current scope</div>
          </div>
          <div className="card">
            Consume / revoke rate
            <div className="metric">
              {auditSummary
                ? `${formatPercent(auditSummary.consume_rate_percent)} / ${formatPercent(auditSummary.revoke_rate_percent)}`
                : "-"}
            </div>
            <div className="metric-note">Percent of issued actions in current scope</div>
          </div>
          <div className="card">
            Unique actors
            <div className="metric">{auditSummary?.unique_actor_count ?? "-"}</div>
            <div className="metric-note">Distinct operator IDs</div>
          </div>
          <div className="card">
            Latest audit event
            <div className="metric">
              {auditSummary?.latest_created_at ? new Date(auditSummary.latest_created_at).toLocaleString() : "n/a"}
            </div>
            <div className="metric-note">Most recent created_at in filter window</div>
          </div>
        </div>
        <div className="card trend-card">
          <div className="section-header">
            <h3>Audit trend</h3>
            <span className="metric-note">
              {auditTrend ? `${auditTrend.granularity} buckets` : "No trend data"}
            </span>
          </div>
          {auditTrend && auditTrend.items.length > 0 ? (
            <div className="trend-panel">
              <div className="trend-meta">
                <span>Window start: {formatTrendWindow(auditTrend.window_start_created_at)}</span>
                <span>Window end: {formatTrendWindow(auditTrend.window_end_created_at)}</span>
                <span>Timezone: {auditTrend.window_effective_timezone}</span>
              </div>
              <div className="trend-chart" role="img" aria-label="Replay token audit trend chart">
                {auditTrend.items.map((bucket) => {
                  const maxValue = Math.max(bucket.issued_count, bucket.consumed_count, bucket.revoked_count, 1);
                  return (
                    <div className="trend-column" key={bucket.bucket_start_created_at}>
                      <div className="trend-bars" title={formatTrendLabel(bucket.bucket_start_created_at)}>
                        <div
                          className="trend-segment trend-issued"
                          style={{ height: `${(bucket.issued_count / maxValue) * 100}%` }}
                          aria-label={`Issued ${bucket.issued_count}`}
                        />
                        <div
                          className="trend-segment trend-consumed"
                          style={{ height: `${(bucket.consumed_count / maxValue) * 100}%` }}
                          aria-label={`Consumed ${bucket.consumed_count}`}
                        />
                        <div
                          className="trend-segment trend-revoked"
                          style={{ height: `${(bucket.revoked_count / maxValue) * 100}%` }}
                          aria-label={`Revoked ${bucket.revoked_count}`}
                        />
                      </div>
                      <div className="trend-label">{formatTrendLabel(bucket.bucket_start_created_at)}</div>
                      <div className="metric-note">Total {bucket.total_count}</div>
                    </div>
                  );
                })}
              </div>
              <div className="trend-legend">
                <span><i className="trend-swatch trend-issued" />Issue</span>
                <span><i className="trend-swatch trend-consumed" />Consume</span>
                <span><i className="trend-swatch trend-revoked" />Revoke</span>
              </div>
            </div>
          ) : (
            <p className="metric-note">No trend buckets found for the current audit filters.</p>
          )}
        </div>
        <div className="form-grid replay-controls-grid">
          <label>
            Audit sort
            <select value={auditSort} onChange={(e) => setAuditSort(e.target.value as ReplayTokenAuditSort)}>
              <option value="-created_at">Newest first</option>
              <option value="+created_at">Oldest first</option>
            </select>
          </label>
          <label>
            Audit action
            <select value={auditAction} onChange={(e) => setAuditAction(e.target.value as ReplayTokenAuditAction)}>
              <option value="all">All actions</option>
              <option value="issue_replay_history_export_token">Issue</option>
              <option value="consume_replay_history_export_token">Consume</option>
              <option value="revoke_replay_history_export_token">Revoke</option>
            </select>
          </label>
          <label>
            Trend granularity
            <select
              value={auditTrendGranularity}
              onChange={(e) => setAuditTrendGranularity(e.target.value as ReplayTokenAuditTrendGranularity)}
            >
              <option value="day">Day</option>
              <option value="hour">Hour</option>
            </select>
          </label>
          <label>
            Audit window preset
            <select
              value={auditWindowPreset}
              onChange={(e) => applyAuditWindowPreset(e.target.value as ReplayTokenAuditWindowPreset)}
            >
              <option value="all">All time</option>
              <option value="last_1h">Last 1 hour</option>
              <option value="last_6h">Last 6 hours</option>
              <option value="last_12h">Last 12 hours</option>
              <option value="last_24h">Last 24 hours</option>
              <option value="last_48h">Last 48 hours</option>
              <option value="last_72h">Last 72 hours</option>
              <option value="last_96h">Last 96 hours</option>
              <option value="last_120h">Last 120 hours</option>
              <option value="last_144h">Last 144 hours</option>
              <option value="last_168h">Last 168 hours</option>
              <option value="last_7d">Last 7 days</option>
              <option value="last_14d">Last 14 days</option>
              <option value="last_21d">Last 21 days</option>
              <option value="last_30d">Last 30 days</option>
              <option value="custom">Custom</option>
            </select>
          </label>
          <label>
            Actor user ID
            <input
              type="text"
              value={auditActorUserId}
              onChange={(e) => setAuditActorUserId(e.target.value)}
              placeholder="Filter by actor"
            />
          </label>
          <label>
            Token ID
            <input
              type="text"
              value={auditTokenId}
              onChange={(e) => setAuditTokenId(e.target.value)}
              placeholder="Filter by token"
            />
          </label>
          <label>
            Start created at (UTC ISO)
            <input
              type="text"
              value={auditStartCreatedAt}
              onChange={(e) => {
                setAuditStartCreatedAt(e.target.value);
                setAuditWindowPreset("custom");
              }}
              placeholder="2026-07-25T00:00:00Z"
            />
          </label>
          <label>
            End created at (UTC ISO)
            <input
              type="text"
              value={auditEndCreatedAt}
              onChange={(e) => {
                setAuditEndCreatedAt(e.target.value);
                setAuditWindowPreset("custom");
              }}
              placeholder="2026-07-26T00:00:00Z"
            />
          </label>
        </div>
        {auditLoading ? (
          <p>Loading audit entries...</p>
        ) : auditEntries.length === 0 ? (
          <p>No replay token audit entries found.</p>
        ) : (
          <div>
            <div className="token-state-table-wrap">
              <table className="token-state-table">
                <thead>
                  <tr>
                    <th>Action</th>
                    <th>Token</th>
                    <th>Actor</th>
                    <th>Created at</th>
                  </tr>
                </thead>
                <tbody>
                  {auditEntries.map((entry) => (
                    <tr key={entry.id}>
                      <td>{entry.action}</td>
                      <td className="mono-cell">{entry.resource_id}</td>
                      <td className="mono-cell">{entry.actor_user_id}</td>
                      <td>{new Date(entry.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="replay-pagination-row">
              <div className="metric-note">
                Audit cursor: {auditNextCursorCreatedAt || "none"}
                {auditNextCursorId ? ` / ${auditNextCursorId}` : ""}
              </div>
              <button
                onClick={() => void loadMoreAudit()}
                disabled={!auditHasMore || auditLoading || auditLoadingMore}
              >
                {auditLoadingMore ? "Loading more..." : auditHasMore ? "Load more audit" : "No more audit rows"}
              </button>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
