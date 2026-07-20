"use client";

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
      setMessage("Email is required.");
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
      setMessage(payload?.detail || "Unable to assign user.");
      return;
    }

    setEmail("");
    setMessage("User assigned to company.");
    await loadMembers();
  }

  return (
    <AppShell titleKey="settings.users">
      <div className="card form-grid">
        <input
          placeholder="User email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          placeholder="Role name"
          value={roleName}
          onChange={(e) => setRoleName(e.target.value)}
        />
        <button onClick={assignUser}>{t(locale, "common.save")}</button>
        {message ? <p>{message}</p> : null}
      </div>
      <div className="list">
        {memberships.map((membership) => (
          <div className="list-item" key={`${membership.user_id}-${membership.role_name}`}>
            <strong>{membership.display_name} ({membership.email})</strong>
            <span>{membership.role_name} - {membership.status}</span>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
