"use client";

import AppShell from "@/components/AppShell";
import { ROLE_WORKSPACES } from "@/lib/roles";
import { getLocale, t } from "@/lib/i18n";

export default function ModulesPage() {
  const locale = getLocale();

  return (
    <AppShell titleKey="modules.title">
      <div className="card">
        <h2>{t(locale, "modules.title")}</h2>
        <p>{t(locale, "modules.subtitle")}</p>
      </div>

      <div className="grid">
        {ROLE_WORKSPACES.map((workspace) => (
          <div className="card" key={workspace.key}>
            <span className="auth-eyebrow">{workspace.label}</span>
            <h3>{workspace.summary}</h3>
            <ul>
              {workspace.modules.map((module) => (
                <li key={module}>{module}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </AppShell>
  );
}