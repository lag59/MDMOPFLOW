import en from "@/locales/en.json";
import es from "@/locales/es.json";

export type Locale = "en" | "es";

const dictionaries = { en, es } as const;
const PRODUCTION_API_URL = "https://mdmopflow-production-cd89.up.railway.app";

function isPrivateIpv4(host: string): boolean {
  const parts = host.split(".");
  if (parts.length !== 4 || parts.some((part) => !/^\d+$/.test(part))) {
    return false;
  }

  const [a, b] = parts.map((value) => Number.parseInt(value, 10));
  if (a === 10) {
    return true;
  }
  if (a === 172 && b >= 16 && b <= 31) {
    return true;
  }
  if (a === 192 && b === 168) {
    return true;
  }
  return false;
}

export function getLocale(): Locale {
  if (typeof window === "undefined") {
    return "en";
  }
  const value = window.localStorage.getItem("opsflow_locale");
  return value === "es" ? "es" : "en";
}

export function setLocale(locale: Locale): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem("opsflow_locale", locale);
}

export function t(locale: Locale, key: string): string {
  const selected = dictionaries[locale] as Record<string, unknown>;
  const value = key.split(".").reduce<unknown>((acc, part) => {
    if (acc && typeof acc === "object" && part in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[part];
    }
    return key;
  }, selected);
  return typeof value === "string" ? value : key;
}

export function getApiBaseUrl(): string {
  const configured = (process.env.NEXT_PUBLIC_API_URL || "").trim();
  if (configured) {
    return configured;
  }

  if (typeof window !== "undefined") {
    const host = window.location.hostname.toLowerCase();
    const localHosts = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);
    const isLocalNetworkHost =
      localHosts.has(host) || host.endsWith(".local") || isPrivateIpv4(host);

    if (isLocalNetworkHost) {
      return `${window.location.protocol}//${window.location.hostname}:8080`;
    }

    if (
      host === "www.mdmopflow.com" ||
      host === "mdmopflow.com" ||
      host.endsWith(".up.railway.app")
    ) {
      return PRODUCTION_API_URL;
    }

    if (window.location.protocol === "http:") {
      return `${window.location.protocol}//${window.location.hostname}:8080`;
    }
  }

  return PRODUCTION_API_URL;
}
