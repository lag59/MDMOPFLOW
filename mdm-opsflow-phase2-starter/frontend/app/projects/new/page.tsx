"use client";

import React, { useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

type ApiErrorPayload = {
  detail?: string | Array<{ msg?: string }>;
};

type ProjectCreateResponse = {
  id: string;
};

type IntakeUploadResponseItem = {
  id: string;
  original_filename: string;
  document_type: string;
  extracted_summary: string;
  ocr_status: string;
  ai_status: string;
  classification_confidence: number;
  needs_review: boolean;
};

type IntakePlacementSuggestion = {
  item_id: string;
  destination_label: string;
  destination_href: string;
  confidence: number;
  reason: string;
  signal_source: string;
  document_intelligence?: {
    primary_document_type: string;
    recommended_module: string;
    confidence: number;
    supporting_evidence: string[];
    conflicting_evidence: string[];
  } | null;
};

type IntakePlacementSuggestionResponse = {
  items: IntakePlacementSuggestion[];
};

type ProjectDocumentUploadResult = {
  itemId: string;
  originalFilename: string;
  documentType: string;
  extractedSummary: string;
  ocrStatus: string;
  aiStatus: string;
  classificationConfidence: number;
  needsReview: boolean;
  suggestedLabel: string;
  suggestedHref: string;
  routingConfidence: number;
  reason: string;
  signalSource: string;
  supportingEvidence: string[];
  conflictingEvidence: string[];
};

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return `${(value * 100).toFixed(0)}%`;
}

