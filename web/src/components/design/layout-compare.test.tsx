import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { FrameSpec, LayoutComparison } from "@/lib/api/service";

const { compareLayouts, ServiceError } = vi.hoisted(() => {
  class ServiceError extends Error {}
  return { compareLayouts: vi.fn(), ServiceError };
});
vi.mock("@/lib/api/service", () => ({
  compareLayouts: (spec: FrameSpec, rate?: number) => compareLayouts(spec, rate),
  ServiceError,
}));

import { LayoutCompare } from "./layout-compare";

const SPEC = {} as FrameSpec;

const COMPARISON: LayoutComparison = {
  building_length_m: 30,
  baseline_bays: 5,
  lightest_passing_bays: 4,
  options: [
    {
      number_of_bays: 4, bay_spacing_m: 7.5, number_of_frames: 5, feasible: true,
      per_frame_mass_kg: 900, total_primary_mass_kg: 4500, passed: true,
      governing_utilisation: 0.9, is_baseline: false,
      sections: [{ member: "column", designation: "IPE 450" }, { member: "rafter", designation: "IPE 400" }],
    },
    {
      number_of_bays: 5, bay_spacing_m: 6.0, number_of_frames: 6, feasible: true,
      per_frame_mass_kg: 800, total_primary_mass_kg: 4800, passed: true,
      governing_utilisation: 0.8, is_baseline: true,
      sections: [{ member: "column", designation: "IPE 400" }, { member: "rafter", designation: "IPE 360" }],
    },
  ],
  notes: ["Total steel compares the PRIMARY portal frames only."],
};

describe("LayoutCompare", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches and ranks framing options, and applies the chosen one", async () => {
    compareLayouts.mockResolvedValue(COMPARISON);
    const onApply = vi.fn();
    render(<LayoutCompare getSpec={() => SPEC} currentBays={5} onApply={onApply} />);

    await userEvent.click(screen.getByRole("button", { name: /^compare$/i }));
    await waitFor(() => expect(screen.getByText(/IPE 450 \/ IPE 400/)).toBeTruthy());

    // The lightest passing layout is flagged.
    expect(screen.getByText(/lightest/i)).toBeTruthy();
    // The current (baseline) layout's Use button is disabled ("In use").
    expect(screen.getByRole("button", { name: /in use/i })).toBeTruthy();

    // Applying the 4-bay option lifts its bay count + spacing.
    await userEvent.click(screen.getByRole("button", { name: /^use$/i }));
    expect(onApply).toHaveBeenCalledWith(4, 7.5);
  });

  it("refuses to compare when the spec isn't ready yet", async () => {
    const onApply = vi.fn();
    render(<LayoutCompare getSpec={() => null} currentBays={5} onApply={onApply} />);
    await userEvent.click(screen.getByRole("button", { name: /^compare$/i }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(compareLayouts).not.toHaveBeenCalled();
  });
});
