"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";
import { useEffect, useMemo, useState } from "react";

import { clearSession } from "@/lib/auth";
import { Locale, getLocale, t } from "@/lib/i18n";

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

export default function AppShell({ titleKey, children }: AppShellProps) {
  const [locale, setLocaleState] = useState<Locale>("en");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [navSearch, setNavSearch] = useState("");
  const pathname = usePathname();
  const currentPath = pathname || "";

  useEffect(() => { setLocaleState(getLocale()); }, []);

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
  }, [currentPath]);

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
          <button
            className="btn-ghost"
            onClick={() => { clearSession(); window.location.href = "/login"; }}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Page body ── */}
      <main id="main-content" className="main">{children}</main>
    </div>
  );
}
