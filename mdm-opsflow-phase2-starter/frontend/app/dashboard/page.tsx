"use client";

import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";
import { ReplayTokenStateAlerts, fetchReplayTokenStateAlerts } from "@/lib/replayTokens";
import { MaterialDensityPreset, Ticket, listMaterialDensityPresets, listTickets } from "@/lib/tickets";

type Project = {
  id: string;
  project_name: string;
  status: string;
};

export default function DashboardPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [projects, setProjects] = useState<Project[]>([]);
  const [alerts, setAlerts] = useState<ReplayTokenStateAlerts | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [densityPresets, setDensityPresets] = useState<MaterialDensityPreset[]>([]);

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

    fetchReplayTokenStateAlerts({
      staleThresholdMinutes: 60,
      staleActiveThresholdCount: 10,
    })
      .then((data) => setAlerts(data))
      .catch(() => {
        setAlerts(null);
      });

    listTickets()
      .then((data) => setTickets(data))
      .catch(() => {
        setTickets([]);
      });

    listMaterialDensityPresets()
      .then((data) => setDensityPresets(data))
      .catch(() => {
        setDensityPresets([]);
      });
  }, []);

  const consumedRevokedRatio =
    alerts?.consumed_to_revoked_ratio === null || alerts?.consumed_to_revoked_ratio === undefined
      ? "n/a"
      : alerts.consumed_to_revoked_ratio.toFixed(2);

  const materialCounts = tickets.reduce<Record<string, number>>((acc, ticket) => {
    const material = ticket.material.trim();
    if (!material) {
      return acc;
    }
    acc[material] = (acc[material] || 0) + 1;
    return acc;
  }, {});

  const topMaterials = Object.entries(materialCounts)
    .sort((a, b) => {
      if (b[1] !== a[1]) {
        return b[1] - a[1];
      }
      return a[0].localeCompare(b[0]);
    })
    .slice(0, 3);

  const normalizedPresetMap = new Map(
    densityPresets.map((preset) => [preset.material_name.trim().toLowerCase(), preset.density_tons_per_cubic_yard])
  );
  const distinctMaterialCount = Object.keys(materialCounts).length;
  const effectivePresetCount = Object.keys(materialCounts).filter((name) => normalizedPresetMap.has(name.toLowerCase())).length;

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
          <div className="metric">{alerts?.total_tokens ?? "-"}</div>
          <div className="metric-note">Replay export tokens in current alert window</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.budgetHealth")}
          <div className="metric">{consumedRevokedRatio}</div>
          <div className="metric-note">Consumed to revoked token ratio</div>
        </div>
        <div className="card">
          {t(locale, "dashboard.pendingReviews")}
          <div className="metric">{alerts?.active_tokens_older_than_threshold ?? "-"}</div>
          <div className="metric-note">Active tokens older than 60 minutes</div>
        </div>
        <div className="card">
          Material intelligence
          <div className="metric">{effectivePresetCount}/{distinctMaterialCount}</div>
          <div className="metric-note">materials currently covered by density presets</div>
          {topMaterials.length === 0 ? (
            <div className="metric-note">No ticket materials yet.</div>
          ) : (
            topMaterials.map(([material, count]) => {
              const density = normalizedPresetMap.get(material.toLowerCase()) || "n/a";
              return (
                <div className="metric-note" key={material}>
                  {material}: {count} ticket(s) | density {density}
                </div>
              );
            })
          )}
        </div>
      </div>

      {alerts?.active_tokens_older_than_threshold_exceeded ? (
        <div className="card warning-card">
          <strong>Replay token alert</strong>
          <p>
            Threshold exceeded: {alerts.active_tokens_older_than_threshold} active tokens older than
            {" "}
            {alerts.stale_threshold_minutes} minutes (limit {alerts.stale_active_threshold_count}).
          </p>
        </div>
      ) : null}

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
