"use client";

import React from "react";
import { useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId, saveSession } from "@/lib/auth";
import { getApiBaseUrl, getLocale, setLocale as persistLocale, t } from "@/lib/i18n";

const COMPANY_TYPES = [
  "Earthwork / Site Development",
  "General Contractor",
  "Trucking / Hauling",
  "Heavy Civil",
  "Safety / Training",
  "Specialty Contractor",
  "Other",
];

const MODULE_OPTIONS = ["Projects", "Budget", "Safety", "Documents", "Payroll", "Fleet"];

type Step = {
  key: string;
  title: string;
};

export default function OnboardingPage() {
  const [locale, setLocale] = useState<"en" | "es">("en");
  const [stepIndex, setStepIndex] = useState(0);
  const [accountConfirmed, setAccountConfirmed] = useState(false);
  const [companyName, setCompanyName] = useState("");
  const [companyType, setCompanyType] = useState(COMPANY_TYPES[0]);
  const [language, setLanguage] = useState<"en" | "es">("en");
  const [modules, setModules] = useState<string[]>(["Projects", "Budget", "Safety"]);
  const [invites, setInvites] = useState("");
  const [firstProject, setFirstProject] = useState("First Launch Project");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const steps: Step[] = useMemo(
    () => [
      { key: "createAccount", title: t(locale, "onboarding.steps.createAccount") },
      { key: "createCompany", title: t(locale, "onboarding.steps.createCompany") },
      { key: "companyType", title: t(locale, "onboarding.steps.companyType") },
      { key: "language", title: t(locale, "onboarding.steps.language") },
      { key: "modules", title: t(locale, "onboarding.steps.modules") },
      { key: "invite", title: t(locale, "onboarding.steps.invite") },
      { key: "firstProject", title: t(locale, "onboarding.steps.firstProject") },
      { key: "openDashboard", title: t(locale, "onboarding.steps.openDashboard") },
    ],
    [locale]
  );

  useEffect(() => {
    setLocale(getLocale());
    const tenantId = getTenantId();
    if (tenantId) {
      window.location.href = "/dashboard";
    }
  }, []);

  const progressPercent = Math.round(((stepIndex + 1) / steps.length) * 100);

  function validateCurrentStep(): string {
    const inviteEmails = invites
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

    if (stepIndex === 0 && !accountConfirmed) {
      return t(locale, "onboarding.validation.accountConfirm");
    }

    if (stepIndex === 1 && companyName.trim().length < 2) {
      return t(locale, "onboarding.validation.companyName");
    }

    if (stepIndex === 2 && !companyType) {
      return t(locale, "onboarding.validation.companyType");
    }

    if (stepIndex === 3 && !["en", "es"].includes(language)) {
      return t(locale, "onboarding.validation.language");
    }

    if (stepIndex === 4 && modules.length === 0) {
      return t(locale, "onboarding.validation.modules");
    }

    if (stepIndex === 5) {
      const invalid = inviteEmails.find((email) => !/^\S+@\S+\.\S+$/.test(email));
      if (invalid) {
        return t(locale, "onboarding.validation.invites");
      }
    }

    if (stepIndex === 6 && firstProject.trim().length < 2) {
      return t(locale, "onboarding.validation.firstProject");
    }

    return "";
  }

  function goNext(): void {
    const error = validateCurrentStep();
    setMessage(error);
    if (error) {
      return;
    }

    setStepIndex((prev) => Math.min(prev + 1, steps.length - 1));
  }

  function goBack(): void {
    setMessage("");
    setStepIndex((prev) => Math.max(prev - 1, 0));
  }

  function toggleModule(moduleName: string): void {
    setModules((prev) => {
      if (prev.includes(moduleName)) {
        return prev.filter((item) => item !== moduleName);
      }
      return [...prev, moduleName];
    });
  }

  async function submit(): Promise<void> {
    const error = validateCurrentStep();
    setMessage(error);
    if (error) {
      return;
    }

    setIsSubmitting(true);
    const accessToken = getAccessToken();
    const response = await fetch(`${getApiBaseUrl()}/api/onboarding/complete`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        company_name: companyName,
        company_type: companyType,
        language,
        modules,
        invite_emails: invites.split(",").map((x) => x.trim()).filter(Boolean),
        first_project_name: firstProject,
      }),
    });

    if (!response.ok) {
      setMessage(t(locale, "common.onboardingFailed"));
      setIsSubmitting(false);
      return;
    }

    const data = await response.json();
    saveSession({
      accessToken,
      refreshToken: window.localStorage.getItem("opsflow_refresh_token") || "",
      tenantId: data.tenant_id,
    });
    setMessage(t(locale, "common.onboardingComplete"));
    window.location.href = "/dashboard";
  }

  return (
    <AppShell titleKey="onboarding.title">
      <p>{t(locale, "onboarding.wizardSubtitle")}</p>
      <div className="wizard-progress-wrap">
        <div className="wizard-progress-text">
          <span>{t(locale, "onboarding.stepLabel")}</span>
          <strong>
            {stepIndex + 1}/{steps.length} - {steps[stepIndex].title}
          </strong>
        </div>
        <div className="wizard-progress-track">
          <div className="wizard-progress-fill" style={{ width: `${progressPercent}%` }} />
        </div>
      </div>

      <div className="wizard-step-list">
        {steps.map((step, index) => (
          <div key={step.key} className={`wizard-chip ${index === stepIndex ? "is-active" : ""} ${index < stepIndex ? "is-done" : ""}`}>
            {index + 1}. {step.title}
          </div>
        ))}
      </div>

      <div className="form-grid">
        {stepIndex === 0 ? (
          <label className="wizard-check">
            <input type="checkbox" checked={accountConfirmed} onChange={(e) => setAccountConfirmed(e.target.checked)} />
            <span>{t(locale, "onboarding.createAccountDone")}</span>
          </label>
        ) : null}

        {stepIndex === 1 ? (
          <input
            placeholder={t(locale, "onboarding.companyName")}
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
          />
        ) : null}

        {stepIndex === 2 ? (
          <select value={companyType} onChange={(e) => setCompanyType(e.target.value)}>
            {COMPANY_TYPES.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        ) : null}

        {stepIndex === 3 ? (
          <select
            value={language}
            onChange={(e) => {
              const selected = e.target.value as "en" | "es";
              setLanguage(selected);
              setLocale(selected);
              persistLocale(selected);
            }}
          >
            <option value="en">{t(locale, "common.english")}</option>
            <option value="es">{t(locale, "common.spanish")}</option>
          </select>
        ) : null}

        {stepIndex === 4 ? (
          <div className="wizard-module-grid">
            {MODULE_OPTIONS.map((item) => (
              <label key={item} className="wizard-check">
                <input type="checkbox" checked={modules.includes(item)} onChange={() => toggleModule(item)} />
                <span>{item}</span>
              </label>
            ))}
          </div>
        ) : null}

        {stepIndex === 5 ? (
          <input
            placeholder={t(locale, "onboarding.invites")}
            value={invites}
            onChange={(e) => setInvites(e.target.value)}
          />
        ) : null}

        {stepIndex === 6 ? (
          <input
            placeholder={t(locale, "onboarding.firstProject")}
            value={firstProject}
            onChange={(e) => setFirstProject(e.target.value)}
          />
        ) : null}

        {stepIndex === 7 ? (
          <div className="card">
            <p>{t(locale, "onboarding.reviewTitle")}</p>
            <p>
              <strong>{t(locale, "onboarding.companyName")}:</strong> {companyName}
            </p>
            <p>
              <strong>{t(locale, "onboarding.companyType")}:</strong> {companyType}
            </p>
            <p>
              <strong>{t(locale, "onboarding.language")}:</strong> {language}
            </p>
            <p>
              <strong>{t(locale, "onboarding.modules")}:</strong> {modules.join(", ")}
            </p>
            <p>
              <strong>{t(locale, "onboarding.firstProject")}:</strong> {firstProject}
            </p>
          </div>
        ) : null}
      </div>

      <div className="wizard-actions">
        <button onClick={goBack} disabled={stepIndex === 0}>
          {t(locale, "onboarding.back")}
        </button>
        {stepIndex < steps.length - 1 ? (
          <button onClick={goNext}>{t(locale, "onboarding.next")}</button>
        ) : (
          <button onClick={submit} disabled={isSubmitting}>
            {isSubmitting ? t(locale, "common.loading") : t(locale, "onboarding.openDashboard")}
          </button>
        )}
      </div>

      {message ? <p>{message}</p> : null}
    </AppShell>
  );
}
