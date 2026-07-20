export type SessionData = {
  accessToken: string;
  refreshToken: string;
  tenantId: string | null;
};

export function saveSession(data: SessionData): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem("opsflow_access_token", data.accessToken);
  window.localStorage.setItem("opsflow_refresh_token", data.refreshToken);
  if (data.tenantId) {
    window.localStorage.setItem("opsflow_tenant_id", data.tenantId);
  }
}

export function clearSession(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem("opsflow_access_token");
  window.localStorage.removeItem("opsflow_refresh_token");
  window.localStorage.removeItem("opsflow_tenant_id");
}

export function getAccessToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("opsflow_access_token") || "";
}

export function getTenantId(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("opsflow_tenant_id") || "";
}
