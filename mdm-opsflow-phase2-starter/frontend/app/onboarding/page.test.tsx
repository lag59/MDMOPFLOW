import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import OnboardingPage from "./page";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
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

    const companyTypeOption = screen.getByLabelText("General Contractor");
    await user.click(companyTypeOption);
    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByRole("combobox")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByLabelText("General Contractor")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByPlaceholderText("Company name")).toBeInTheDocument();
  });

  it("shows a failure banner when onboarding completion is rejected", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(new Response("server error", { status: 500 }));

    const user = userEvent.setup();
    render(<OnboardingPage />);

    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.type(screen.getByPlaceholderText("Company name"), "Acme Civil");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.click(screen.getByLabelText("General Contractor"));
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.type(screen.getByPlaceholderText("Invite emails (comma separated)"), "ops@example.com");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.type(screen.getByPlaceholderText("First project name"), "Central Yard");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.click(screen.getByRole("button", { name: "Open dashboard" }));

    expect(await screen.findByText("Onboarding failed")).toBeInTheDocument();
    expect(screen.getByText("Onboarding failed").closest("div")).toHaveClass("danger-card");
  });
});
