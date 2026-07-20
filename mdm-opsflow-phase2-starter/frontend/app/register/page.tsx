"use client";

import Link from "next/link";
import { useState } from "react";

import { saveSession } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

export default function RegisterPage() {
  const locale = getLocale();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(): Promise<void> {
    setError("");
    const response = await fetch(`${getApiBaseUrl()}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: displayName, email, password }),
    });
    if (!response.ok) {
      setError(t(locale, "common.registerFailed"));
      return;
    }
    const data = await response.json();
    saveSession({
      accessToken: data.tokens.access_token,
      refreshToken: data.tokens.refresh_token,
      tenantId: data.tenant_id,
    });
    window.location.href = "/onboarding";
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>{t(locale, "auth.register")}</h1>
        <input
          placeholder={t(locale, "auth.displayName")}
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
        />
        <input placeholder={t(locale, "auth.email")} value={email} onChange={(e) => setEmail(e.target.value)} />
        <input
          placeholder={t(locale, "auth.password")}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button onClick={submit}>{t(locale, "auth.registerCta")}</button>
        {error ? <p>{error}</p> : null}
        <Link href="/login">{t(locale, "auth.goToLogin")}</Link>
      </div>
    </div>
  );
}
