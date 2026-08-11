"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

// ── types ────────────────────────────────────────────────────────────────────

type Project = {
  id: string;
  project_name: string;
  project_number: string;
  customer: string;
  address: string;
  project_manager: string;
  start_date: string | null;
  end_date: string | null;
  contract_amount: string | null;
  budget: string | null;
  status: string;
  description: string;
  created_at: string;
};

type Ticket = {
  id: string;
  ticket_number: string;
  project_id: string | null;
  material: string;
  quantity: string;
  unit: string;
  status: string;
  notes: string;
  created_at: string;
};

type ProjectCost = {
  project_id: string;
  labor_cost: string;
  material_cost: string;
  equipment_cost: string;
  overhead_cost: string;
  total_cost: string;
};

type CreateProjectForm = {
  project_name: string;
  project_number: string;
  customer: string;
  address: string;
  project_manager: string;
  start_date: string;
  end_date: string;
  contract_amount: string;
  budget: string;
  status: string;
  description: string;
};

const STATUS_COLORS: Record<string, string> = {
  planning:   "#2563eb",
  active:     "#16a34a",
  on_hold:    "#d97706",
  complete:   "#7c3aed",
  cancelled:  "#dc2626",
};

const fmt = (n: string | number | null | undefined) =>
  !n || n === "0" ? "—" : Number(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const BLANK_FORM: CreateProjectForm = {
  project_name: "", project_number: "", customer: "", address: "",
  project_manager: "", start_date: "", end_date: "",
  contract_amount: "", budget: "", status: "planning", description: "",
};

type View = "list" | "create" | "detail";
type DetailTab = "overview" | "tickets" | "costs";

// ── component ────────────────────────────────────────────────────────────────

export default function ProjectManagerPage() {
  const [projects, setProjects]     = useState<Project[]>([]);
  const [selected, setSelected]     = useState<Project | null>(null);
  const [tickets, setTickets]       = useState<Ticket[]>([]);
  const [costs, setCosts]           = useState<ProjectCost | null>(null);
  const [view, setView]             = useState<View>("list");
  const [tab, setTab]               = useState<DetailTab>("overview");
  const [form, setForm]             = useState<CreateProjectForm>(BLANK_FORM);
  const [saving, setSaving]         = useState(false);
  const [msg, setMsg]               = useState<{ text: string; ok: boolean } | null>(null);
  const [search, setSearch]         = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const api    = getApiBaseUrl();
  const token  = getAccessToken();
  const tenant = getTenantId();

  function headers() {
    return { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "X-Tenant-ID": tenant };
  }

  async function loadProjects() {
    const r = await fetch(`${api}/api/projects`, { headers: headers() });
    if (r.ok) setProjects(await r.json());
  }

  async function loadProjectDetail(project: Project) {
    setSelected(project);
    setView("detail");
    setTab("overview");
    setMsg(null);

    // Load tickets for this project
    const tr = await fetch(`${api}/api/projects/${project.id}/tickets`, { headers: headers() });
    if (tr.ok) setTickets(await tr.json());

    // Load cost summary
    const cr = await fetch(`${api}/api/projects/${project.id}/costs`, { headers: headers() });
    if (cr.ok) setCosts(await cr.json());
  }

  useEffect(() => {
    if (!token) { window.location.href = "/login"; return; }
    loadProjects();
  }, []);

  // ── derived counts
  const counts = {
    active:   projects.filter(p => p.status === "active").length,
    planning: projects.filter(p => p.status === "planning").length,
    onHold:   projects.filter(p => p.status === "on_hold").length,
    complete: projects.filter(p => p.status === "complete").length,
  };

  const filtered = projects.filter(p => {
    const matchesSearch = !search || p.project_name.toLowerCase().includes(search.toLowerCase()) ||
      p.project_number.toLowerCase().includes(search.toLowerCase()) ||
      (p.customer || "").toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // ── create project
  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.project_name.trim() || !form.project_number.trim()) {
      setMsg({ text: "Project name and number are required.", ok: false });
      return;
    }
    setSaving(true); setMsg(null);
    const body = {
      ...form,
      contract_amount: form.contract_amount || null,
      budget: form.budget || null,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
    };
    const r = await fetch(`${api}/api/projects`, { method: "POST", headers: headers(), body: JSON.stringify(body) });
    setSaving(false);
    if (r.ok) {
      const created: Project = await r.json();
      setProjects(prev => [created, ...prev]);
      setForm(BLANK_FORM);
      await loadProjectDetail(created);
      setMsg({ text: "Project created.", ok: true });
    } else {
      const d = await r.json().catch(() => null);
      setMsg({ text: d?.detail || "Failed to create project.", ok: false });
    }
  }

  // ── update project status
  async function updateStatus(projectId: string, newStatus: string) {
    const r = await fetch(`${api}/api/projects/${projectId}`, {
      method: "PATCH", headers: headers(), body: JSON.stringify({ status: newStatus }),
    });
    if (r.ok) {
      const updated: Project = await r.json();
      setProjects(prev => prev.map(p => p.id === updated.id ? updated : p));
      setSelected(updated);
      setMsg({ text: `Status updated to ${newStatus}.`, ok: true });
    } else {
      setMsg({ text: "Status update failed.", ok: false });
    }
  }

  const statusPill = (status: string) => (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 999, fontSize: 11, fontWeight: 700,
      background: (STATUS_COLORS[status] ?? "#64748b") + "22",
      color: STATUS_COLORS[status] ?? "#64748b",
      border: `1px solid ${STATUS_COLORS[status] ?? "#cbd5e1"}`,
      textTransform: "capitalize",
    }}>{status.replace("_", " ")}</span>
  );

  return (
    <AppShell titleKey="nav.projectManager">
      {/* ── Metrics */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(4,1fr)", marginBottom: 20 }}>
        {[
          { label: "Active",   value: counts.active,   color: "#16a34a" },
          { label: "Planning", value: counts.planning,  color: "#2563eb" },
          { label: "On Hold",  value: counts.onHold,    color: "#d97706" },
          { label: "Complete", value: counts.complete,  color: "#7c3aed" },
        ].map(m => (
          <div className="card" key={m.label}>
            <div className="metric-note">{m.label} Projects</div>
            <div className="metric" style={{ color: m.color }}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* ── Feedback */}
      {msg && (
        <div style={{ marginBottom: 14, padding: "9px 14px", borderRadius: 8, fontSize: 13,
          background: msg.ok ? "#dcfce7" : "#fee2e2", color: msg.ok ? "#166534" : "#991b1b" }}>
          {msg.text}
        </div>
      )}

      {/* ── Main layout */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>

        {/* Left panel: project list */}
        <div className="card" style={{ flex: "0 0 300px", minWidth: 260 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <h3 style={{ margin: 0, fontSize: 15 }}>Projects ({filtered.length})</h3>
            <button onClick={() => { setView("create"); setSelected(null); setMsg(null); }}
              style={{ fontSize: 12, padding: "5px 10px" }}>+ New</button>
          </div>

          {/* Filters */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 }}>
            <input placeholder="Search projects…" value={search}
              onChange={e => setSearch(e.target.value)} style={{ fontSize: 12, padding: "6px 10px" }} />
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              style={{ fontSize: 12, padding: "6px 10px" }}>
              <option value="all">All statuses</option>
              <option value="planning">Planning</option>
              <option value="active">Active</option>
              <option value="on_hold">On Hold</option>
              <option value="complete">Complete</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          <div className="list" style={{ maxHeight: 520, overflowY: "auto", marginTop: 0 }}>
            {filtered.length === 0 && <p className="muted" style={{ fontSize: 13 }}>No projects found.</p>}
            {filtered.map(p => (
              <div key={p.id} className="list-item"
                onClick={() => loadProjectDetail(p)}
                style={{ cursor: "pointer",
                  background: selected?.id === p.id ? "rgba(249,115,22,0.06)" : undefined,
                  borderLeft: selected?.id === p.id ? "3px solid #f97316" : "3px solid transparent",
                  padding: "9px 12px" }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{p.project_name}</div>
                <div className="muted" style={{ fontSize: 11 }}>{p.project_number} · {p.customer || "—"}</div>
                <div style={{ marginTop: 4, display: "flex", gap: 6, alignItems: "center" }}>
                  {statusPill(p.status)}
                  {p.contract_amount && (
                    <span style={{ fontSize: 11, color: "#16a34a" }}>{fmt(p.contract_amount)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel */}
        <div className="card" style={{ flex: 1, minWidth: 0 }}>

          {/* Create form */}
          {view === "create" && (
            <form onSubmit={handleCreate}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <h3 style={{ margin: 0 }}>New Project</h3>
                <button type="button" className="btn-ghost" onClick={() => setView("list")} style={{ fontSize: 12 }}>✕ Cancel</button>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {([
                  ["Project Name *",   "project_name",    "text"],
                  ["Project Number *", "project_number",  "text"],
                  ["Customer",         "customer",        "text"],
                  ["Address",          "address",         "text"],
                  ["Project Manager",  "project_manager", "text"],
                  ["Start Date",       "start_date",      "date"],
                  ["End Date",         "end_date",        "date"],
                  ["Contract Amount",  "contract_amount", "number"],
                  ["Budget",           "budget",          "number"],
                ] as [string, keyof CreateProjectForm, string][]).map(([label, key, type]) => (
                  <label key={key} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                    {label}
                    <input type={type} value={form[key]}
                      onChange={e => setForm(prev => ({ ...prev, [key]: e.target.value }))} />
                  </label>
                ))}
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Status
                  <select value={form.status} onChange={e => setForm(prev => ({ ...prev, status: e.target.value }))}>
                    <option value="planning">Planning</option>
                    <option value="active">Active</option>
                    <option value="on_hold">On Hold</option>
                  </select>
                </label>
              </div>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, marginTop: 12 }}>
                Description
                <textarea rows={3} value={form.description}
                  onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))} />
              </label>
              <div style={{ marginTop: 14, display: "flex", gap: 8 }}>
                <button type="submit" disabled={saving}>{saving ? "Saving…" : "Create Project"}</button>
                <button type="button" className="btn-ghost" onClick={() => setView("list")}>Cancel</button>
              </div>
            </form>
          )}

          {/* Detail view */}
          {view === "detail" && selected && (
            <>
              {/* Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                <div>
                  <h3 style={{ margin: 0, marginBottom: 2 }}>{selected.project_name}</h3>
                  <div className="muted" style={{ fontSize: 12 }}>{selected.project_number} · {selected.customer || "—"}</div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  {statusPill(selected.status)}
                  {/* Status transitions */}
                  {selected.status === "planning" && (
                    <button onClick={() => updateStatus(selected.id, "active")} style={{ fontSize: 12, padding: "5px 12px" }}>
                      Start Project →
                    </button>
                  )}
                  {selected.status === "active" && (
                    <>
                      <button onClick={() => updateStatus(selected.id, "on_hold")} className="btn-ghost"
                        style={{ fontSize: 12, padding: "5px 10px" }}>Pause</button>
                      <button onClick={() => updateStatus(selected.id, "complete")}
                        style={{ fontSize: 12, padding: "5px 12px", background: "linear-gradient(135deg,#7c3aed,#6d28d9)" }}>
                        Mark Complete ✓
                      </button>
                    </>
                  )}
                  {selected.status === "on_hold" && (
                    <button onClick={() => updateStatus(selected.id, "active")} style={{ fontSize: 12, padding: "5px 12px" }}>
                      Resume →
                    </button>
                  )}
                </div>
              </div>

              {/* Tab bar */}
              <div style={{ display: "flex", gap: 4, margin: "16px 0 0", borderBottom: "1px solid #e2e8f0" }}>
                {(["overview","tickets","costs"] as DetailTab[]).map(t => (
                  <button key={t} onClick={() => setTab(t)} className={tab === t ? "" : "btn-ghost"}
                    style={{ fontSize: 12, padding: "6px 14px", borderRadius: "8px 8px 0 0",
                      borderBottom: tab === t ? "2px solid #f97316" : "2px solid transparent",
                      textTransform: "capitalize" }}>
                    {t}
                  </button>
                ))}
              </div>

              {/* Overview tab */}
              {tab === "overview" && (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginTop: 16 }}>
                    {[
                      ["Contract Value",  fmt(selected.contract_amount)],
                      ["Budget",         fmt(selected.budget)],
                      ["Customer",       selected.customer || "—"],
                      ["Project Manager",selected.project_manager || "—"],
                      ["Start Date",     selected.start_date ?? "—"],
                      ["End Date",       selected.end_date ?? "—"],
                      ["Address",        selected.address || "—"],
                      ["Created",        selected.created_at?.slice(0,10)],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#64748b" }}>{label}</div>
                        <div style={{ fontSize: 13, marginTop: 2 }}>{value}</div>
                      </div>
                    ))}
                  </div>
                  {selected.description && (
                    <div style={{ marginTop: 16, padding: "10px 14px", background: "#f8fafc", borderRadius: 8, fontSize: 13 }}>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>Description</div>
                      {selected.description}
                    </div>
                  )}
                </>
              )}

              {/* Tickets tab */}
              {tab === "tickets" && (
                <div style={{ marginTop: 14 }}>
                  {tickets.length === 0 ? (
                    <p className="muted" style={{ fontSize: 13 }}>No tickets on this project yet.</p>
                  ) : (
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                        <thead>
                          <tr style={{ borderBottom: "2px solid #e2e8f0", textAlign: "left" }}>
                            {["Ticket #","Material","Qty","Unit","Status","Date"].map(h => (
                              <th key={h} style={{ padding: "8px 10px", fontSize: 11, fontWeight: 700,
                                textTransform: "uppercase", letterSpacing: "0.04em", color: "#64748b" }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {tickets.map(t => (
                            <tr key={t.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                              <td style={{ padding: "8px 10px", fontWeight: 600 }}>{t.ticket_number}</td>
                              <td style={{ padding: "8px 10px" }}>{t.material}</td>
                              <td style={{ padding: "8px 10px" }}>{t.quantity}</td>
                              <td style={{ padding: "8px 10px" }}>{t.unit}</td>
                              <td style={{ padding: "8px 10px" }}>
                                <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
                                  background: "#f1f5f9", color: "#475569" }}>{t.status}</span>
                              </td>
                              <td style={{ padding: "8px 10px" }}>{t.created_at?.slice(0,10)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Costs tab */}
              {tab === "costs" && (
                <div style={{ marginTop: 14 }}>
                  {!costs ? (
                    <p className="muted" style={{ fontSize: 13 }}>No cost data yet.</p>
                  ) : (
                    <>
                      <div className="grid" style={{ gridTemplateColumns: "repeat(3,1fr)", marginTop: 0 }}>
                        {[
                          ["Labor",     costs.labor_cost,     "#2563eb"],
                          ["Materials", costs.material_cost,  "#16a34a"],
                          ["Equipment", costs.equipment_cost, "#d97706"],
                          ["Overhead",  costs.overhead_cost,  "#7c3aed"],
                          ["Total Cost",costs.total_cost,     "#0f172a"],
                        ].map(([label, val, color]) => (
                          <div className="card" key={label as string}>
                            <div className="metric-note">{label}</div>
                            <div className="metric" style={{ color: color as string, fontSize: 22 }}>{fmt(val as string)}</div>
                          </div>
                        ))}
                        {selected.contract_amount && costs.total_cost && (
                          <div className="card">
                            <div className="metric-note">Estimated Margin</div>
                            <div className="metric" style={{ color: "#16a34a", fontSize: 22 }}>
                              {(((Number(selected.contract_amount) - Number(costs.total_cost)) / Number(selected.contract_amount)) * 100).toFixed(1)}%
                            </div>
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )}
            </>
          )}

          {view === "list" && !selected && (
            <p className="muted" style={{ marginTop: 0 }}>Select a project from the list to see details, or click <strong>+ New</strong> to create one.</p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
