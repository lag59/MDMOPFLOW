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
  const pathname = usePathname();
  const currentPath = pathname || "";

  useEffect(() => { setLocaleState(getLocale()); }, []);

  const title = useMemo(() => t(locale, titleKey), [locale, titleKey]);

  function isActive(href: string) {
    if (href === "/dashboard") return currentPath === href;
    return currentPath.startsWith(href);
  }

  return (
    <div className="shell">
      {/* ── Sidebar ── */}
      <aside className="side">
        <div className="brand-wrap">
          <div className="brand">MDM OpsFlow</div>
          <p className="brand-subtitle">AI Operating System for Construction</p>
        </div>
        <nav className="nav">
          {NAV_ITEMS.map((group) => (
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
        </nav>
      </aside>

      {/* ── Top bar ── */}
      <header className="topbar">
        <h1 className="topbar-title">{title}</h1>
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
      <main className="main">{children}</main>
    </div>
  );
}
