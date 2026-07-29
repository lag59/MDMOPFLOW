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
  } else {
    window.localStorage.removeItem("opsflow_tenant_id");
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

export function getRefreshToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("opsflow_refresh_token") || "";
}

export function getTenantId(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("opsflow_tenant_id") || "";
}

export async function refreshSession(apiBaseUrl: string): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearSession();
    return false;
  }

  const response = await fetch(`${apiBaseUrl}/api/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearSession();
    return false;
  }

  const payload = (await response.json()) as {
    access_token: string;
    refresh_token: string;
  };

  saveSession({
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    tenantId: getTenantId() || null,
  });
  return true;
}
