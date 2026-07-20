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
      <div className="card">
        <h3>{t(locale, "dashboard.welcome")}</h3>
        <p>{t(locale, "dashboard.subtitle")}</p>
      </div>
      <div className="grid">
        <div className="card">
          {t(locale, "dashboard.activeProjects")}
          <div className="metric">{projects.length}</div>
          <div className="metric-note">Across all active tenant jobs</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.documentsProcessed")}
          <div className="metric">1284</div>
          <div className="metric-note">Last 30 days of intake and review</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.budgetHealth")}
          <div className="metric">92%</div>
          <div className="metric-note">On-track and protected by approvals</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.pendingReviews")}
          <div className="metric">8</div>
          <div className="metric-note">AI suggested priority review queue</div>
        </div>
      </div>

      <div className="stats-strip">
        <div className="mini-stat">
          <strong>$2.45M</strong>
          <span>Revenue MTD</span>
        </div>
        <div className="mini-stat">
          <strong>96%</strong>
          <span>Safety Compliance</span>
        </div>
        <div className="mini-stat">
          <strong>89%</strong>
          <span>Equipment Utilization</span>
        </div>
        <div className="mini-stat">
          <strong>14</strong>
          <span>AI Action Cards</span>
        </div>
      </div>
    </AppShell>
  );
}
