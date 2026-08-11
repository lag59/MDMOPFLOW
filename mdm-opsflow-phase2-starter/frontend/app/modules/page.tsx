"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getLocale, t } from "@/lib/i18n";
import { MODULE_ROUTE_MAP, buildModuleDetailHref, getVisibleWorkspacesForRole } from "@/lib/modules";
import { getCurrentRoleAccess } from "@/lib/roleAccess";
import { type RoleKey } from "@/lib/roles";

export default function ModulesPage() {
  const locale = getLocale();
  const [activeRole, setActiveRole] = useState<RoleKey>("project_manager");
  const [assignedRoles, setAssignedRoles] = useState<RoleKey[]>(["project_manager"]);
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);

  useEffect(() => {
    const resolveAccess = async () => {
      const context = await getCurrentRoleAccess();
      if (!context) {
        window.location.href = "/login";
        return;
      }
      setActiveRole(context.roleKey);
      setAssignedRoles(context.roleKeys);
      setIsSuperAdmin(context.isSuperAdmin);
    };

    resolveAccess();
  }, []);

  const visibleWorkspaces = getVisibleWorkspacesForRole(assignedRoles, isSuperAdmin);

  return (
    <AppShell titleKey="modules.title">
      <div className="card">
        <h2>{t(locale, "modules.title")}</h2>
        <p>{t(locale, "modules.subtitle")}</p>
      </div>

      <div className="grid">
        {visibleWorkspaces.map((workspace) => (
          <div className="card" key={workspace.key}>
            <div className="flex items-center justify-between gap-2">
              <span className="auth-eyebrow">{workspace.label}</span>
              {workspace.key === activeRole ? (
                <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-1 text-xs font-semibold text-blue-800">
                  Current Role
                </span>
              ) : (
                <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                  Assigned Role
                </span>
              )}
            </div>
            <h3>{workspace.summary}</h3>
            <ul className="space-y-3">
              {workspace.modules.map((module) => (
                <li key={module} className="rounded-lg border border-slate-200 p-3">
                  {MODULE_ROUTE_MAP[module] ? (() => {
                    return (
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center justify-between gap-2">
                        <Link href={buildModuleDetailHref(workspace.key, module)} className="font-semibold text-blue-700 hover:text-blue-900 hover:underline">
                          {module}
                        </Link>
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold ${
                            MODULE_ROUTE_MAP[module].status === "live"
                              ? "bg-green-100 text-green-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {MODULE_ROUTE_MAP[module].status === "live" ? "Live" : "Bridge"}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600">{MODULE_ROUTE_MAP[module].helperText}</p>
                      {workspace.key !== activeRole && !isSuperAdmin ? (
                        <p className="text-xs text-slate-500">This workspace is available through your assigned role access.</p>
                      ) : null}
                    </div>
                    );
                  })() : (
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-700">{module}</span>
                      <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                        Planned
                      </span>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </AppShell>
  );
}