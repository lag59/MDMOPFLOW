"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

type Project = {
  id: string;
  project_name: string;
  project_number: string;
  status: string;
};

type ProjectProfitability = {
  project_id: string;
  project_name: string;
  status: string;
  contract_amount: number;
  actual_revenue: number;
  actual_cost: number;
  gross_profit: number;
  profit_margin: number;
  cost_overrun: boolean;
  revenue_shortfall: boolean;
  ticket_count: number;
};

export default function ProjectsPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [projects, setProjects] = useState<Project[]>([]);
  const [profitability, setProfitability] = useState<Map<string, ProjectProfitability>>(new Map());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLocale(getLocale());
    const token = getAccessToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    const fetchProjects = async () => {
      try {
        const headers = {
          Authorization: `Bearer ${token}`,
          "X-Tenant-ID": getTenantId(),
        };

        // Fetch projects list
        const res = await fetch(`${getApiBaseUrl()}/api/projects`, { headers });
        const data = (res.ok ? await res.json() : []) as Project[];
        setProjects(data);

        // Fetch profitability for each project
        const profitMap = new Map<string, ProjectProfitability>();
        for (const project of data) {
          try {
            const profRes = await fetch(
              `${getApiBaseUrl()}/api/projects/${project.id}/profitability`,
              { headers }
            );
            if (profRes.ok) {
              const profData = await profRes.json();
              profitMap.set(project.id, profData);
            }
          } catch (e) {
            // Silently skip if profitability fetch fails
            console.error(`Failed to fetch profitability for ${project.id}`);
          }
        }
        setProfitability(profitMap);
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  const getProfitMarginColor = (margin: number): string => {
    if (margin >= 20) return "text-green-700";
    if (margin >= 10) return "text-amber-600";
    return "text-red-600";
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);
  };

  return (
    <AppShell titleKey="projects.title">
      <div className="section-header">
        <h3>{t(locale, "projects.title")}</h3>
        <Link className="link-button" href="/projects/new">
          {t(locale, "projects.new")}
        </Link>
      </div>

      {loading ? (
        <div className="p-4 text-slate-600">Loading projects...</div>
      ) : (
        <div className="space-y-3">
          {projects.map((project) => {
            const prof = profitability.get(project.id);
            return (
              <Link
                href={`/projects/${project.id}/dashboard`}
                key={project.id}
                className="group block p-4 border-2 border-slate-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 hover:shadow-lg transition-all duration-200 cursor-pointer bg-white"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <strong className="text-lg text-slate-900 group-hover:text-blue-700 transition-colors">{project.project_name}</strong>
                      <span className="opacity-0 group-hover:opacity-100 transition-opacity text-blue-500">→</span>
                    </div>
                    <div className="text-sm text-slate-600 mt-1 group-hover:text-slate-700 transition-colors">{project.project_number}</div>
                    {prof && (
                      <div className="flex gap-6 mt-3 text-sm">
                        <div>
                          <span className="text-slate-500">Revenue:</span>
                          <span className="ml-2 font-semibold text-slate-900">
                            {formatCurrency(prof.actual_revenue)}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500">Cost:</span>
                          <span className="ml-2 font-semibold text-slate-900">
                            {formatCurrency(prof.actual_cost)}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500">Profit:</span>
                          <span className="ml-2 font-semibold text-slate-900">
                            {formatCurrency(prof.gross_profit)}
                          </span>
                        </div>
                        <div>
                          <span className={`font-bold ${getProfitMarginColor(prof.profit_margin)}`}>
                            {prof.profit_margin.toFixed(1)}% margin
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    {prof?.cost_overrun && (
                      <div className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-semibold">
                        ⚠️ Over Budget
                      </div>
                    )}
                    {prof?.revenue_shortfall && (
                      <div className="px-2 py-1 bg-amber-100 text-amber-700 rounded text-xs font-semibold">
                        📉 Shortfall
                      </div>
                    )}
                    <span className={`status-pill status-${project.status}`}>
                      {project.status.replace("_", " ")}
                    </span>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        window.location.href = `/projects/${project.id}/tickets`;
                      }}
                      className="px-3 py-2 bg-blue-600 text-white rounded font-semibold hover:bg-blue-700 hover:shadow-md transition-all duration-200 cursor-pointer inline-flex items-center gap-1 active:scale-95"
                      title="Click to view all tickets assigned to this project"
                    >
                      📋 View Tickets
                    </button>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