export default function NewProjectPage() {
  const locale = getLocale();
  const [projectName, setProjectName] = useState("");
  const [projectNumber, setProjectNumber] = useState("");
  const [customer, setCustomer] = useState("");
  const [address, setAddress] = useState("");
  const [projectManager, setProjectManager] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [contractAmount, setContractAmount] = useState("");
  const [budget, setBudget] = useState("");
  const [status, setStatus] = useState("planning");
  const [description, setDescription] = useState("");
  const [projectDocuments, setProjectDocuments] = useState<File[]>([]);
  const [createdProjectId, setCreatedProjectId] = useState("");
  const [documentResults, setDocumentResults] = useState<ProjectDocumentUploadResult[]>([]);
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function validateForm(): string {
    if (projectName.trim().length < 2) {
      return t(locale, "projects.validation.projectName");
    }

    if (projectNumber.trim().length < 1) {
      return t(locale, "projects.validation.projectNumber");
    }

    return "";
  }

  async function getErrorMessage(response: Response): Promise<string> {
    try {
      const payload = (await response.json()) as ApiErrorPayload;
      if (typeof payload.detail === "string" && payload.detail) {
        return payload.detail;
      }
      if (Array.isArray(payload.detail)) {
        const firstMessage = payload.detail.find((item) => item.msg)?.msg;
        if (firstMessage) {
          return firstMessage;
        }
      }
    } catch {
      // Ignore malformed error payloads and use the fallback below.
    }

    return t(locale, "common.projectCreateFailed");
  }

  async function fetchPlacementSuggestions(itemIds: string[], token: string, tenantId: string): Promise<Map<string, IntakePlacementSuggestion>> {
    if (itemIds.length === 0) {
      return new Map();
    }

    const response = await fetch(`${getApiBaseUrl()}/api/intake/placement/suggest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        "X-Tenant-ID": tenantId,
      },
      body: JSON.stringify({ item_ids: itemIds }),
    });

    if (!response.ok) {
      return new Map();
    }

    const payload = (await response.json()) as IntakePlacementSuggestionResponse;
    return new Map(payload.items.map((item) => [item.item_id, item]));
  }

  async function uploadProjectDocuments(projectId: string, token: string, tenantId: string): Promise<ProjectDocumentUploadResult[]> {
    const uploadedItems: IntakeUploadResponseItem[] = [];

    for (const file of projectDocuments) {
      const formData = new FormData();
      formData.append("project_id", projectId);
      formData.append("file", file);

      const response = await fetch(`${getApiBaseUrl()}/api/intake/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Tenant-ID": tenantId,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed for ${file.name}`);
      }

      uploadedItems.push((await response.json()) as IntakeUploadResponseItem);
    }

    const suggestions = await fetchPlacementSuggestions(uploadedItems.map((item) => item.id), token, tenantId);
    return uploadedItems.map((uploadedItem) => {
      const suggestion = suggestions.get(uploadedItem.id);
      return {
        itemId: uploadedItem.id,
        originalFilename: uploadedItem.original_filename,
        documentType: suggestion?.document_intelligence?.primary_document_type || uploadedItem.document_type,
        extractedSummary: uploadedItem.extracted_summary,
        ocrStatus: uploadedItem.ocr_status,
        aiStatus: uploadedItem.ai_status,
        classificationConfidence: uploadedItem.classification_confidence,
        needsReview: uploadedItem.needs_review,
        suggestedLabel: suggestion?.destination_label || "Extraction queue review",
        suggestedHref: suggestion?.destination_href || "/extraction-queue",
        routingConfidence: suggestion?.confidence ?? uploadedItem.classification_confidence,
        reason: suggestion?.reason || "Uploaded to intake for OCR, AI extraction, and human review.",
        signalSource: suggestion?.signal_source || "intake_upload",
        supportingEvidence: suggestion?.document_intelligence?.supporting_evidence || [],
        conflictingEvidence: suggestion?.document_intelligence?.conflicting_evidence || [],
      };
    });
  }

  async function submit(): Promise<void> {
    const error = validateForm();
    setMessage(error);
    if (error) {
      return;
    }

    setIsSubmitting(true);
    setDocumentResults([]);
    setCreatedProjectId("");
    const token = getAccessToken();
    const tenantId = getTenantId();
    const response = await fetch(`${getApiBaseUrl()}/api/projects`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        "X-Tenant-ID": tenantId,
      },
      body: JSON.stringify({
        project_name: projectName,
        project_number: projectNumber,
        customer,
        address,
        project_manager: projectManager,
        start_date: startDate ? `${startDate}T00:00:00Z` : null,
        end_date: endDate ? `${endDate}T00:00:00Z` : null,
        contract_amount: contractAmount ? Number(contractAmount) : null,
        budget: budget ? Number(budget) : null,
        status,
        description,
      }),
    });

    if (!response.ok) {
      setMessage(await getErrorMessage(response));
      setIsSubmitting(false);
      return;
    }
    const data = (await response.json()) as ProjectCreateResponse;
    setCreatedProjectId(data.id);

    if (projectDocuments.length === 0) {
      setMessage(t(locale, "common.projectCreated"));
      window.location.href = `/projects/${data.id}`;
      return;
    }

    try {
      const results = await uploadProjectDocuments(data.id, token, tenantId);
      setDocumentResults(results);
      setMessage(`Project created. Uploaded ${results.length} document${results.length === 1 ? "" : "s"} for OCR, AI classification, and routing review.`);
    } catch {
      setMessage("Project created, but one or more documents failed to upload. Open the Intake Hub to retry document upload.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppShell titleKey="projects.new">
      <div className="card">
        <span className="auth-eyebrow">Project Setup</span>
        <p className="muted">Create a structured project record with operational and budget context.</p>
      </div>

      <div className="card form-grid">
        <div className="two-col">
          <input placeholder={t(locale, "projects.projectName")} value={projectName} onChange={(e) => setProjectName(e.target.value)} />
          <input placeholder={t(locale, "projects.projectNumber")} value={projectNumber} onChange={(e) => setProjectNumber(e.target.value)} />
        </div>

        <div className="two-col">
          <input placeholder={t(locale, "projects.customer")} value={customer} onChange={(e) => setCustomer(e.target.value)} />
          <input placeholder={t(locale, "projects.projectManager")} value={projectManager} onChange={(e) => setProjectManager(e.target.value)} />
        </div>

        <input placeholder={t(locale, "projects.address")} value={address} onChange={(e) => setAddress(e.target.value)} />

        <div className="two-col">
          <label>
            {t(locale, "projects.startDate")}
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label>
            {t(locale, "projects.endDate")}
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
        </div>

        <div className="two-col">
          <input placeholder={t(locale, "projects.contractAmount")} value={contractAmount} onChange={(e) => setContractAmount(e.target.value)} />
          <input placeholder={t(locale, "projects.budget")} value={budget} onChange={(e) => setBudget(e.target.value)} />
        </div>

        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="planning">planning</option>
          <option value="active">active</option>
          <option value="on_hold">on_hold</option>
          <option value="complete">complete</option>
          <option value="cancelled">cancelled</option>
        </select>

        <textarea
          placeholder={t(locale, "projects.description")}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <div className="card" style={{ boxShadow: "none", margin: 0 }}>
          <span className="auth-eyebrow">Project Documents</span>
          <p className="muted" style={{ marginTop: 4 }}>
            Upload bid docs, haul tickets, invoices, quotes, manifests, receipts, delivery tickets, or photos. OpsFlow sends them through intake OCR, document classification, routing suggestions, and review.
          </p>
          <label>
            Attach project documents
            <input
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.txt,.csv,.xls,.xlsx,.doc,.docx,*/*"
              onChange={(event) => setProjectDocuments(Array.from(event.target.files ?? []))}
            />
          </label>
          {projectDocuments.length > 0 ? (
            <p className="muted">{projectDocuments.length} document{projectDocuments.length === 1 ? "" : "s"} selected for OCR/AI intake after project creation.</p>
          ) : null}
        </div>

        <div className="top-actions">
          <button onClick={submit} disabled={isSubmitting}>
            {isSubmitting ? "Creating and processing..." : t(locale, "projects.create")}
          </button>
          {createdProjectId ? <a href={`/projects/${createdProjectId}`}>Open Project</a> : null}
          {documentResults.length > 0 ? <a href="/extraction-queue">Review Extraction Queue</a> : null}
        </div>
        {message ? <p>{message}</p> : null}
      </div>

      {documentResults.length > 0 ? (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="section-header">
            <h3>OCR / AI Document Routing</h3>
          </div>
          <div className="list">
            {documentResults.map((result) => (
              <div className="list-item" key={result.itemId}>
                <strong>{result.originalFilename}</strong>
                <span className={`status-pill status-${result.needsReview ? "reviewing" : "uploaded"}`}>
                  {result.needsReview ? "Needs review" : "Uploaded"}
                </span>
                <span className="muted">Document type: {result.documentType}</span>
                <span className="muted">OCR: {result.ocrStatus} | AI: {result.aiStatus}</span>
                <span className="muted">Classification: {formatPercent(result.classificationConfidence)} | Routing: {formatPercent(result.routingConfidence)}</span>
                <span className="muted">Destination: {result.suggestedLabel}</span>
                <p className="muted" style={{ margin: 0 }}>{result.reason}</p>
                {result.extractedSummary ? <p style={{ margin: 0 }}>{result.extractedSummary}</p> : null}
                {result.supportingEvidence.length > 0 ? (
                  <p className="muted" style={{ margin: 0 }}>Evidence: {result.supportingEvidence.slice(0, 3).join("; ")}</p>
                ) : null}
                {result.conflictingEvidence.length > 0 ? (
                  <p style={{ margin: 0 }}>Review: {result.conflictingEvidence.slice(0, 2).join("; ")}</p>
                ) : null}
                <a href={result.suggestedHref}>Open Suggested Workflow</a>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
