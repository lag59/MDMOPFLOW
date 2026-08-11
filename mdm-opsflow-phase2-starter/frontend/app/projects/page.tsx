"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

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

function dedupeProjects(items: Project[]): Project[] {
  const byId = new Map<string, Project>();
  for (const item of items) {
    if (!byId.has(item.id)) {
      byId.set(item.id, item);
    }
  }
  return Array.from(byId.values());
}

export default function ProjectsPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [projects, setProjects] = useState<Project[]>([]);
  const [profitability, setProfitability] = useState<Map<string, ProjectProfitability>>(new Map());
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  const summary = useMemo(() => {
    const totalProjects = projects.length;
    const activeProjects = projects.filter((project) => project.status === "active").length;
    const atRiskProjects = Array.from(profitability.values()).filter((item) => item.cost_overrun || item.revenue_shortfall).length;
    const totalRevenue = Array.from(profitability.values()).reduce((acc, item) => acc + Number(item.actual_revenue || 0), 0);

    return {
      totalProjects,
      activeProjects,
      atRiskProjects,
      totalRevenue,
    };
  }, [projects, profitability]);

  const filteredProjects = useMemo(() => {
    const search = query.trim().toLowerCase();
    if (!search) return projects;
    return projects.filter((project) => {
      const p = profitability.get(project.id);
      return (
        project.project_name.toLowerCase().includes(search) ||
        project.project_number.toLowerCase().includes(search) ||
        project.status.toLowerCase().includes(search) ||
        (p?.cost_overrun ? "over budget" : "").includes(search) ||
        (p?.revenue_shortfall ? "shortfall" : "").includes(search)
      );
    });
  }, [projects, profitability, query]);

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
        const uniqueProjects = dedupeProjects(data);
        setProjects(uniqueProjects);

        // Fetch profitability for each project
        const profitMap = new Map<string, ProjectProfitability>();
        for (const project of uniqueProjects) {
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
      <div className="card">
        <span className="auth-eyebrow">Project module</span>
        <h2>{t(locale, "projects.title")}</h2>
        <p className="muted">Track project setup, budget context, profitability, and ticket flow from one place.</p>
        <div className="top-actions" style={{ marginTop: "1rem", flexWrap: "wrap" }}>
          <Link className="link-button" href="/projects/new">
            {t(locale, "projects.new")}
          </Link>
          <Link className="link-button" href="/ticket-manager">
            Ticket manager
          </Link>
          <Link className="link-button" href="/modules">
            Back to modules
          </Link>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <span className="auth-eyebrow">Portfolio</span>
          <div className="metric">{summary.totalProjects}</div>
          <div className="metric-note">Projects in the tenant portfolio</div>
        </div>
        <div className="card">
          <span className="auth-eyebrow">Active work</span>
          <div className="metric">{summary.activeProjects}</div>
          <div className="metric-note">Projects currently marked active</div>
        </div>
        <div className="card">
          <span className="auth-eyebrow">At risk</span>
          <div className="metric">{summary.atRiskProjects}</div>
          <div className="metric-note">Projects with profitability warnings</div>
        </div>
        <div className="card">
          <span className="auth-eyebrow">Revenue tracked</span>
          <div className="metric">
            {new Intl.NumberFormat("en-US", {
              style: "currency",
              currency: "USD",
              notation: "compact",
              maximumFractionDigits: 1,
            }).format(summary.totalRevenue)}
          </div>
          <div className="metric-note">Aggregated from project profitability records</div>
        </div>
      </div>

      <div className="card">
        <div className="section-header">
          <div>
            <h3>Project workspace</h3>
            <p className="muted">Open a project, inspect profitability, or jump to its ticket view.</p>
          </div>
          <Link className="link-button" href="/projects/new">
            {t(locale, "projects.new")}
          </Link>
        </div>

      <label className="text-sm font-medium text-slate-700">
        Find project
        <input
          className="mt-1"
          placeholder="Search by name, number, status, or risk"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>

      {loading ? (
        <div className="p-4 text-slate-600">Loading projects...</div>
      ) : (
        <div className="space-y-3">
          {filteredProjects.map((project) => {
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
          {filteredProjects.length === 0 ? <p className="p-4 text-slate-600">No projects match that filter.</p> : null}
        </div>
      )}
      </div>
    </AppShell>
  );
}
