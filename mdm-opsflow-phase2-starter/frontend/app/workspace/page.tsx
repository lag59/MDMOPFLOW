"use client";

import React, { useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";
import { ROLE_WORKSPACES, RoleKey, mapBackendRole } from "@/lib/roles";

type MeMembership = {
  role_name: string;
};

type MeResponse = {
  platform_role: string;
  memberships: MeMembership[];
};

type PlatformResource = {
  id: string;
  name?: string;
  unit_number?: string;
  contact_name?: string;
};

type ResourceSection = {
  key: "customers" | "employees" | "equipment" | "trucks" | "materials";
  label: string;
  summary: string;
  accessor: PlatformResource[];
  placeholder: string;
};

type ProjectOption = {
  id: string;
  project_name: string;
  project_number?: string;
};

type DailyReportSummary = {
  id: string;
  report_number: string;
  report_date: string;
  reporting_supervisor: string;
  status: string;
};

export default function WorkspacePage() {
  const locale = getLocale();
  const [activeRole, setActiveRole] = useState<RoleKey>("project_manager");
  const [canPreviewAllRoles, setCanPreviewAllRoles] = useState(false);
  const [customers, setCustomers] = useState<PlatformResource[]>([]);
  const [employees, setEmployees] = useState<PlatformResource[]>([]);
  const [equipment, setEquipment] = useState<PlatformResource[]>([]);
  const [trucks, setTrucks] = useState<PlatformResource[]>([]);
  const [materials, setMaterials] = useState<PlatformResource[]>([]);
  const [selectedResource, setSelectedResource] = useState<ResourceSection["key"]>("customers");
  const [draftName, setDraftName] = useState("");
  const [pendingMessage, setPendingMessage] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [dailyReports, setDailyReports] = useState<DailyReportSummary[]>([]);
  const [dailyReportMessage, setDailyReportMessage] = useState("");
  const [aiRoutingInput, setAiRoutingInput] = useState("");
  const [aiRoutingMessage, setAiRoutingMessage] = useState("");
  const [dailyReportForm, setDailyReportForm] = useState({
    projectId: "",
    reportDate: new Date().toISOString().slice(0, 10),
    companyName: "",
    reportingSupervisor: "",
    shiftStartTime: "",
    shiftEndTime: "",
    workPerformed: "",
    workPlanned: "",
  });

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    fetch(`${getApiBaseUrl()}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((me: MeResponse | null) => {
        if (!me) {
          return;
        }

        const mapped = mapBackendRole(me.platform_role, me.memberships?.[0]?.role_name);
        setActiveRole(mapped);
        setCanPreviewAllRoles(me.platform_role === "platform_super_admin");
      });

    const headers = {
      Authorization: `Bearer ${token}`,
      "X-Tenant-ID": getTenantId(),
    };

    Promise.all([
      fetch(`${getApiBaseUrl()}/api/customers`, { headers }).then((res) => (res.ok ? res.json() : [])),
      fetch(`${getApiBaseUrl()}/api/employees`, { headers }).then((res) => (res.ok ? res.json() : [])),
      fetch(`${getApiBaseUrl()}/api/equipment`, { headers }).then((res) => (res.ok ? res.json() : [])),
      fetch(`${getApiBaseUrl()}/api/trucks`, { headers }).then((res) => (res.ok ? res.json() : [])),
      fetch(`${getApiBaseUrl()}/api/materials`, { headers }).then((res) => (res.ok ? res.json() : [])),
      fetch(`${getApiBaseUrl()}/api/projects`, { headers }).then((res) => (res.ok ? res.json() : [])),
      fetch(`${getApiBaseUrl()}/api/daily-field-reports`, { headers }).then((res) => (res.ok ? res.json() : [])),
    ])
      .then(([customerData, employeeData, equipmentData, truckData, materialData, projectData, reportData]) => {
        setCustomers(customerData as PlatformResource[]);
        setEmployees(employeeData as PlatformResource[]);
        setEquipment(equipmentData as PlatformResource[]);
        setTrucks(truckData as PlatformResource[]);
        setMaterials(materialData as PlatformResource[]);
        setProjects(projectData as ProjectOption[]);
        setDailyReports(reportData as DailyReportSummary[]);
      })
      .catch(() => {
        setCustomers([]);
        setEmployees([]);
        setEquipment([]);
        setTrucks([]);
        setMaterials([]);
        setProjects([]);
        setDailyReports([]);
      });
  }, []);

  useEffect(() => {
    if (projects.length && !dailyReportForm.projectId) {
      setDailyReportForm((current) => ({ ...current, projectId: projects[0].id }));
    }
  }, [projects, dailyReportForm.projectId]);

  const current = useMemo(() => ROLE_WORKSPACES.find((item) => item.key === activeRole) || ROLE_WORKSPACES[0], [activeRole]);

  const resources: ResourceSection[] = [
    {
      key: "customers",
      label: "Customers",
      summary: "Track client accounts and account contacts",
      accessor: customers,
      placeholder: "Enter customer name",
    },
    {
      key: "employees",
      label: "Employees",
      summary: "Review internal team members and staffing",
      accessor: employees,
      placeholder: "Enter employee name",
    },
    {
      key: "equipment",
      label: "Equipment",
      summary: "Monitor plant assets and equipment units",
      accessor: equipment,
      placeholder: "Enter equipment name",
    },
    {
      key: "trucks",
      label: "Trucks",
      summary: "Stay on top of fleet availability",
      accessor: trucks,
      placeholder: "Enter truck unit number",
    },
    {
      key: "materials",
      label: "Materials",
      summary: "See the catalog of available materials",
      accessor: materials,
      placeholder: "Enter material name",
    },
  ];

  const selectedResourceData = resources.find((resource) => resource.key === selectedResource) || resources[0];

  async function refreshResourceList() {
    const token = getAccessToken();
    const headers = {
      Authorization: `Bearer ${token}`,
      "X-Tenant-ID": getTenantId(),
    };

    const refreshed = await fetch(`${getApiBaseUrl()}/api/${selectedResource}`, { headers });
    if (!refreshed.ok) {
      return;
    }

    const payload = await refreshed.json();
    if (selectedResource === "customers") {
      setCustomers(payload as PlatformResource[]);
    } else if (selectedResource === "employees") {
      setEmployees(payload as PlatformResource[]);
    } else if (selectedResource === "equipment") {
      setEquipment(payload as PlatformResource[]);
    } else if (selectedResource === "trucks") {
      setTrucks(payload as PlatformResource[]);
    } else if (selectedResource === "materials") {
      setMaterials(payload as PlatformResource[]);
    }
  }

  async function handleCreateResource(event: React.FormEvent) {
    event.preventDefault();
    const token = getAccessToken();
    if (!token || !draftName.trim()) {
      return;
    }

    const headers = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-Tenant-ID": getTenantId(),
    };

    const bodyMap: Record<ResourceSection["key"], Record<string, string>> = {
      customers: { name: draftName },
      employees: { name: draftName },
      equipment: { name: draftName },
      trucks: { unit_number: draftName },
      materials: { name: draftName },
    };

    const response = await fetch(`${getApiBaseUrl()}/api/${selectedResource}`, {
      method: "POST",
      headers,
      body: JSON.stringify(bodyMap[selectedResource]),
    });

    if (!response.ok) {
      setPendingMessage(`Unable to create ${selectedResourceData.label.toLowerCase()}.`);
      return;
    }

    setDraftName("");
    setPendingMessage(`${selectedResourceData.label} created.`);
    await refreshResourceList();
  }

  async function handleSaveEdit(itemId: string) {
    const token = getAccessToken();
    if (!token || !editValue.trim()) {
      return;
    }

    const headers = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-Tenant-ID": getTenantId(),
    };

    const bodyMap: Record<ResourceSection["key"], Record<string, string>> = {
      customers: { name: editValue },
      employees: { name: editValue },
      equipment: { name: editValue },
      trucks: { unit_number: editValue },
      materials: { name: editValue },
    };

    const response = await fetch(`${getApiBaseUrl()}/api/${selectedResource}/${itemId}`, {
      method: "PATCH",
      headers,
      body: JSON.stringify(bodyMap[selectedResource]),
    });

    if (!response.ok) {
      setPendingMessage(`Unable to update ${selectedResourceData.label.toLowerCase()}.`);
      return;
    }

    setEditingId(null);
    setEditValue("");
    setPendingMessage(`${selectedResourceData.label} updated.`);
    await refreshResourceList();
  }

  async function handleDelete(itemId: string) {
    const token = getAccessToken();
    if (!token) {
      return;
    }

    const response = await fetch(`${getApiBaseUrl()}/api/${selectedResource}/${itemId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-ID": getTenantId(),
      },
    });

    if (!response.ok) {
      setPendingMessage(`Unable to delete ${selectedResourceData.label.toLowerCase()}.`);
      return;
    }

    setPendingMessage(`${selectedResourceData.label} deleted.`);
    await refreshResourceList();
  }

  async function refreshDailyReports() {
    const token = getAccessToken();
    if (!token) {
      return;
    }

    const headers = {
      Authorization: `Bearer ${token}`,
      "X-Tenant-ID": getTenantId(),
    };

    const response = await fetch(`${getApiBaseUrl()}/api/daily-field-reports`, { headers });
    if (!response.ok) {
      return;
    }

    setDailyReports((await response.json()) as DailyReportSummary[]);
  }

  async function handleCreateDailyReport(event: React.FormEvent) {
    event.preventDefault();
    const token = getAccessToken();
    if (!token || !dailyReportForm.projectId) {
      setDailyReportMessage("Choose a project before creating a daily report.");
      return;
    }

    const headers = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-Tenant-ID": getTenantId(),
    };

    const response = await fetch(`${getApiBaseUrl()}/api/daily-field-reports`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        project_id: dailyReportForm.projectId,
        report_date: dailyReportForm.reportDate,
        company_name: dailyReportForm.companyName,
        reporting_supervisor: dailyReportForm.reportingSupervisor,
        shift_start_time: dailyReportForm.shiftStartTime,
        shift_end_time: dailyReportForm.shiftEndTime,
        work_performed: dailyReportForm.workPerformed,
        work_planned_for_tomorrow: dailyReportForm.workPlanned,
      }),
    });

    if (!response.ok) {
      setDailyReportMessage("Unable to create the daily report.");
      return;
    }

    setDailyReportMessage("Daily report created.");
    setDailyReportForm((current) => ({
      ...current,
      companyName: "",
      reportingSupervisor: "",
      shiftStartTime: "",
      shiftEndTime: "",
      workPerformed: "",
      workPlanned: "",
    }));
    await refreshDailyReports();
  }

  async function handleRouteAiInput(event: React.FormEvent) {
    event.preventDefault();
    const token = getAccessToken();
    if (!token) {
      return;
    }

    const headers = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-Tenant-ID": getTenantId(),
    };

    const response = await fetch(`${getApiBaseUrl()}/api/ai/workflow/route`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        note: aiRoutingInput,
        project_id: dailyReportForm.projectId || projects[0]?.id || undefined,
        report_date: dailyReportForm.reportDate,
      }),
    });

    if (!response.ok) {
      setAiRoutingMessage("The routing service was unable to process that note.");
      return;
    }

    const payload = (await response.json()) as { message?: string; customer_name?: string; material_name?: string; report_number?: string };
    setAiRoutingInput("");
    setAiRoutingMessage(payload.message || "Captured once and routed to the right places.");

    if (payload.customer_name) {
      setDailyReportForm((current) => ({ ...current, companyName: payload.customer_name || current.companyName }));
    }
    if (payload.report_number) {
      await refreshDailyReports();
    }
  }

  async function handleExportDailyReport(reportId: string) {
    const token = getAccessToken();
    if (!token) {
      return;
    }

    const response = await fetch(`${getApiBaseUrl()}/api/daily-field-reports/${reportId}/pdf`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-ID": getTenantId(),
      },
    });

    if (!response.ok) {
      setDailyReportMessage("Unable to export the PDF.");
      return;
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${reportId}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    setDailyReportMessage("PDF exported.");
  }

  async function handleDailyReportAction(reportId: string, action: "submit" | "review" | "return") {
    const token = getAccessToken();
    if (!token) {
      return;
    }

    const response = await fetch(`${getApiBaseUrl()}/api/daily-field-reports/${reportId}/${action}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-ID": getTenantId(),
      },
    });

    if (!response.ok) {
      setDailyReportMessage(`Unable to ${action} the report.`);
      return;
    }

    setDailyReportMessage(`Report ${action}ed.`);
    await refreshDailyReports();
  }

  return (
    <AppShell titleKey="workspace.title">
      <div className="card">
        <span className="auth-eyebrow">{t(locale, "workspace.roleWorkspace")}</span>
        <h2>{current.label}</h2>
        <p>{current.summary}</p>

        {canPreviewAllRoles ? (
          <label>
            {t(locale, "workspace.rolePreview")}
            <select value={activeRole} onChange={(e) => setActiveRole(e.target.value as RoleKey)}>
              {ROLE_WORKSPACES.map((role) => (
                <option key={role.key} value={role.key}>
                  {role.label}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      <div className="workspace-grid">
        {current.modules.map((module) => (
          <div className="workspace-module" key={module}>
            <strong>{module}</strong>
            <span>{t(locale, "workspace.moduleReady")}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>AI routing assistant</h3>
        <p>Paste one note and route it once into the customer, material, and daily report flows.</p>

        <form onSubmit={handleRouteAiInput} style={{ display: "grid", gap: "0.75rem", marginTop: "0.75rem" }}>
          <label htmlFor="ai-routing-assistant">AI routing assistant</label>
          <textarea
            id="ai-routing-assistant"
            aria-label="AI routing assistant"
            value={aiRoutingInput}
            onChange={(event) => setAiRoutingInput(event.target.value)}
            placeholder="Company: Northwind Civil\nSupervisor: Avery Chen\nMaterial: Concrete Mix\nWork: Completed excavation\nPlan: Pour foundation"
          />
          <button type="submit">Route once</button>
        </form>

        {aiRoutingMessage ? <p>{aiRoutingMessage}</p> : null}
      </div>

      <div className="card">
        <h3>Daily field reports</h3>
        <p>Create and review daily project reports from the workspace.</p>

        <form onSubmit={handleCreateDailyReport} style={{ display: "grid", gap: "0.75rem", marginTop: "0.75rem" }}>
          <label>
            Project
            <select value={dailyReportForm.projectId} onChange={(event) => setDailyReportForm((current) => ({ ...current, projectId: event.target.value }))}>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.project_name} {project.project_number ? `(${project.project_number})` : ""}
                </option>
              ))}
            </select>
          </label>

          <label>
            Report date
            <input type="date" value={dailyReportForm.reportDate} onChange={(event) => setDailyReportForm((current) => ({ ...current, reportDate: event.target.value }))} />
          </label>

          <label>
            Company
            <input value={dailyReportForm.companyName} onChange={(event) => setDailyReportForm((current) => ({ ...current, companyName: event.target.value }))} placeholder="Company name" />
          </label>

          <label>
            Supervisor
            <input value={dailyReportForm.reportingSupervisor} onChange={(event) => setDailyReportForm((current) => ({ ...current, reportingSupervisor: event.target.value }))} placeholder="Foreman or superintendent" />
          </label>

          <div style={{ display: "grid", gap: "0.75rem", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
            <label>
              Shift start
              <input value={dailyReportForm.shiftStartTime} onChange={(event) => setDailyReportForm((current) => ({ ...current, shiftStartTime: event.target.value }))} placeholder="06:00" />
            </label>
            <label>
              Shift end
              <input value={dailyReportForm.shiftEndTime} onChange={(event) => setDailyReportForm((current) => ({ ...current, shiftEndTime: event.target.value }))} placeholder="14:00" />
            </label>
          </div>

          <label>
            Work performed
            <textarea value={dailyReportForm.workPerformed} onChange={(event) => setDailyReportForm((current) => ({ ...current, workPerformed: event.target.value }))} placeholder="Summary of work completed" />
          </label>

          <label>
            Work planned for tomorrow
            <textarea value={dailyReportForm.workPlanned} onChange={(event) => setDailyReportForm((current) => ({ ...current, workPlanned: event.target.value }))} placeholder="Planned next steps" />
          </label>

          <button type="submit">Create report</button>
        </form>

        {dailyReportMessage ? <p>{dailyReportMessage}</p> : null}

        <ul>
          {dailyReports.length > 0 ? (
            dailyReports.map((report) => (
              <li key={report.id} style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <span>
                  {report.report_number} • {report.reporting_supervisor || "Unnamed supervisor"} • {report.status}
                </span>
                <span style={{ display: "flex", gap: "0.5rem" }}>
                  <button type="button" onClick={() => handleDailyReportAction(report.id, "submit")}>Submit</button>
                  <button type="button" onClick={() => handleDailyReportAction(report.id, "review")}>Review</button>
                  <button type="button" onClick={() => handleDailyReportAction(report.id, "return")}>Return</button>
                  <button type="button" onClick={() => handleExportDailyReport(report.id)}>Export PDF</button>
                </span>
              </li>
            ))
          ) : (
            <li>No daily reports yet.</li>
          )}
        </ul>
      </div>

      <div className="card">
        <h3>Platform resources</h3>
        <div className="workspace-grid">
          {resources.map((resource) => (
            <button key={resource.key} className={`workspace-module ${selectedResource === resource.key ? "is-active" : ""}`} onClick={() => setSelectedResource(resource.key)}>
              <strong>{resource.label}</strong>
              <span>{resource.accessor.length} {resource.label.toLowerCase()}</span>
            </button>
          ))}
        </div>

        <div className="card" style={{ marginTop: "1rem" }}>
          <h4>{selectedResourceData.label}</h4>
          <p>{selectedResourceData.summary}</p>

          <form onSubmit={handleCreateResource} style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem", marginBottom: "0.75rem" }}>
            <input aria-label={`${selectedResourceData.label} name`} value={draftName} onChange={(event) => setDraftName(event.target.value)} placeholder={selectedResourceData.placeholder} />
            <button type="submit">Create</button>
          </form>

          {pendingMessage ? <p>{pendingMessage}</p> : null}

          <ul>
            {selectedResourceData.accessor.length > 0 ? (
              selectedResourceData.accessor.slice(0, 5).map((item) => {
                const currentValue = item.name || item.unit_number || item.contact_name || item.id;
                return (
                  <li key={item.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem", marginBottom: "0.5rem" }}>
                    {editingId === item.id ? (
                      <>
                        <input aria-label={`${selectedResourceData.label} edit`} value={editValue} onChange={(event) => setEditValue(event.target.value)} />
                        <button type="button" onClick={() => handleSaveEdit(item.id)}>Save</button>
                      </>
                    ) : (
                      <span>{currentValue}</span>
                    )}
                    <span style={{ display: "flex", gap: "0.5rem" }}>
                      <button type="button" onClick={() => {
                        setEditingId(item.id);
                        setEditValue(currentValue);
                      }}>
                        Edit
                      </button>
                      <button type="button" onClick={() => handleDelete(item.id)}>Delete</button>
                    </span>
                  </li>
                );
              })
            ) : (
              <li>No records available yet.</li>
            )}
          </ul>
        </div>
      </div>

      <div className="card">
        <h3>{t(locale, "workspace.allRoleWorkspaces")}</h3>
        <div className="workspace-chip-row">
          {ROLE_WORKSPACES.map((role) => (
            <button key={role.key} className={`workspace-chip ${activeRole === role.key ? "is-active" : ""}`} onClick={() => setActiveRole(role.key)}>
              {role.label}
            </button>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
