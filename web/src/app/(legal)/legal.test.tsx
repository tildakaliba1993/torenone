import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import LegalLayout from "./layout";
import PrivacyPage from "./privacy/page";
import TermsPage from "./terms/page";

describe("Legal pages", () => {
  it("layout shows a prominent DRAFT / not-legal-advice banner", () => {
    render(
      <LegalLayout>
        <p>content</p>
      </LegalLayout>,
    );
    expect(screen.getByRole("note").textContent).toMatch(/draft — not legal advice/i);
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
