"use client";

import { useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";
import { ROLE_WORKSPACES, RoleKey, mapBackendRole } from "@/lib/roles";

type MeMembership = {
  role_name: string;
};

type MeResponse = {
  platform_role: string;
  memberships: MeMembership[];
};

export default function WorkspacePage() {
  const locale = getLocale();
  const [activeRole, setActiveRole] = useState<RoleKey>("project_manager");
  const [canPreviewAllRoles, setCanPreviewAllRoles] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    fetch(`${getApiBaseUrl()}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((me: MeResponse | null) => {
        if (!me) {
          return;
        }

        const mapped = mapBackendRole(me.platform_role, me.memberships?.[0]?.role_name);
        setActiveRole(mapped);
        setCanPreviewAllRoles(me.platform_role === "platform_super_admin");
      });
  }, []);

  const current = useMemo(() => ROLE_WORKSPACES.find((item) => item.key === activeRole) || ROLE_WORKSPACES[0], [activeRole]);

  return (
    <AppShell titleKey="workspace.title">
      <div className="card">
        <span className="auth-eyebrow">{t(locale, "workspace.roleWorkspace")}</span>
        <h2>{current.label}</h2>
        <p>{current.summary}</p>

        {canPreviewAllRoles ? (
          <label>
            {t(locale, "workspace.rolePreview")}
            <select value={activeRole} onChange={(e) => setActiveRole(e.target.value as RoleKey)}>
              {ROLE_WORKSPACES.map((role) => (
                <option key={role.key} value={role.key}>
                  {role.label}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      <div className="workspace-grid">
        {current.modules.map((module) => (
          <div className="workspace-module" key={module}>
            <strong>{module}</strong>
            <span>{t(locale, "workspace.moduleReady")}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>{t(locale, "workspace.allRoleWorkspaces")}</h3>
        <div className="workspace-chip-row">
          {ROLE_WORKSPACES.map((role) => (
            <button key={role.key} className={`workspace-chip ${activeRole === role.key ? "is-active" : ""}`} onClick={() => setActiveRole(role.key)}>
              {role.label}
            </button>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
