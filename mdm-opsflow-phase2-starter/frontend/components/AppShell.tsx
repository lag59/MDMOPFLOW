"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
  const pathname = usePathname();
  const currentPath = pathname || "";

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
        <p className="brand-subtitle">The AI Operating System for Construction</p>
        <nav className="nav">
          <Link className={currentPath === "/dashboard" ? "is-active" : ""} href="/dashboard">{labels.dashboard}</Link>
          <Link className={currentPath.startsWith("/projects") ? "is-active" : ""} href="/projects">{labels.projects}</Link>
          <Link className={currentPath === "/onboarding" ? "is-active" : ""} href="/onboarding">{labels.onboarding}</Link>
          <Link className={currentPath === "/settings/company" ? "is-active" : ""} href="/settings/company">{labels.company}</Link>
          <Link className={currentPath === "/settings/users" ? "is-active" : ""} href="/settings/users">{labels.users}</Link>
          <Link className={currentPath === "/platform-admin" ? "is-active" : ""} href="/platform-admin">{labels.platformAdmin}</Link>
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
