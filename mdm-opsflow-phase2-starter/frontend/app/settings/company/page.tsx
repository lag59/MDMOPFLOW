"use client";

import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

export default function CompanySettingsPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [displayName, setDisplayName] = useState("");
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setLocale(getLocale());
    fetch(`${getApiBaseUrl()}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
      },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        setDisplayName(data?.display_name ?? "");
        setTitle(data?.title ?? "");
      });
  }, []);

  async function saveProfile(): Promise<void> {
    setMessage("");

    if (displayName.trim().length < 2) {
      setMessage("Display name must be at least 2 characters.");
      return;
    }

    setIsSaving(true);
    const response = await fetch(`${getApiBaseUrl()}/api/auth/me`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
      },
      body: JSON.stringify({
        display_name: displayName.trim(),
        title: title.trim(),
      }),
    });

    if (!response.ok) {
      setMessage("Unable to save company profile.");
      setIsSaving(false);
      return;
    }

    const payload = await response.json();
    setDisplayName(payload.display_name ?? "");
    setTitle(payload.title ?? "");
    setMessage("Company profile updated.");
    setIsSaving(false);
  }

  return (
    <AppShell titleKey="settings.company">
      <div className="card">
        <span className="auth-eyebrow">Company Profile</span>
        <div className="info-grid">
          <div className="info-item">
            <strong>Primary Contact</strong>
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
          </div>
          <div className="info-item">
            <strong>Title</strong>
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </div>
        </div>
      </div>
      <div className="top-actions">
        <button onClick={saveProfile} disabled={isSaving}>
          {isSaving ? `${t(locale, "common.save")}...` : t(locale, "common.save")}
        </button>
      </div>
      {message ? <p>{message}</p> : null}
    </AppShell>
  );
}
