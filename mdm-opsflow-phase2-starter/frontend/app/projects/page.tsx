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

export default function ProjectsPage() {
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
    <AppShell titleKey="projects.title">
      <div className="section-header">
        <h3>{t(locale, "projects.title")}</h3>
        <Link className="link-button" href="/projects/new">{t(locale, "projects.new")}</Link>
      </div>
      <div className="list">
        {projects.map((project) => (
          <Link href={`/projects/${project.id}`} key={project.id} className="list-item is-link">
            <strong>{project.project_name}</strong>
            <span className="muted">{project.project_number}</span>
            <span className={`status-pill status-${project.status}`}>{project.status.replace("_", " ")}</span>
          </Link>
        ))}
      </div>
    </AppShell>
  );
}
