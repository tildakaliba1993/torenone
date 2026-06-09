import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "./status-badge";

describe("StatusBadge", () => {
  it("renders a text label so status is never colour-only (PRD FR-19)", () => {
    render(<StatusBadge status="fail" />);
    expect(screen.getByText("FAIL")).toBeTruthy();
  });

  it("exposes an accessible status with a descriptive aria-label", () => {
    render(<StatusBadge status="pass">Utilisation 0.82</StatusBadge>);
    const el = screen.getByRole("status");
    expect(el.getAttribute("aria-label")).toBe("PASS: Utilisation 0.82");
  });

  it("renders the custom content when provided", () => {
    render(<StatusBadge status="review">Near limit</StatusBadge>);
    expect(screen.getByText("Near limit")).toBeTruthy();
  });
});
