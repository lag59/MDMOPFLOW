"use client";

import React from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import AppShell from "@/components/AppShell";
import TicketCalculatorPanel from "@/components/TicketCalculatorPanel";
import { getAccessToken } from "@/lib/auth";
import {
  Ticket,
  TicketApiError,
  TicketUploadExtractionItem,
  createTicket,
  deleteTicket,
  listTickets,
  updateTicket,
  uploadTicketFilesForExtraction,
} from "@/lib/tickets";

function normalizeTicketNumber(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

function canonicalizeTicketNumber(value: string): string {
  return normalizeTicketNumber(value).replace(/[^a-z0-9]/g, "");
}

function resolvePreviewKind(file: File, originalFilename: string): "image" | "pdf" | "text" | "unknown" {
  const mimeType = (file.type || "").toLowerCase();
  const lowerName = originalFilename.toLowerCase();

  if (mimeType.startsWith("image/") || /\.(png|jpe?g|gif|webp)$/i.test(lowerName)) {
    return "image";
  }
  if (mimeType === "application/pdf" || /\.pdf$/i.test(lowerName)) {
    return "pdf";
  }
  if (mimeType.startsWith("text/") || /\.(txt|csv|log)$/i.test(lowerName)) {
    return "text";
  }
  return "unknown";
}

function buildFallbackExtractionPreview(item: TicketUploadExtractionItem): string {
  const lines: string[] = ["Extracted fields:"];
  const entries = Object.entries(item.extracted_entities || {}).filter(([, value]) => `${value}`.trim().length > 0);

  if (entries.length > 0) {
    for (const [key, value] of entries) {
      lines.push(`- ${key}: ${value}`);
    }
  } else {
    lines.push("- No entity fields were extracted.");
  }

  const numberOfLoads = item.calculator_prefill?.number_of_loads;
  if (numberOfLoads !== null && numberOfLoads !== undefined) {
    lines.push("");
    lines.push(`Number of loads (prefill): ${numberOfLoads}`);
  }

  return lines.join("\n");
}

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [ticketNumber, setTicketNumber] = useState("");
  const [material, setMaterial] = useState("");
  const [weight, setWeight] = useState("");
  const [tons, setTons] = useState("");
  const [volumeYards, setVolumeYards] = useState("");
  const [revenue, setRevenue] = useState("");
  const [status, setStatus] = useState("draft");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [selectedTicketId, setSelectedTicketId] = useState("");
  const [editingTicketId, setEditingTicketId] = useState("");
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadItems, setUploadItems] = useState<TicketUploadExtractionItem[]>([]);
  const [ticketBeingDeletedId, setTicketBeingDeletedId] = useState("");
  const [previewTarget, setPreviewTarget] = useState<{
    item: TicketUploadExtractionItem;
    file: File | null;
    objectUrl: string | null;
    previewKind: "image" | "pdf" | "text" | "unknown";
  } | null>(null);
  const [calculatorPrefill, setCalculatorPrefill] = useState<{
    materialName?: string;
    grossWeightLbs?: string;
    tareWeightLbs?: string;
    netWeightLbs?: string;
    numberOfLoads?: string;
  } | null>(null);
  const previewCardRef = useRef<HTMLDivElement | null>(null);

  const ticketMetrics = useMemo(() => {
    const totalTickets = tickets.length;
    const draftTickets = tickets.filter((ticket) => ticket.status === "draft").length;
    const assignedTickets = tickets.filter((ticket) => ticket.status !== "draft").length;
    const uploadedItems = uploadItems.length;

    return {
      totalTickets,
      draftTickets,
      assignedTickets,
      uploadedItems,
    };
  }, [tickets, uploadItems]);

  const potentialDuplicates = ticketNumber.trim()
    ? tickets
        .filter((ticket) => ticket.id !== editingTicketId && ticket.ticket_number.trim().length > 0)
        .map((ticket) => {
          const exactMatch = normalizeTicketNumber(ticket.ticket_number) === normalizeTicketNumber(ticketNumber);
          const canonicalMatch = canonicalizeTicketNumber(ticket.ticket_number) === canonicalizeTicketNumber(ticketNumber);
          if (!exactMatch && !canonicalMatch) {
            return null;
          }
          return {
            id: ticket.id,
            ticket,
            ticketNumber: ticket.ticket_number,
            material: ticket.material,
            status: ticket.status,
            matchType: exactMatch ? "exact" : "near",
          };
        })
        .filter((match): match is NonNullable<typeof match> => match !== null)
    : [];

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    void refreshTickets();
  }, []);

  useEffect(() => {
    return () => {
      if (previewTarget?.objectUrl) {
        URL.revokeObjectURL(previewTarget.objectUrl);
      }
    };
  }, [previewTarget]);

  useEffect(() => {
    if (
      previewTarget &&
      previewCardRef.current &&
      typeof previewCardRef.current.scrollIntoView === "function"
    ) {
      previewCardRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [previewTarget]);

  async function refreshTickets(): Promise<void> {
    try {
      const data = await listTickets();
      setTickets(data);
      if (!selectedTicketId && data.length > 0) {
        setSelectedTicketId(data[0].id);
      }
    } catch {
      setTickets([]);
    }
  }

  async function saveTicket(): Promise<void> {
    if (!ticketNumber.trim()) {
      setMessage("Ticket number is required.");
      return;
    }

    setBusy(true);
    setMessage("");
    try {
      await createTicket({
        ticket_number: ticketNumber.trim(),
        material: material.trim(),
        weight: weight.trim() || null,
        tons: tons.trim() || null,
        volume_yards: volumeYards.trim() || null,
        revenue: revenue.trim() || null,
        status,
        notes: "Created from tickets workspace calculator flow",
      });
      await refreshTickets();
      setMessage("Ticket created with standardized calculation outputs.");
    } catch (err) {
      if (err instanceof TicketApiError) {
        setMessage(err.detail);
      } else {
        setMessage("Unable to create ticket.");
      }
    } finally {
      setBusy(false);
    }
  }

  function loadTicketIntoForm(ticket: Ticket): void {
    setSelectedTicketId(ticket.id);
    setEditingTicketId(ticket.id);
    setTicketNumber(ticket.ticket_number || "");
    setMaterial(ticket.material || "");
    setWeight(ticket.weight || "");
    setTons(ticket.tons || "");
    setVolumeYards(ticket.volume_yards || "");
    setRevenue(ticket.revenue || "");
    setStatus(ticket.status || "draft");
    setMessage(`Loaded ticket ${ticket.ticket_number || ticket.id} into form.`);
  }

  async function deleteTicketRow(ticket: Ticket): Promise<void> {
    const label = ticket.ticket_number || ticket.id;
    const shouldDelete = window.confirm(`Delete ticket ${label}? This cannot be undone.`);
    if (!shouldDelete) {
      return;
    }

    setTicketBeingDeletedId(ticket.id);
    setMessage("");
    try {
      await deleteTicket(ticket.id);
      if (selectedTicketId === ticket.id) {
        setSelectedTicketId("");
      }
      if (editingTicketId === ticket.id) {
        setEditingTicketId("");
      }
      await refreshTickets();
      setMessage(`Deleted ticket ${label}.`);
    } catch (err) {
      if (err instanceof TicketApiError) {
        setMessage(err.detail);
      } else {
        setMessage("Unable to delete ticket.");
      }
    } finally {
      setTicketBeingDeletedId("");
    }
  }

  async function applyOutputsToSelectedTicket(): Promise<void> {
    if (!selectedTicketId) {
      setMessage("Select a ticket first.");
      return;
    }

    setBusy(true);
    setMessage("");
    try {
      await updateTicket(selectedTicketId, {
        material: material.trim() || undefined,
        weight: weight.trim() || undefined,
        tons: tons.trim() || undefined,
        volume_yards: volumeYards.trim() || undefined,
        revenue: revenue.trim() || undefined,
      });
      await refreshTickets();
      setMessage("Selected ticket updated with standardized outputs.");
    } catch (err) {
      if (err instanceof TicketApiError) {
        setMessage(err.detail);
      } else {
        setMessage("Unable to update selected ticket.");
      }
    } finally {
      setBusy(false);
    }
  }

  function applyExtractedItem(item: TicketUploadExtractionItem): void {
    setEditingTicketId("");
    setTicketNumber(item.extracted_entities.ticket_number || "");
    setMaterial(item.extracted_entities.material || "");
    setWeight(item.extracted_entities.net_weight_lbs || "");
    setCalculatorPrefill({
      materialName: item.calculator_prefill.material_name || undefined,
      grossWeightLbs: item.calculator_prefill.gross_weight_lbs || undefined,
      tareWeightLbs: item.calculator_prefill.tare_weight_lbs || undefined,
      netWeightLbs: item.calculator_prefill.net_weight_lbs || undefined,
      numberOfLoads:
        item.calculator_prefill.number_of_loads !== null
          ? String(item.calculator_prefill.number_of_loads)
          : undefined,
    });
    const hasTicketNumber = !!(item.extracted_entities.ticket_number || "").trim();
    setUploadMessage(
      hasTicketNumber
        ? `Loaded extraction from ${item.original_filename} into calculator and ticket form.`
        : `Loaded extraction from ${item.original_filename}. Ticket number was not detected — enter it manually in the Ticket form below before saving.`
    );
  }

  function getSourceFileForUploadItem(item: TicketUploadExtractionItem): File | null {
    const match = selectedFiles.find(
      (file) => file.name === item.original_filename && file.size === item.file_size_bytes
    );
    return match ?? null;
  }

  function openFilePreview(item: TicketUploadExtractionItem): void {
    const sourceFile = getSourceFileForUploadItem(item);
    const objectUrl = sourceFile ? URL.createObjectURL(sourceFile) : null;
    setPreviewTarget((previous) => {
      if (previous?.objectUrl) {
        URL.revokeObjectURL(previous.objectUrl);
      }
      return {
        item,
        file: sourceFile,
        objectUrl,
        previewKind: sourceFile
          ? resolvePreviewKind(sourceFile, item.original_filename)
          : resolvePreviewKind(new File([], item.original_filename, { type: item.mime_type }), item.original_filename),
      };
    });

    if (!sourceFile) {
      setUploadMessage(
        "Original file is no longer in picker, but extraction preview is still available below. Re-select and re-upload for full file rendering."
      );
    }
  }

  function closeFilePreview(): void {
    setPreviewTarget((previous) => {
      if (previous?.objectUrl) {
        URL.revokeObjectURL(previous.objectUrl);
      }
      return null;
    });
  }

  async function deleteSelectedTicket(): Promise<void> {
    if (!selectedTicketId) {
      setMessage("Select a ticket first.");
      return;
    }

    const selected = tickets.find((ticket) => ticket.id === selectedTicketId);
    if (!selected) {
      setMessage("Selected ticket no longer exists in the loaded list.");
      return;
    }

    await deleteTicketRow(selected);
  }

  async function runUploadExtraction(createTicketsFromUpload: boolean): Promise<void> {
    if (selectedFiles.length === 0) {
      setUploadMessage("Select one or more PDF, JPG, PNG, or TXT ticket files first.");
      return;
    }

    setUploadBusy(true);
    setUploadMessage("");
    try {
      const response = await uploadTicketFilesForExtraction(selectedFiles, createTicketsFromUpload);
      setUploadItems(response.items);

      if (response.items.length > 0) {
        applyExtractedItem(response.items[0]);
        openFilePreview(response.items[0]);
      }

      if (createTicketsFromUpload) {
        await refreshTickets();
        const createdCount = response.items.filter((item) => item.created_ticket_id).length;
        const duplicateCount = response.items.filter((item) => item.duplicate_ticket_id).length;
        setUploadMessage(
          `Uploaded ${response.items.length} file(s); created ${createdCount} draft ticket(s); skipped ${duplicateCount} duplicate(s).`
        );
      } else {
        setUploadMessage(`Uploaded ${response.items.length} file(s). Select a row to prefill calculator inputs.`);
      }
    } catch (err) {
      if (err instanceof TicketApiError) {
        setUploadMessage(err.detail);
      } else {
        setUploadMessage("Unable to upload files for extraction.");
      }
    } finally {
      setUploadBusy(false);
    }
  }

  function extractionConfidenceLabel(confidence: number): "high" | "medium" | "low" {
    const safeConfidence = Number.isFinite(confidence) ? confidence : 0;
    if (safeConfidence >= 0.8) {
      return "high";
    }
    if (safeConfidence >= 0.5) {
      return "medium";
    }
    return "low";
  }

  return (
    <AppShell titleKey="tickets.title">
      <div className="card">
        <span className="auth-eyebrow">Ticket module</span>
        <h2>Tickets</h2>
        <p className="muted">Upload source files, extract fields, run the calculator, and keep ticket values standardized.</p>
        <div className="top-actions" style={{ marginTop: "1rem", flexWrap: "wrap" }}>
          <a className="link-button" href="/ticket-manager">
            Ticket manager
          </a>
          <a className="link-button" href="/projects">
            Projects
          </a>
          <a className="link-button" href="/modules">
            Back to modules
          </a>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <span className="auth-eyebrow">Inventory</span>
          <div className="metric">{ticketMetrics.totalTickets}</div>
          <div className="metric-note">Tickets currently loaded in the workspace</div>
        </div>
        <div className="card">
          <span className="auth-eyebrow">Drafts</span>
          <div className="metric">{ticketMetrics.draftTickets}</div>
          <div className="metric-note">Tickets ready for calculation or project assignment</div>
        </div>
        <div className="card">
          <span className="auth-eyebrow">Assigned</span>
          <div className="metric">{ticketMetrics.assignedTickets}</div>
          <div className="metric-note">Tickets already tied to a project</div>
        </div>
        <div className="card">
          <span className="auth-eyebrow">Uploads</span>
          <div className="metric">{ticketMetrics.uploadedItems}</div>
          <div className="metric-note">Files extracted in the current session</div>
        </div>
      </div>

      <div className="card">
        <div className="section-header">
          <h3>Bulk ticket upload (PDF/JPG/PNG/TXT)</h3>
        </div>
        <div className="form-grid replay-controls-grid">
          <label>
            Ticket files
            <input
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.txt"
              onChange={(event) => setSelectedFiles(Array.from(event.target.files || []))}
            />
          </label>
        </div>
        <div className="replay-action-row">
          <button onClick={() => void runUploadExtraction(false)} disabled={uploadBusy || selectedFiles.length === 0}>
            {uploadBusy ? "Uploading..." : "Upload and extract"}
          </button>
          <button onClick={() => void runUploadExtraction(true)} disabled={uploadBusy || selectedFiles.length === 0}>
            {uploadBusy ? "Uploading..." : "Upload and auto-create draft tickets"}
          </button>
          <button type="button" onClick={() => openFilePreview(uploadItems[0])} disabled={uploadItems.length === 0}>
            Preview first result
          </button>
        </div>
        {uploadItems.length > 0 ? (
          <div className="token-state-table-wrap">
            <table className="token-state-table">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Ticket #</th>
                  <th>Material</th>
                  <th>Net lbs</th>
                  <th>Confidence</th>
                  <th>Status</th>
                  <th>Preview source</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {uploadItems.map((item, idx) => {
                  const confidence = Number.isFinite(item.extraction_confidence)
                    ? item.extraction_confidence
                    : 0;
                  const confidenceLabel = extractionConfidenceLabel(confidence);
                  const confidencePercent = Math.round(confidence * 100);

                  return (
                    <tr key={`${item.original_filename}-${item.file_size_bytes}-${idx}`}>
                      <td>{item.original_filename}</td>
                      <td>{item.extracted_entities.ticket_number || "n/a"}</td>
                      <td>{item.extracted_entities.material || "n/a"}</td>
                      <td>{item.extracted_entities.net_weight_lbs || "n/a"}</td>
                      <td>
                        <span className={`confidence-badge confidence-${confidenceLabel}`}>
                          {confidenceLabel} ({confidencePercent}%)
                        </span>
                      </td>
                      <td>
                        {item.created_ticket_id
                          ? "draft ticket created"
                          : item.duplicate_ticket_id
                            ? "duplicate skipped"
                            : "extracted only"}
                      </td>
                      <td>{getSourceFileForUploadItem(item) ? "file + extracted text" : "extracted text only"}</td>
                      <td>
                        <div className="replay-action-row">
                          <button type="button" onClick={() => applyExtractedItem(item)}>
                            Use in calculator
                          </button>
                          <button type="button" onClick={() => openFilePreview(item)}>
                            Preview file
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="metric-note">
              Confidence guide: high (80%+) = likely ready, medium (50-79%) = quick review, low (&lt;50%) = manual review.
            </p>
            <p className="metric-note">
              For circled numbers, hand tallies, or unclear marks, open Preview and verify Number of loads before saving.
            </p>
          </div>
        ) : null}
        {uploadItems.length === 0 ? (
          <p className="metric-note">
            The Preview file button appears after Upload and extract, in each row under Bulk ticket upload.
          </p>
        ) : null}
        {uploadItems.some((item) => item.review_required) ? (
          <p className="metric-note">One or more files were marked low-confidence and may need manual review.</p>
        ) : null}
        {uploadMessage ? <p className="metric-note">{uploadMessage}</p> : null}
      </div>

      <div className="card" ref={previewCardRef}>
        <div className="section-header">
          <h3>Ticket file preview</h3>
          <button type="button" onClick={closeFilePreview} disabled={!previewTarget}>Close preview</button>
        </div>
        {previewTarget ? (
          <>
            <p className="metric-note">
              Reviewing: {previewTarget.item.original_filename} ({previewTarget.file?.type || previewTarget.item.mime_type || "unknown type"})
            </p>
            {previewTarget.objectUrl ? (
              <div className="replay-action-row">
                <a href={previewTarget.objectUrl} target="_blank" rel="noreferrer" download={previewTarget.item.original_filename}>
                  Open / download file
                </a>
              </div>
            ) : (
              <p className="metric-note">Source file not bound in this browser session. Extraction preview is still available below.</p>
            )}
            {previewTarget.previewKind === "image" && previewTarget.objectUrl ? (
              <img
                src={previewTarget.objectUrl}
                alt={`Preview of ${previewTarget.item.original_filename}`}
                style={{ width: "100%", maxHeight: "70vh", objectFit: "contain", borderRadius: "8px" }}
              />
            ) : null}
            {previewTarget.previewKind === "pdf" ? (
              <p className="metric-note">
                PDF inline preview is disabled in this workspace because it can render as a black box. Use Open / download file and review the Extracted text preview below.
              </p>
            ) : null}
            {previewTarget.previewKind === "text" ? (
              <p className="metric-note">
                Text files are shown in the Extracted text preview below for consistent readability.
              </p>
            ) : null}
            {previewTarget.previewKind === "unknown" ? (
              <p className="metric-note">Preview is not supported for this file type. You can still use extracted values.</p>
            ) : null}
            <p className="metric-note">Extractor summary: {previewTarget.item.extracted_summary || "n/a"}</p>
            {previewTarget.item.extracted_text_preview ? (
              <div>
                <p className="metric-note">Extracted text preview (review tally/load cues):</p>
                <pre
                  style={{
                    whiteSpace: "pre-wrap",
                    maxHeight: "35vh",
                    overflow: "auto",
                    padding: "0.75rem",
                    border: "1px solid #d0d7de",
                    borderRadius: "8px",
                    background: "#f8fafc",
                  }}
                >
                  {previewTarget.item.extracted_text_preview}
                </pre>
              </div>
            ) : (
              <div>
                <p className="metric-note">
                  OCR text preview was unavailable for this file, so showing extracted fields instead. Verify loads manually from source file if needed.
                </p>
                <pre
                  style={{
                    whiteSpace: "pre-wrap",
                    maxHeight: "35vh",
                    overflow: "auto",
                    padding: "0.75rem",
                    border: "1px solid #d0d7de",
                    borderRadius: "8px",
                    background: "#f8fafc",
                  }}
                >
                  {buildFallbackExtractionPreview(previewTarget.item)}
                </pre>
              </div>
            )}
          </>
        ) : (
          <p className="metric-note">No preview selected yet. Upload and extract a file, then click Preview first result.</p>
        )}
      </div>

      <TicketCalculatorPanel
        title="Ticket quantity and cost calculator"
        prefill={calculatorPrefill}
        onApply={(payload) => {
          setMaterial(payload.material);
          setWeight(payload.weight);
          setTons(payload.tons);
          setVolumeYards(payload.volumeYards);
          setRevenue(payload.selectedTotalCost);
        }}
      />

      <div className="card">
        <div className="section-header">
          <h3>Ticket form</h3>
          <button onClick={() => void saveTicket()} disabled={busy}>
            {busy ? "Saving..." : "Create ticket"}
          </button>
        </div>
        {potentialDuplicates.length > 0 ? (
          <div className="token-state-table-wrap">
            <p className="metric-note">Possible duplicates found before save:</p>
            <table className="token-state-table">
              <thead>
                <tr>
                  <th>Match</th>
                  <th>Ticket #</th>
                  <th>Material</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {potentialDuplicates.map((match) => (
                  <tr key={match.id}>
                    <td>{match.matchType === "exact" ? "exact match" : "near match"}</td>
                    <td>{match.ticketNumber}</td>
                    <td>{match.material || "n/a"}</td>
                    <td>{match.status || "n/a"}</td>
                    <td>
                      <button type="button" onClick={() => loadTicketIntoForm(match.ticket)}>
                        Load existing
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="metric-note">Near match compares ticket numbers after removing punctuation and spaces.</p>
          </div>
        ) : null}

        <div className="form-grid replay-controls-grid">
          <label>
            Ticket number
            <input value={ticketNumber} onChange={(e) => setTicketNumber(e.target.value)} placeholder="TCK-1001" />
          </label>
          <label>
            Material
            <input value={material} onChange={(e) => setMaterial(e.target.value)} placeholder="Aggregate" />
          </label>
          <label>
            Net weight (lbs)
            <input value={weight} onChange={(e) => setWeight(e.target.value)} />
          </label>
          <label>
            Tons
            <input value={tons} onChange={(e) => setTons(e.target.value)} />
          </label>
          <label>
            Cubic yards
            <input value={volumeYards} onChange={(e) => setVolumeYards(e.target.value)} />
          </label>
          <label>
            Revenue
            <input value={revenue} onChange={(e) => setRevenue(e.target.value)} />
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="draft">draft</option>
              <option value="approved">approved</option>
              <option value="rejected">rejected</option>
            </select>
          </label>
        </div>

        <div className="replay-action-row">
          <label>
            Selected ticket for update
            <select value={selectedTicketId} onChange={(e) => setSelectedTicketId(e.target.value)}>
              <option value="">Select ticket...</option>
              {tickets.map((ticket) => (
                <option key={ticket.id} value={ticket.id}>
                  {ticket.ticket_number || ticket.id}
                </option>
              ))}
            </select>
          </label>
          <button onClick={() => void applyOutputsToSelectedTicket()} disabled={busy || !selectedTicketId}>
            Apply outputs to selected ticket
          </button>
          <button
            type="button"
            onClick={() => {
              const selected = tickets.find((ticket) => ticket.id === selectedTicketId);
              if (!selected) {
                setMessage("Select a ticket first.");
                return;
              }
              loadTicketIntoForm(selected);
            }}
            disabled={!selectedTicketId}
          >
            Edit selected ticket
          </button>
          <button type="button" onClick={() => void deleteSelectedTicket()} disabled={!selectedTicketId || busy}>
            Delete selected ticket
          </button>
        </div>

        {message ? <p className="metric-note">{message}</p> : null}
      </div>

      <div className="card">
        <div className="section-header">
          <h3>Tickets</h3>
          <button onClick={() => void refreshTickets()} disabled={busy}>Refresh</button>
        </div>
        {tickets.length === 0 ? (
          <p>No tickets yet.</p>
        ) : (
          <div className="token-state-table-wrap">
            <table className="token-state-table">
              <thead>
                <tr>
                  <th>Ticket</th>
                  <th>Material</th>
                  <th>Weight</th>
                  <th>Tons</th>
                  <th>Yards</th>
                  <th>Revenue</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((ticket) => (
                  <tr key={ticket.id}>
                    <td>{ticket.ticket_number || "n/a"}</td>
                    <td>{ticket.material || "n/a"}</td>
                    <td>{ticket.weight || "n/a"}</td>
                    <td>{ticket.tons || "n/a"}</td>
                    <td>{ticket.volume_yards || "n/a"}</td>
                    <td>{ticket.revenue || "n/a"}</td>
                    <td>{ticket.status}</td>
                    <td>
                      <div className="replay-action-row">
                        <button type="button" onClick={() => loadTicketIntoForm(ticket)}>
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => void deleteTicketRow(ticket)}
                          disabled={ticketBeingDeletedId === ticket.id}
                        >
                          {ticketBeingDeletedId === ticket.id ? "Deleting..." : "Delete"}
                        </button>
                      </div>
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
