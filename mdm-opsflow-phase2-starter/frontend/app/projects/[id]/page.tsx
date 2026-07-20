"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

type Project = {
  id: string;
  project_name: string;
  project_number: string;
  customer: string;
  address: string;
  project_manager: string;
  status: string;
  description: string;
};

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [projectName, setProjectName] = useState("");
  const [projectNumber, setProjectNumber] = useState("");
  const [customer, setCustomer] = useState("");
  const [address, setAddress] = useState("");
  const [projectManager, setProjectManager] = useState("");
  const [status, setStatus] = useState("planning");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const locale = getLocale();

  useEffect(() => {
    if (!params?.id) {
      return;
    }

    fetch(`${getApiBaseUrl()}/api/projects/${params.id}`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
      },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        setProject(data);
        if (!data) {
          return;
        }
        setProjectName(data.project_name || "");
        setProjectNumber(data.project_number || "");
        setCustomer(data.customer || "");
        setAddress(data.address || "");
        setProjectManager(data.project_manager || "");
        setStatus(data.status || "planning");
        setDescription(data.description || "");
      });
  }, [params?.id]);

  async function saveChanges(): Promise<void> {
    if (!params?.id) {
      return;
    }

    setMessage("");
    setIsSaving(true);
    const response = await fetch(`${getApiBaseUrl()}/api/projects/${params.id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
      },
      body: JSON.stringify({
        project_name: projectName,
        project_number: projectNumber,
        customer,
        address,
        project_manager: projectManager,
        status,
        description,
      }),
    });

    if (!response.ok) {
      setMessage("Unable to save project changes.");
      setIsSaving(false);
      return;
    }

    const updated = await response.json();
    setProject(updated);
    setMessage("Project updated.");
    setIsSaving(false);
  }

  async function deleteProject(): Promise<void> {
    if (!params?.id) {
      return;
    }

    const confirmed = window.confirm("Delete this project?");
    if (!confirmed) {
      return;
    }

    setMessage("");
    setIsDeleting(true);
    const response = await fetch(`${getApiBaseUrl()}/api/projects/${params.id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
      },
    });

    if (!response.ok) {
      setMessage("Unable to delete project.");
      setIsDeleting(false);
      return;
    }

    window.location.href = "/projects";
  }

  return (
    <AppShell titleKey="projects.title">
      {!project ? (
        <p>{t(locale, "common.loading")}</p>
      ) : (
        <>
          <div className="card">
            <div className="section-header">
              <h3>{projectName}</h3>
              <span className={`status-pill status-${status}`}>{status.replace("_", " ")}</span>
            </div>
            <div className="info-grid">
              <div className="info-item">
                <strong>{t(locale, "projects.projectNumber")}</strong>
                <span>{projectNumber || "-"}</span>
              </div>
              <div className="info-item">
                <strong>{t(locale, "projects.customer")}</strong>
                <span>{customer || "-"}</span>
              </div>
            </div>
          </div>

          <div className="card form-grid">
            <div className="two-col">
              <input value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder={t(locale, "projects.projectName")} />
              <input value={projectNumber} onChange={(e) => setProjectNumber(e.target.value)} placeholder={t(locale, "projects.projectNumber")} />
            </div>
            <div className="two-col">
              <input value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder={t(locale, "projects.customer")} />
              <input
                value={projectManager}
                onChange={(e) => setProjectManager(e.target.value)}
                placeholder={t(locale, "projects.projectManager")}
              />
            </div>
            <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder={t(locale, "projects.address")} />
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="planning">planning</option>
              <option value="active">active</option>
              <option value="on_hold">on_hold</option>
              <option value="complete">complete</option>
              <option value="cancelled">cancelled</option>
            </select>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t(locale, "projects.description")}
            />
            <div className="top-actions">
              <button onClick={saveChanges} disabled={isSaving || isDeleting}>
                {isSaving ? "Saving..." : "Save Changes"}
              </button>
              <button onClick={deleteProject} disabled={isSaving || isDeleting}>
                {isDeleting ? "Deleting..." : "Delete Project"}
              </button>
            </div>
            {message ? <p>{message}</p> : null}
          </div>
        </>
      )}
    </AppShell>
  );
}
