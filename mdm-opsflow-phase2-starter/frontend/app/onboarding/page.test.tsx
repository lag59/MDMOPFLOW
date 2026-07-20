import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import OnboardingPage from "./page";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: unknown }) => <a href={href}>{children}</a>,
}));

describe("Onboarding wizard", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("opsflow_locale", "en");
    window.localStorage.setItem("opsflow_access_token", "token");
    vi.restoreAllMocks();
  });

  it("blocks step advance until current step is valid", async () => {
    const user = userEvent.setup();
    render(<OnboardingPage />);

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Confirm account creation to continue.")).toBeInTheDocument();

    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByPlaceholderText("Company name")).toBeInTheDocument();
  });

  it("supports navigation and validates company step before moving forward", async () => {
    const user = userEvent.setup();
    render(<OnboardingPage />);

    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Next" }));

    const companyNameInput = screen.getByPlaceholderText("Company name");
    await user.clear(companyNameInput);
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Company name must be at least 2 characters.")).toBeInTheDocument();

    await user.type(companyNameInput, "Acme Civil");
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("combobox")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByPlaceholderText("Company name")).toBeInTheDocument();
  });
});
