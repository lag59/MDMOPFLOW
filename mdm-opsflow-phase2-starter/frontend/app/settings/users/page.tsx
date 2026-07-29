"use client";

import React from "react";
import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId, refreshSession } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

type UserMembership = {
  user_id: string;
  email: string;
  display_name: string;
  title: string;
  role_name: string;
  status: string;
};

type UserPermissionOverride = {
  permission: string;
  enabled: boolean;
};

type TenantUserPermissions = {
  user_id: string;
  email: string;
  role_name: string;
  base_permissions: string[];
  effective_permissions: string[];
  overrides: UserPermissionOverride[];
};

type TenantOption = {
  tenant_id: string;
  tenant_name: string;
};

const ROLE_OPTIONS = [
  "owner",
  "executive",
  "project_manager",
  "estimator",
  "dispatcher",
  "accounting",
  "payroll",
  "safety_manager",
  "fleet_manager",
  "administrator",
  "customer",
  "vendor",
];

function mapAssignmentError(locale: "en" | "es", detail: string | undefined): string {
  switch (detail) {
    case "User not found":
      return t(locale, "settings.usersPage.errors.userNotFound");
    case "Role not found for tenant":
      return t(locale, "settings.usersPage.errors.roleNotFound");
    case "Insufficient permissions":
      return t(locale, "settings.usersPage.errors.insufficientPermissions");
    default:
      return t(locale, "settings.usersPage.errors.assignFailed");
  }
}

