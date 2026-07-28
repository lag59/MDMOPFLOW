import { describe, expect, it } from "vitest";

import { buildModuleDetailHref, getModuleDetail, toModuleSlug } from "./modules";

describe("module metadata helpers", () => {
  it("slugifies labels and builds role-scoped module detail links", () => {
    expect(toModuleSlug("Executive Dashboard")).toBe("executive-dashboard");
    expect(buildModuleDetailHref("company_owner", "Executive Dashboard")).toBe(
      "/modules/company_owner/executive-dashboard"
    );
  });

  it("resolves module detail metadata for known role/module combinations", () => {
    const detail = getModuleDetail("dispatcher", "dispatch-board");
    expect(detail).not.toBeNull();
    expect(detail?.moduleLabel).toBe("Dispatch Board");
    expect(detail?.route.href).toBe("/ticket-manager");
    expect(detail?.route.status).toBe("live");
  });

  it("returns null for unknown role or module slugs", () => {
    expect(getModuleDetail("unknown", "dispatch-board")).toBeNull();
    expect(getModuleDetail("dispatcher", "not-a-real-module")).toBeNull();
  });
});
