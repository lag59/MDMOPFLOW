"use client";

import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

type Overview = { tenants: number; users: number; projects: number };

type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  title: string;
  platform_role: "platform_super_admin" | "user";
  is_active: boolean;
};

type Membership = {
  membership_id: string;
  tenant_id: string;
  tenant_name: string;
  role_name: string;
  status: string;
};

type Tenant = { id: string; name: string };

type ServiceInsights = {
  tickets: number;
  intake_items: number;
  intake_needs_review: number;
  extractions_pending_review: number;
  extractions_review_submitted: number;
  unresolved_extraction_issues: number;
  integration_events_pending: number;
  integration_events_failed: number;
  opportunities: string[];
};

const DEFAULT_ROLE_OPTIONS = [
  "owner",
  "executive",
  "project_manager",
  "estimator",
  "field_supervisor",
  "dispatcher",
  "accounting",
  "payroll",
  "safety_manager",
  "fleet_manager",
  "administrator",
  "customer",
  "vendor",
];

export default function PlatformAdminPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [authorized, setAuthorized] = useState(false);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [insights, setInsights] = useState<ServiceInsights | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [newTenantId, setNewTenantId] = useState("");
  const [roleOptions, setRoleOptions] = useState<string[]>(DEFAULT_ROLE_OPTIONS);
  const [newRoleName, setNewRoleName] = useState(DEFAULT_ROLE_OPTIONS[0]);
  const [newPassword, setNewPassword] = useState("");
  const [newTenantName, setNewTenantName] = useState("");
  const [newTenantType, setNewTenantType] = useState("General Contractor");
  const [editRole, setEditRole] = useState<"platform_super_admin" | "user">("user");
  const [editActive, setEditActive] = useState(true);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const selectedUser = users.find((u) => u.id === selectedUserId) ?? null;

  const api = getApiBaseUrl();
  function authHeaders() {
    return { "Content-Type": "application/json", Authorization: `Bearer ${getAccessToken()}` };
  }

  async function loadUsers() {
    const res = await fetch(`${api}/api/admin/users`, { headers: authHeaders() });
    if (res.ok) setUsers(await res.json());
  }

  async function loadTenants() {
    const res = await fetch(`${api}/api/admin/tenant-service-summary`, { headers: authHeaders() });
    if (res.ok) {
      const data = await res.json();
      setTenants((data.items ?? []).map((t: { tenant_id: string; tenant_name: string }) => ({ id: t.tenant_id, name: t.tenant_name })));
    }
  }

  async function loadRoleCatalog() {
    const res = await fetch(`${api}/api/admin/roles/catalog`, { headers: authHeaders() });
    if (!res.ok) {
      setRoleOptions(DEFAULT_ROLE_OPTIONS);
      if (!DEFAULT_ROLE_OPTIONS.includes(newRoleName)) {
        setNewRoleName(DEFAULT_ROLE_OPTIONS[0]);
      }
      return;
    }

    const catalog = (await res.json()) as string[];
    const options = catalog.length > 0 ? catalog : DEFAULT_ROLE_OPTIONS;
    setRoleOptions(options);
    if (!options.includes(newRoleName)) {
      setNewRoleName(options[0] || DEFAULT_ROLE_OPTIONS[0]);
    }
  }

  async function loadAdminData() {
    const [ovRes, insRes] = await Promise.all([
      fetch(`${api}/api/admin/overview`, { headers: authHeaders() }),
      fetch(`${api}/api/admin/service-insights`, { headers: authHeaders() }),
    ]);
    if (ovRes.ok) setOverview(await ovRes.json());
    if (insRes.ok) setInsights(await insRes.json());
    await loadUsers();
    await loadTenants();
    await loadRoleCatalog();
  }

  async function selectUser(user: AdminUser) {
    setSelectedUserId(user.id);
    setEditRole(user.platform_role);
    setEditActive(user.is_active);
    setNewPassword("");
    setMessage(null);
    const res = await fetch(`${api}/api/admin/users/${user.id}/memberships`, { headers: authHeaders() });
    if (res.ok) setMemberships(await res.json());
    else setMemberships([]);
  }

  async function saveAccess() {
    setMessage(null);
    if (!selectedUser) return;
    const res = await fetch(`${api}/api/admin/users/${selectedUser.id}/access`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ platform_role: editRole, is_active: editActive }),
    });
    if (res.ok) {
      setMessage({ text: "Access updated.", ok: true });
      await loadUsers();
    } else {
      const d = await res.json().catch(() => null);
      setMessage({ text: d?.detail || "Failed to update access.", ok: false });
    }
  }

  async function savePassword() {
    setMessage(null);
    if (!selectedUser) return;
    if (newPassword.trim().length < 8) {
      setMessage({ text: "Password must be at least 8 characters.", ok: false });
      return;
    }
    const res = await fetch(`${api}/api/admin/users/${selectedUser.id}/reset-password`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ new_password: newPassword.trim() }),
    });
    if (res.ok) {
      setNewPassword("");
      setMessage({ text: "Password reset.", ok: true });
    } else {
      const d = await res.json().catch(() => null);
      setMessage({ text: d?.detail || "Failed to reset password.", ok: false });
    }
  }

  async function assignRole() {
    setMessage(null);
    if (!selectedUser || !newTenantId) {
      setMessage({ text: "Select a tenant first.", ok: false });
      return;
    }
    const res = await fetch(`${api}/api/admin/users/${selectedUser.id}/memberships`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ tenant_id: newTenantId, role_name: newRoleName }),
    });
    if (res.ok) {
      setMessage({ text: `Role "${newRoleName}" assigned.`, ok: true });
      const r2 = await fetch(`${api}/api/admin/users/${selectedUser.id}/memberships`, { headers: authHeaders() });
      if (r2.ok) setMemberships(await r2.json());
    } else {
      const d = await res.json().catch(() => null);
      setMessage({ text: d?.detail || "Failed to assign role.", ok: false });
    }
  }

  async function removeMembership(membershipId: string, tenantId: string) {
    setMessage(null);
    if (!selectedUser) return;
    const res = await fetch(`${api}/api/admin/users/${selectedUser.id}/memberships/${membershipId}`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ tenant_id: tenantId, status: "inactive" }),
    });
    if (res.ok) {
      setMessage({ text: "Membership removed.", ok: true });
      const r2 = await fetch(`${api}/api/admin/users/${selectedUser.id}/memberships`, { headers: authHeaders() });
      if (r2.ok) setMemberships(await r2.json());
    } else {
      const d = await res.json().catch(() => null);
      setMessage({ text: d?.detail || "Failed to remove membership.", ok: false });
    }
  }

  async function createTenant() {
    setMessage(null);
    if (!newTenantName.trim()) {
      setMessage({ text: "Enter a tenant name first.", ok: false });
      return;
    }

    const res = await fetch(`${api}/api/admin/tenants`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        tenant_name: newTenantName.trim(),
        company_type: newTenantType,
        preferred_language: "en",
        selected_modules: ["Projects", "Budget", "Safety"],
      }),
    });

    if (!res.ok) {
      const d = await res.json().catch(() => null);
      setMessage({ text: d?.detail || "Failed to create tenant.", ok: false });
      return;
    }

    const payload = (await res.json()) as { tenant_id: string; tenant_name: string };
    setNewTenantName("");
    setMessage({ text: `Tenant "${payload.tenant_name}" created. You can now assign users to it.`, ok: true });
    await loadTenants();
    await loadAdminData();
  }

  useEffect(() => {
    setLocale(getLocale());
    fetch(`${api}/api/auth/me`, { headers: authHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((me) => {
        if (!me || me.platform_role !== "platform_super_admin") return;
        setAuthorized(true);
        loadAdminData();
      });
  }, []);

  return (
    <AppShell titleKey="platformAdmin.title">
      {!authorized ? (
        <p>{t(locale, "platformAdmin.denied")}</p>
      ) : (
        <>
          {/* Overview metrics */}
          <div className="grid" style={{ marginBottom: 16 }}>
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

          {/* Tenant creation */}
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ marginTop: 0 }}>Create Tenant</h3>
            <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
              Super Admin can create a new tenant workspace, then assign user memberships and roles.
            </p>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, minWidth: 240 }}>
                Tenant name
                <input value={newTenantName} onChange={(e) => setNewTenantName(e.target.value)} placeholder="New tenant name" />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, minWidth: 220 }}>
                Company type
                <input value={newTenantType} onChange={(e) => setNewTenantType(e.target.value)} placeholder="General Contractor" />
              </label>
              <button onClick={createTenant}>Create Tenant</button>
            </div>
          </div>

          {/* User management: list + detail panel */}
          <div style={{ display: "flex", gap: 16, alignItems: "flex-start", marginBottom: 16 }}>
            {/* Left: user list */}
            <div className="card" style={{ flex: "0 0 280px", minWidth: 220 }}>
              <h3 style={{ marginTop: 0 }}>All Users</h3>
              <div className="list" style={{ maxHeight: 480, overflowY: "auto" }}>
                {users.map((user) => (
                  <div
                    key={user.id}
                    className="list-item"
                    onClick={() => selectUser(user)}
                    style={{
                      cursor: "pointer",
                      background: selectedUserId === user.id ? "rgba(249,115,22,0.08)" : undefined,
                      borderLeft: selectedUserId === user.id ? "3px solid #f97316" : "3px solid transparent",
                      padding: "8px 10px",
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{user.display_name}</div>
                    <div className="muted" style={{ fontSize: 11 }}>{user.email}</div>
                    <div style={{ fontSize: 11, marginTop: 2 }}>
                      <span style={{
                        background: user.platform_role === "platform_super_admin" ? "#f97316" : "#64748b",
                        color: "#fff", borderRadius: 4, padding: "1px 6px", fontSize: 10,
                      }}>
                        {user.platform_role === "platform_super_admin" ? "Super Admin" : "User"}
                      </span>
                      {!user.is_active && (
                        <span style={{ marginLeft: 4, color: "#ef4444", fontSize: 10 }}>Inactive</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: detail panel */}
            <div className="card" style={{ flex: 1 }}>
              {!selectedUser ? (
                <p className="muted" style={{ marginTop: 0 }}>Select a user from the list to manage their access, password, and tenant roles.</p>
              ) : (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <h3 style={{ marginTop: 0, marginBottom: 2 }}>{selectedUser.display_name}</h3>
                      <div className="muted" style={{ fontSize: 13 }}>{selectedUser.email}</div>
                      {selectedUser.title && <div className="muted" style={{ fontSize: 12 }}>{selectedUser.title}</div>}
                    </div>
                    <button onClick={() => { setSelectedUserId(null); setMessage(null); }} style={{ fontSize: 12 }}>✕ Close</button>
                  </div>

                  {message && (
                    <div style={{ marginTop: 12, padding: "8px 12px", borderRadius: 6, fontSize: 13,
                      background: message.ok ? "#dcfce7" : "#fee2e2",
                      color: message.ok ? "#166534" : "#991b1b" }}>
                      {message.text}
                    </div>
                  )}

                  {/* Platform access */}
                  <div style={{ marginTop: 20, borderTop: "1px solid #e2e8f0", paddingTop: 16 }}>
                    <h4 style={{ marginTop: 0, marginBottom: 10 }}>Platform Access</h4>
                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
                      <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                        Role
                        <select value={editRole} onChange={(e) => setEditRole(e.target.value as AdminUser["platform_role"])}>
                          <option value="user">User</option>
                          <option value="platform_super_admin">Platform Super Admin</option>
                        </select>
                      </label>
                      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                        <input type="checkbox" checked={editActive} onChange={(e) => setEditActive(e.target.checked)} />
                        Active
                      </label>
                      <button onClick={saveAccess}>Save Access</button>
                    </div>
                  </div>

                  {/* Password reset */}
                  <div style={{ marginTop: 20, borderTop: "1px solid #e2e8f0", paddingTop: 16 }}>
                    <h4 style={{ marginTop: 0, marginBottom: 10 }}>Reset Password</h4>
                    <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
                      <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, flex: 1 }}>
                        New password
                        <input
                          type="password"
                          placeholder="Min. 8 characters"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                        />
                      </label>
                      <button onClick={savePassword}>Set Password</button>
                    </div>
                  </div>

                  {/* Tenant memberships */}
                  <div style={{ marginTop: 20, borderTop: "1px solid #e2e8f0", paddingTop: 16 }}>
                    <h4 style={{ marginTop: 0, marginBottom: 10 }}>Tenant Roles &amp; Modules</h4>

                    {/* Existing memberships */}
                    {memberships.filter((m) => m.status === "active").length === 0 ? (
                      <p className="muted" style={{ fontSize: 13 }}>No active tenant memberships. Use Tenant and Role/Module below to assign this user.</p>
                    ) : (
                      <div className="list" style={{ marginBottom: 12 }}>
                        {memberships.filter((m) => m.status === "active").map((m) => (
                          <div key={m.membership_id} className="list-item" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 10px" }}>
                            <div>
                              <span style={{ fontWeight: 600, fontSize: 13 }}>{m.tenant_name}</span>
                              <span style={{ marginLeft: 8, background: "#e2e8f0", borderRadius: 4, padding: "1px 7px", fontSize: 11 }}>{m.role_name}</span>
                            </div>
                            <button
                              onClick={() => removeMembership(m.membership_id, m.tenant_id)}
                              style={{ fontSize: 11, padding: "2px 8px", background: "#fee2e2", color: "#991b1b", border: "none", borderRadius: 4, cursor: "pointer" }}
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Assign new membership */}
                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
                      <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                        Tenant
                        <select value={newTenantId} onChange={(e) => setNewTenantId(e.target.value)}>
                          <option value="">— select tenant —</option>
                          {tenants.map((ten) => (
                            <option key={ten.id} value={ten.id}>{ten.name}</option>
                          ))}
                        </select>
                      </label>
                      <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                        Role / Module
                        <select value={newRoleName} onChange={(e) => setNewRoleName(e.target.value)}>
                          {roleOptions.map((r) => (
                            <option key={r} value={r}>{r}</option>
                          ))}
                        </select>
                      </label>
                      <button onClick={assignRole}>Assign Role</button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Service Insights */}
          <div className="card">
            <h3>Service Insights</h3>
            <p className="muted">Platform-wide operational data to guide improvements.</p>
            <div className="grid">
              <div className="card">Tickets<div className="metric">{insights?.tickets ?? 0}</div></div>
              <div className="card">Intake Items<div className="metric">{insights?.intake_items ?? 0}</div></div>
              <div className="card">Intake Needs Review<div className="metric">{insights?.intake_needs_review ?? 0}</div></div>
              <div className="card">Pending Extractions<div className="metric">{(insights?.extractions_pending_review ?? 0) + (insights?.extractions_review_submitted ?? 0)}</div></div>
              <div className="card">Unresolved Extraction Issues<div className="metric">{insights?.unresolved_extraction_issues ?? 0}</div></div>
              <div className="card">Failed Integration Events<div className="metric">{insights?.integration_events_failed ?? 0}</div></div>
            </div>
            {(insights?.opportunities ?? []).length > 0 && (
              <>
                <h3 style={{ marginTop: 16 }}>Improvement Opportunities</h3>
                <div className="list">
                  {(insights?.opportunities ?? []).map((o) => (
                    <div className="list-item" key={o}>{o}</div>
                  ))}
                </div>
              </>
            )}
          </div>
        </>
      )}
    </AppShell>
  );
}
