import { clearSession, getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

export type EstimatorTakeoff = {
  id: string;
  tenant_id: string;
  project_id: string | null;
  takeoff_number: string;
  material_name: string;
  quantity: string;
  unit_of_measure: string;
  estimated_cost: string | null;
  status: string;
  notes: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type CreateEstimatorTakeoffPayload = {
  project_id?: string | null;
  takeoff_number: string;
  material_name?: string;
  quantity: string;
  unit_of_measure?: string;
  estimated_cost?: string | null;
  status?: string;
  notes?: string;
};

export type EstimatorVersion = {
  id: string;
  tenant_id: string;
  project_id: string | null;
  version_name: string;
  revision_number: number;
  estimated_revenue: string | null;
  estimated_cost: string | null;
  status: string;
  notes: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type CreateEstimatorVersionPayload = {
  project_id?: string | null;
  version_name: string;
  revision_number?: number;
  estimated_revenue?: string | null;
  estimated_cost?: string | null;
  status?: string;
  notes?: string;
};

export type EstimatorBidPipelineItem = {
  id: string;
  tenant_id: string;
  project_id: string | null;
  bid_number: string;
  customer_name: string;
  stage: string;
  bid_amount: string | null;
  probability_percent: string | null;
  due_date: string | null;
  status: string;
  notes: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type EstimatorWinLossRecord = {
  id: string;
  tenant_id: string;
  project_id: string | null;
  bid_pipeline_item_id: string | null;
  outcome: string;
  final_amount: string | null;
  decision_date: string | null;
  reason: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type EstimatorSummary = {
  takeoff_count: number;
  version_count: number;
  bid_pipeline_count: number;
  wins: number;
  losses: number;
  pending: number;
  win_rate_percent: string;
};

class EstimatorApiError extends Error {
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
    throw new EstimatorApiError(401, "Session expired. Please log in again.");
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

  throw new EstimatorApiError(response.status, detail);
}

export async function listEstimatorTakeoffs(): Promise<EstimatorTakeoff[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimator/takeoffs`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load estimator takeoffs");
  return (await response.json()) as EstimatorTakeoff[];
}

export async function createEstimatorTakeoff(
  payload: CreateEstimatorTakeoffPayload
): Promise<EstimatorTakeoff> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimator/takeoffs`, {
    method: "POST",
    headers: {
      ...buildAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      project_id: payload.project_id ?? null,
      takeoff_number: payload.takeoff_number,
      material_name: payload.material_name || "",
      quantity: payload.quantity,
      unit_of_measure: payload.unit_of_measure || "cy",
      estimated_cost: payload.estimated_cost ?? null,
      status: payload.status || "draft",
      notes: payload.notes || "",
    }),
  });
  await throwIfNotOk(response, "Unable to create estimator takeoff");
  return (await response.json()) as EstimatorTakeoff;
}

export async function listEstimatorVersions(): Promise<EstimatorVersion[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimator/versions`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load estimate versions");
  return (await response.json()) as EstimatorVersion[];
}

export async function createEstimatorVersion(
  payload: CreateEstimatorVersionPayload
): Promise<EstimatorVersion> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimator/versions`, {
    method: "POST",
    headers: {
      ...buildAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      project_id: payload.project_id ?? null,
      version_name: payload.version_name,
      revision_number: payload.revision_number ?? 1,
      estimated_revenue: payload.estimated_revenue ?? null,
      estimated_cost: payload.estimated_cost ?? null,
      status: payload.status || "draft",
      notes: payload.notes || "",
    }),
  });
  await throwIfNotOk(response, "Unable to create estimate version");
  return (await response.json()) as EstimatorVersion;
}

export async function listEstimatorBidPipelineItems(): Promise<EstimatorBidPipelineItem[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimator/bid-pipeline`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load bid pipeline");
  return (await response.json()) as EstimatorBidPipelineItem[];
}

export async function listEstimatorWinLossRecords(): Promise<EstimatorWinLossRecord[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimator/win-loss`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load win/loss records");
  return (await response.json()) as EstimatorWinLossRecord[];
}

export async function getEstimatorSummary(): Promise<EstimatorSummary> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimator/summary`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load estimator summary");
  return (await response.json()) as EstimatorSummary;
}
