"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { ProcessIndicator, REPORT_PROCESS } from "@/components/ProcessIndicator";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";

type DailyReport = {
  id: string;
  report_number?: string;
  project_id: string;
  report_date: string;
  reporting_supervisor: string;
  status: string;
  work_performed: string;
  weather?: Record<string, unknown> | null;
  crew_members?: Array<Record<string, unknown>>;
  safety_observations?: Array<Record<string, unknown>>;
  created_at: string;
};

type CreateReportForm = {
  project_id: string;
  report_date: string;
  reporting_supervisor: string;
  weather_conditions: string;
  temperature_max_c: string;
  work_performed: string;
  total_workers: string;
  safety_incidents: string;
  notes: string;
  equipment_used: string;
};

type AssistResponse = {
  project_id: string;
  report_date: string;
  ai_generated: boolean;
  productivity_score: number;
  productivity_summary: string;
  suggested_work_performed: string;
  suggested_delay_notes: string[];
  suggested_safety_observations: string[];
  ticket_context: Record<string, unknown>;
  weather_context: Record<string, unknown>;
};

type Project = { id: string; project_name: string; project_number: string };

const STATUS_COLORS: Record<string, string> = {
  draft: "#64748b", submitted: "#2563eb", reviewed: "#7c3aed", approved: "#16a34a", returned: "#dc2626",
};

const BLANK: CreateReportForm = {
  project_id: "", report_date: new Date().toISOString().slice(0,10),
  reporting_supervisor: "", weather_conditions: "Clear",
  temperature_max_c: "",
  work_performed: "", total_workers: "", safety_incidents: "0", notes: "", equipment_used: "",
};

