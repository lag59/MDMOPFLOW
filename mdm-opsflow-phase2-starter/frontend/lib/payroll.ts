import { clearSession, getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

export type PayrollTimecard = {
  id: string;
  tenant_id: string;
  employee_id: string;
  project_id: string | null;
  work_date: string;
  regular_hours: string;
  overtime_hours: string;
  double_time_hours: string;
  cost_code: string;
  work_description: string;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type PayrollRun = {
  id: string;
  tenant_id: string;
  run_number: string;
  period_start: string;
  period_end: string;
  status: string;
  notes: string;
  employee_count: number;
  total_regular_hours: string;
  total_overtime_hours: string;
  total_double_time_hours: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type PayrollSummaryByProject = {
  project_id: string | null;
  timecard_count: number;
  regular_hours: string;
  overtime_hours: string;
  double_time_hours: string;
};

export type PayrollSummary = {
  employee_count: number;
  timecard_count: number;
  payroll_run_count: number;
  total_regular_hours: string;
  total_overtime_hours: string;
  total_double_time_hours: string;
  by_project: PayrollSummaryByProject[];
};

class PayrollApiError extends Error {
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
    throw new PayrollApiError(401, "Session expired. Please log in again.");
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

  throw new PayrollApiError(response.status, detail);
}

export async function listPayrollTimecards(): Promise<PayrollTimecard[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/payroll/timecards`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load payroll timecards");
  return (await response.json()) as PayrollTimecard[];
}

export async function listPayrollRuns(): Promise<PayrollRun[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/payroll/runs`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load payroll runs");
  return (await response.json()) as PayrollRun[];
}

export async function getPayrollSummary(): Promise<PayrollSummary> {
  const response = await fetch(`${getApiBaseUrl()}/api/payroll/summary`, {
    headers: buildAuthHeaders(),
  });
  await throwIfNotOk(response, "Unable to load payroll summary");
  return (await response.json()) as PayrollSummary;
}
