"use client";

import { useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

type ApiErrorPayload = {
  detail?: string | Array<{ msg?: string }>;
};

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

  async function submit(): Promise<void> {
    const error = validateForm();
    setMessage(error);
    if (error) {
      return;
    }

    setIsSubmitting(true);
    const response = await fetch(`${getApiBaseUrl()}/api/projects`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken()}`,
        "X-Tenant-ID": getTenantId(),
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
    const data = await response.json();
    setMessage(t(locale, "common.projectCreated"));
    window.location.href = `/projects/${data.id}`;
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

        <div className="top-actions">
          <button onClick={submit} disabled={isSubmitting}>
            {isSubmitting ? `${t(locale, "projects.create")}...` : t(locale, "projects.create")}
          </button>
        </div>
        {message ? <p>{message}</p> : null}
      </div>
    </AppShell>
  );
}
