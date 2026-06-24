import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import LegalLayout from "./layout";
import PrivacyPage from "./privacy/page";
import RefundsPage from "./refunds/page";
import TermsPage from "./terms/page";

describe("Legal pages", () => {
  it("layout shows the legal sub-nav (Terms, Privacy, Refunds)", () => {
    render(
      <LegalLayout>
        <p>content</p>
      </LegalLayout>,
    );
    const nav = screen.getByRole("navigation", { name: /legal/i });
    expect(within(nav).getByRole("link", { name: /terms/i }).getAttribute("href")).toBe("/terms");
    expect(within(nav).getByRole("link", { name: /privacy/i }).getAttribute("href")).toBe(
      "/privacy",
    );
    expect(within(nav).getByRole("link", { name: /refunds/i }).getAttribute("href")).toBe(
      "/refunds",
    );
  });

  it("Refund policy: 14-day refund, cancel any time, via Paddle, statutory rights", () => {
    render(<RefundsPage />);
    expect(screen.getByText(/Refund & Cancellation Policy/i)).toBeTruthy();
    expect(screen.getByText(/14 days/i)).toBeTruthy();
    expect(screen.getByText(/at any time/i)).toBeTruthy();
    expect(screen.getAllByText(/Paddle/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Consumer Protection Act/i)).toBeTruthy();
  });

  it("Terms states TorenOne is a computational aid and the engineer is the responsible agent", () => {
    render(<TermsPage />);
    expect(screen.getByText("Terms of Service")).toBeTruthy();
    expect(screen.getByText(/computational aid/i)).toBeTruthy();
    expect(screen.getByText(/authoritative, responsible agent/i)).toBeTruthy();
    expect(screen.getByText(/limitation of liability/i)).toBeTruthy();
  });

  it("Privacy is PoPIA-aware and discloses the third-party AI processing", () => {
    render(<PrivacyPage />);
    expect(screen.getAllByText(/Privacy Policy/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/PoPIA/).length).toBeGreaterThan(0);
    expect(screen.getByText(/third-party AI provider/i)).toBeTruthy();
    expect(screen.getAllByText(/Information Regulator/i).length).toBeGreaterThan(0);
  });
});
