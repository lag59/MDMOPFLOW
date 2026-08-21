"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";
import { useEffect, useMemo, useState } from "react";

import { clearSession, getAccessToken, getTenantId, refreshSession, setTenantId } from "@/lib/auth";
import { Locale, getApiBaseUrl, getLocale, t } from "@/lib/i18n";

const NAV_ITEMS = [
  { group: "Workspace", items: [
    { href: "/dashboard",        label: "Dashboard",         icon: "⊞" },
    { href: "/modules",          label: "Modules",            icon: "⬡" },
  ]},
  { group: "Operations", items: [
    { href: "/project-manager",  label: "Project Manager",    icon: "🛠" },
    { href: "/estimator",        label: "Estimator",          icon: "📊" },
    { href: "/field-supervisor", label: "Field Supervisor",   icon: "📝" },
    { href: "/tickets",          label: "Tickets",            icon: "🎫" },
    { href: "/intake",           label: "Intake Hub",         icon: "📥" },
    { href: "/extraction-queue", label: "Extraction Queue",   icon: "🔍" },
    { href: "/projects",         label: "Projects",           icon: "📁" },
    { href: "/vendor",           label: "Vendor Portal",      icon: "🚚" },
  ]},
  { group: "Finance", items: [
    { href: "/accounting",       label: "Accounting",         icon: "💰" },
  ]},
  { group: "Management", items: [
    { href: "/owner",            label: "Owner Dashboard",    icon: "🏢" },
    { href: "/onboarding",       label: "Onboarding",         icon: "🚀" },
    { href: "/settings/company", label: "Company Settings",   icon: "⚙️" },
    { href: "/settings/users",   label: "User Settings",      icon: "👥" },
    { href: "/platform-admin",   label: "Platform Admin",     icon: "🛡" },
  ]},
];

type AppShellProps = { titleKey: string; children: React.ReactNode };

type AuthMeMembership = {
  tenant_id?: string;
};

type AuthMeResponse = {
  tenant_id?: string | null;
  memberships?: AuthMeMembership[];
};

type AiRouteResponse = {
  routed: boolean;
  customer_created: boolean;
  material_created: boolean;
  report_created: boolean;
  customer_name?: string | null;
  material_name?: string | null;
  report_number?: string | null;
  message: string;
};

