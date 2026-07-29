"use client";

import Link from "next/link";
import React, { useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { listTickets, type Ticket } from "@/lib/tickets";

type QueueFilter = "all" | "mechanic" | "material";

function isMechanicQueueTicket(ticket: Ticket): boolean {
  const destination = (ticket.destination || "").toLowerCase();
  const number = (ticket.ticket_number || "").toUpperCase();
  return destination.includes("mechanic") || number.startsWith("MECH-");
}

function isMaterialQueueTicket(ticket: Ticket): boolean {
  const destination = (ticket.destination || "").toLowerCase();
  const number = (ticket.ticket_number || "").toUpperCase();
  return destination.includes("material") || number.startsWith("MAT-");
}

export default function DailyProductionQueuePage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [queueFilter, setQueueFilter] = useState<QueueFilter>("all");

  const queueTickets = useMemo(() => {
    const autoTickets = tickets.filter((ticket) => isMechanicQueueTicket(ticket) || isMaterialQueueTicket(ticket));
    if (queueFilter === "mechanic") {
      return autoTickets.filter(isMechanicQueueTicket);
    }
    if (queueFilter === "material") {
      return autoTickets.filter(isMaterialQueueTicket);
    }
    return autoTickets;
  }, [tickets, queueFilter]);

  const mechanicCount = useMemo(() => tickets.filter(isMechanicQueueTicket).length, [tickets]);
  const materialCount = useMemo(() => tickets.filter(isMaterialQueueTicket).length, [tickets]);

  const refreshQueue = async () => {
    setLoading(true);
    setMessage("");
    try {
      const data = await listTickets();
      setTickets(data);
      setMessage("Queue refreshed.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unable to load queue tickets.";
      setMessage(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell titleKey="modules.title">
      <div className="space-y-6 p-6">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h1 className="text-2xl font-bold text-slate-900">Mechanic and Superintendent Queue</h1>
          <p className="mt-2 text-sm text-slate-600">
            Dedicated dashboard for auto-created daily production tickets for machine issues and material needs.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={refreshQueue}
              disabled={loading}
              className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60"
            >
              {loading ? "Refreshing..." : "Refresh Queue"}
            </button>
            <Link href="/daily-production" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Back to Daily Production Form
            </Link>
          </div>
          {message ? <p className="mt-3 text-sm text-slate-700">{message}</p> : null}
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Auto queue tickets</div>
            <div className="mt-2 text-3xl font-bold text-slate-900">{mechanicCount + materialCount}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Mechanic queue</div>
            <div className="mt-2 text-3xl font-bold text-amber-700">{mechanicCount}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Material queue</div>
            <div className="mt-2 text-3xl font-bold text-green-700">{materialCount}</div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="mb-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setQueueFilter("all")}
              className={`rounded-lg px-3 py-1 text-sm font-semibold ${queueFilter === "all" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700"}`}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => setQueueFilter("mechanic")}
              className={`rounded-lg px-3 py-1 text-sm font-semibold ${queueFilter === "mechanic" ? "bg-amber-700 text-white" : "bg-amber-100 text-amber-800"}`}
            >
              Mechanic
            </button>
            <button
              type="button"
              onClick={() => setQueueFilter("material")}
              className={`rounded-lg px-3 py-1 text-sm font-semibold ${queueFilter === "material" ? "bg-green-700 text-white" : "bg-green-100 text-green-800"}`}
            >
              Material
            </button>
          </div>

          <div className="space-y-3">
            {queueTickets.length === 0 ? (
              <p className="text-sm text-slate-600">No queue tickets found for this filter. Click Refresh Queue.</p>
            ) : (
              queueTickets.map((ticket) => {
                const queueTag = isMechanicQueueTicket(ticket)
                  ? "Mechanic"
                  : isMaterialQueueTicket(ticket)
                    ? "Material"
                    : "Other";

                return (
                  <div key={ticket.id} className="rounded-lg border border-slate-200 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="font-semibold text-slate-900">{ticket.ticket_number || ticket.id}</div>
                        <div className="text-sm text-slate-600">{ticket.material || "n/a"} • {ticket.destination || "n/a"}</div>
                      </div>
                      <div className="text-right">
                        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">{queueTag}</span>
                        <div className="mt-1 text-xs text-slate-500">Status: {ticket.status}</div>
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-slate-700 whitespace-pre-wrap">{ticket.notes || "No notes"}</p>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
