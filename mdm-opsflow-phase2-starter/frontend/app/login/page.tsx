"use client";

import Link from "next/link";
import { useState } from "react";

import { saveSession } from "@/lib/auth";
import { getApiBaseUrl, getLocale, t } from "@/lib/i18n";

export default function LoginPage() {
  const locale = getLocale();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(): Promise<void> {
    setError("");
    const response = await fetch(`${getApiBaseUrl()}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      setError(t(locale, "common.loginFailed"));
      return;
    }
    const data = await response.json();
    saveSession({
      accessToken: data.tokens.access_token,
      refreshToken: data.tokens.refresh_token,
      tenantId: data.tenant_id,
    });
    if (data.platform_role === "platform_super_admin") {
      window.location.href = "/platform-admin";
      return;
    }

    window.location.href = data.tenant_id ? "/dashboard" : "/onboarding";
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <span className="auth-eyebrow">MDM OpsFlow</span>
        <h1>{t(locale, "auth.login")}</h1>
        <p className="auth-tagline">The AI Operating System for Construction.</p>
        <input placeholder={t(locale, "auth.email")} value={email} onChange={(e) => setEmail(e.target.value)} />
        <input
          placeholder={t(locale, "auth.password")}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button onClick={submit}>{t(locale, "auth.loginCta")}</button>
        {error ? <p>{error}</p> : null}
        <Link href="/register">{t(locale, "auth.goToRegister")}</Link>
      </div>
    </div>
  );
}
