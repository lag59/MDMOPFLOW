import { clearSession, getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

export type VendorPurchaseOrder = {
  id: string;
  tenant_id: string;
  project_id: string | null;
  po_number: string;
  vendor_name: string;
  description: string;
  status: string;
  total_amount: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type VendorInvoiceSubmission = {
  id: string;
  tenant_id: string;
  project_id: string | null;
  purchase_order_id: string | null;
  invoice_number: string;
  vendor_name: string;
  amount: string | null;
  status: string;
  notes: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type VendorDeliveryRecord = {
  id: string;
  tenant_id: string;
  project_id: string | null;
  purchase_order_id: string | null;
  ticket_number: string;
  vendor_name: string;
  destination: string;
  status: string;
  received_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type VendorComplianceDocument = {
  id: string;
  tenant_id: string;
  project_id: string | null;
  document_name: string;
  vendor_name: string;
  status: string;
  expires_at: string | null;
  notes: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

class VendorApiError extends Error {
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
    throw new VendorApiError(401, "Session expired. Please log in again.");
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

  throw new VendorApiError(response.status, detail);
}

export async function listVendorPurchaseOrders(): Promise<VendorPurchaseOrder[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/vendor/purchase-orders`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load vendor purchase orders");
  return (await response.json()) as VendorPurchaseOrder[];
}

export async function listVendorInvoiceSubmissions(): Promise<VendorInvoiceSubmission[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/vendor/invoice-submissions`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load vendor invoice submissions");
  return (await response.json()) as VendorInvoiceSubmission[];
}

export async function listVendorDeliveryRecords(): Promise<VendorDeliveryRecord[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/vendor/delivery-records`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load vendor delivery records");
  return (await response.json()) as VendorDeliveryRecord[];
}

export async function listVendorComplianceDocuments(): Promise<VendorComplianceDocument[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/vendor/compliance-documents`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load vendor compliance documents");
  return (await response.json()) as VendorComplianceDocument[];
}
