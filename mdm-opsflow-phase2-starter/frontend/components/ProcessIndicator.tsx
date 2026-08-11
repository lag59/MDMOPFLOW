"use client";

// Shared process indicator used on every module page to show workflow position.

type Step = { key: string; label: string };

type Props = {
  steps: Step[];
  currentKey: string;
  errorKeys?: string[];
};

const STEP_COLORS = {
  done:    { bg: "#dcfce7", border: "#86efac", text: "#166534" },
  current: { bg: "#eff6ff", border: "#93c5fd", text: "#1e40af" },
  error:   { bg: "#fee2e2", border: "#fca5a5", text: "#991b1b" },
  future:  { bg: "#f8fafc", border: "#e2e8f0", text: "#94a3b8" },
};

export function ProcessIndicator({ steps, currentKey, errorKeys = [] }: Props) {
  const currentIdx = steps.findIndex(s => s.key === currentKey);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 0, flexWrap: "wrap", margin: "12px 0 16px" }}>
      {steps.map((step, idx) => {
        const isError   = errorKeys.includes(step.key);
        const isDone    = !isError && idx < currentIdx;
        const isCurrent = step.key === currentKey;
        const colors    = isError ? STEP_COLORS.error : isDone ? STEP_COLORS.done : isCurrent ? STEP_COLORS.current : STEP_COLORS.future;

        return (
          <div key={step.key} style={{ display: "flex", alignItems: "center" }}>
            <div style={{
              padding: "4px 12px", borderRadius: 999,
              background: colors.bg, border: `1px solid ${colors.border}`,
              color: colors.text, fontSize: 11, fontWeight: isCurrent ? 700 : 500,
              whiteSpace: "nowrap",
            }}>
              {isDone && <span style={{ marginRight: 4 }}>✓</span>}
              {isError && <span style={{ marginRight: 4 }}>✗</span>}
              {step.label}
            </div>
            {idx < steps.length - 1 && (
              <div style={{ width: 20, height: 1, background: idx < currentIdx ? "#86efac" : "#e2e8f0", flexShrink: 0 }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Standard process flows used across the platform ──────────────────────────

export const ESTIMATE_PROCESS = [
  { key: "Draft Estimate",         label: "Draft" },
  { key: "Pending Review",         label: "PM Review" },
  { key: "Submitted",              label: "Submitted" },
  { key: "Under Review",           label: "Under Review" },
  { key: "Awarded",                label: "Awarded" },
  { key: "Converted to Project",   label: "Converted" },
];

export const PROJECT_PROCESS = [
  { key: "planning",  label: "Planning" },
  { key: "active",    label: "Active" },
  { key: "on_hold",   label: "On Hold" },
  { key: "complete",  label: "Complete" },
];

export const TICKET_PROCESS = [
  { key: "open",      label: "Open" },
  { key: "pending",   label: "Pending" },
  { key: "approved",  label: "Approved" },
  { key: "closed",    label: "Closed" },
];

export const REPORT_PROCESS = [
  { key: "draft",     label: "Draft" },
  { key: "submitted", label: "Submitted" },
  { key: "reviewed",  label: "Reviewed" },
  { key: "approved",  label: "Approved" },
];

export const PO_PROCESS = [
  { key: "pending",   label: "Pending" },
  { key: "approved",  label: "Approved" },
  { key: "received",  label: "Received" },
];

export const INVOICE_PROCESS = [
  { key: "submitted", label: "Submitted" },
  { key: "approved",  label: "Approved" },
  { key: "paid",      label: "Paid" },
];

export const INTAKE_PROCESS = [
  { key: "uploaded",          label: "Uploaded" },
  { key: "processing",        label: "Processing" },
  { key: "pending_review",    label: "Review" },
  { key: "approved",          label: "Approved" },
  { key: "rejected",          label: "Rejected" },
];