export default function UserSettingsPage() {
  const locale = getLocale();
  const [memberships, setMemberships] = useState<UserMembership[]>([]);
  const [permissionCatalog, setPermissionCatalog] = useState<string[]>([]);
  const [tenantOptions, setTenantOptions] = useState<TenantOption[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState(() => getTenantId());
  const [selectedUser, setSelectedUser] = useState<UserMembership | null>(null);
  const [selectedPermissions, setSelectedPermissions] = useState<Set<string>>(new Set());
  const [basePermissions, setBasePermissions] = useState<Set<string>>(new Set());
  const [email, setEmail] = useState("");
  const [roleName, setRoleName] = useState("owner");
  const [message, setMessage] = useState("");
  const [toggleMessage, setToggleMessage] = useState("");
  const [loadError, setLoadError] = useState("");

  function formatPermissionLabel(permission: string): string {
    return permission
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function resolveTenantHeader(): string {
    return selectedTenantId || getTenantId();
  }

  async function fetchWithSessionRetry(input: RequestInfo | URL, init: RequestInit): Promise<Response> {
    const firstAttempt = await fetch(input, init);
    if (firstAttempt.status !== 401) {
      return firstAttempt;
    }

    const refreshed = await refreshSession(getApiBaseUrl());
    if (!refreshed) {
      return firstAttempt;
    }

    const retryHeaders: Record<string, string> = {
      ...(init.headers as Record<string, string>),
      Authorization: `Bearer ${getAccessToken()}`,
    };
    return fetch(input, {
      ...init,
      headers: retryHeaders,
    });
  }

  async function loadTenantOptions(): Promise<void> {
    const response = await fetchWithSessionRetry(`${getApiBaseUrl()}/api/admin/tenant-service-summary`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
      },
    });

    if (!response.ok) {
      setTenantOptions([]);
      return;
    }

    const payload = (await response.json()) as { items: TenantOption[] };
    setTenantOptions(payload.items);

    if (!selectedTenantId && payload.items.length > 0) {
      setSelectedTenantId(payload.items[0].tenant_id);
    }
  }

  async function loadMembers(): Promise<void> {
    setLoadError("");
    const tenantId = resolveTenantHeader();
    if (!tenantId) {
      setMemberships([]);
      setLoadError("Select a tenant to manage team members and function access.");
      return;
    }

    const response = await fetchWithSessionRetry(`${getApiBaseUrl()}/api/tenant-users`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": tenantId,
      },
    });
    if (!response.ok) {
      setMemberships([]);
      if (response.status === 401) {
        setLoadError("Your session expired. Please log in again.");
      } else if (response.status === 400) {
        setLoadError("Tenant context is missing. Complete onboarding or select a tenant before managing services.");
      } else if (response.status === 403) {
        setLoadError("You do not have permission to manage users for this tenant.");
      } else {
        setLoadError(`Could not load team members (HTTP ${response.status}).`);
      }
      return;
    }
    const data = await response.json();
    setMemberships(data);
  }

  async function loadPermissionCatalog(): Promise<void> {
    const response = await fetchWithSessionRetry(`${getApiBaseUrl()}/api/tenant-users/permissions/catalog`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": resolveTenantHeader(),
      },
    });
    if (!response.ok) {
      setPermissionCatalog([]);
      let nextError = "Could not load service function catalog.";
      if (response.status === 401) {
        nextError = "Your session expired. Please log in again.";
      } else if (response.status === 400) {
        nextError = "Tenant context is missing. Complete onboarding or select a tenant before managing services.";
      } else if (response.status === 403) {
        nextError = "You do not have permission to manage service functions for this tenant.";
      } else if (response.status === 404) {
        nextError = "Service function catalog is unavailable on the backend right now (HTTP 404). Please redeploy the backend service and try again.";
      } else {
        nextError = `Could not load service function catalog (HTTP ${response.status}).`;
      }

      // Preserve a clearer prior error (for example auth/tenant error from member load).
      setLoadError((previous) => previous || nextError);
      return;
    }
    const data = (await response.json()) as string[];
    setPermissionCatalog(data);
  }

  async function loadUserPermissions(userId: string): Promise<void> {
    setToggleMessage("");
    const response = await fetchWithSessionRetry(`${getApiBaseUrl()}/api/tenant-users/${userId}/permissions`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": resolveTenantHeader(),
      },
    });
    if (!response.ok) {
      setToggleMessage("Could not load function toggles for this user.");
      return;
    }

    const data = (await response.json()) as TenantUserPermissions;
    setSelectedPermissions(new Set(data.effective_permissions));
    setBasePermissions(new Set(data.base_permissions));
  }

  useEffect(() => {
    void loadTenantOptions();
  }, []);

  useEffect(() => {
    if (!selectedTenantId) {
      setMemberships([]);
      setPermissionCatalog([]);
      return;
    }

    void loadMembers();
    void loadPermissionCatalog();
  }, [selectedTenantId]);

  async function assignUser(): Promise<void> {
    setMessage("");
    if (!email.trim()) {
      setMessage(t(locale, "settings.usersPage.errors.emailRequired"));
      return;
    }

    const response = await fetchWithSessionRetry(`${getApiBaseUrl()}/api/tenant-users`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": resolveTenantHeader(),
      },
      body: JSON.stringify({ email: email.trim().toLowerCase(), role_name: roleName }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      setMessage(mapAssignmentError(locale, payload?.detail));
      return;
    }

    setEmail("");
    setMessage(t(locale, "settings.usersPage.success.assigned"));
    await loadMembers();
  }

  async function savePermissionOverrides(): Promise<void> {
    if (!selectedUser) {
      return;
    }

    const overrides = permissionCatalog.map((permission) => ({
      permission,
      enabled: selectedPermissions.has(permission),
    }));

    const response = await fetchWithSessionRetry(`${getApiBaseUrl()}/api/tenant-users/${selectedUser.user_id}/permissions`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": resolveTenantHeader(),
      },
      body: JSON.stringify({ overrides }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      setToggleMessage(payload?.detail ?? "Failed to update function toggles.");
      if (response.status === 401) {
        setToggleMessage("Your session expired. Please log in again.");
        window.location.href = "/login";
      }
      return;
    }

    await loadUserPermissions(selectedUser.user_id);
    setToggleMessage("Function toggles updated.");
  }

  function togglePermission(permission: string): void {
    const next = new Set(selectedPermissions);
    if (next.has(permission)) {
      next.delete(permission);
    } else {
      next.add(permission);
    }
    setSelectedPermissions(next);
  }

  return (
    <AppShell titleKey="settings.users">
      <div className="card form-grid">
        <div className="section-header">
          <h3>Tenant Context</h3>
        </div>
        <label>
          Tenant
          <select
            value={selectedTenantId}
            onChange={(event) => {
              const nextTenantId = event.target.value;
              setSelectedTenantId(nextTenantId);
              setSelectedUser(null);
              setToggleMessage("");
              setLoadError("");
              setPermissionCatalog([]);
              setMemberships([]);
            }}
          >
            <option value="">Select a tenant</option>
            {tenantOptions.map((tenant) => (
              <option key={tenant.tenant_id} value={tenant.tenant_id}>
                {tenant.tenant_name}
              </option>
            ))}
          </select>
        </label>
        <p className="muted">
          {selectedTenantId
            ? "You are managing users and function access for the selected tenant."
            : "Select a tenant to manage users and service functions."}
        </p>
      </div>

      <div className="card form-grid">
        <div className="section-header">
          <h3>Assign User</h3>
        </div>
        <input
          placeholder={t(locale, "settings.usersPage.userEmail")}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <label>
          Role
          <select
            value={roleName}
            onChange={(e) => setRoleName(e.target.value)}
            disabled={!selectedTenantId}
          >
            {ROLE_OPTIONS.map((role) => (
              <option key={role} value={role}>
                {t(locale, `settings.usersPage.roles.${role}`)}
              </option>
            ))}
          </select>
        </label>
        <button onClick={assignUser} disabled={!selectedTenantId}>
          {t(locale, "common.save")}
        </button>
        {message ? <p>{message}</p> : null}
      </div>

      <div className="section-header">
        <h3>Team Members</h3>
      </div>
      <div className="card" style={{ marginBottom: "12px" }}>
        <p className="muted">
          To turn services on/off (Payroll, Tickets, Intake, Dispatch, etc.), click <strong>Manage Functions</strong>
          next to a team member, then check/uncheck permissions and click <strong>Save Function Access</strong>.
        </p>
        {loadError ? <p>{loadError}</p> : null}
      </div>
      <div className="list">
        {memberships.map((membership) => (
          <div className="list-item" key={`${membership.user_id}-${membership.role_name}`}>
            <strong>{membership.display_name} ({membership.email})</strong>
            <span className="muted">{membership.role_name}</span>
            <span className={`status-pill status-${membership.status}`}>{membership.status}</span>
            <button
              type="button"
              onClick={() => {
                setSelectedUser(membership);
                void loadUserPermissions(membership.user_id);
              }}
            >
              Manage Functions
            </button>
          </div>
        ))}
      </div>

      {selectedUser ? (
        <div className="card" style={{ marginTop: "16px" }}>
          <div className="section-header">
            <h3>
              Function Access: {selectedUser.display_name} ({selectedUser.email})
            </h3>
          </div>
          <div className="list">
            {permissionCatalog.map((permission) => {
              const checked = selectedPermissions.has(permission);
              const isRoleDefault = basePermissions.has(permission);
              return (
                <label key={permission} className="list-item" style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => togglePermission(permission)}
                  />
                  <span style={{ flex: 1 }}>{formatPermissionLabel(permission)}</span>
                  <span className="muted">{isRoleDefault ? "role default" : "override"}</span>
                </label>
              );
            })}
          </div>
          <button type="button" onClick={savePermissionOverrides} style={{ marginTop: "12px" }}>
            Save Function Access
          </button>
          {toggleMessage ? <p>{toggleMessage}</p> : null}
        </div>
      ) : null}
    </AppShell>
  );
}
