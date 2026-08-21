import { clearSession, getAccessToken, getTenantId, refreshSession } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

export type DocumentIntakeConfig = {
  auto_route_min_confidence: number;
  auto_post_financial_or_ticket_min_confidence: number;
  never_silent_overwrite: boolean;
  preserve_source_value: boolean;
  preserve_units: boolean;
  flag_cross_document_conflicts: boolean;
  require_tenant_scope: boolean;
  create_audit_event: boolean;
  routes: Record<string, string>;
};

export type DocumentIntakeRouteResult = {
  document_type: string;
  classification_confidence: number;
  recommended_route: string;
  project: { name: string | null; number: string | null; match_confidence: number };
  vendor: { name: string | null; document_number: string | null };
  extracted_fields: Record<string, unknown>;
  uncertain_fields: string[];
  conflicts: Array<Record<string, unknown>>;
  requires_human_review: boolean;
  reason_for_review: string | null;
};

export class DocumentIntakeApiError extends Error {
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
  if (!tenantId) {
    throw new Error("Missing tenant context");
  }

  return {
    Authorization: `Bearer ${token}`,
    "X-Tenant-ID": tenantId,
  };
}

async function parseError(response: Response, fallback: string): Promise<DocumentIntakeApiError> {
  let detail = fallback;
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload?.detail) {
      detail = payload.detail;
    }
  } catch {
    // Keep fallback for non-JSON errors.
  }
  return new DocumentIntakeApiError(response.status, detail);
}

async function fetchWithSessionRetry(input: string, init: RequestInit, fallback: string): Promise<Response> {
  const apiBaseUrl = getApiBaseUrl();
  let response = await fetch(input, { ...init, headers: { ...buildAuthHeaders(), ...(init.headers as Record<string, string> | undefined) } });

  if (response.status === 401 && await refreshSession(apiBaseUrl)) {
    response = await fetch(input, { ...init, headers: { ...buildAuthHeaders(), ...(init.headers as Record<string, string> | undefined) } });
  }

  if (response.status === 401) {
    clearSession();
  }

  if (!response.ok) {
    throw await parseError(response, fallback);
  }

  return response;
}

export async function getDocumentIntakeConfig(): Promise<DocumentIntakeConfig> {
  const response = await fetchWithSessionRetry(
    `${getApiBaseUrl()}/api/document-intake/config`,
    { method: "GET" },
    "Unable to load document intake configuration."
  );
  return (await response.json()) as DocumentIntakeConfig;
}

export async function routeDocumentForIntake(file: File): Promise<DocumentIntakeRouteResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithSessionRetry(
    `${getApiBaseUrl()}/api/document-intake`,
    { method: "POST", body: formData },
    "Unable to route document for intake."
  );
  return (await response.json()) as DocumentIntakeRouteResult;
}