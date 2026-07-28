"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import AppShell from "@/components/AppShell";
import { getModuleDetail } from "@/lib/modules";

export default function ModuleDetailPage() {
  const params = useParams();
  const role = String(params?.role || "");
  const moduleSlug = String(params?.module || "");
  const detail = getModuleDetail(role, moduleSlug);

  if (!detail) {
    return (
      <AppShell titleKey="modules.title">
        <div className="space-y-4 p-6">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <h2 className="text-lg font-semibold text-red-900">Module route not found</h2>
            <p className="mt-1 text-sm text-red-800">The requested role/module combination does not exist in the current module catalog.</p>
          </div>
          <Link href="/modules" className="inline-flex text-sm font-semibold text-blue-700 hover:text-blue-900 hover:underline">
            Back to Modules
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell titleKey="modules.title">
      <div className="space-y-6 p-6">
        <div className="mb-2">
          <Link href="/modules" className="inline-flex text-sm font-semibold text-blue-700 hover:text-blue-900 hover:underline">
            Back to Modules
          </Link>
        </div>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{detail.roleLabel}</span>
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                detail.route.status === "live" ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"
              }`}
            >
              {detail.route.status === "live" ? "Live Module" : "Bridge Module"}
            </span>
          </div>

          <h1 className="text-3xl font-bold text-slate-900">{detail.moduleLabel}</h1>
          <p className="mt-2 text-sm text-slate-600">{detail.roleSummary}</p>
          <p className="mt-2 text-sm text-slate-700">{detail.route.helperText}</p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link
              href={detail.route.href}
              className="inline-flex items-center rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
            >
              Open Module Workspace
            </Link>
            <Link
              href="/modules"
              className="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              Browse Other Modules
            </Link>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
