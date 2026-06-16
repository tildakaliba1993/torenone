import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { FrameSpec } from "@/lib/api/service";

const { runDesign, ServiceError } = vi.hoisted(() => {
  class ServiceError extends Error {}
  return { runDesign: vi.fn(), ServiceError };
});
vi.mock("@/lib/api/service", () => ({
  runDesign: (request: unknown) => runDesign(request),
  ServiceError,
}));

import { ReviewStep } from "./review-step";

const SPEC: FrameSpec = {
  geometry: { span_m: 20, eaves_height_m: 6, roof_pitch_deg: 10, bay_spacing_m: 6, number_of_bays: 5 },
  materials: { steel_grade: "S355JR" },
  base_fixity: "pinned",
  restraints: { rafter_restraint_spacing_m: null, column_restraint_spacing_m: null },
  dead: { roof_kpa: 0.15, services_kpa: 0.1, wall_cladding_kpa: 0.15 },
  imposed: { roof_access: false },
  wind: { basic_wind_speed_ms: 36, terrain_category: "B", site_altitude_m: 1400, has_dominant_opening: false },
  foundation: { allowable_bearing_kpa: 150, concrete_fcu_mpa: 25 },
};

const OK = {
  result: { passed: true, governing_utilisation: 0.82 },
  report: { run_id: "r", report_id: "rep", storage_path: "p", content_type: "application/pdf", size_bytes: 1 },
};

function renderStep(overrides: Partial<Parameters<typeof ReviewStep>[0]> = {}) {
  const onComplete = vi.fn();
  const onBack = vi.fn();
  render(
    <ReviewStep spec={SPEC} projectId="proj-1" onComplete={onComplete} onBack={onBack} {...overrides} />,
  );
  return { onComplete, onBack };
}

describe("ReviewStep", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("prefills the editable fields from the parsed spec", () => {
    renderStep();
    expect((screen.getByLabelText(/^span/i) as HTMLInputElement).value).toBe("20");
    expect((screen.getByLabelText(/roof dead load/i) as HTMLInputElement).value).toBe("0.15");
  });

  it("keeps Run disabled until the engineer explicitly confirms", async () => {
    renderStep();
    const run = screen.getByRole("button", { name: /run design/i });
    expect((run as HTMLButtonElement).disabled).toBe(true);
    await userEvent.click(screen.getByLabelText(/reviewed these inputs/i));
    expect((run as HTMLButtonElement).disabled).toBe(false);
  });

  it("runs the design with the built spec after confirmation", async () => {
    runDesign.mockResolvedValue(OK);
    const { onComplete } = renderStep();
    await userEvent.click(screen.getByLabelText(/reviewed these inputs/i));
    await userEvent.click(screen.getByRole("button", { name: /run design/i }));
    await waitFor(() => expect(runDesign).toHaveBeenCalledTimes(1));
    const req = runDesign.mock.calls[0][0];
    expect(req.mode).toBe("design");
    expect(req.project_id).toBe("proj-1");
    expect(req.sections).toBeNull();
    expect(req.spec.geometry.span_m).toBe(20);
    expect(req.spec.wind.terrain_category).toBe("B");
    await waitFor(() => expect(onComplete).toHaveBeenCalledWith(OK));
  });

  it("explains Check mode as the lower-liability path (FR-24)", async () => {
    renderStep();
    // Design mode framing by default…
    expect(screen.getByText(/auto-sizes the lightest adequate sections/i)).toBeTruthy();
    // …switching to Check mode surfaces the "you stay the author" framing.
    await userEvent.click(screen.getByRole("button", { name: /check my sections/i }));
    expect(screen.getByText(/you stay the author of the design/i)).toBeTruthy();
  });

  it("requires section sizes in Check mode", async () => {
    const { onComplete } = renderStep();
    await userEvent.click(screen.getByRole("button", { name: /check my sections/i }));
    await userEvent.click(screen.getByLabelText(/reviewed these inputs/i));
    await userEvent.click(screen.getByRole("button", { name: /run design/i }));
    expect(await screen.findByText(/required in check mode/i)).toBeTruthy();
    expect(onComplete).not.toHaveBeenCalled();
    expect(runDesign).not.toHaveBeenCalled();
  });

  it("surfaces a service error from the design run", async () => {
    runDesign.mockRejectedValue(new ServiceError("The design run failed (422)."));
    renderStep();
    await userEvent.click(screen.getByLabelText(/reviewed these inputs/i));
    await userEvent.click(screen.getByRole("button", { name: /run design/i }));
    expect(await screen.findByText("The design run failed (422).")).toBeTruthy();
  });
});
