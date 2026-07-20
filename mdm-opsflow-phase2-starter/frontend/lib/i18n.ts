import en from "@/locales/en.json";
import es from "@/locales/es.json";

export type Locale = "en" | "es";

const dictionaries = { en, es } as const;

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
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
}
