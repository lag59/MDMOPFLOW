"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

type DailyReport = {
  id: string;
  report_number: string;
  project_id: string | null;
  report_date: string;
  reporting_supervisor: string;
  status: string;
  work_performed: string;
  weather_conditions: string;
  total_workers: number | null;
  created_at: string;
};

type CreateReportForm = {
  project_id: string;
  report_date: string;
  reporting_supervisor: string;
  weather_conditions: string;
  work_performed: string;
  total_workers: string;
  safety_incidents: string;
  notes: string;
};

type Project = { id: string; project_name: string; project_number: string };

const STATUS_COLORS: Record<string, string> = {
  draft: "#64748b", submitted: "#2563eb", reviewed: "#7c3aed", approved: "#16a34a", returned: "#dc2626",
};

const BLANK: CreateReportForm = {
  project_id: "", report_date: new Date().toISOString().slice(0,10),
  reporting_supervisor: "", weather_conditions: "Clear",
  work_performed: "", total_workers: "", safety_incidents: "0", notes: "",
};

export default function FieldSupervisorPage() {
  const [reports, setReports]   = useState<DailyReport[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<DailyReport | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm]         = useState<CreateReportForm>(BLANK);
  const [saving, setSaving]     = useState(false);
  const [msg, setMsg]           = useState<{ text: string; ok: boolean } | null>(null);

  const api = getApiBaseUrl();
  const token = getAccessToken();
  const tenant = getTenantId();

  function headers() {
    return { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "X-Tenant-ID": tenant };
  }

  useEffect(() => {
    if (!token) { window.location.href = "/login"; return; }
    Promise.all([
      fetch(`${api}/api/daily-field-reports`, { headers: headers() }).then(r => r.ok ? r.json() : []),
      fetch(`${api}/api/projects`, { headers: headers() }).then(r => r.ok ? r.json() : []),
    ]).then(([rpts, projs]) => { setReports(rpts); setProjects(projs); });
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.report_date || !form.reporting_supervisor.trim()) {
      setMsg({ text: "Date and supervisor name are required.", ok: false }); return;
    }
    setSaving(true); setMsg(null);
    const r = await fetch(`${api}/api/daily-field-reports`, {
      method: "POST", headers: headers(),
      body: JSON.stringify({
        ...form,
        project_id: form.project_id || null,
        total_workers: form.total_workers ? Number(form.total_workers) : null,
        safety_incidents: Number(form.safety_incidents || 0),
      }),
    });
    setSaving(false);
    if (r.ok) {
      const created = await r.json();
      setReports(prev => [created, ...prev]);
      setShowCreate(false); setForm(BLANK);
      setSelected(created);
      setMsg({ text: "Report created.", ok: true });
    } else {
      const d = await r.json().catch(() => null);
      setMsg({ text: d?.detail || "Failed to create report.", ok: false });
    }
  }

  async function submitReport(reportId: string) {
    const r = await fetch(`${api}/api/daily-field-reports/${reportId}/submit`, { method: "POST", headers: headers() });
    if (r.ok) {
      const updated = await r.json();
      setReports(prev => prev.map(rpt => rpt.id === updated.id ? updated : rpt));
      setSelected(updated);
      setMsg({ text: "Report submitted for review.", ok: true });
    }
  }

  const pill = (status: string) => (
    <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, textTransform: "capitalize",
      background: (STATUS_COLORS[status] ?? "#64748b") + "22",
      color: STATUS_COLORS[status] ?? "#64748b",
      border: `1px solid ${STATUS_COLORS[status] ?? "#cbd5e1"}44` }}>
      {status}
    </span>
  );

  return (
    <AppShell titleKey="nav.fieldSupervisor">
      {/* Metrics */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(4,1fr)", marginBottom: 20 }}>
        {[
          { label: "Total Reports",   value: reports.length,                                        color: "#64748b" },
          { label: "Draft",           value: reports.filter(r => r.status === "draft").length,      color: "#d97706" },
          { label: "Submitted",       value: reports.filter(r => r.status === "submitted").length,  color: "#2563eb" },
          { label: "Approved",        value: reports.filter(r => r.status === "approved").length,   color: "#16a34a" },
        ].map(m => (
          <div className="card" key={m.label}>
            <div className="metric-note">{m.label}</div>
            <div className="metric" style={{ color: m.color }}>{m.value}</div>
          </div>
        ))}
      </div>

      {msg && (
        <div style={{ marginBottom: 14, padding: "9px 14px", borderRadius: 8, fontSize: 13,
          background: msg.ok ? "#dcfce7" : "#fee2e2", color: msg.ok ? "#166534" : "#991b1b" }}>
          {msg.text}
        </div>
      )}

      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
        {/* Reports list */}
        <div className="card" style={{ flex: "0 0 280px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <h3 style={{ margin: 0, fontSize: 15 }}>Reports ({reports.length})</h3>
            <button onClick={() => { setShowCreate(true); setSelected(null); setMsg(null); }} style={{ fontSize: 12, padding: "5px 10px" }}>+ New</button>
          </div>
          <div className="list" style={{ maxHeight: 540, overflowY: "auto", marginTop: 0 }}>
            {reports.length === 0 && <p className="muted" style={{ fontSize: 13 }}>No reports yet.</p>}
            {reports.map(rpt => (
              <div key={rpt.id} className="list-item"
                onClick={() => { setSelected(rpt); setShowCreate(false); setMsg(null); }}
                style={{ cursor: "pointer",
                  background: selected?.id === rpt.id ? "rgba(249,115,22,0.06)" : undefined,
                  borderLeft: selected?.id === rpt.id ? "3px solid #f97316" : "3px solid transparent",
                  padding: "8px 12px" }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{rpt.report_number || rpt.id.slice(0,8)}</div>
                <div className="muted" style={{ fontSize: 11 }}>{rpt.report_date} · {rpt.reporting_supervisor}</div>
                <div style={{ marginTop: 3 }}>{pill(rpt.status)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Detail / Create */}
        <div className="card" style={{ flex: 1 }}>
          {showCreate && (
            <form onSubmit={handleCreate}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <h3 style={{ margin: 0 }}>New Daily Field Report</h3>
                <button type="button" className="btn-ghost" onClick={() => setShowCreate(false)} style={{ fontSize: 12 }}>✕ Cancel</button>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Report Date *
                  <input type="date" value={form.report_date} onChange={e => setForm(p => ({ ...p, report_date: e.target.value }))} />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Project
                  <select value={form.project_id} onChange={e => setForm(p => ({ ...p, project_id: e.target.value }))}>
                    <option value="">— select project —</option>
                    {projects.map(proj => <option key={proj.id} value={proj.id}>{proj.project_name}</option>)}
                  </select>
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Reporting Supervisor *
                  <input value={form.reporting_supervisor} onChange={e => setForm(p => ({ ...p, reporting_supervisor: e.target.value }))} />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Weather Conditions
                  <select value={form.weather_conditions} onChange={e => setForm(p => ({ ...p, weather_conditions: e.target.value }))}>
                    {["Clear","Partly Cloudy","Overcast","Rain","Heavy Rain","Wind","Cold","Hot","Snow"].map(w => <option key={w}>{w}</option>)}
                  </select>
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Total Workers on Site
                  <input type="number" min="0" value={form.total_workers} onChange={e => setForm(p => ({ ...p, total_workers: e.target.value }))} />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Safety Incidents
                  <input type="number" min="0" value={form.safety_incidents} onChange={e => setForm(p => ({ ...p, safety_incidents: e.target.value }))} />
                </label>
              </div>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, marginTop: 12 }}>
                Work Performed *
                <textarea rows={4} placeholder="Describe work performed today…" value={form.work_performed}
                  onChange={e => setForm(p => ({ ...p, work_performed: e.target.value }))} />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, marginTop: 10 }}>
                Notes
                <textarea rows={2} value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} />
              </label>
              <div style={{ marginTop: 14, display: "flex", gap: 8 }}>
                <button type="submit" disabled={saving}>{saving ? "Saving…" : "Save Report"}</button>
                <button type="button" className="btn-ghost" onClick={() => setShowCreate(false)}>Cancel</button>
              </div>
            </form>
          )}

          {!showCreate && selected && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                <div>
                  <h3 style={{ margin: 0 }}>{selected.report_number || selected.id.slice(0,8)}</h3>
                  <div className="muted" style={{ fontSize: 12 }}>{selected.report_date} · {selected.reporting_supervisor}</div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  {pill(selected.status)}
                  {selected.status === "draft" && (
                    <button onClick={() => submitReport(selected.id)} style={{ fontSize: 12, padding: "5px 12px" }}>
                      Submit for Review →
                    </button>
                  )}
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 16, paddingTop: 16, borderTop: "1px solid #e2e8f0" }}>
                {[
                  ["Report Date",    selected.report_date],
                  ["Supervisor",     selected.reporting_supervisor],
                  ["Weather",        selected.weather_conditions],
                  ["Workers on Site",selected.total_workers ?? "—"],
                  ["Status",         selected.status],
                  ["Created",        selected.created_at?.slice(0,10)],
                ].map(([label, value]) => (
                  <div key={label as string}>
                    <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#64748b" }}>{label}</div>
                    <div style={{ fontSize: 13, marginTop: 2 }}>{value as string}</div>
                  </div>
                ))}
              </div>
              {selected.work_performed && (
                <div style={{ marginTop: 14, padding: "10px 14px", background: "#f8fafc", borderRadius: 8, fontSize: 13 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>Work Performed</div>
                  {selected.work_performed}
                </div>
              )}
            </>
          )}

          {!showCreate && !selected && (
            <p className="muted" style={{ marginTop: 0 }}>Select a report or click <strong>+ New</strong> to create today's field report.</p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
