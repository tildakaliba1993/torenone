import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { FrameSpec, SpanComparison } from "@/lib/api/service";

const { compareSpans, ServiceError } = vi.hoisted(() => {
  class ServiceError extends Error {}
  return { compareSpans: vi.fn(), ServiceError };
});
vi.mock("@/lib/api/service", () => ({
  compareSpans: (spec: FrameSpec, rate?: number) => compareSpans(spec, rate),
  ServiceError,
}));

import { SpanCompare } from "./span-compare";

const CMP: SpanComparison = {
  building_width_m: 24,
  baseline_spans: 1,
  lightest_passing_spans: 2,
  options: [
    {
      number_of_spans: 2, span_m: 12, number_of_frames: 5, feasible: true,
      per_frame_mass_kg: 700, total_primary_mass_kg: 3500, passed: true,
      governing_utilisation: 0.8, is_baseline: false, provisional: true,
      sections: [{ member: "column", designation: "254x146x37" }, { member: "rafter", designation: "254x146x31" }],
    },
    {
      number_of_spans: 1, span_m: 24, number_of_frames: 5, feasible: true,
      per_frame_mass_kg: 900, total_primary_mass_kg: 4500, passed: true,
      governing_utilisation: 0.95, is_baseline: true, provisional: false,
      sections: [{ member: "column", designation: "356x171x51" }, { member: "rafter", designation: "406x178x60" }],
    },
  ],
  notes: ["Any option with more than one span is MULTI-SPAN — PROVISIONAL."],
};

describe("SpanCompare", () => {
  beforeEach(() => vi.clearAllMocks());

  it("ranks span splits, flags multi-span provisional, and applies a choice", async () => {
    compareSpans.mockResolvedValue(CMP);
    const onApply = vi.fn();
    render(<SpanCompare getSpec={() => ({}) as FrameSpec} currentSpans={1} onApply={onApply} />);

    await userEvent.click(screen.getByRole("button", { name: /^compare$/i }));
    await waitFor(() => expect(screen.getByText(/2 × 12\.0 m/)).toBeTruthy());
    expect(screen.getAllByText(/provisional/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /in use/i })).toBeTruthy(); // baseline single span

    await userEvent.click(screen.getByRole("button", { name: /^use$/i }));
    expect(onApply).toHaveBeenCalledWith(2, 12);
  });

  it("refuses when the spec isn't ready", async () => {
    render(<SpanCompare getSpec={() => null} currentSpans={1} onApply={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /^compare$/i }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(compareSpans).not.toHaveBeenCalled();
  });
});
