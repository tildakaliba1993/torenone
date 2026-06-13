import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ParseResponse } from "@/lib/api/service";

const { parseDescription, ServiceError } = vi.hoisted(() => {
  class ServiceError extends Error {}
  return { parseDescription: vi.fn(), ServiceError };
});
vi.mock("@/lib/api/service", () => ({
  parseDescription: (description: string) => parseDescription(description),
  ServiceError,
}));

import { DescribeStep } from "./describe-step";

const completeResult: ParseResponse = {
  status: "complete",
  spec: {
    geometry: {
      span_m: 20,
      eaves_height_m: 6,
      roof_pitch_deg: 10,
      bay_spacing_m: 6,
      number_of_bays: 5,
    },
    dead: { roof_kpa: 0.15, services_kpa: 0, wall_cladding_kpa: 0 },
    wind: { basic_wind_speed_ms: 36, terrain_category: "B", site_altitude_m: 0, has_dominant_opening: false },
  },
  assumptions: [],
  questions: [],
  missing: [],
  errors: [],
  scope_note: null,
};

describe("DescribeStep", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("disables Parse until there is a description", async () => {
    render(<DescribeStep onComplete={vi.fn()} />);
    const button = screen.getByRole("button", { name: /parse description/i });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    await userEvent.type(screen.getByLabelText("Describe your portal frame"), "20 m span shed");
    expect((button as HTMLButtonElement).disabled).toBe(false);
  });

  it("fills the textarea from an example", async () => {
    render(<DescribeStep onComplete={vi.fn()} />);
    const examples = screen.getAllByRole("button", { name: /span|portal frame|warehouse/i });
    await userEvent.click(examples[0]);
    const textarea = screen.getByLabelText("Describe your portal frame") as HTMLTextAreaElement;
    expect(textarea.value.length).toBeGreaterThan(0);
  });

  it("calls onComplete when parsing succeeds", async () => {
    const onComplete = vi.fn();
    parseDescription.mockResolvedValue(completeResult);
    render(<DescribeStep onComplete={onComplete} />);
    await userEvent.type(screen.getByLabelText("Describe your portal frame"), "20 m span warehouse");
    await userEvent.click(screen.getByRole("button", { name: /parse description/i }));
    await waitFor(() => expect(onComplete).toHaveBeenCalledWith(completeResult));
  });

  it("surfaces clarifying questions inline", async () => {
    parseDescription.mockResolvedValue({
      ...completeResult,
      status: "needs_clarification",
      spec: null,
      questions: [{ field: "span_m", question: "What is the clear span?", kind: "missing", unit: "m" }],
      missing: ["span_m"],
    });
    const onComplete = vi.fn();
    render(<DescribeStep onComplete={onComplete} />);
    await userEvent.type(screen.getByLabelText("Describe your portal frame"), "a shed");
    await userEvent.click(screen.getByRole("button", { name: /parse description/i }));
    expect(await screen.findByText(/what is the clear span\?/i)).toBeTruthy();
    expect(onComplete).not.toHaveBeenCalled();
  });

  it("shows the scope note when out of scope", async () => {
    parseDescription.mockResolvedValue({
      ...completeResult,
      status: "out_of_scope",
      spec: null,
      scope_note: "Multi-bay frames are not supported yet.",
    });
    render(<DescribeStep onComplete={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Describe your portal frame"), "a suspension bridge");
    await userEvent.click(screen.getByRole("button", { name: /parse description/i }));
    expect(await screen.findByText("Multi-bay frames are not supported yet.")).toBeTruthy();
  });

  it("shows a friendly error when the service is unreachable", async () => {
    parseDescription.mockRejectedValue(new ServiceError("Couldn’t reach the engineering service. Is it running?"));
    render(<DescribeStep onComplete={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Describe your portal frame"), "20 m span warehouse");
    await userEvent.click(screen.getByRole("button", { name: /parse description/i }));
    expect(await screen.findByText(/couldn.t reach the engineering service/i)).toBeTruthy();
  });
});