export default function AppShell({ titleKey, children }: AppShellProps) {
  const [locale, setLocaleState] = useState<Locale>("en");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [navSearch, setNavSearch] = useState("");
  const [aiOpen, setAiOpen] = useState(false);
  const [aiNote, setAiNote] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiResult, setAiResult] = useState<AiRouteResponse | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const pathname = usePathname();
  const currentPath = pathname || "";

  useEffect(() => { setLocaleState(getLocale()); }, []);

  useEffect(() => {
    const token = getAccessToken();
    if (!token || getTenantId()) {
      return;
    }

    void fetch(`${getApiBaseUrl()}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((me: AuthMeResponse | null) => {
        if (!me) {
          return;
        }
        const resolvedTenantId = me.tenant_id || me.memberships?.[0]?.tenant_id || "";
        if (resolvedTenantId) {
          setTenantId(resolvedTenantId);
        }
      })
      .catch(() => {
        // Ignore hydration failures and let page-level requests show explicit errors.
      });
  }, []);

  const title = useMemo(() => t(locale, titleKey), [locale, titleKey]);

  const filteredNavGroups = useMemo(() => {
    const search = navSearch.trim().toLowerCase();
    if (!search) return NAV_ITEMS;
    return NAV_ITEMS
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => item.label.toLowerCase().includes(search)),
      }))
      .filter((group) => group.items.length > 0);
  }, [navSearch]);

  const activeNavLabel = useMemo(() => {
    for (const group of NAV_ITEMS) {
      const exact = group.items.find((item) => item.href === currentPath);
      if (exact) return exact.label;
    }
    for (const group of NAV_ITEMS) {
      const partial = group.items.find((item) => item.href !== "/dashboard" && currentPath.startsWith(item.href));
      if (partial) return partial.label;
    }
    return "Workspace";
  }, [currentPath]);

  useEffect(() => {
    setMobileNavOpen(false);
    setAiOpen(false);
  }, [currentPath]);

  function authHeaders(): Record<string, string> {
    return {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json",
      "X-Tenant-ID": getTenantId(),
    };
  }

  async function submitGlobalAiCapture(event: React.FormEvent) {
    event.preventDefault();
    const note = aiNote.trim();
    if (!note || aiBusy) {
      return;
    }

    setAiBusy(true);
    setAiError(null);
    setAiResult(null);

    try {
      let response = await fetch(`${getApiBaseUrl()}/api/ai/workflow/route`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ note }),
      });

      if (response.status === 401) {
        const refreshed = await refreshSession(getApiBaseUrl());
        if (refreshed) {
          response = await fetch(`${getApiBaseUrl()}/api/ai/workflow/route`, {
            method: "POST",
            headers: authHeaders(),
            body: JSON.stringify({ note }),
          });
        }
      }

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || "AI capture could not process that note.");
      }

      const payload = (await response.json()) as AiRouteResponse;
      setAiResult(payload);
      if (payload.routed) {
        setAiNote("");
      }
    } catch (error) {
      setAiError(error instanceof Error ? error.message : "AI capture could not process that note.");
    } finally {
      setAiBusy(false);
    }
  }

  function isActive(href: string) {
    if (href === "/dashboard") return currentPath === href;
    return currentPath.startsWith(href);
  }

  return (
    <div className="shell">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      {mobileNavOpen ? <button type="button" className="mobile-overlay" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation" /> : null}

      {/* ── Sidebar ── */}
      <aside className={`side ${mobileNavOpen ? "mobile-open" : ""}`}>
        <div className="brand-wrap">
          <div className="brand">MDM OpsFlow</div>
          <p className="brand-subtitle">AI Operating System for Construction</p>
          <div className="nav-search-wrap">
            <input
              aria-label="Search modules"
              className="nav-search-input"
              placeholder="Search module"
              value={navSearch}
              onChange={(event) => setNavSearch(event.target.value)}
            />
          </div>
        </div>
        <nav className="nav">
          {filteredNavGroups.map((group) => (
            <React.Fragment key={group.group}>
              <div className="nav-section-label">{group.group}</div>
              {group.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={isActive(item.href) ? "is-active" : ""}
                >
                  <span className="nav-icon" aria-hidden>{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </React.Fragment>
          ))}
          {filteredNavGroups.length === 0 ? <p className="nav-empty">No modules match that search.</p> : null}
        </nav>
      </aside>

      {/* ── Top bar ── */}
      <header className="topbar">
        <div className="topbar-heading-wrap">
          <button type="button" className="mobile-nav-toggle" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation menu">
            Menu
          </button>
          <div>
            <h1 className="topbar-title">{title}</h1>
            <p className="topbar-subtitle">Current module: {activeNavLabel}</p>
          </div>
        </div>
        <div className="top-actions">
          <label className="global-search">
            <span aria-hidden>⌕</span>
            <input aria-label="Search documents, tickets, vendors" placeholder="Search documents, tickets, vendors..." />
          </label>
          <button type="button" className="ai-capture-toggle" onClick={() => setAiOpen((value) => !value)}>
            AI Capture
          </button>
          <Link href="/intake" className="top-upload-action">
            Upload
          </Link>
          <button
            className="btn-ghost"
            onClick={() => { clearSession(); window.location.href = "/login"; }}
          >
            Sign out
          </button>
        </div>
      </header>

      {aiOpen ? (
        <section className="ai-capture-panel" aria-label="AI capture assistant">
          <div className="ai-capture-card">
            <div className="ai-capture-head">
              <div>
                <h2>AI Capture</h2>
                <p>Paste once. OpsFlow creates the customer, material, or field report draft when it can.</p>
              </div>
              <button type="button" className="btn-ghost" onClick={() => setAiOpen(false)}>Close</button>
            </div>
            <form onSubmit={submitGlobalAiCapture} className="ai-capture-form">
              <textarea
                value={aiNote}
                onChange={(event) => setAiNote(event.target.value)}
                placeholder="Example: Company: Summit Peak Builders\nMaterial: 57 stone\nSupervisor: John\nWork performed: Imported subgrade and placed base rock"
                rows={6}
              />
              <div className="ai-capture-actions">
                <button type="submit" disabled={aiBusy || !aiNote.trim()}>{aiBusy ? "Routing..." : "Route with AI"}</button>
                <Link href="/intake" className="link-button">Upload document instead</Link>
              </div>
            </form>
            {aiResult ? (
              <div className="ai-capture-result">
                <strong>{aiResult.message}</strong>
                <ul>
                  <li>Customer: {aiResult.customer_created ? aiResult.customer_name || "created" : "no new record"}</li>
                  <li>Material: {aiResult.material_created ? aiResult.material_name || "created" : "no new record"}</li>
                  <li>Report: {aiResult.report_created ? aiResult.report_number || "draft created" : "no draft created"}</li>
                </ul>
              </div>
            ) : null}
            {aiError ? <div className="ai-capture-error">{aiError}</div> : null}
          </div>
        </section>
      ) : null}

      {/* ── Page body ── */}
      <main id="main-content" className="main">{children}</main>
    </div>
  );
}
