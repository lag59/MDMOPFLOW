'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import AppShell from '@/components/AppShell';
import { getAccessToken, getTenantId } from '@/lib/auth';
import { getApiBaseUrl } from '@/lib/i18n';
import ExtractionReview from '@/components/ExtractionReview';

interface ExtractionListItem {
  id: string;
  status: string;
  document_type: string;
  company_name: string;
  ticket_number: string;
  issue_count: number;
  avg_confidence: number;
  created_at: string;
}

export default function ExtractionQueuePage() {
  const [extractions, setExtractions] = useState<ExtractionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('review_pending');

  const queueMetrics = useMemo(() => {
    const total = extractions.length;
    const pending = extractions.filter((item) => item.status === 'review_pending').length;
    const submitted = extractions.filter((item) => item.status === 'review_submitted').length;
    const flaggedIssues = extractions.filter((item) => item.issue_count > 0).length;

    return {
      total,
      pending,
      submitted,
      flaggedIssues,
    };
  }, [extractions]);

  const fetchExtractions = async () => {
    try {
      setLoading(true);
      const token = getAccessToken();
      const tenantId = getTenantId();
      const baseUrl = getApiBaseUrl();

      const response = await fetch(
        `${baseUrl}/api/extractions?status_filter=${statusFilter}&limit=50`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-ID': tenantId,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch extractions');
      }

      const data = await response.json();
      setExtractions(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExtractions();
  }, [statusFilter]);

  const ConfidenceBadge = ({ confidence }: { confidence: number }) => {
    let bgColor = 'bg-gray-200';
    let textColor = 'text-gray-700';

    if (confidence >= 0.8) {
      bgColor = 'bg-green-100';
      textColor = 'text-green-700';
    } else if (confidence >= 0.6) {
      bgColor = 'bg-yellow-100';
      textColor = 'text-yellow-700';
    } else if (confidence > 0) {
      bgColor = 'bg-red-100';
      textColor = 'text-red-700';
    }

    return (
      <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${bgColor} ${textColor}`}>
        {Math.round(confidence * 100)}%
      </span>
    );
  };

  const StatusBadge = ({ status }: { status: string }) => {
    const colors: Record<string, { bg: string; text: string }> = {
      review_pending: { bg: 'bg-blue-100', text: 'text-blue-700' },
      review_submitted: { bg: 'bg-purple-100', text: 'text-purple-700' },
      approved: { bg: 'bg-green-100', text: 'text-green-700' },
      distributed: { bg: 'bg-cyan-100', text: 'text-cyan-700' },
      rejected: { bg: 'bg-red-100', text: 'text-red-700' },
    };

    const color = colors[status] || colors.review_pending;

    return (
      <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${color.bg} ${color.text}`}>
        {status.replace('_', ' ')}
      </span>
    );
  };

  if (selectedId) {
    const selected = extractions.find((e) => e.id === selectedId);
    return (
      <AppShell titleKey="intake.title">
        <div className="card">
          <div className="section-header">
            <div>
              <h3>{selected?.status === 'review_submitted' ? 'Approve extraction' : 'Review extraction'}</h3>
              <p className="muted">Process extraction details and move this item through approval.</p>
            </div>
            <button onClick={() => setSelectedId(null)}>Back to queue</button>
          </div>
          {selected ? <StatusBadge status={selected.status} /> : null}
        </div>

        <ExtractionReview
          extractionId={selectedId}
          onReviewSubmitted={() => {
            setSelectedId(null);
            fetchExtractions();
          }}
        />
      </AppShell>
    );
  }

  return (
    <AppShell titleKey="intake.title">
      <div className="card">
        <span className="auth-eyebrow">Extraction module</span>
        <h2>Extraction queue</h2>
        <p className="muted">Review extracted documents, resolve quality issues, and move approved records downstream.</p>
        <div className="top-actions" style={{ marginTop: '1rem', flexWrap: 'wrap' }}>
          <Link className="link-button" href="/intake">
            Intake
          </Link>
          <Link className="link-button" href="/tickets">
            Tickets
          </Link>
          <Link className="link-button" href="/modules">
            Back to modules
          </Link>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <span className="auth-eyebrow">Total</span>
          <div className="metric">{queueMetrics.total}</div>
          <div className="metric-note">Extractions in the current filtered window</div>
        </div>
        <div className="card">
          <span className="auth-eyebrow">Pending review</span>
          <div className="metric">{queueMetrics.pending}</div>
          <div className="metric-note">Items waiting for reviewer action</div>
        </div>
        <div className="card">
          <span className="auth-eyebrow">Submitted</span>
          <div className="metric">{queueMetrics.submitted}</div>
          <div className="metric-note">Items waiting for approver decision</div>
        </div>
        <div className="card">
          <span className="auth-eyebrow">Flagged</span>
          <div className="metric">{queueMetrics.flaggedIssues}</div>
          <div className="metric-note">Items with one or more validation issues</div>
        </div>
      </div>

      <div className="card">
        <div className="section-header">
          <h3>Queue controls</h3>
        </div>
        <div className="replay-action-row" style={{ marginBottom: '1rem' }}>
          <label className="font-semibold text-gray-700">Filter by status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="review_pending">Pending Review</option>
            <option value="review_submitted">Submitted for Approval</option>
            <option value="approved">Approved</option>
            <option value="distributed">Distributed</option>
            <option value="rejected">Rejected</option>
          </select>
          <div className="text-sm text-gray-600">
            Total: {extractions.length} extractions
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Error: {error}
          </div>
        )}

        {loading && (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading extractions...</p>
          </div>
        )}

        {!loading && extractions.length === 0 && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-500 text-lg">No extractions found</p>
            <p className="text-gray-400 text-sm mt-2">Check back later or change the filter</p>
          </div>
        )}

        {!loading && extractions.length > 0 && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Company</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Document Type</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Ticket #</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Confidence</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Issues</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Status</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Created</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Action</th>
                </tr>
              </thead>
              <tbody>
                {extractions.map((extraction) => (
                  <tr key={extraction.id} className="border-b hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-900">{extraction.company_name}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      <span className="inline-block px-2 py-1 bg-gray-100 rounded text-xs">
                        {extraction.document_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 font-mono">
                      {extraction.ticket_number || '—'}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <ConfidenceBadge confidence={extraction.avg_confidence} />
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {extraction.issue_count > 0 ? (
                        <span className="inline-block px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs font-semibold">
                          {extraction.issue_count} issue{extraction.issue_count !== 1 ? 's' : ''}
                        </span>
                      ) : (
                        <span className="text-green-600 text-xs">✓ No issues</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <StatusBadge status={extraction.status} />
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {new Date(extraction.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {extraction.status === 'review_pending' ? (
                        <button
                          onClick={() => setSelectedId(extraction.id)}
                          className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                        >
                          Review
                        </button>
                      ) : extraction.status === 'review_submitted' ? (
                        <button
                          onClick={() => setSelectedId(extraction.id)}
                          className="px-3 py-1 bg-purple-500 text-white rounded hover:bg-purple-600 text-sm"
                        >
                          Approve
                        </button>
                      ) : (
                        <button
                          onClick={() => setSelectedId(extraction.id)}
                          className="px-3 py-1 bg-gray-400 text-white rounded hover:bg-gray-500 text-sm"
                        >
                          View
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
