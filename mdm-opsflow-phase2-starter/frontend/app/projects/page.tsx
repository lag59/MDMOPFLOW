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
      <p>
        <Link href="/projects/new">{t(locale, "projects.new")}</Link>
      </p>
      <div className="list">
        {projects.map((project) => (
          <Link href={`/projects/${project.id}`} key={project.id} className="list-item">
            <strong>{project.project_name}</strong>
            <span>{project.project_number}</span>
            <span>{project.status}</span>
          </Link>
        ))}
      </div>
    </AppShell>
  );
}
