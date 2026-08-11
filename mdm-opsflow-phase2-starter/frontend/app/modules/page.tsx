"use client";

import Link from "next/link";
import React, { useEffect, useMemo, useState } from "react";

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
  const [query, setQuery] = useState("");

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
  const filteredWorkspaces = useMemo(() => {
    const search = query.trim().toLowerCase();
    if (!search) return visibleWorkspaces;
    return visibleWorkspaces
      .map((workspace) => ({
        ...workspace,
        modules: workspace.modules.filter((module) => {
          const moduleMeta = MODULE_ROUTE_MAP[module];
          return (
            module.toLowerCase().includes(search) ||
            workspace.label.toLowerCase().includes(search) ||
            (moduleMeta?.helperText || "").toLowerCase().includes(search)
          );
        }),
      }))
      .filter((workspace) => workspace.modules.length > 0);
  }, [query, visibleWorkspaces]);

  const liveCount = useMemo(() => visibleWorkspaces.flatMap((workspace) => workspace.modules).filter((module) => MODULE_ROUTE_MAP[module]?.status === "live").length, [visibleWorkspaces]);
  const bridgeCount = useMemo(() => visibleWorkspaces.flatMap((workspace) => workspace.modules).filter((module) => MODULE_ROUTE_MAP[module]?.status === "bridge").length, [visibleWorkspaces]);

  return (
    <AppShell titleKey="modules.title">
      <div className="card">
        <h2>{t(locale, "modules.title")}</h2>
        <p>{t(locale, "modules.subtitle")}</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Assigned Workspaces</div>
            <div className="mt-1 text-2xl font-bold text-slate-900">{visibleWorkspaces.length}</div>
          </div>
          <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
            <div className="text-xs font-semibold uppercase tracking-wide text-green-700">Live Modules</div>
            <div className="mt-1 text-2xl font-bold">{liveCount}</div>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">Bridge Modules</div>
            <div className="mt-1 text-2xl font-bold">{bridgeCount}</div>
          </div>
        </div>
        <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
          Start tip: open your Current Role first, then work from top to bottom in that workspace.
        </div>
        <div className="mt-3">
          <label className="text-sm font-medium text-slate-700">
            Find a module quickly
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="mt-1"
              placeholder="Search by module name, workspace, or helper text"
            />
          </label>
        </div>
      </div>

      <div className="grid">
        {filteredWorkspaces.map((workspace) => (
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
        {filteredWorkspaces.length === 0 ? (
          <div className="card">
            <h3 className="text-base font-semibold text-slate-900">No matching modules</h3>
            <p className="mt-1 text-sm text-slate-600">Try a shorter search term or clear the search box to show all modules.</p>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}