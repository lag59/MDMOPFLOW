'use client';

import { useEffect, useState } from 'react';
import { getAccessToken, getTenantId } from '@/lib/auth';
import { getApiBaseUrl } from '@/lib/i18n';

interface ExtractionField {
  value: string | null;
  confidence: number;
  label: string;
}

interface ExtractionIssue {
  id: string;
  issue_type: string;
  field_name: string;
  severity: string;
  message: string;
  suggested_value: string | null;
  resolved: boolean;
  resolved_value: string | null;
}

interface Extraction {
  id: string;
  intake_item_id: string;
  status: string;
  document_type: string;
  mime_type: string;
  company_name: string;
  ticket_number: string;
  destination: string;
  destination_confidence: number;
  material: string;
  material_confidence: number;
  tons: number | null;
  invoice_total: number | null;
  review_notes: string;
  created_at: string;
}

interface PlacementSuggestionItem {
  item_id: string;
  destination_key: string;
  destination_label: string;
  destination_href: string;
  confidence: number;
  reason: string;
  signal_source: string;
}

interface ConflictCandidate {
  item_id: string;
  field_name: string;
  value: number;
  unit: string;
  document_type: string;
  document_subtype: string;
  source_text: string;
  page: number | null;
  confidence: number;
  created_at: string;
}

interface ConflictSuggestion {
  field_name: string;
  candidates: ConflictCandidate[];
  recommended: ConflictCandidate;
  reason: string;
}

interface FieldConfig {
  key: string;
  label: string;
  confidence: number;
  value: (item: Extraction) => string | null;
}

const DEFAULT_FIELD_CONFIDENCE = 0.75;

const FIELD_CONFIGS: Record<string, FieldConfig> = {
  company_name: {
    key: 'company_name',
    label: 'Company',
    confidence: 0.85,
    value: (item) => item.company_name || null,
  },
  ticket_number: {
    key: 'ticket_number',
    label: 'Ticket Number',
    confidence: 0.92,
    value: (item) => item.ticket_number || null,
  },
  destination: {
    key: 'destination',
    label: 'Destination',
    confidence: DEFAULT_FIELD_CONFIDENCE,
    value: (item) => item.destination || null,
  },
  material: {
    key: 'material',
    label: 'Material',
    confidence: 0.65,
    value: (item) => item.material || null,
  },
  tons: {
    key: 'tons',
    label: 'Tons',
    confidence: 0.88,
    value: (item) => (item.tons !== null ? String(item.tons) : null),
  },
  invoice_total: {
    key: 'invoice_total',
    label: 'Invoice Total',
    confidence: 0.83,
    value: (item) => (item.invoice_total !== null ? String(item.invoice_total) : null),
  },
};

function resolveIntentSchema(documentType: string, destinationKey: string | null): { label: string; fieldKeys: string[] } {
  const normalizedType = (documentType || '').toLowerCase();
  const normalizedDestination = (destinationKey || '').toLowerCase();

  if (normalizedDestination === 'tickets' || normalizedType.includes('ticket')) {
    return {
      label: 'Ticket extraction schema',
      fieldKeys: ['company_name', 'ticket_number', 'material', 'tons', 'destination'],
    };
  }

  if (normalizedDestination === 'accounting' || normalizedType.includes('invoice')) {
    return {
      label: 'Accounting extraction schema',
      fieldKeys: ['company_name', 'invoice_total', 'destination', 'ticket_number'],
    };
  }

  if (normalizedDestination === 'estimator' || ['bid', 'proposal', 'quote', 'estimate', 'takeoff', 'addendum'].some((token) => normalizedType.includes(token))) {
    return {
      label: 'Estimator extraction schema',
      fieldKeys: ['company_name', 'material', 'tons', 'destination', 'ticket_number'],
    };
  }

  return {
    label: 'General review schema',
    fieldKeys: ['company_name', 'destination', 'material', 'ticket_number', 'tons'],
  };
}

interface ExtractionReviewProps {
  extractionId: string;
  onReviewSubmitted?: () => void;
}

