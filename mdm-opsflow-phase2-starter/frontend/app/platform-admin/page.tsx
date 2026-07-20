"use client";

import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

type Overview = {
  tenants: number;
  users: number;
  projects: number;
};

export default function PlatformAdminPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [authorized, setAuthorized] = useState(false);
  const [overview, setOverview] = useState<Overview | null>(null);

  useEffect(() => {
    setLocale(getLocale());
    const token = getAccessToken();
    fetch(`${getApiBaseUrl()}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((me) => {
        if (!me || me.platform_role !== "platform_super_admin") {
          setAuthorized(false);
          return;
        }
        setAuthorized(true);
        fetch(`${getApiBaseUrl()}/api/admin/overview`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
          .then((res) => (res.ok ? res.json() : null))
          .then((data) => setOverview(data));
      });
  }, []);

  return (
    <AppShell titleKey="platformAdmin.title">
      {!authorized ? (
        <p>{t(locale, "platformAdmin.denied")}</p>
      ) : (
        <div className="grid">
          <div className="card">{t(locale, "platformAdmin.tenants")}<div className="metric">{overview?.tenants ?? 0}</div></div>
          <div className="card">{t(locale, "platformAdmin.users")}<div className="metric">{overview?.users ?? 0}</div></div>
          <div className="card">{t(locale, "platformAdmin.projects")}<div className="metric">{overview?.projects ?? 0}</div></div>
        </div>
      )}
    </AppShell>
  );
}
