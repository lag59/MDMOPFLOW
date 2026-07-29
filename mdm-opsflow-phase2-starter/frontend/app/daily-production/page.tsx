"use client";

import Link from "next/link";
import React, { useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";
import { createTicket, listTickets, type Ticket } from "@/lib/tickets";

type ProjectSummary = {
  id: string;
  project_name: string;
  project_number: string;
  status: string;
};

type CrewLine = {
  id: string;
  role: string;
  count: number;
  hours: number;
};

type EquipmentLine = {
  id: string;
  machine: string;
  hours: number;
  fuelGallons: number;
  issue: string;
};

type MaterialLine = {
  id: string;
  material: string;
  usedQty: number;
  unit: string;
  needQty: number;
};

type DailyFieldReportResponse = {
  id: string;
  report_number: string;
};

type AiRouteResponse = {
  routed: boolean;
  message: string;
};

const defaultCrew: CrewLine[] = [
  { id: "crew-1", role: "Foreman", count: 1, hours: 10 },
  { id: "crew-2", role: "Operator", count: 2, hours: 10 },
  { id: "crew-3", role: "Laborer", count: 3, hours: 10 },
];

const defaultEquipment: EquipmentLine[] = [
  { id: "eq-1", machine: "Excavator", hours: 8, fuelGallons: 22, issue: "" },
  { id: "eq-2", machine: "Dozer", hours: 7, fuelGallons: 18, issue: "" },
];

const defaultMaterials: MaterialLine[] = [
  { id: "mat-1", material: "Aggregate Base", usedQty: 120, unit: "tons", needQty: 50 },
];

function isoDateToday(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function DailyProductionPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [recentTickets, setRecentTickets] = useState<Ticket[]>([]);

  const [projectId, setProjectId] = useState("");
  const [reportDate, setReportDate] = useState(isoDateToday());
  const [reportingSupervisor, setReportingSupervisor] = useState("");
  const [preparedBy, setPreparedBy] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [shiftStart, setShiftStart] = useState("06:30");
  const [shiftEnd, setShiftEnd] = useState("17:00");

  const [weatherConditions, setWeatherConditions] = useState("Clear");
  const [weatherTempF, setWeatherTempF] = useState("78");
  const [weatherWindMph, setWeatherWindMph] = useState("8");

  const [workPerformed, setWorkPerformed] = useState("");
  const [workTomorrow, setWorkTomorrow] = useState("");
  const [superintendentNotes, setSuperintendentNotes] = useState("");

  const [crewLines, setCrewLines] = useState<CrewLine[]>(defaultCrew);
  const [equipmentLines, setEquipmentLines] = useState<EquipmentLine[]>(defaultEquipment);
  const [materialLines, setMaterialLines] = useState<MaterialLine[]>(defaultMaterials);

  const [createMechanicTicket, setCreateMechanicTicket] = useState(true);
  const [createMaterialTicket, setCreateMaterialTicket] = useState(true);

  const [aiMessage, setAiMessage] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [lastReportId, setLastReportId] = useState("");
  const [lastReportNumber, setLastReportNumber] = useState("");
  const [exportingPdf, setExportingPdf] = useState(false);

  const totalLaborHours = useMemo(
    () => crewLines.reduce((sum, line) => sum + line.count * line.hours, 0),
    [crewLines]
  );

  const totalMachineHours = useMemo(
    () => equipmentLines.reduce((sum, line) => sum + line.hours, 0),
    [equipmentLines]
  );

  const machineIssues = useMemo(
    () => equipmentLines.filter((line) => line.issue.trim().length > 0),
    [equipmentLines]
  );

  const materialNeeds = useMemo(
    () => materialLines.filter((line) => line.needQty > 0),
    [materialLines]
  );

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      return;
    }

    const headers = {
      Authorization: `Bearer ${token}`,
      "X-Tenant-ID": getTenantId(),
    };

    const load = async () => {
      try {
        const projectRes = await fetch(`${getApiBaseUrl()}/api/projects`, { headers });
        if (projectRes.ok) {
          const projectData = (await projectRes.json()) as ProjectSummary[];
          setProjects(projectData);
          if (!projectId && projectData.length > 0) {
            setProjectId(projectData[0].id);
          }
        }
      } catch {
        setProjects([]);
      }

      try {
        const ticketData = await listTickets();
        setRecentTickets(ticketData.slice(0, 6));
      } catch {
        setRecentTickets([]);
      }
    };

    load();
  }, [projectId]);

  const updateCrew = (id: string, patch: Partial<CrewLine>) => {
    setCrewLines((prev) => prev.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  const updateEquipment = (id: string, patch: Partial<EquipmentLine>) => {
    setEquipmentLines((prev) => prev.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  const updateMaterial = (id: string, patch: Partial<MaterialLine>) => {
    setMaterialLines((prev) => prev.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  const aiRouteNote = useMemo(() => {
    const materials = materialLines
      .map((line) => `${line.material}: used ${line.usedQty} ${line.unit}, need ${line.needQty} ${line.unit}`)
      .join("; ");
    const machine = equipmentLines
      .map((line) => `${line.machine}: ${line.hours}h, issue=${line.issue || "none"}`)
      .join("; ");

    return [
      `Daily production for ${reportDate}`,
      `Supervisor: ${reportingSupervisor}`,
      `Work performed: ${workPerformed}`,
      `Tomorrow plan: ${workTomorrow}`,
      `Labor hours: ${totalLaborHours}`,
      `Machine hours: ${totalMachineHours}`,
      `Materials: ${materials}`,
      `Equipment: ${machine}`,
      `Superintendent notes: ${superintendentNotes}`,
    ]
      .filter(Boolean)
      .join("\n");
  }, [reportDate, reportingSupervisor, workPerformed, workTomorrow, totalLaborHours, totalMachineHours, materialLines, equipmentLines, superintendentNotes]);

  const runAiAssist = async () => {
    setAiMessage("");
    const token = getAccessToken();
    if (!token) {
      setAiMessage("Login required.");
      return;
    }

    const response = await fetch(`${getApiBaseUrl()}/api/ai/workflow/route`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-ID": getTenantId(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        note: aiRouteNote,
        company_name: companyName,
        reporting_supervisor: reportingSupervisor,
        material_name: materialLines[0]?.material || "",
        project_id: projectId || null,
      }),
    });

    if (!response.ok) {
      setAiMessage("AI assist failed for this note.");
      return;
    }

    const data = (await response.json()) as AiRouteResponse;
    setAiMessage(data.message || "AI routing complete.");
  };

  const submitDailyProduction = async () => {
    setStatusMessage("");
    if (!projectId) {
      setStatusMessage("Project is required.");
      return;
    }
    if (!reportingSupervisor.trim()) {
      setStatusMessage("Foreman/Superintendent name is required.");
      return;
    }

    const token = getAccessToken();
    if (!token) {
      setStatusMessage("Login required.");
      return;
    }

    setSaving(true);
    try {
      const reportPayload = {
        project_id: projectId,
        report_date: `${reportDate}T00:00:00Z`,
        company_name: companyName,
        reporting_supervisor: reportingSupervisor,
        shift_start_time: shiftStart,
        shift_end_time: shiftEnd,
        weather: {
          conditions: weatherConditions,
          temp_f: weatherTempF,
          wind_mph: weatherWindMph,
        },
        crew_members: crewLines.map((line) => ({ role: line.role, count: line.count, hours: line.hours })),
        equipment_used: equipmentLines.map((line) => ({ machine: line.machine, hours: line.hours, fuel_gallons: line.fuelGallons, issue: line.issue })),
        deliveries: materialLines.map((line) => ({ material: line.material, used_qty: line.usedQty, unit: line.unit, need_qty: line.needQty })),
        production_quantities: materialLines.map((line) => ({ material: line.material, quantity: line.usedQty, unit: line.unit })),
        safety_observations: machineIssues.map((line) => ({ machine: line.machine, issue: line.issue })),
        work_performed: workPerformed,
        work_planned_for_tomorrow: workTomorrow,
        prepared_by: preparedBy || reportingSupervisor,
        electronic_signature: preparedBy || reportingSupervisor,
        status: "draft",
      };

      const reportRes = await fetch(`${getApiBaseUrl()}/api/daily-field-reports`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Tenant-ID": getTenantId(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(reportPayload),
      });

      if (!reportRes.ok) {
        const detail = await reportRes.text();
        setStatusMessage(`Unable to create daily report: ${detail}`);
        return;
      }

      const report = (await reportRes.json()) as DailyFieldReportResponse;
      setLastReportId(report.id);
      setLastReportNumber(report.report_number);

      const createdTicketNumbers: string[] = [];

      if (createMechanicTicket && machineIssues.length > 0) {
        const mechanicTicket = await createTicket({
          project_id: projectId,
          ticket_number: `MECH-${Date.now().toString().slice(-6)}`,
          material: "Maintenance",
          origin: "Daily Production",
          destination: "Mechanic Queue",
          status: "draft",
          notes: [
            `Daily report: ${report.report_number}`,
            `Supervisor: ${reportingSupervisor}`,
            "Machine issues:",
            ...machineIssues.map((line) => `- ${line.machine}: ${line.issue}`),
          ].join("\n"),
        });
        createdTicketNumbers.push(mechanicTicket.ticket_number || mechanicTicket.id);
      }

      if (createMaterialTicket && materialNeeds.length > 0) {
        const materialTicket = await createTicket({
          project_id: projectId,
          ticket_number: `MAT-${Date.now().toString().slice(-6)}`,
          material: materialNeeds[0].material || "Material Request",
          origin: "Daily Production",
          destination: "Superintendent Material Queue",
          status: "draft",
          notes: [
            `Daily report: ${report.report_number}`,
            `Supervisor: ${reportingSupervisor}`,
            "Material needs:",
            ...materialNeeds.map((line) => `- ${line.material}: need ${line.needQty} ${line.unit}`),
          ].join("\n"),
        });
        createdTicketNumbers.push(materialTicket.ticket_number || materialTicket.id);
      }

      setStatusMessage(
        createdTicketNumbers.length > 0
          ? `Daily report ${report.report_number} created. Queue tickets: ${createdTicketNumbers.join(", ")}`
          : `Daily report ${report.report_number} created.`
      );

      const refreshed = await listTickets();
      setRecentTickets(refreshed.slice(0, 6));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected save error.";
      setStatusMessage(message);
    } finally {
      setSaving(false);
    }
  };

  const exportLastReportPdf = async () => {
    if (!lastReportId) {
      setStatusMessage("Create a daily report first, then export PDF.");
      return;
    }

    const token = getAccessToken();
    if (!token) {
      setStatusMessage("Login required.");
      return;
    }

    setExportingPdf(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/daily-field-reports/${lastReportId}/pdf`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Tenant-ID": getTenantId(),
        },
      });

      if (!response.ok) {
        setStatusMessage("Unable to export PDF for this report.");
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${lastReportNumber || "daily-production"}.pdf`;
      anchor.click();
      window.URL.revokeObjectURL(url);
      setStatusMessage(`Exported PDF for ${lastReportNumber || "latest report"}.`);
    } catch {
      setStatusMessage("Unable to export PDF for this report.");
    } finally {
      setExportingPdf(false);
    }
  };

  return (
    <AppShell titleKey="modules.title">
      <div className="space-y-6 p-6">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h1 className="text-2xl font-bold text-slate-900">Foreman/Superintendent Daily Production</h1>
          <p className="mt-2 text-sm text-slate-600">
            Capture labor, machine hours, materials, weather, and site issues in one workflow. AI assist can route key details and submit will auto-create queue tickets for mechanic and material requests.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link href="/daily-production/queue" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Open Mechanic and Material Queue
            </Link>
          </div>
        </div>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Daily context</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <label className="text-sm font-medium text-slate-700">Project
              <select value={projectId} onChange={(event) => setProjectId(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                <option value="">Select project</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>{project.project_name} ({project.project_number})</option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium text-slate-700">Report date
              <input type="date" value={reportDate} onChange={(event) => setReportDate(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-sm font-medium text-slate-700">Company
              <input value={companyName} onChange={(event) => setCompanyName(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-sm font-medium text-slate-700">Foreman/Superintendent
              <input value={reportingSupervisor} onChange={(event) => setReportingSupervisor(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-sm font-medium text-slate-700">Shift start
              <input type="time" value={shiftStart} onChange={(event) => setShiftStart(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-sm font-medium text-slate-700">Shift end
              <input type="time" value={shiftEnd} onChange={(event) => setShiftEnd(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-sm font-medium text-slate-700">Prepared by
              <input value={preparedBy} onChange={(event) => setPreparedBy(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Weather</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <label className="text-sm font-medium text-slate-700">Conditions
              <input value={weatherConditions} onChange={(event) => setWeatherConditions(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-sm font-medium text-slate-700">Temp (F)
              <input value={weatherTempF} onChange={(event) => setWeatherTempF(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-sm font-medium text-slate-700">Wind (mph)
              <input value={weatherWindMph} onChange={(event) => setWeatherWindMph(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Labor hours</h2>
            <div className="mt-3 space-y-2">
              {crewLines.map((line) => (
                <div key={line.id} className="grid grid-cols-3 gap-2 text-xs">
                  <input value={line.role} onChange={(event) => updateCrew(line.id, { role: event.target.value })} className="rounded border border-slate-300 px-2 py-1" />
                  <input type="number" value={line.count} onChange={(event) => updateCrew(line.id, { count: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                  <input type="number" value={line.hours} onChange={(event) => updateCrew(line.id, { hours: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                </div>
              ))}
            </div>
            <p className="mt-3 text-sm font-semibold text-slate-800">Total labor hours: {totalLaborHours.toFixed(1)}</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Machine hours and issues</h2>
            <div className="mt-3 space-y-2">
              {equipmentLines.map((line) => (
                <div key={line.id} className="space-y-1 rounded border border-slate-200 p-2 text-xs">
                  <div className="grid grid-cols-3 gap-2">
                    <input value={line.machine} onChange={(event) => updateEquipment(line.id, { machine: event.target.value })} className="rounded border border-slate-300 px-2 py-1" />
                    <input type="number" value={line.hours} onChange={(event) => updateEquipment(line.id, { hours: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                    <input type="number" value={line.fuelGallons} onChange={(event) => updateEquipment(line.id, { fuelGallons: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                  </div>
                  <input value={line.issue} onChange={(event) => updateEquipment(line.id, { issue: event.target.value })} placeholder="Issue for mechanic queue" className="w-full rounded border border-slate-300 px-2 py-1" />
                </div>
              ))}
            </div>
            <p className="mt-3 text-sm font-semibold text-slate-800">Total machine hours: {totalMachineHours.toFixed(1)}</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Materials used and needed</h2>
            <div className="mt-3 space-y-2">
              {materialLines.map((line) => (
                <div key={line.id} className="grid grid-cols-4 gap-2 text-xs">
                  <input value={line.material} onChange={(event) => updateMaterial(line.id, { material: event.target.value })} className="rounded border border-slate-300 px-2 py-1" />
                  <input type="number" value={line.usedQty} onChange={(event) => updateMaterial(line.id, { usedQty: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                  <input value={line.unit} onChange={(event) => updateMaterial(line.id, { unit: event.target.value })} className="rounded border border-slate-300 px-2 py-1" />
                  <input type="number" value={line.needQty} onChange={(event) => updateMaterial(line.id, { needQty: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Work narrative and planning</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <label className="text-sm font-medium text-slate-700">Work performed
              <textarea value={workPerformed} onChange={(event) => setWorkPerformed(event.target.value)} className="mt-1 min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-sm font-medium text-slate-700">Tomorrow plan
              <textarea value={workTomorrow} onChange={(event) => setWorkTomorrow(event.target.value)} className="mt-1 min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-sm font-medium text-slate-700 md:col-span-2">Superintendent notes
              <textarea value={superintendentNotes} onChange={(event) => setSuperintendentNotes(event.target.value)} className="mt-1 min-h-24 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <label className="inline-flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={createMechanicTicket} onChange={(event) => setCreateMechanicTicket(event.target.checked)} />
              Auto-create mechanic queue ticket from machine issues
            </label>
            <label className="inline-flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={createMaterialTicket} onChange={(event) => setCreateMaterialTicket(event.target.checked)} />
              Auto-create superintendent material queue ticket from needs
            </label>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={runAiAssist} className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800">
              Run AI Assist
            </button>
            <button type="button" onClick={submitDailyProduction} disabled={saving} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-60">
              {saving ? "Saving..." : "Save Daily Production + Queue Tickets"}
            </button>
            <button type="button" onClick={exportLastReportPdf} disabled={exportingPdf} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60">
              {exportingPdf ? "Exporting PDF..." : "Export Last Report PDF"}
            </button>
          </div>
          {aiMessage ? <p className="mt-3 text-sm text-indigo-800">AI: {aiMessage}</p> : null}
          {statusMessage ? <p className="mt-2 text-sm text-slate-800">{statusMessage}</p> : null}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Recent queue tickets</h2>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            {recentTickets.length === 0 ? (
              <p>No recent tickets.</p>
            ) : (
              recentTickets.map((ticket) => (
                <div key={ticket.id} className="rounded-md border border-slate-200 px-3 py-2">
                  {(ticket.ticket_number || ticket.id)} • {ticket.material || "n/a"} • {ticket.destination || "n/a"} • {ticket.status}
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
