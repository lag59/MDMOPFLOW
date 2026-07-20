"use client";

import Link from "next/link";
import React from "react";
import { useEffect, useMemo, useState } from "react";

import { clearSession } from "@/lib/auth";
import { Locale, getLocale, setLocale, t } from "@/lib/i18n";

type AppShellProps = {
  titleKey: string;
  children: React.ReactNode;
};

export default function AppShell({ titleKey, children }: AppShellProps) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    setLocaleState(getLocale());
  }, []);

  const labels = useMemo(
    () => ({
      appName: t(locale, "common.appName"),
      dashboard: t(locale, "nav.dashboard"),
      projects: t(locale, "nav.projects"),
      onboarding: t(locale, "nav.onboarding"),
      company: t(locale, "nav.company"),
      users: t(locale, "nav.users"),
      platformAdmin: t(locale, "nav.platformAdmin"),
      logout: t(locale, "common.logout"),
      english: t(locale, "common.english"),
      spanish: t(locale, "common.spanish"),
      title: t(locale, titleKey),
    }),
    [locale, titleKey]
  );

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">{labels.appName}</div>
        <nav className="nav">
          <Link href="/dashboard">{labels.dashboard}</Link>
          <Link href="/projects">{labels.projects}</Link>
          <Link href="/onboarding">{labels.onboarding}</Link>
          <Link href="/settings/company">{labels.company}</Link>
          <Link href="/settings/users">{labels.users}</Link>
          <Link href="/platform-admin">{labels.platformAdmin}</Link>
        </nav>
      </aside>
      <main className="main">
        <div className="top-row">
          <h1>{labels.title}</h1>
          <div className="top-actions">
            <button
              onClick={() => {
                const next = locale === "en" ? "es" : "en";
                setLocale(next);
                setLocaleState(next);
              }}
            >
              {locale === "en" ? labels.spanish : labels.english}
            </button>
            <button
              onClick={() => {
                clearSession();
                window.location.href = "/login";
              }}
            >
              {labels.logout}
            </button>
          </div>
        </div>
        {children}
      </main>
    </div>
  );
}
