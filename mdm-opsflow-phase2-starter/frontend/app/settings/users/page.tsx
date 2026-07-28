"use client";

import React from "react";
import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
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

  async function loadMembers(): Promise<void> {
    setLoadError("");
    const response = await fetch(`${getApiBaseUrl()}/api/tenant-users`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
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
        setLoadError("Could not load team members.");
      }
      return;
    }
    const data = await response.json();
    setMemberships(data);
  }

  async function loadPermissionCatalog(): Promise<void> {
    const response = await fetch(`${getApiBaseUrl()}/api/tenant-users/permissions/catalog`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
      },
    });
    if (!response.ok) {
      setPermissionCatalog([]);
      if (!loadError) {
        setLoadError("Could not load service function catalog.");
      }
      return;
    }
    const data = (await response.json()) as string[];
    setPermissionCatalog(data);
  }

  async function loadUserPermissions(userId: string): Promise<void> {
    setToggleMessage("");
    const response = await fetch(`${getApiBaseUrl()}/api/tenant-users/${userId}/permissions`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
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
    loadMembers();
    loadPermissionCatalog();
  }, []);

  async function assignUser(): Promise<void> {
    setMessage("");
    if (!email.trim()) {
      setMessage(t(locale, "settings.usersPage.errors.emailRequired"));
      return;
    }

    const response = await fetch(`${getApiBaseUrl()}/api/tenant-users`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
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

    const response = await fetch(`${getApiBaseUrl()}/api/tenant-users/${selectedUser.user_id}/permissions`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
      },
      body: JSON.stringify({ overrides }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      setToggleMessage(payload?.detail ?? "Failed to update function toggles.");
      return;
    }

    setToggleMessage("Function toggles updated.");
    await loadUserPermissions(selectedUser.user_id);
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
          <h3>Assign User</h3>
        </div>
        <input
          placeholder={t(locale, "settings.usersPage.userEmail")}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <select
          value={roleName}
          onChange={(e) => setRoleName(e.target.value)}
        >
          {ROLE_OPTIONS.map((role) => (
            <option key={role} value={role}>
              {t(locale, `settings.usersPage.roles.${role}`)}
            </option>
          ))}
        </select>
        <button onClick={assignUser}>{t(locale, "common.save")}</button>
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
