import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ModulesPage from "./page";

const accessState = {
  roleKey: "project_manager",
  roleKeys: ["project_manager"],
  isSuperAdmin: false,
};

vi.mock("@/components/AppShell", () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/lib/i18n", () => ({
  getLocale: () => "en",
  t: (_locale: string, key: string) => key,
}));

vi.mock("@/lib/roleAccess", () => ({
  getCurrentRoleAccess: vi.fn(async () => accessState),
  canAccessModuleRole: vi.fn((context: { roleKey: string; roleKeys: string[]; isSuperAdmin: boolean } | null, routeRoleKey: string) => {
    if (!context) {
      return false;
    }
    return context.isSuperAdmin || context.roleKeys.includes(routeRoleKey);
  }),
}));

describe("Modules page workspace visibility", () => {
  beforeEach(() => {
    accessState.roleKey = "project_manager";
    accessState.roleKeys = ["project_manager"];
    accessState.isSuperAdmin = false;
  });

  it("shows all assigned role workspaces for non-super-admin users with multiple roles", async () => {
    accessState.roleKey = "project_manager";
    accessState.roleKeys = ["project_manager", "estimator"];

    render(<ModulesPage />);

    await waitFor(() => {
      expect(screen.getByText("Project Manager")).toBeInTheDocument();
      expect(screen.getByText("Estimator")).toBeInTheDocument();
      expect(screen.getByText("Current Role")).toBeInTheDocument();
      expect(screen.getByText("Assigned Role")).toBeInTheDocument();
    });
  });

  it("shows all role module cards for super admins", async () => {
    accessState.roleKey = "administrator";
    accessState.roleKeys = ["administrator"];
    accessState.isSuperAdmin = true;

    render(<ModulesPage />);

    await waitFor(() => {
      expect(screen.getByText("Project Manager")).toBeInTheDocument();
      expect(screen.getByText("Estimator")).toBeInTheDocument();
      expect(screen.getByText("Vendor")).toBeInTheDocument();
    });
  });
});
