"use client";

import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

type Overview = {
  tenants: number;
  users: number;
  projects: number;
};

type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  title: string;
  platform_role: "platform_super_admin" | "user";
  is_active: boolean;
};

export default function PlatformAdminPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [authorized, setAuthorized] = useState(false);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [message, setMessage] = useState("");
  const [resetPasswords, setResetPasswords] = useState<Record<string, string>>({});

  async function loadAdminData(token: string): Promise<void> {
    const [overviewResponse, usersResponse] = await Promise.all([
      fetch(`${getApiBaseUrl()}/api/admin/overview`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }),
      fetch(`${getApiBaseUrl()}/api/admin/users`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }),
    ]);

    if (overviewResponse.ok) {
      const data = await overviewResponse.json();
      setOverview(data);
    }

    if (usersResponse.ok) {
      const data = await usersResponse.json();
      setUsers(data);
    }
  }

  async function updateAccess(userId: string, platformRole: AdminUser["platform_role"], isActive: boolean): Promise<void> {
    setMessage("");
    const token = getAccessToken();
    const response = await fetch(`${getApiBaseUrl()}/api/admin/users/${userId}/access`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ platform_role: platformRole, is_active: isActive }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      setMessage(payload?.detail || "Unable to update access.");
      return;
    }

    setMessage("Access updated.");
    await loadAdminData(token);
  }

  async function resetPassword(userId: string): Promise<void> {
    setMessage("");
    const newPassword = (resetPasswords[userId] || "").trim();
    if (newPassword.length < 8) {
      setMessage("New password must be at least 8 characters.");
      return;
    }

    const token = getAccessToken();
    const response = await fetch(`${getApiBaseUrl()}/api/admin/users/${userId}/reset-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ new_password: newPassword }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      setMessage(payload?.detail || "Unable to reset password.");
      return;
    }

    setResetPasswords((prev) => ({ ...prev, [userId]: "" }));
    setMessage("Password reset successfully.");
  }

  useEffect(() => {
    setLocale(getLocale());
    const token = getAccessToken();
    fetch(`${getApiBaseUrl()}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((me) => {
        if (!me || me.platform_role !== "platform_super_admin") {
          setAuthorized(false);
          return;
        }
        setAuthorized(true);
        loadAdminData(token);
      });
  }, []);

  return (
    <AppShell titleKey="platformAdmin.title">
      {!authorized ? (
        <p>{t(locale, "platformAdmin.denied")}</p>
      ) : (
        <>
          <div className="card">
            <span className="auth-eyebrow">Platform Operations</span>
            <p className="muted">System-wide visibility and controls for tenants, users, and active projects.</p>
          </div>
          <div className="grid">
            <div className="card">
              {t(locale, "platformAdmin.tenants")}
              <div className="metric">{overview?.tenants ?? 0}</div>
              <div className="metric-note">Managed organizations</div>
            </div>
            <div className="card">
              {t(locale, "platformAdmin.users")}
              <div className="metric">{overview?.users ?? 0}</div>
              <div className="metric-note">Platform-wide active users</div>
            </div>
            <div className="card">
              {t(locale, "platformAdmin.projects")}
              <div className="metric">{overview?.projects ?? 0}</div>
              <div className="metric-note">Tracked live projects</div>
            </div>
          </div>
          <div className="card">
            <h3>User Access Management</h3>
            <p className="muted">Manage platform access and reset user passwords.</p>
            {message ? <p>{message}</p> : null}
            <div className="list">
              {users.map((user) => (
                <div className="list-item" key={user.id}>
                  <div>
                    <strong>{user.display_name} ({user.email})</strong>
                    <div className="muted">{user.title || "No title"}</div>
                  </div>
                  <div className="form-grid" style={{ marginTop: 12 }}>
                    <label>
                      Platform role
                      <select
                        value={user.platform_role}
                        onChange={(event) => {
                          const nextRole = event.target.value as AdminUser["platform_role"];
                          setUsers((prev) =>
                            prev.map((row) => (row.id === user.id ? { ...row, platform_role: nextRole } : row))
                          );
                        }}
                      >
                        <option value="user">user</option>
                        <option value="platform_super_admin">platform_super_admin</option>
                      </select>
                    </label>
                    <label>
                      Active
                      <input
                        type="checkbox"
                        checked={user.is_active}
                        onChange={(event) => {
                          const checked = event.target.checked;
                          setUsers((prev) => prev.map((row) => (row.id === user.id ? { ...row, is_active: checked } : row)));
                        }}
                      />
                    </label>
                    <button onClick={() => updateAccess(user.id, user.platform_role, user.is_active)}>Update Access</button>
                    <input
                      type="password"
                      placeholder="Temporary password"
                      value={resetPasswords[user.id] || ""}
                      onChange={(event) => {
                        const value = event.target.value;
                        setResetPasswords((prev) => ({ ...prev, [user.id]: value }));
                      }}
                    />
                    <button onClick={() => resetPassword(user.id)}>Reset Password</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </AppShell>
  );
}
