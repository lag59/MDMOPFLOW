import { clearSession, getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

export type Ticket = {
  id: string;
  tenant_id: string;
  intake_item_id: string | null;
  project_id: string | null;
  ticket_number: string;
  truck: string;
  driver: string;
  material: string;
  origin: string;
  destination: string;
  load_time: string | null;
  unload_time: string | null;
  miles: string | null;
  weight: string | null;
  volume_yards: string | null;
  tons: string | null;
  fuel_cost: string | null;
  revenue: string | null;
  status: string;
  notes: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type MaterialDensityPreset = {
  id: string;
  tenant_id: string;
  material_name: string;
  density_tons_per_cubic_yard: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type TicketQuantityCalculationRequest = {
  gross_weight_lbs?: string;
  tare_weight_lbs?: string;
  net_weight_lbs?: string;
  material_name?: string;
  number_of_loads?: number;
  truck_type?: string;
  truck_capacity_tons?: string;
  material_density_tons_per_cubic_yard?: string;
  rate_per_ton?: string;
  rate_per_cubic_yard?: string;
  rate_per_load?: string;
};

export type TicketQuantityCalculationResponse = {
  net_weight_lbs: string | null;
  net_tons: string | null;
  total_tons: string | null;
  total_cubic_yards: string | null;
  estimated_cubic_yards: string | null;
  estimated_load_count: string | null;
  tons_per_load: string | null;
  cubic_yards_per_load: string | null;
  cost_from_ton: string | null;
  cost_from_cubic_yard: string | null;
  cost_from_load: string | null;
  selected_cost_method: string | null;
  selected_total_cost: string | null;
  resolved_material_name: string | null;
  resolved_density_source: string | null;
  weight_method: string | null;
  resolved_truck_type: string | null;
  resolved_truck_capacity_tons: string | null;
  assumptions: string[];
};

export type TicketCalculatorPrefill = {
  material_name: string | null;
  gross_weight_lbs: string | null;
  tare_weight_lbs: string | null;
  net_weight_lbs: string | null;
  number_of_loads: number | null;
};

export type TicketUploadExtractionItem = {
  filename: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  extracted_summary: string;
  extracted_text_preview?: string | null;
  extraction_confidence: number;
  review_required: boolean;
  extracted_entities: Record<string, string>;
  calculator_prefill: TicketCalculatorPrefill;
  created_ticket_id: string | null;
  duplicate_ticket_id: string | null;
};

export type TicketUploadExtractionResponse = {
  items: TicketUploadExtractionItem[];
};

export class TicketApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

function buildAuthHeaders(contentType = false): Record<string, string> {
  const token = getAccessToken();
  const tenantId = getTenantId();
  if (!token) {
    throw new Error("Missing auth token");
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Tenant-ID": tenantId,
  };

  if (contentType) {
    headers["Content-Type"] = "application/json";
  }

  return headers;
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
    throw new TicketApiError(401, "Session expired. Please log in again.");
  }

  let detail = fallbackMessage;
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload?.detail) {
      detail = payload.detail;
    }
  } catch {
    // Keep fallback detail if non-JSON body.
  }

  throw new TicketApiError(response.status, detail);
}

export async function listTickets(): Promise<Ticket[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/tickets`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load tickets");
  return (await response.json()) as Ticket[];
}

export async function createTicket(payload: Partial<Ticket>): Promise<Ticket> {
  const response = await fetch(`${getApiBaseUrl()}/api/tickets`, {
    method: "POST",
    headers: buildAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  await throwIfNotOk(response, "Unable to create ticket");
  return (await response.json()) as Ticket;
}

export async function updateTicket(ticketId: string, payload: Partial<Ticket>): Promise<Ticket> {
  const response = await fetch(`${getApiBaseUrl()}/api/tickets/${ticketId}`, {
    method: "PATCH",
    headers: buildAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  await throwIfNotOk(response, "Unable to update ticket");
  return (await response.json()) as Ticket;
}

export async function deleteTicket(ticketId: string): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/api/tickets/${ticketId}`, {
    method: "DELETE",
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to delete ticket");
}

export async function listMaterialDensityPresets(): Promise<MaterialDensityPreset[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/tickets/material-density-presets`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load material density presets");
  return (await response.json()) as MaterialDensityPreset[];
}

export async function upsertMaterialDensityPreset(materialName: string, density: string): Promise<MaterialDensityPreset> {
  const encodedMaterial = encodeURIComponent(materialName);
  const response = await fetch(`${getApiBaseUrl()}/api/tickets/material-density-presets/${encodedMaterial}`, {
    method: "PUT",
    headers: buildAuthHeaders(true),
    body: JSON.stringify({ density_tons_per_cubic_yard: density }),
  });
  await throwIfNotOk(response, "Unable to save material density preset");
  return (await response.json()) as MaterialDensityPreset;
}

export async function calculateTicketQuantities(
  payload: TicketQuantityCalculationRequest
): Promise<TicketQuantityCalculationResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/tickets/quantity-calculation`, {
    method: "POST",
    headers: buildAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  await throwIfNotOk(response, "Unable to calculate ticket quantities");
  return (await response.json()) as TicketQuantityCalculationResponse;
}

export async function uploadTicketFilesForExtraction(
  files: File[],
  createTickets: boolean
): Promise<TicketUploadExtractionResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(
    `${getApiBaseUrl()}/api/tickets/upload-extract?create_tickets=${createTickets ? "true" : "false"}`,
    {
      method: "POST",
      headers: buildAuthHeaders(),
      body: formData,
    }
  );
  await throwIfNotOk(response, "Unable to upload ticket files");
  return (await response.json()) as TicketUploadExtractionResponse;
}
