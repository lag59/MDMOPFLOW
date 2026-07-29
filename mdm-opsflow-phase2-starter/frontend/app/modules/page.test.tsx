import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ModulesPage from "./page";

const accessState = {
  roleKey: "project_manager",
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
}));

describe("Modules page role filtering", () => {
  beforeEach(() => {
    accessState.roleKey = "project_manager";
    accessState.isSuperAdmin = false;
  });

  it("shows only the current role modules for non-super-admin users", async () => {
    render(<ModulesPage />);

    await waitFor(() => {
      expect(screen.getByText("Project Manager")).toBeInTheDocument();
      expect(screen.queryByText("Estimator")).not.toBeInTheDocument();
      expect(screen.queryByText("Vendor")).not.toBeInTheDocument();
    });
  });

  it("shows all role module cards for super admins", async () => {
    accessState.roleKey = "administrator";
    accessState.isSuperAdmin = true;

    render(<ModulesPage />);

    await waitFor(() => {
      expect(screen.getByText("Project Manager")).toBeInTheDocument();
      expect(screen.getByText("Estimator")).toBeInTheDocument();
      expect(screen.getByText("Vendor")).toBeInTheDocument();
    });
  });
});
