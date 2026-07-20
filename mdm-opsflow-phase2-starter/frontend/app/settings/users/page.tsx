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
  const [email, setEmail] = useState("");
  const [roleName, setRoleName] = useState("owner");
  const [message, setMessage] = useState("");

  async function loadMembers(): Promise<void> {
    const response = await fetch(`${getApiBaseUrl()}/api/tenant-users`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
      },
    });
    if (!response.ok) {
      setMemberships([]);
      return;
    }
    const data = await response.json();
    setMemberships(data);
  }

  useEffect(() => {
    loadMembers();
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
      <div className="list">
        {memberships.map((membership) => (
          <div className="list-item" key={`${membership.user_id}-${membership.role_name}`}>
            <strong>{membership.display_name} ({membership.email})</strong>
            <span className="muted">{membership.role_name}</span>
            <span className={`status-pill status-${membership.status}`}>{membership.status}</span>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
