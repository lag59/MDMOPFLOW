'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

import AppShell from '@/components/AppShell';
import { getAccessToken, getTenantId } from '@/lib/auth';
import { getApiBaseUrl } from '@/lib/i18n';

interface ProjectCosts {
  total_tickets: number;
  total_revenue: number;
  total_fuel_cost: number;
  total_net_tons: number;
  total_cubic_yards: number;
  avg_revenue_per_ton: number;
}

interface ProjectProfitability {
  project_id: string;
  project_name: string;
  status: string;
  contract_amount: number;
  budgeted_cost: number;
  actual_cost: number;
  actual_revenue: number;
  contract_variance: number;
  budget_variance: number;
  gross_profit: number;
  profit_margin: number;
  cost_overrun: boolean;
  revenue_shortfall: boolean;
  ticket_count: number;
  total_tons: number;
  total_cubic_yards: number;
}

export default function ProjectDashboard() {
  const params = useParams();
  const projectId = (params?.id as string) || '';

  const [profitability, setProfitability] = useState<ProjectProfitability | null>(null);
  const [costs, setCosts] = useState<ProjectCosts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;

    const fetchData = async () => {
      try {
        setLoading(true);
        const token = getAccessToken();
        const tenantId = getTenantId();
        const baseUrl = getApiBaseUrl();

        const headers: HeadersInit = {
          'Content-Type': 'application/json',
        };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (tenantId) headers['X-Tenant-ID'] = tenantId;

        // Fetch profitability
        const profRes = await fetch(`${baseUrl}/api/projects/${projectId}/profitability`, { headers });
        if (!profRes.ok) throw new Error(`Profitability fetch failed: ${profRes.status}`);
        const profData = await profRes.json();
        setProfitability(profData);

        // Fetch costs
        const costsRes = await fetch(`${baseUrl}/api/projects/${projectId}/costs`, { headers });
        if (!costsRes.ok) throw new Error(`Costs fetch failed: ${costsRes.status}`);
        const costsData = await costsRes.json();
        setCosts(costsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [projectId]);

  if (loading)
    return (
      <div className="flex items-center justify-center p-8">
        <div>Loading project dashboard...</div>
      </div>
    );

  if (error)
    return (
      <div className="flex items-center justify-center p-8 bg-red-50 border border-red-200 rounded-lg">
        <div className="text-red-800">Error: {error}</div>
      </div>
    );

  if (!profitability || !costs) return null;

  // Determine status color
  const getStatusColor = () => {
    if (profitability.profit_margin >= 20) return 'text-green-700 bg-green-50';
    if (profitability.profit_margin >= 10) return 'text-amber-700 bg-amber-50';
    return 'text-red-700 bg-red-50';
  };

  const formatCurrency = (value: number | string) => {
    const num = typeof value === 'string' ? parseFloat(value) : value;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(num);
  };

  const formatPercent = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  const formatNumber = (value: number) => {
    return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
  };

  return (
    <AppShell titleKey="projects.title">
      <div className="space-y-6 p-6">
        {/* Navigation */}
        <div className="mb-4">
          <Link href="/projects" className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline text-sm font-medium transition-all cursor-pointer group">
            <span className="group-hover:-translate-x-1 transition-transform">←</span> Back to Projects
          </Link>
        </div>

        {loading && (
          <div className="flex items-center justify-center p-8">
            <div>Loading project dashboard...</div>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center p-8 bg-red-50 border border-red-200 rounded-lg">
            <div className="text-red-800">Error: {error}</div>
          </div>
        )}

        {!loading && !error && profitability && costs && (
          <>
            {/* Header */}
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-600 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-slate-900">{profitability.project_name}</h1>
                  <p className="text-slate-500 mt-1">Project ID: {projectId}</p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => window.location.href = `/projects/${projectId}/tickets`}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 hover:shadow-md transition-all duration-200 text-sm font-medium cursor-pointer active:scale-95"
                    title="View all tickets assigned to this project"
                  >
                    📋 View Tickets
                  </button>
                  <div className={`px-4 py-2 rounded-full font-semibold ${getStatusColor()}`}>
                    {formatPercent(profitability.profit_margin)} Margin
                  </div>
                </div>
              </div>
            </div>

            {/* Alerts */}
            {profitability.cost_overrun && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-800 font-semibold">⚠️ Budget Warning</p>
                <p className="text-red-700 mt-1">
                  Actual costs ({formatCurrency(profitability.actual_cost)}) exceed budgeted costs (
                  {formatCurrency(profitability.budgeted_cost)}) by{' '}
                  {formatCurrency(profitability.actual_cost - profitability.budgeted_cost)}.
                </p>
              </div>
            )}

            {profitability.revenue_shortfall && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <p className="text-amber-800 font-semibold">📊 Revenue Shortfall</p>
                <p className="text-amber-700 mt-1">
                  Actual revenue ({formatCurrency(profitability.actual_revenue)}) is below contract amount (
                  {formatCurrency(profitability.contract_amount)}) by{' '}
                  {formatCurrency(profitability.contract_amount - profitability.actual_revenue)}.
                </p>
              </div>
            )}

            {/* Financial Summary Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-slate-500 text-sm font-medium uppercase tracking-wide">Contract Amount</p>
                <p className="text-2xl font-bold text-slate-900 mt-2">
                  {formatCurrency(profitability.contract_amount)}
                </p>
              </div>

              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-slate-500 text-sm font-medium uppercase tracking-wide">Actual Revenue</p>
                <p className="text-2xl font-bold text-green-600 mt-2">
                  {formatCurrency(profitability.actual_revenue)}
                </p>
                <p className="text-xs text-slate-400 mt-1">From {costs.total_tickets} tickets</p>
              </div>

              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-slate-500 text-sm font-medium uppercase tracking-wide">Budgeted Cost</p>
                <p className="text-2xl font-bold text-slate-900 mt-2">
                  {formatCurrency(profitability.budgeted_cost)}
                </p>
              </div>

              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-slate-500 text-sm font-medium uppercase tracking-wide">Actual Cost</p>
                <p className="text-2xl font-bold text-slate-900 mt-2">
                  {formatCurrency(profitability.actual_cost)}
                </p>
              </div>
            </div>

            {/* Profitability Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-white rounded-lg shadow p-6 border-t-4 border-green-500">
                <p className="text-slate-500 text-sm font-medium uppercase tracking-wide">Gross Profit</p>
                <p className="text-4xl font-bold text-green-600 mt-3">
                  {formatCurrency(profitability.gross_profit)}
                </p>
                <p className="text-slate-600 mt-2">
                  <strong>Profit Margin:</strong> {formatPercent(profitability.profit_margin)}
                </p>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between items-center">
                      <p className="text-slate-600 font-medium">Contract Variance</p>
                      <p
                        className={`font-bold text-lg ${
                          profitability.contract_variance > 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {formatCurrency(profitability.contract_variance)}
                      </p>
                    </div>
                  </div>

                  <div className="border-t border-slate-200 pt-4">
                    <div className="flex justify-between items-center">
                      <p className="text-slate-600 font-medium">Budget Variance</p>
                      <p
                        className={`font-bold text-lg ${
                          profitability.budget_variance > 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {formatCurrency(profitability.budget_variance)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Volume & Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-slate-500 text-sm font-medium uppercase tracking-wide">Total Tons</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">
                  {formatNumber(Number(costs.total_net_tons))}
                </p>
              </div>

              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-slate-500 text-sm font-medium uppercase tracking-wide">Total Cubic Yards</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">
                  {formatNumber(Number(costs.total_cubic_yards))}
                </p>
              </div>

              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-slate-500 text-sm font-medium uppercase tracking-wide">Avg Revenue/Ton</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">
                  {formatCurrency(Number(costs.avg_revenue_per_ton))}
                </p>
              </div>
            </div>

            {/* Activity Summary */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold text-slate-900 mb-4">Activity Summary</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <p className="text-sm text-slate-500">Total Tickets</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">{costs.total_tickets}</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-slate-500">Avg Cost/Ticket</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">
                    {formatCurrency(profitability.actual_cost / (costs.total_tickets || 1))}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-slate-500">Avg Revenue/Ticket</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">
                    {formatCurrency(profitability.actual_revenue / (costs.total_tickets || 1))}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-slate-500">Status</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1 capitalize">
                    {profitability.status}
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
