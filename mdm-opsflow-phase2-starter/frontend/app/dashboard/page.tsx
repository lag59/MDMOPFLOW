"use client";

import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

type Project = {
  id: string;
  project_name: string;
  status: string;
};

export default function DashboardPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    setLocale(getLocale());
    const token = getAccessToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    fetch(`${getApiBaseUrl()}/api/projects`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-ID": getTenantId(),
      },
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setProjects(data));
  }, []);

  return (
    <AppShell titleKey="dashboard.title">
      <p>{t(locale, "dashboard.subtitle")}</p>
      <div className="grid">
        <div className="card">
          {t(locale, "dashboard.activeProjects")}
          <div className="metric">{projects.length}</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.documentsProcessed")}
          <div className="metric">1284</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.budgetHealth")}
          <div className="metric">92%</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.pendingReviews")}
          <div className="metric">8</div>
        </div>
      </div>
    </AppShell>
  );
}