export default function FieldSupervisorPage() {
  const [reports, setReports]   = useState<DailyReport[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<DailyReport | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm]         = useState<CreateReportForm>(BLANK);
  const [saving, setSaving]     = useState(false);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [assisting, setAssisting] = useState(false);
  const [assist, setAssist] = useState<AssistResponse | null>(null);
  const [msg, setMsg]           = useState<{ text: string; ok: boolean } | null>(null);

  const api = getApiBaseUrl();
  const token = getAccessToken();
  const tenant = getTenantId();

  function headers() {
    return { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "X-Tenant-ID": tenant };
  }

  useEffect(() => {
    if (!token) { window.location.href = "/login"; return; }
    setLoading(true);
    setError(null);
    Promise.all([
      fetch(`${api}/api/daily-field-reports`, { headers: headers() }).then(r => r.ok ? r.json() : []),
      fetch(`${api}/api/projects`, { headers: headers() }).then(r => r.ok ? r.json() : []),
    ]).then(([rpts, projs]) => {
      setReports(rpts);
      setProjects(projs);
      setLoading(false);
    }).catch(() => {
      setError("Could not load reports. Please refresh.");
      setLoading(false);
    });
  }, []);

  const selectedProject = projects.find((project) => project.id === form.project_id);

  function parseEquipmentRows(input: string): Array<Record<string, unknown>> {
    return input
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean)
      .map((name) => ({ name, hours: 8 }));
  }

  function parseTemperature(value: string): number | null {
    const normalized = value.trim();
    if (!normalized) return null;
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : null;
  }

  async function runAssist() {
    if (!form.project_id) {
      setMsg({ text: "Select a project first.", ok: false });
      return;
    }
    if (!form.reporting_supervisor.trim()) {
      setMsg({ text: "Enter reporting supervisor before running AI assist.", ok: false });
      return;
    }

    setAssisting(true);
    setMsg(null);

    const weatherPayload: Record<string, unknown> = {
      condition: form.weather_conditions,
    };
    const temp = parseTemperature(form.temperature_max_c);
    if (temp !== null) weatherPayload.temperature_max_c = temp;

    const response = await fetch(`${api}/api/daily-field-reports/assist`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({
        project_id: form.project_id,
        report_date: form.report_date,
        reporting_supervisor: form.reporting_supervisor,
        total_workers: form.total_workers ? Number(form.total_workers) : null,
        weather: weatherPayload,
        work_performed: form.work_performed,
        equipment_used: parseEquipmentRows(form.equipment_used),
      }),
    });

    setAssisting(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setMsg({ text: detail?.detail || "Failed to generate assist recommendations.", ok: false });
      return;
    }

    const payload = (await response.json()) as AssistResponse;
    setAssist(payload);
    setForm((prev) => {
      const newNotes = [prev.notes.trim(), ...payload.suggested_delay_notes].filter(Boolean).join("\n");
      const next = { ...prev, work_performed: payload.suggested_work_performed, notes: newNotes };

      const condition = String(payload.weather_context?.condition || "").trim();
      if (condition) next.weather_conditions = condition;

      const suggestedTemp = payload.weather_context?.temperature_max_c;
      if (suggestedTemp !== undefined && suggestedTemp !== null && Number.isFinite(Number(suggestedTemp))) {
        next.temperature_max_c = String(Number(suggestedTemp));
      }
      return next;
    });

    setMsg({ text: "AI assist applied. Review and submit when ready.", ok: true });
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.project_id || !form.report_date || !form.reporting_supervisor.trim()) {
      setMsg({ text: "Project, date, and supervisor name are required.", ok: false }); return;
    }
    setSaving(true); setMsg(null);

    const weather: Record<string, unknown> = {
      condition: form.weather_conditions,
    };
    const temperature = parseTemperature(form.temperature_max_c);
    if (temperature !== null) {
      weather.temperature_max_c = temperature;
    }

    const workerCount = form.total_workers ? Number(form.total_workers) : 0;
    const crewMembers = workerCount > 0
      ? [{ role: "Crew", count: workerCount, hours: 8 }]
      : [];

    const safetyObservations: Array<Record<string, unknown>> = [];
    const incidents = Number(form.safety_incidents || 0);
    if (incidents > 0) {
      safetyObservations.push({
        observation_type: "incident",
        description: `${incidents} safety incident(s) reported.`,
        severity: incidents > 1 ? "high" : "medium",
      });
    }
    for (const note of assist?.suggested_safety_observations || []) {
      safetyObservations.push({ observation_type: "recommendation", description: note, severity: "low" });
    }

    const delayRows = (assist?.suggested_delay_notes || [])
      .map((text) => ({ category: "Operational", description: text, duration_hours: 1 }));

    const workPerformed = [form.work_performed.trim(), assist?.productivity_summary?.trim() || ""]
      .filter(Boolean)
      .join("\n\n");

    const r = await fetch(`${api}/api/daily-field-reports`, {
      method: "POST", headers: headers(),
      body: JSON.stringify({
        project_id: form.project_id,
        report_date: form.report_date,
        reporting_supervisor: form.reporting_supervisor,
        company_name: selectedProject?.project_name || "",
        shift_start_time: "06:00",
        shift_end_time: "14:00",
        weather,
        crew_members: crewMembers,
        equipment_used: parseEquipmentRows(form.equipment_used),
        deliveries: [],
        visitors: [],
        delays: delayRows,
        photos: [],
        production_quantities: [],
        safety_observations: safetyObservations,
        work_performed: workPerformed,
        work_planned_for_tomorrow: form.notes,
        prepared_by: form.reporting_supervisor,
        electronic_signature: form.reporting_supervisor,
        status: "draft",
      }),
    });
    setSaving(false);
    if (r.ok) {
      const created = await r.json();
      setReports(prev => [created, ...prev]);
      setShowCreate(false); setForm(BLANK);
      setAssist(null);
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
      {loading ? <p className="muted">Loading field reports...</p> : null}
      {!loading && error ? (
        <div className="card" style={{ borderColor: "#fecaca", background: "#fef2f2" }}>
          <p style={{ margin: 0, color: "#991b1b", fontWeight: 600 }}>{error}</p>
        </div>
      ) : null}

      {!loading && !error ? (
      <>
      {/* Metrics */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", marginBottom: 20 }}>
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

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,280px) minmax(0,1fr)", gap: 16, alignItems: "flex-start" }}>
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
                <div style={{ display: "flex", gap: 8 }}>
                  <button type="button" className="btn-ghost" onClick={() => void runAssist()} disabled={assisting} style={{ fontSize: 12 }}>
                    {assisting ? "Running AI..." : "AI Assist"}
                  </button>
                  <button type="button" className="btn-ghost" onClick={() => setShowCreate(false)} style={{ fontSize: 12 }}>✕ Cancel</button>
                </div>
              </div>
              {assist ? (
                <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-900" style={{ marginBottom: 12 }}>
                  <div style={{ fontWeight: 700 }}>AI productivity score: {assist.productivity_score}/100</div>
                  <div style={{ marginTop: 4 }}>{assist.productivity_summary}</div>
                </div>
              ) : null}
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
                  Temp Max (C)
                  <input value={form.temperature_max_c} onChange={e => setForm(p => ({ ...p, temperature_max_c: e.target.value }))} placeholder="e.g. 31" />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Total Workers on Site
                  <input type="number" min="0" value={form.total_workers} onChange={e => setForm(p => ({ ...p, total_workers: e.target.value }))} />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>
                  Equipment Used (comma-separated)
                  <input value={form.equipment_used} onChange={e => setForm(p => ({ ...p, equipment_used: e.target.value }))} placeholder="Excavator 12, Dump Truck 7" />
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
              <ProcessIndicator steps={REPORT_PROCESS} currentKey={selected.status} />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 16, paddingTop: 16, borderTop: "1px solid #e2e8f0" }}>
                {[
                  ["Report Date",    selected.report_date],
                  ["Supervisor",     selected.reporting_supervisor],
                  ["Weather",        String(selected.weather?.condition || "—")],
                  ["Workers on Site",String((selected.crew_members || [])[0]?.count || "—")],
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
      </>
      ) : null}
    </AppShell>
  );
}