const ConfidenceBadge = ({ confidence }: { confidence: number }) => {
  let bgColor = 'bg-gray-200';
  let textColor = 'text-gray-700';
  let label = 'Missing';

  if (confidence >= 0.8) {
    bgColor = 'bg-green-100';
    textColor = 'text-green-700';
    label = 'High';
  } else if (confidence >= 0.6) {
    bgColor = 'bg-yellow-100';
    textColor = 'text-yellow-700';
    label = 'Medium';
  } else if (confidence > 0) {
    bgColor = 'bg-red-100';
    textColor = 'text-red-700';
    label = 'Low';
  }

  return (
    <span className={`inline-block px-2 py-1 rounded text-sm font-semibold ${bgColor} ${textColor}`}>
      {label} ({Math.round(confidence * 100)}%)
    </span>
  );
};

const EditableField = ({
  label,
  value,
  confidence,
  onEdit,
  suggestedValue,
}: {
  label: string;
  value: string | null;
  confidence: number;
  onEdit: (newValue: string) => void;
  suggestedValue?: string | null;
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value || '');

  const handleSave = () => {
    onEdit(editValue);
    setIsEditing(false);
  };

  const handleSuggest = () => {
    if (suggestedValue) {
      setEditValue(suggestedValue);
    }
  };

  return (
    <div className="mb-4 border rounded-lg p-4 bg-white">
      <div className="flex justify-between items-start mb-2">
        <label className="font-semibold text-gray-700">{label}</label>
        <ConfidenceBadge confidence={confidence} />
      </div>

      {isEditing ? (
        <div className="flex gap-2">
          <input
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Save
          </button>
          <button
            onClick={() => {
              setIsEditing(false);
              setEditValue(value || '');
            }}
            className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
          >
            Cancel
          </button>
        </div>
      ) : (
        <>
          <div className="mb-2 p-2 bg-gray-100 rounded">
            <p className="text-gray-800">{value || '(empty)'}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setIsEditing(true)}
              className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
            >
              Edit
            </button>
            {suggestedValue && suggestedValue !== value && (
              <button
                onClick={handleSuggest}
                className="px-3 py-1 text-sm bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200"
              >
                Use Suggestion: {suggestedValue}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
};

const IssueItem = ({
  issue,
  onSuggest,
}: {
  issue: ExtractionIssue;
  onSuggest?: (suggestedValue: string) => void;
}) => {
  const severityColor = issue.severity === 'error' ? 'text-red-600' : 'text-yellow-600';

  return (
    <div className="border-l-4 border-yellow-400 bg-yellow-50 p-3 mb-2">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <p className={`font-semibold ${severityColor}`}>{issue.field_name}</p>
          <p className="text-sm text-gray-700 mt-1">{issue.message}</p>
          {issue.suggested_value && (
            <p className="text-sm text-gray-600 mt-1">Suggestion: {issue.suggested_value}</p>
          )}
        </div>
        {issue.suggested_value && onSuggest && (
          <button
            onClick={() => onSuggest(issue.suggested_value || '')}
            className="ml-2 px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 whitespace-nowrap"
          >
            Use
          </button>
        )}
      </div>
      {issue.resolved && <p className="text-xs text-green-600 mt-1">✓ Resolved: {issue.resolved_value}</p>}
    </div>
  );
};

const DocumentPreview = ({
  fileUrl,
  mimeType,
  documentType,
  loading,
  error,
}: {
  fileUrl: string | null;
  mimeType?: string;
  documentType: string;
  loading: boolean;
  error: string | null;
}) => {
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-3 text-center">
        <p className="text-sm text-red-700">⚠️ Could not load file</p>
        <p className="text-xs text-red-600 mt-1">{error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-gray-100 aspect-square flex items-center justify-center rounded border-2 border-dashed border-gray-300">
        <div className="text-center text-gray-500">
          <p className="text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  if (!fileUrl) {
    return (
      <div className="bg-gray-100 aspect-square flex items-center justify-center rounded border-2 border-dashed border-gray-300">
        <div className="text-center text-gray-500">
          <p className="text-sm">No file available</p>
          <p className="text-xs mt-2">{documentType}</p>
        </div>
      </div>
    );
  }

  // For images, show inline
  if (mimeType?.startsWith('image/')) {
    return (
      <img
        src={fileUrl}
        alt="Document preview"
        className="w-full h-auto rounded border border-gray-200 max-h-96 object-cover"
      />
    );
  }

  // For PDFs, show embedded viewer
  if (mimeType === 'application/pdf') {
    return (
      <iframe
        src={`${fileUrl}#toolbar=0`}
        className="w-full h-96 rounded border border-gray-200"
        title="PDF Preview"
      />
    );
  }

  // For text files, show in a code block
  if (mimeType?.startsWith('text/')) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded p-3 max-h-96 overflow-y-auto">
        <pre className="text-xs whitespace-pre-wrap break-words text-gray-700">
          <a
            href={fileUrl}
            download
            className="text-blue-600 hover:underline text-sm block mb-2"
          >
            📥 Download file
          </a>
        </pre>
      </div>
    );
  }

  // Default: show download link
  return (
    <div className="bg-gray-100 aspect-square flex items-center justify-center rounded border-2 border-dashed border-gray-300">
      <div className="text-center">
        <p className="text-sm text-gray-700">📄 {documentType}</p>
        <a
          href={fileUrl}
          download
          className="text-blue-600 hover:underline text-sm mt-3 inline-block"
        >
          📥 Download File
        </a>
      </div>
    </div>
  );
};

export default function ExtractionReview({ extractionId, onReviewSubmitted }: ExtractionReviewProps) {
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [issues, setIssues] = useState<ExtractionIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewNotes, setReviewNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [fileLoading, setFileLoading] = useState(false);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationResults, setValidationResults] = useState<ExtractionIssue[] | null>(null);
  const [showValidationResults, setShowValidationResults] = useState(false);
  const [approving, setApproving] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [actionResult, setActionResult] = useState<{ status: string; message: string } | null>(null);
  const [placementSuggestion, setPlacementSuggestion] = useState<PlacementSuggestionItem | null>(null);
  const [conflictSuggestions, setConflictSuggestions] = useState<ConflictSuggestion[]>([]);
  const [intentLoading, setIntentLoading] = useState(false);

  const loadIntentContext = async (intakeItemId: string) => {
    try {
      setIntentLoading(true);
      const token = getAccessToken();
      const tenantId = getTenantId();
      const baseUrl = getApiBaseUrl();

      const headers = {
        'Authorization': `Bearer ${token}`,
        'X-Tenant-ID': tenantId,
        'Content-Type': 'application/json',
      };

      const [placementResponse, conflictsResponse] = await Promise.all([
        fetch(`${baseUrl}/api/intake/placement/suggest`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ item_ids: [intakeItemId] }),
        }),
        fetch(`${baseUrl}/api/intake/conflicts/suggest`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ item_ids: [intakeItemId] }),
        }),
      ]);

      if (placementResponse.ok) {
        const placementPayload = await placementResponse.json() as { items?: PlacementSuggestionItem[] };
        setPlacementSuggestion(placementPayload.items?.[0] ?? null);
      }

      if (conflictsResponse.ok) {
        const conflictPayload = await conflictsResponse.json() as { items?: ConflictSuggestion[] };
        setConflictSuggestions(Array.isArray(conflictPayload.items) ? conflictPayload.items : []);
      }
    } catch {
      setPlacementSuggestion(null);
      setConflictSuggestions([]);
    } finally {
      setIntentLoading(false);
    }
  };

  useEffect(() => {
    const fetchExtraction = async () => {
      try {
        const token = getAccessToken();
        const tenantId = getTenantId();
        const baseUrl = getApiBaseUrl();

        const response = await fetch(
          `${baseUrl}/api/extractions/${extractionId}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'X-Tenant-ID': tenantId,
            },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch extraction');
        }

        const data = await response.json();
        setExtraction(data.extraction);
        setIssues(data.issues);

        // Build file URL for the document preview
        if (data.extraction.intake_item_id) {
          const baseUrl = getApiBaseUrl();
          const fileUrl = `${baseUrl}/api/intake/items/${data.extraction.intake_item_id}/file`;
          setFileUrl(fileUrl);
          await loadIntentContext(data.extraction.intake_item_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchExtraction();
  }, [extractionId]);

  const handleSubmitReview = async () => {
    try {
      setSubmitting(true);
      const token = getAccessToken();
      const tenantId = getTenantId();
      const baseUrl = getApiBaseUrl();

      const response = await fetch(
        `${baseUrl}/api/extractions/${extractionId}/review`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-ID': tenantId,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            review_notes: reviewNotes,
            corrections,
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to submit review');
      }

      const data = await response.json();
      setExtraction(data.extraction);
      setIssues(data.issues);
      setReviewNotes('');
      setCorrections({});

      if (onReviewSubmitted) {
        onReviewSubmitted();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleValidateReview = async () => {
    try {
      setValidationLoading(true);
      const token = getAccessToken();
      const tenantId = getTenantId();
      const baseUrl = getApiBaseUrl();

      const response = await fetch(
        `${baseUrl}/api/extractions/${extractionId}/validate`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-ID': tenantId,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to validate extraction');
      }

      const data = await response.json();
      // Update the issues list with new validation results
      setValidationResults(data.issues);
      setShowValidationResults(true);
      // Also update the main issues list
      setIssues(data.issues);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setValidationLoading(false);
    }
  };

  const handleApprove = async () => {
    try {
      setApproving(true);
      const token = getAccessToken();
      const tenantId = getTenantId();
      const baseUrl = getApiBaseUrl();

      const response = await fetch(
        `${baseUrl}/api/extractions/${extractionId}/approve`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-ID': tenantId,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            approve: true,
            approval_notes: approvalNotes,
          }),
        }
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Approval failed' }));
        throw new Error(err.detail || 'Approval failed');
      }

      const data = await response.json();
      setActionResult({ status: 'approved', message: `Approved and distributed. Status: ${data.status}` });
      if (onReviewSubmitted) onReviewSubmitted();
    } catch (err) {
      setActionResult({ status: 'error', message: err instanceof Error ? err.message : 'Unknown error' });
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) return;
    try {
      setApproving(true);
      const token = getAccessToken();
      const tenantId = getTenantId();
      const baseUrl = getApiBaseUrl();

      const response = await fetch(
        `${baseUrl}/api/extractions/${extractionId}/approve`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-ID': tenantId,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            approve: false,
            rejection_reason: rejectionReason,
          }),
        }
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Rejection failed' }));
        throw new Error(err.detail || 'Rejection failed');
      }

      setShowRejectModal(false);
      setActionResult({ status: 'rejected', message: 'Extraction rejected.' });
      if (onReviewSubmitted) onReviewSubmitted();
    } catch (err) {
      setActionResult({ status: 'error', message: err instanceof Error ? err.message : 'Unknown error' });
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading extraction...</div>;
  }

  if (error) {
    return <div className="text-red-600 py-8">Error: {error}</div>;
  }

  if (!extraction) {
    return <div className="text-center py-8">Extraction not found</div>;
  }

  const unresolvedIssues = issues.filter((i) => !i.resolved);
  const intentSchema = resolveIntentSchema(extraction.document_type, placementSuggestion?.destination_key ?? null);
  const suggestedValueByField = issues.reduce<Record<string, string | null>>((acc, issue) => {
    if (issue.suggested_value) {
      acc[issue.field_name] = issue.suggested_value;
    }
    return acc;
  }, {});
  const autoPlacementSafe = Boolean(
    placementSuggestion &&
    placementSuggestion.confidence >= 0.95 &&
    unresolvedIssues.length === 0
  );

  return (
    <div className="space-y-6 p-6 bg-gray-50 min-h-screen">
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="font-semibold text-lg">AI Document Intent</h3>
            <p className="text-sm text-gray-600 mt-1">Schema: {intentSchema.label}</p>
          </div>
          {intentLoading ? <span className="text-sm text-gray-500">Loading intent...</span> : null}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className="rounded border border-slate-200 p-3 bg-slate-50">
            <p className="text-xs uppercase tracking-wide text-slate-500">Primary type</p>
            <p className="font-semibold text-slate-900 mt-1">{extraction.document_type || 'unknown'}</p>
          </div>
          <div className="rounded border border-slate-200 p-3 bg-slate-50">
            <p className="text-xs uppercase tracking-wide text-slate-500">Recommended destination</p>
            <p className="font-semibold text-slate-900 mt-1">{placementSuggestion?.destination_label || 'Pending'}</p>
            {placementSuggestion ? (
              <p className="text-xs text-slate-600 mt-1">Confidence {Math.round(placementSuggestion.confidence * 100)}%</p>
            ) : null}
          </div>
          <div className="rounded border border-slate-200 p-3 bg-slate-50">
            <p className="text-xs uppercase tracking-wide text-slate-500">Automatic placement safe</p>
            <p className={`font-semibold mt-1 ${autoPlacementSafe ? 'text-emerald-700' : 'text-amber-700'}`}>
              {autoPlacementSafe ? 'Yes' : 'No'}
            </p>
          </div>
          <div className="rounded border border-slate-200 p-3 bg-slate-50">
            <p className="text-xs uppercase tracking-wide text-slate-500">Human review required</p>
            <p className="font-semibold text-amber-700 mt-1">{unresolvedIssues.length > 0 || !autoPlacementSafe ? 'Yes' : 'No'}</p>
          </div>
        </div>

        {placementSuggestion ? (
          <div className="mt-4 rounded border border-blue-100 bg-blue-50 p-3 text-sm text-blue-900">
            <p><strong>Routing reason:</strong> {placementSuggestion.reason}</p>
            <p className="mt-1 text-xs text-blue-700">Signal source: {placementSuggestion.signal_source}</p>
          </div>
        ) : null}

        {conflictSuggestions.length > 0 ? (
          <div className="mt-4 rounded border border-amber-200 bg-amber-50 p-3">
            <p className="text-sm font-semibold text-amber-900">Conflict suggestions</p>
            {conflictSuggestions.map((conflict) => (
              <div key={conflict.field_name} className="mt-2 text-sm text-amber-900">
                <p>
                  <strong>{conflict.field_name}</strong>: recommended {conflict.recommended.value} {conflict.recommended.unit}
                </p>
                <p className="text-xs text-amber-700">{conflict.reason}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      <div className="grid grid-cols-3 gap-6">
      {/* Left: Document Preview */}
      <div className="col-span-1 bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold text-lg mb-4">📄 Document</h3>
        <DocumentPreview
          fileUrl={fileUrl}
          mimeType={extraction.mime_type}
          documentType={extraction.document_type}
          loading={fileLoading}
          error={fileError}
        />
      </div>

      {/* Middle: Extracted Fields */}
      <div className="col-span-1 bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold text-lg mb-4">✏️ Extracted Fields</h3>
        <p className="text-xs text-gray-500 mb-3">Showing fields based on detected document intent.</p>
        <div className="space-y-2">
          {intentSchema.fieldKeys.map((fieldKey) => {
            const config = FIELD_CONFIGS[fieldKey];
            if (!config) {
              return null;
            }

            const confidence =
              fieldKey === 'destination'
                ? extraction.destination_confidence
                : fieldKey === 'material'
                ? extraction.material_confidence
                : config.confidence;

            return (
              <EditableField
                key={fieldKey}
                label={config.label}
                value={config.value(extraction)}
                confidence={confidence}
                suggestedValue={suggestedValueByField[fieldKey]}
                onEdit={(value) => setCorrections({ ...corrections, [fieldKey]: value })}
              />
            );
          })}
        </div>
      </div>

      {/* Right: Issues + Actions */}
      <div className="col-span-1 bg-white rounded-lg shadow p-4 flex flex-col">
        <h3 className="font-semibold text-lg mb-4">⚠️ Issues ({unresolvedIssues.length})</h3>

        <div className="flex-1 overflow-y-auto mb-4">
          {unresolvedIssues.length === 0 ? (
            <p className="text-green-600 text-sm">✓ All issues resolved</p>
          ) : (
            unresolvedIssues.map((issue) => (
              <IssueItem
                key={issue.id}
                issue={issue}
                onSuggest={(value) =>
                  setCorrections({
                    ...corrections,
                    [issue.field_name]: value,
                  })
                }
              />
            ))
          )}
        </div>

        {/* Action result banner */}
        {actionResult && (
          <div
            className={`mb-3 rounded p-3 text-sm ${
              actionResult.status === 'approved'
                ? 'bg-green-50 border border-green-300 text-green-800'
                : actionResult.status === 'rejected'
                ? 'bg-red-50 border border-red-300 text-red-800'
                : 'bg-yellow-50 border border-yellow-300 text-yellow-800'
            }`}
          >
            {actionResult.status === 'approved' && '✅ '}
            {actionResult.status === 'rejected' && '🚫 '}
            {actionResult.status === 'error' && '⚠️ '}
            {actionResult.message}
          </div>
        )}

        {/* Approval panel — shown when review has been submitted */}
        {extraction.status === 'review_submitted' ? (
          <div className="border-t pt-4">
            <div className="mb-3 bg-purple-50 border border-purple-200 rounded p-3">
              <p className="text-sm font-semibold text-purple-800">Ready for Approval</p>
              <p className="text-xs text-purple-600 mt-1">Review is complete. Approve to distribute or reject to return for rework.</p>
            </div>

            <label className="block text-sm font-semibold text-gray-700 mb-2">Approval Notes (optional)</label>
            <textarea
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400"
              rows={3}
              placeholder="Any notes for the record..."
            />

            <div className="flex gap-2 mt-4">
              <button
                onClick={handleApprove}
                disabled={approving}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 font-semibold"
              >
                {approving ? 'Processing...' : '✅ Approve & Distribute'}
              </button>
              <button
                onClick={() => setShowRejectModal(true)}
                disabled={approving}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:bg-gray-400"
              >
                🚫 Reject
              </button>
            </div>

            <div className="flex gap-2 mt-3">
              <button
                onClick={handleValidateReview}
                disabled={validationLoading}
                className="w-full px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200"
              >
                {validationLoading ? 'Validating...' : '🔄 Re-Validate'}
              </button>
            </div>

            {/* Reject Modal */}
            {showRejectModal && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full mx-4">
                  <h2 className="text-xl font-semibold mb-4">Reject Extraction</h2>
                  <p className="text-sm text-gray-600 mb-4">Provide a reason — this will be logged and visible to the reviewer.</p>
                  <textarea
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-400"
                    rows={4}
                    placeholder="Why is this extraction being rejected?"
                    autoFocus
                  />
                  <div className="flex gap-3 mt-4">
                    <button
                      onClick={handleReject}
                      disabled={!rejectionReason.trim() || approving}
                      className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 font-semibold"
                    >
                      {approving ? 'Rejecting...' : 'Confirm Reject'}
                    </button>
                    <button
                      onClick={() => { setShowRejectModal(false); setRejectionReason(''); }}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Review panel — shown for review_pending or other statuses */
          <div className="border-t pt-4">
            <label className="block text-sm font-semibold text-gray-700 mb-2">Review Notes</label>
            <textarea
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
              placeholder="Add notes about this extraction..."
            />

            <div className="flex gap-2 mt-4">
              <button
                onClick={handleSubmitReview}
                disabled={submitting || ['approved', 'distributed', 'rejected'].includes(extraction.status)}
                className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-400"
              >
                {submitting ? 'Submitting...' : 'Submit Review'}
              </button>
              <button
                onClick={handleValidateReview}
                disabled={validationLoading}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400"
              >
                {validationLoading ? 'Validating...' : '🔄 Re-Validate'}
              </button>
            </div>
          </div>
        )}

        {/* Validation Results Modal */}
        {showValidationResults && validationResults && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl max-h-96 overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Validation Results</h2>
                <button
                  onClick={() => setShowValidationResults(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
                >
                  ×
                </button>
              </div>

              {validationResults.length === 0 ? (
                <div className="bg-green-50 border border-green-200 rounded p-4 text-center">
                  <p className="text-green-700 font-semibold">✓ All validations passed!</p>
                  <p className="text-green-600 text-sm mt-1">No issues found in this extraction.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-gray-600 mb-4">
                    Found {validationResults.length} issue{validationResults.length !== 1 ? 's' : ''}:
                  </p>
                  {validationResults.map((issue) => {
                    const isResolved = issue.resolved;
                    const isError = issue.severity === 'error';
                    return (
                      <div
                        key={issue.id}
                        className={`border-l-4 p-3 rounded ${
                          isResolved
                            ? 'border-green-400 bg-green-50'
                            : isError
                            ? 'border-red-400 bg-red-50'
                            : 'border-yellow-400 bg-yellow-50'
                        }`}
                      >
                        <p
                          className={`font-semibold ${
                            isResolved ? 'text-green-700' : isError ? 'text-red-700' : 'text-yellow-700'
                          }`}
                        >
                          {isResolved ? '✓ ' : ''}{issue.field_name}
                        </p>
                        <p className="text-sm text-gray-700 mt-1">{issue.message}</p>
                        {isResolved && issue.resolved_value && (
                          <p className="text-xs text-green-600 mt-2">Resolved as: {issue.resolved_value}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              <button
                onClick={() => setShowValidationResults(false)}
                className="mt-6 w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
