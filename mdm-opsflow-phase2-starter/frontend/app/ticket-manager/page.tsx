'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import AppShell from '@/components/AppShell';
import AIProjectSuggestions from '@/components/AIProjectSuggestions';
import { getAccessToken, getTenantId } from '@/lib/auth';
import { getApiBaseUrl } from '@/lib/i18n';

interface Ticket {
  id: string;
  ticket_number: string;
  truck: string;
  driver: string;
  material: string;
  destination: string;
  project_id: string | null;
  status: string;
  revenue: number | null;
  created_at: string;
}

interface Project {
  id: string;
  project_name: string;
  project_number: string;
}

export default function TicketManagerPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [updating, setUpdating] = useState(false);
  const [filter, setFilter] = useState<'all' | 'unassigned' | 'assigned'>('unassigned');
  const [query, setQuery] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

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

      // Fetch tickets
      const ticketsRes = await fetch(`${baseUrl}/api/tickets`, { headers });
      if (!ticketsRes.ok) throw new Error(`Failed to fetch tickets (${ticketsRes.status})`);
      const ticketsData = await ticketsRes.json();
      setTickets(ticketsData);

      // Fetch projects
      const projectsRes = await fetch(`${baseUrl}/api/projects`, { headers });
      if (!projectsRes.ok) throw new Error(`Failed to fetch projects (${projectsRes.status})`);
      const projectsData = await projectsRes.json();
      setProjects(projectsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleAssignProject = async (ticketId: string, projectId: string) => {
    try {
      setUpdating(true);
      const token = getAccessToken();
      const tenantId = getTenantId();
      const baseUrl = getApiBaseUrl();

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (tenantId) headers['X-Tenant-ID'] = tenantId;

      const response = await fetch(`${baseUrl}/api/tickets/${ticketId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ project_id: projectId || null }),
      });

      if (!response.ok) throw new Error('Failed to assign project');

      // Update local state
      setTickets(
        tickets.map((t) =>
          t.id === ticketId ? { ...t, project_id: projectId || null } : t
        )
      );

      setSelectedTicketId(null);
      setSelectedProjectId('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign project');
    } finally {
      setUpdating(false);
    }
  };

  const formatCurrency = (value: number | null) => {
    if (value === null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
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

  const getProjectName = (projectId: string | null) => {
    if (!projectId) return 'Unassigned';
    const project = projects.find((p) => p.id === projectId);
    return project?.project_name || 'Unknown';
  };

  const filteredTickets = tickets.filter((t) => {
    if (filter === 'unassigned') return !t.project_id;
    if (filter === 'assigned') return !!t.project_id;
    return true;
  }).filter((t) => {
    const search = query.trim().toLowerCase();
    if (!search) return true;
    const projectName = getProjectName(t.project_id).toLowerCase();
    return [t.ticket_number, t.truck, t.driver, t.material, t.destination, t.status, projectName]
      .join(' ')
      .toLowerCase()
      .includes(search);
  });

  const unassignedCount = tickets.filter((t) => !t.project_id).length;
  const assignedCount = tickets.filter((t) => !!t.project_id).length;

  return (
    <AppShell titleKey="tickets.title">
      <div className="space-y-6 p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Ticket Project Assignment</h1>
            <p className="text-slate-600 mt-1">Assign tickets to projects to track costs and profitability</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200"
              onClick={() => void fetchData()}
            >
              Refresh
            </button>
            <Link href="/projects" className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700">
              View Projects
            </Link>
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
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">Find ticket quickly</label>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Search by ticket #, driver, truck, material, destination, project"
              />
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                onClick={() => setFilter('all')}
                className={`rounded-lg p-4 cursor-pointer transition-all duration-200 ${filter === 'all' ? 'bg-blue-100 border-2 border-blue-500 shadow-md' : 'bg-white border border-slate-200 hover:bg-slate-50 hover:border-blue-300 hover:shadow-md'}`}
                title="Show all tickets"
              >
                <p className="text-slate-600 text-sm">All Tickets</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">{tickets.length}</p>
              </button>

              <button
                onClick={() => setFilter('unassigned')}
                className={`rounded-lg p-4 cursor-pointer transition-all duration-200 ${filter === 'unassigned' ? 'bg-amber-100 border-2 border-amber-500 shadow-md' : 'bg-white border border-slate-200 hover:bg-slate-50 hover:border-amber-300 hover:shadow-md'}`}
                title="Show unassigned tickets"
              >
                <p className="text-slate-600 text-sm">Unassigned</p>
                <p className="text-3xl font-bold text-amber-600 mt-2">{unassignedCount}</p>
              </button>

              <button
                onClick={() => setFilter('assigned')}
                className={`rounded-lg p-4 cursor-pointer transition-all duration-200 ${filter === 'assigned' ? 'bg-green-100 border-2 border-green-500 shadow-md' : 'bg-white border border-slate-200 hover:bg-slate-50 hover:border-green-300 hover:shadow-md'}`}
                title="Show assigned tickets"
              >
                <p className="text-slate-600 text-sm">Assigned</p>
                <p className="text-3xl font-bold text-green-600 mt-2">{assignedCount}</p>
              </button>
            </div>

            {/* Tickets Table */}
            {filteredTickets.length === 0 ? (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-8 text-center">
                <p className="text-slate-600">
                  {filter === 'unassigned' && 'All tickets have been assigned to projects!'}
                  {filter === 'assigned' && 'No tickets assigned yet.'}
                  {filter === 'all' && 'No tickets found.'}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto bg-white rounded-lg shadow">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-100 border-b border-slate-300">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Ticket #</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Truck</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Driver</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Material</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Project</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-slate-900">Revenue</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Status</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTickets.map((ticket) => (
                      <tr key={ticket.id} className="border-b border-slate-200 hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-900 font-medium">{ticket.ticket_number}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{ticket.truck}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{ticket.driver}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{ticket.material}</td>
                        <td className="px-4 py-3 text-sm">
                          <span className="px-2 py-1 rounded bg-slate-100 text-slate-700 text-xs font-medium">
                            {getProjectName(ticket.project_id)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-700 text-right font-medium">
                          {formatCurrency(ticket.revenue)}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(ticket.status)}`}>
                            {ticket.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <button
                            onClick={() => {
                              setSelectedTicketId(ticket.id);
                              setSelectedProjectId(ticket.project_id || '');
                            }}
                            className="px-3 py-1 bg-blue-100 text-blue-700 rounded font-medium hover:bg-blue-200 hover:text-blue-900 transition-all duration-200 cursor-pointer active:scale-95"
                            title={ticket.project_id ? 'Change the project assigned to this ticket' : 'Assign this ticket to a project'}
                          >
                            {ticket.project_id ? '✎ Change' : '➕ Assign'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* Modal */}
        {selectedTicketId && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
              <h2 className="text-xl font-bold text-slate-900 mb-4">Assign Project to Ticket</h2>

              <div className="mb-4">
                <p className="text-sm text-slate-600 mb-2">
                  Ticket: <span className="font-semibold">{tickets.find((t) => t.id === selectedTicketId)?.ticket_number}</span>
                </p>
                {tickets.find((t) => t.id === selectedTicketId)?.destination && (
                  <p className="text-sm text-slate-600">
                    📍 Destination: <span className="font-semibold">{tickets.find((t) => t.id === selectedTicketId)?.destination}</span>
                  </p>
                )}
              </div>

              {/* AI Project Suggestions */}
              {selectedTicketId && (
                <AIProjectSuggestions
                  ticketId={selectedTicketId}
                  ticketDestination={tickets.find((t) => t.id === selectedTicketId)?.destination || ''}
                  onSelectProject={(projectId) => {
                    setSelectedProjectId(projectId);
                  }}
                />
              )}

              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-700 mb-2">Select Project</label>
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— Unassigned —</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.project_name} ({project.project_number})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setSelectedTicketId(null);
                    setSelectedProjectId('');
                  }}
                  className="flex-1 px-4 py-2 border-2 border-slate-300 text-slate-700 rounded-lg hover:bg-slate-100 hover:border-slate-400 transition-all duration-200 cursor-pointer font-medium"
                  disabled={updating}
                  title="Cancel without saving changes"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleAssignProject(selectedTicketId!, selectedProjectId)}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 hover:shadow-md transition-all duration-200 cursor-pointer font-medium disabled:bg-gray-400 disabled:cursor-not-allowed active:scale-95"
                  disabled={updating}
                  title="Assign this ticket to the selected project"
                >
                  {updating ? 'Assigning...' : '✓ Assign'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
