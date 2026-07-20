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
        <span className="auth-eyebrow">Company Profile</span>
        <div className="info-grid">
          <div className="info-item">
            <strong>Primary Contact</strong>
            <span>{me ? me.display_name : "-"}</span>
          </div>
          <div className="info-item">
            <strong>Title</strong>
            <span>{me ? me.title : "-"}</span>
          </div>
        </div>
      </div>
      <div className="top-actions">
        <button>{t(locale, "common.save")}</button>
      </div>
    </AppShell>
  );
}
