import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { KernelProgress } from "./kernel-progress";

describe("KernelProgress", () => {
  it("shows the live status header and the real kernel pipeline stages", () => {
    render(<KernelProgress />);
    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.getByText(/running the deterministic sans kernel/i)).toBeTruthy();
    // A couple of the real stages are listed (names the actual SANS steps).
    expect(screen.getByText(/load combinations — SANS 10160-1/i)).toBeTruthy();
    expect(screen.getByText(/plane-frame analysis/i)).toBeTruthy();
    expect(screen.getByText(/calc-package PDF/i)).toBeTruthy();
  });
});
