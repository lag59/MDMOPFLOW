'use client';

import Link from 'next/link';
import React from 'react';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

import AppShell from '@/components/AppShell';
import { getAccessToken, getTenantId } from '@/lib/auth';
import { getApiBaseUrl } from '@/lib/i18n';

interface Ticket {
  id: string;
  ticket_number: string;
  truck: string;
  driver: string;
  material: string;
  origin: string;
  destination: string;
  project_id: string | null;
  status: string;
  revenue: number | null;
  fuel_cost: number | null;
  tons: number | null;
  volume_yards: number | null;
  created_at: string;
}

export default function ProjectTicketsPage() {
  const params = useParams();
  const projectId = (params?.id as string) || '';

  const [projectName, setProjectName] = useState('');
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      setError(null);
      setLoading(true);
      const token = getAccessToken();
      const tenantId = getTenantId();
      const baseUrl = getApiBaseUrl();

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (tenantId) headers['X-Tenant-ID'] = tenantId;

      // Fetch project details
      const projectRes = await fetch(`${baseUrl}/api/projects/${projectId}`, { headers });
      if (projectRes.ok) {
        const projectData = await projectRes.json();
        setProjectName(projectData.project_name);
      } else {
        throw new Error(`Failed to fetch project (${projectRes.status})`);
      }

      // Fetch project tickets
      const ticketsRes = await fetch(`${baseUrl}/api/projects/${projectId}/tickets`, { headers });
      if (ticketsRes.ok) {
        const ticketsData = await ticketsRes.json();
        setTickets(ticketsData);
      } else {
        // Fallback for backends that don't yet expose /projects/{id}/tickets.
        const allTicketsRes = await fetch(`${baseUrl}/api/tickets`, { headers });
        if (!allTicketsRes.ok) {
          throw new Error(`Failed to fetch tickets (${ticketsRes.status} / fallback ${allTicketsRes.status})`);
        }
        const allTicketsData = (await allTicketsRes.json()) as Ticket[];
        setTickets(allTicketsData.filter((ticket) => ticket.project_id === projectId));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number | null) => {
    if (value === null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatNumber = (value: number | null) => {
    if (value === null) return 'N/A';
    return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-800';
      case 'completed':
        return 'bg-blue-100 text-blue-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-slate-100 text-slate-800';
    }
  };

  return (
    <AppShell titleKey="projects.title">
      <div className="space-y-6 p-6">
        {/* Navigation */}
        <div className="mb-4">
          <Link href="/projects" className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline text-sm font-medium transition-all cursor-pointer group">
            <span className="group-hover:-translate-x-1 transition-transform">←</span> Back to Projects
          </Link>
          <Link href={`/projects/${projectId}/dashboard`} className="ml-4 inline-flex items-center gap-1 text-slate-600 hover:text-slate-800 hover:underline text-sm font-medium transition-all cursor-pointer group">
            <span className="group-hover:translate-x-1 transition-transform">→</span> Project Dashboard
          </Link>
        </div>

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Project Tickets</h1>
            <p className="text-slate-600 mt-1">{projectName}</p>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center p-8">
            <div>Loading tickets...</div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 font-semibold">Error: {error}</p>
          </div>
        )}

        {!loading && !error && (
          <>
            {tickets.length === 0 ? (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-8 text-center">
                <p className="text-slate-600">No tickets assigned to this project yet.</p>
                <Link href="/ticket-manager" className="text-blue-600 hover:text-blue-800 font-medium mt-2 inline-block">
                  Assign tickets to this project
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="bg-slate-100 border-b border-slate-300">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Ticket #</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Truck</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Driver</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Material</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Origin</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Destination</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-slate-900">Tons</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-slate-900">Yards</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-slate-900">Revenue</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-slate-900">Fuel Cost</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tickets.map((ticket) => (
                      <tr key={ticket.id} className="border-b border-slate-200 hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-900 font-medium">{ticket.ticket_number}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{ticket.truck}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{ticket.driver}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{ticket.material}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{ticket.origin}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{ticket.destination}</td>
                        <td className="px-4 py-3 text-sm text-slate-700 text-right">{formatNumber(ticket.tons)}</td>
                        <td className="px-4 py-3 text-sm text-slate-700 text-right">{formatNumber(ticket.volume_yards)}</td>
                        <td className="px-4 py-3 text-sm text-slate-700 text-right text-green-600 font-medium">
                          {formatCurrency(ticket.revenue)}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-700 text-right text-red-600 font-medium">
                          {formatCurrency(ticket.fuel_cost)}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(ticket.status)}`}>
                            {ticket.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-slate-50 border-t-2 border-slate-300 font-semibold">
                      <td colSpan={6} className="px-4 py-3 text-right text-slate-900">
                        Totals:
                      </td>
                      <td className="px-4 py-3 text-right text-slate-900">
                        {formatNumber(tickets.reduce((sum, t) => sum + (t.tons || 0), 0))}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-900">
                        {formatNumber(tickets.reduce((sum, t) => sum + (t.volume_yards || 0), 0))}
                      </td>
                      <td className="px-4 py-3 text-right text-green-600">
                        {formatCurrency(tickets.reduce((sum, t) => sum + (t.revenue || 0), 0))}
                      </td>
                      <td className="px-4 py-3 text-right text-red-600">
                        {formatCurrency(tickets.reduce((sum, t) => sum + (t.fuel_cost || 0), 0))}
                      </td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </>
        )}

        {/* Summary Stats */}
        {!loading && !error && tickets.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6 p-6 bg-slate-50 rounded-lg">
            <div className="text-center">
              <p className="text-slate-600 text-sm">Total Tickets</p>
              <p className="text-3xl font-bold text-slate-900 mt-2">{tickets.length}</p>
            </div>
            <div className="text-center">
              <p className="text-slate-600 text-sm">Total Tons</p>
              <p className="text-3xl font-bold text-slate-900 mt-2">
                {formatNumber(tickets.reduce((sum, t) => sum + (t.tons || 0), 0))}
              </p>
            </div>
            <div className="text-center">
              <p className="text-slate-600 text-sm">Total Revenue</p>
              <p className="text-3xl font-bold text-green-600 mt-2">
                {formatCurrency(tickets.reduce((sum, t) => sum + (t.revenue || 0), 0))}
              </p>
            </div>
            <div className="text-center">
              <p className="text-slate-600 text-sm">Total Fuel Cost</p>
              <p className="text-3xl font-bold text-red-600 mt-2">
                {formatCurrency(tickets.reduce((sum, t) => sum + (t.fuel_cost || 0), 0))}
              </p>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
