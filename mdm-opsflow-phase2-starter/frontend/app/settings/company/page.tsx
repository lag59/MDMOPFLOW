"use client";

import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

export default function CompanySettingsPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [me, setMe] = useState<{ display_name: string; title: string } | null>(null);

  useEffect(() => {
    setLocale(getLocale());
    fetch(`${getApiBaseUrl()}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
      },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setMe(data));
  }, []);

  return (
    <AppShell titleKey="settings.company">
      <div className="card">
        <p>{me ? me.display_name : "-"}</p>
        <p>{me ? me.title : "-"}</p>
      </div>
      <button>{t(locale, "common.save")}</button>
    </AppShell>
  );
}
