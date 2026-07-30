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

export type Estimate = {
  id: string;
  tenant_id: string;
  project_id: string | null;
  estimate_name: string;
  estimate_number: string;
  customer_name: string;
  project_name: string;
  project_address: string;
  project_type: string;
  bid_due_date: string | null;
  expected_start_date: string | null;
  expected_completion_date: string | null;
  estimator_name: string;
  project_manager_name: string;
  sales_contact: string;
  contract_type: string;
  estimate_type: string;
  currency: string;
  tax_jurisdiction: string;
  target_margin_percent: string;
  default_overhead_percent: string;
  default_contingency_percent: string;
  notes: string;
  status: string;
  approval_status: string;
  is_locked: boolean;
  locked_at: string | null;
  converted_project_id: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type CreateEstimatePayload = {
  project_id?: string | null;
  estimate_name: string;
  estimate_number: string;
  customer_name?: string;
  project_name?: string;
  project_address?: string;
  project_type?: string;
  bid_due_date?: string | null;
  expected_start_date?: string | null;
  expected_completion_date?: string | null;
  estimator_name?: string;
  project_manager_name?: string;
  sales_contact?: string;
  contract_type?: string;
  estimate_type?: string;
  currency?: string;
  tax_jurisdiction?: string;
  target_margin_percent?: string;
  default_overhead_percent?: string;
  default_contingency_percent?: string;
  notes?: string;
  status?: string;
};

export type EstimateDocument = {
  id: string;
  tenant_id: string;
  estimate_id: string;
  intake_item_id: string | null;
  filename: string;
  document_type: string;
  processing_status: string;
  confidence_score: string;
  version_label: string;
  review_status: string;
  uploaded_by: string;
  uploaded_at: string;
  created_at: string;
  updated_at: string;
};

export type EstimateValidation = {
  completion_score: number;
  unresolved_issues: string[];
};

export type EstimateAiReview = {
  estimate_id: string;
  warnings: string[];
  recommendations: string[];
};

export type EstimateDocumentExtractionField = {
  field: string;
  extracted_value: string;
  confidence: string;
  status: string;
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

export async function listEstimates(): Promise<Estimate[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimates`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load estimates");
  return (await response.json()) as Estimate[];
}

export async function createEstimate(payload: CreateEstimatePayload): Promise<Estimate> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimates`, {
    method: "POST",
    headers: {
      ...buildAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      project_id: payload.project_id ?? null,
      estimate_name: payload.estimate_name,
      estimate_number: payload.estimate_number,
      customer_name: payload.customer_name || "",
      project_name: payload.project_name || "",
      project_address: payload.project_address || "",
      project_type: payload.project_type || "",
      bid_due_date: payload.bid_due_date ?? null,
      expected_start_date: payload.expected_start_date ?? null,
      expected_completion_date: payload.expected_completion_date ?? null,
      estimator_name: payload.estimator_name || "",
      project_manager_name: payload.project_manager_name || "",
      sales_contact: payload.sales_contact || "",
      contract_type: payload.contract_type || "",
      estimate_type: payload.estimate_type || "",
      currency: payload.currency || "USD",
      tax_jurisdiction: payload.tax_jurisdiction || "",
      target_margin_percent: payload.target_margin_percent || "0.00",
      default_overhead_percent: payload.default_overhead_percent || "0.00",
      default_contingency_percent: payload.default_contingency_percent || "0.00",
      notes: payload.notes || "",
      status: payload.status || "New",
    }),
  });
  await throwIfNotOk(response, "Unable to create estimate");
  return (await response.json()) as Estimate;
}

export async function uploadEstimateDocuments(estimateId: string, files: File[]): Promise<EstimateDocument[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const response = await fetch(`${getApiBaseUrl()}/api/estimates/${estimateId}/documents`, {
    method: "POST",
    headers: buildAuthHeaders(),
    body: formData,
  });
  await throwIfNotOk(response, "Unable to upload estimate documents");
  return (await response.json()) as EstimateDocument[];
}

export async function processEstimateDocument(documentId: string): Promise<EstimateDocument> {
  const response = await fetch(`${getApiBaseUrl()}/api/documents/${documentId}/process`, {
    method: "POST",
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to process estimate document");
  return (await response.json()) as EstimateDocument;
}

export async function listEstimateDocumentExtractions(documentId: string): Promise<EstimateDocumentExtractionField[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/documents/${documentId}/extractions`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load estimate document extractions");
  return (await response.json()) as EstimateDocumentExtractionField[];
}

export async function validateEstimate(estimateId: string): Promise<EstimateValidation> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimates/${estimateId}/validate`, {
    method: "POST",
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to validate estimate");
  return (await response.json()) as EstimateValidation;
}

export async function submitEstimate(estimateId: string): Promise<Estimate> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimates/${estimateId}/submit`, {
    method: "POST",
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to submit estimate");
  return (await response.json()) as Estimate;
}

export async function approveEstimate(estimateId: string): Promise<{ decision: string }> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimates/${estimateId}/approve`, {
    method: "POST",
    headers: {
      ...buildAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ decision: "approved", comments: "Approved from estimator workspace" }),
  });
  await throwIfNotOk(response, "Unable to approve estimate");
  return (await response.json()) as { decision: string };
}

export async function convertEstimateToProject(estimateId: string): Promise<Estimate> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimates/${estimateId}/convert-to-project`, {
    method: "POST",
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to convert estimate to project");
  return (await response.json()) as Estimate;
}

export async function runEstimateAiReview(estimateId: string): Promise<EstimateAiReview> {
  const response = await fetch(`${getApiBaseUrl()}/api/estimates/${estimateId}/ai-review`, {
    method: "POST",
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to run estimate AI review");
  return (await response.json()) as EstimateAiReview;
}
