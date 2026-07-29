import { clearSession, getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

export type CustomerPortalProjectSummary = {
  project_id: string;
  project_name: string;
  project_number: string;
  status: string;
  project_manager: string;
  actual_revenue: string;
  ticket_count: number;
  total_documents: number;
  pending_review_documents: number;
};

export type CustomerPortalBillingStatus = {
  project_id: string;
  project_name: string;
  status: string;
  actual_revenue: string;
  ticket_count: number;
  total_tons: string;
  total_cubic_yards: string;
  revenue_shortfall: boolean;
};

export type CustomerPortalDocumentStatus = {
  project_id: string;
  project_name: string;
  total_documents: number;
  pending_review_documents: number;
  latest_document_at: string | null;
};

class CustomerPortalApiError extends Error {
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

async function throwIfNotOk(response: Response, fallbackMessage: string): Promise<void> {
  if (response.ok) {
    return;
  }

  if (response.status === 401) {
    clearSession();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new CustomerPortalApiError(401, "Session expired. Please log in again.");
  }

  let detail = fallbackMessage;
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload?.detail) {
      detail = payload.detail;
    }
  } catch {
    // keep fallback
  }

  throw new CustomerPortalApiError(response.status, detail);
}

export async function listCustomerPortalProjects(): Promise<CustomerPortalProjectSummary[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/customer-portal/projects`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load customer portal projects");
  return (await response.json()) as CustomerPortalProjectSummary[];
}

export async function getCustomerPortalBillingStatus(projectId: string): Promise<CustomerPortalBillingStatus> {
  const response = await fetch(`${getApiBaseUrl()}/api/customer-portal/projects/${projectId}/billing-status`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load customer billing status");
  return (await response.json()) as CustomerPortalBillingStatus;
}

export async function getCustomerPortalDocumentStatus(projectId: string): Promise<CustomerPortalDocumentStatus> {
  const response = await fetch(`${getApiBaseUrl()}/api/customer-portal/projects/${projectId}/documents`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load customer document status");
  return (await response.json()) as CustomerPortalDocumentStatus;
}
