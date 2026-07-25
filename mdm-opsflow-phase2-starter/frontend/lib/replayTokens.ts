import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

export type ReplayTokenState = {
  token_id: string;
  tenant_id: string;
  state: "issued" | "consumed" | "revoked" | "expired";
  issued_at: string;
  issued_by_user_id: string;
  consumed_at: string | null;
  consumed_by_user_id: string | null;
  revoked_at: string | null;
  revoked_by_user_id: string | null;
  expires_at: string;
  latest_activity_at: string;
  event_id: string | null;
  output: string | null;
  export_limit: number | null;
};

export type ReplayTokenStateListEnvelope = {
  items: ReplayTokenState[];
  limit: number;
  has_more: boolean;
  next_cursor_issued_at: string | null;
  next_cursor_token_id: string | null;
  sort: "-issued_at" | "+issued_at";
  window_start_issued_at: string | null;
  window_end_issued_at: string | null;
  window_effective_timezone: string;
};

export type ReplayTokenStateAlerts = {
  as_of: string;
  stale_threshold_minutes: number;
  stale_active_threshold_count: number;
  window_start_issued_at: string | null;
  window_end_issued_at: string | null;
  window_effective_timezone: string;
  total_tokens: number;
  active_tokens: number;
  active_tokens_older_than_threshold: number;
  active_tokens_older_than_threshold_exceeded: boolean;
  consumed_tokens: number;
  revoked_tokens: number;
  consumed_to_revoked_ratio: number | null;
};

export type ReplayTokenAuditEntry = {
  id: string;
  tenant_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: string;
  actor_user_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type ReplayTokenBulkRevokeActiveResponse = {
  tenant_id: string;
  dry_run: boolean;
  inspected_tokens: number;
  candidate_count: number;
  revoked_count: number;
  skipped_consumed_count: number;
  skipped_revoked_count: number;
  skipped_expired_count: number;
  candidate_token_ids: string[];
  revoked_token_ids: string[];
  revoked_at: string;
};

export type ReplayTokenAuditHistoryPage = {
  items: ReplayTokenAuditEntry[];
  has_more: boolean;
  next_cursor_created_at: string | null;
  next_cursor_id: string | null;
};

export class ReplayTokenApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

function buildAuthHeaders(): Record<string, string> {
  const token = getAccessToken();
  const tenantId = getTenantId();
  if (!token) {
    throw new Error("Missing auth token");
  }

  return {
    Authorization: `Bearer ${token}`,
    "X-Tenant-ID": tenantId,
  };
}

export async function fetchReplayTokenStateEnvelope(params: {
  limit?: number;
  sort?: "-issued_at" | "+issued_at";
  cursorIssuedAt?: string;
  cursorTokenId?: string;
  staleWindowStart?: string;
  staleWindowEnd?: string;
}): Promise<ReplayTokenStateListEnvelope> {
  const query = new URLSearchParams();
  if (params.limit) {
    query.set("limit", String(params.limit));
  }
  if (params.sort) {
    query.set("sort", params.sort);
  }
  if (params.cursorIssuedAt) {
    query.set("cursor_issued_at", params.cursorIssuedAt);
  }
  if (params.cursorTokenId) {
    query.set("cursor_token_id", params.cursorTokenId);
  }
  if (params.staleWindowStart) {
    query.set("start_issued_at", params.staleWindowStart);
  }
  if (params.staleWindowEnd) {
    query.set("end_issued_at", params.staleWindowEnd);
  }

  const response = await fetch(`${getApiBaseUrl()}/api/intake/events/replay-history/export-token-states/list?${query.toString()}`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load replay token states");

  return (await response.json()) as ReplayTokenStateListEnvelope;
}

export async function fetchReplayTokenStateAlerts(params: {
  staleThresholdMinutes: number;
  staleActiveThresholdCount: number;
}): Promise<ReplayTokenStateAlerts> {
  const query = new URLSearchParams({
    stale_threshold_minutes: String(params.staleThresholdMinutes),
    stale_active_threshold_count: String(params.staleActiveThresholdCount),
  });

  const response = await fetch(`${getApiBaseUrl()}/api/intake/events/replay-history/export-token-states/alerts?${query.toString()}`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load replay token alerts");

  return (await response.json()) as ReplayTokenStateAlerts;
}

export async function fetchReplayTokenAuditHistoryPage(params?: {
  limit?: number;
  tokenId?: string;
  actorUserId?: string;
  action?: "issue_replay_history_export_token" | "consume_replay_history_export_token" | "revoke_replay_history_export_token";
  startCreatedAt?: string;
  endCreatedAt?: string;
  cursorCreatedAt?: string;
  cursorId?: string;
}): Promise<ReplayTokenAuditHistoryPage> {
  const query = new URLSearchParams({
    limit: String(params?.limit ?? 20),
  });
  if (params?.tokenId) {
    query.set("token_id", params.tokenId);
  }
  if (params?.actorUserId) {
    query.set("actor_user_id", params.actorUserId);
  }
  if (params?.action) {
    query.set("action", params.action);
  }
  if (params?.startCreatedAt) {
    query.set("start_created_at", params.startCreatedAt);
  }
  if (params?.endCreatedAt) {
    query.set("end_created_at", params.endCreatedAt);
  }
  if (params?.cursorCreatedAt) {
    query.set("cursor_created_at", params.cursorCreatedAt);
  }
  if (params?.cursorId) {
    query.set("cursor_id", params.cursorId);
  }
  const response = await fetch(`${getApiBaseUrl()}/api/intake/events/replay-history/export-token-history?${query.toString()}`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load replay token audit history");

  const items = (await response.json()) as ReplayTokenAuditEntry[];
  const nextCursorCreatedAt = response.headers.get("x-next-cursor-created-at");
  const nextCursorId = response.headers.get("x-next-cursor-id");

  return {
    items,
    has_more: !!nextCursorCreatedAt,
    next_cursor_created_at: nextCursorCreatedAt,
    next_cursor_id: nextCursorId,
  };
}

export async function fetchReplayTokenAuditHistory(params?: {
  limit?: number;
  tokenId?: string;
  actorUserId?: string;
  action?: "issue_replay_history_export_token" | "consume_replay_history_export_token" | "revoke_replay_history_export_token";
  startCreatedAt?: string;
  endCreatedAt?: string;
}): Promise<ReplayTokenAuditEntry[]> {
  const page = await fetchReplayTokenAuditHistoryPage(params);
  return page.items;
}

export async function bulkRevokeActiveReplayTokens(params: {
  limit: number;
  issuedBefore: string;
  reason: string;
  dryRun: boolean;
}): Promise<ReplayTokenBulkRevokeActiveResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/intake/events/replay-history/export-token/revoke-active`, {
    method: "POST",
    headers: {
      ...buildAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      limit: params.limit,
      issued_before: params.issuedBefore,
      reason: params.reason,
      dry_run: params.dryRun,
    }),
  });
  await throwIfNotOk(response, "Unable to revoke active replay tokens");
  return (await response.json()) as ReplayTokenBulkRevokeActiveResponse;
}

async function throwIfNotOk(response: Response, fallbackMessage: string): Promise<void> {
  if (response.ok) {
    return;
  }

  let detail = fallbackMessage;
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload?.detail) {
      detail = payload.detail;
    }
  } catch {
    // Keep fallback detail when response body is not JSON.
  }

  throw new ReplayTokenApiError(response.status, detail);
}
