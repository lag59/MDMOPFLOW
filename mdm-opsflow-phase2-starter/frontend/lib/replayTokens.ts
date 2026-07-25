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
  if (!response.ok) {
    throw new Error("Unable to load replay token states");
  }

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
  if (!response.ok) {
    throw new Error("Unable to load replay token alerts");
  }

  return (await response.json()) as ReplayTokenStateAlerts;
}
