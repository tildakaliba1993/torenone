import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DesignResponse } from "@/lib/api/service";

const { getReportSignedUrl, ServiceError } = vi.hoisted(() => {
  class ServiceError extends Error {}
  return { getReportSignedUrl: vi.fn(), ServiceError };
});
vi.mock("@/lib/api/service", () => ({
  getReportSignedUrl: (path: string) => getReportSignedUrl(path),
  ServiceError,
}));

import { ResultsStep } from "./results-step";

const RESP: DesignResponse = {
  result: {
    frame_spec: {
      geometry: { span_m: 20, eaves_height_m: 6, roof_pitch_deg: 10, bay_spacing_m: 6, number_of_bays: 5 },
      dead: { roof_kpa: 0.15, services_kpa: 0, wall_cladding_kpa: 0 },
      wind: { basic_wind_speed_ms: 36, terrain_category: "B", site_altitude_m: 0, has_dominant_opening: false },
    },
    sections: [
      { member: "rafter", designation: "IPE 400" },
      { member: "column", designation: "IPE 450" },
    ],
    checks: [
      { name: "Rafter bending", clause: "SANS 10162-1 13.5", utilisation: 0.78, passed: true },
      { name: "Column LTB", clause: "SANS 10162-1 13.6", utilisation: 1.14, passed: false },
    ],
    rules_version: {},
    warnings: ["Footing not designed — no allowable bearing supplied."],
    total_steel_mass_kg: 1234,
    indicative_cost_zar: 56789,
    total_steel_tonnes: 1.234,
    connections: [
      {
        location: "eaves",
        description: "M20 8.8 bolts, 12 mm end plate",
        design_moment_knm: 120,
        design_shear_kn: 45,
        design_axial_kn: 0,
        checks: [],
      },
    ],
    baseplate: {
      base_fixity: "pinned",
      description: "300×300×20 plate, 4×M20",
      design_axial_kn: 80,
      design_shear_kn: 20,
      design_moment_knm: 0,
      checks: [],
    },
    footing: null,
    wind: {
      peak_velocity_pressure_kpa: 0.72,
      reference_height_m: 7.74,
      scenario: "enclosed building (no dominant opening)",
      clause: "SANS 10160-3:2019 cl. 7–8 — net = qp·(cpe − cpi)",
      cases: [
        {
          name: "cpi=+0.20, roof suction (uplift)",
          cpi: 0.2,
          net_cp_windward_wall: 0.6,
          net_cp_leeward_wall: -0.5,
          net_cp_windward_roof: -1.0,
          net_cp_leeward_roof: -0.8,
          windward_column_udl_kn_per_m: 2.6,
          leeward_column_udl_kn_per_m: -2.2,
          windward_rafter_udl_kn_per_m: -4.3,
          leeward_rafter_udl_kn_per_m: -3.5,
        },
      ],
    },
    passed: false,
    governing_utilisation: 1.14,
  },
  report: {
    run_id: "r",
    report_id: "rep_abc",
    storage_path: "firm-1/rep_abc.pdf",
    content_type: "application/pdf",
    size_bytes: 1000,
  },
};

describe("ResultsStep", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "open").mockReturnValue(null);
  });

  it("renders the overall result, member sizes, tonnage and cost", () => {
    render(<ResultsStep result={RESP} onRestart={vi.fn()} />);
    expect(screen.getByText("Some checks fail")).toBeTruthy();
    expect(screen.getAllByText("1.14").length).toBeGreaterThan(0); // governing + the failing check
    expect(screen.getByText("IPE 400")).toBeTruthy();
    expect(screen.getByText("IPE 450")).toBeTruthy();
    expect(screen.getByText("1.23 t")).toBeTruthy();
    expect(screen.getByText("R 56,789")).toBeTruthy();
  });

  it("renders each check with its clause and utilisation", () => {
    render(<ResultsStep result={RESP} onRestart={vi.fn()} />);
    expect(screen.getByText("Rafter bending")).toBeTruthy();
    expect(screen.getByText("SANS 10162-1 13.6")).toBeTruthy();
    expect(screen.getByText("0.78")).toBeTruthy();
  });

  it("shows an informational (non-gating) check as ADVISORY, not FAIL", () => {
    const withAdvisory: DesignResponse = {
      ...RESP,
      result: {
        ...RESP.result,
        checks: [
          ...RESP.result.checks,
          {
            name: "Horizontal sway (SLS) — H/400 [SLS-2 wind]",
            clause: "SANS 10162-1:2011 Annex D, Table D.1 (H/400)",
            utilisation: 3.6, // exceeds the limit, but advisory-only
            passed: false,
            informational: true,
          },
        ],
      },
    };
    render(<ResultsStep result={withAdvisory} onRestart={vi.fn()} />);
    expect(screen.getByText("Horizontal sway (SLS) — H/400 [SLS-2 wind]")).toBeTruthy();
    // The advisory row carries the ADVISORY label even though it exceeds its limit...
    const advisoryBadge = screen.getByText("advisory");
    expect(advisoryBadge).toBeTruthy();
    // ...and the gating column LTB failure is still the only "fail" badge.
    expect(screen.getAllByText("fail")).toHaveLength(1);
  });

  it("renders the wind actions (qp + load cases)", () => {
    render(<ResultsStep result={RESP} onRestart={vi.fn()} />);
    expect(screen.getByText("Wind actions — SANS 10160-3")).toBeTruthy();
    expect(screen.getByText("0.720 kPa")).toBeTruthy();
    expect(screen.getByText(/roof suction \(uplift\)/i)).toBeTruthy();
  });

  it("renders connection and baseplate detail blocks", () => {
    render(<ResultsStep result={RESP} onRestart={vi.fn()} />);
    expect(screen.getByText("M20 8.8 bolts, 12 mm end plate")).toBeTruthy();
    expect(screen.getByText("300×300×20 plate, 4×M20")).toBeTruthy();
    expect(screen.getByText(/footing not designed/i)).toBeTruthy();
  });

  it("downloads the PDF via a signed URL", async () => {
    getReportSignedUrl.mockResolvedValue("https://signed.example/rep.pdf");
    render(<ResultsStep result={RESP} onRestart={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /download calc package/i }));
    await waitFor(() => expect(getReportSignedUrl).toHaveBeenCalledWith("firm-1/rep_abc.pdf"));
    expect(window.open).toHaveBeenCalledWith(
      "https://signed.example/rep.pdf",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("shows an error when the download link fails", async () => {
    getReportSignedUrl.mockRejectedValue(new ServiceError("Could not generate a download link."));
    render(<ResultsStep result={RESP} onRestart={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /download calc package/i }));
    expect(await screen.findByText("Could not generate a download link.")).toBeTruthy();
  });

  // FR-26 — provenance on-screen
  it("renders the deterministic-kernel provenance badge", () => {
    render(<ResultsStep result={RESP} onRestart={vi.fn()} />);
    expect(screen.getByText(/deterministic kernel — not ai/i)).toBeTruthy();
  });

  it("renders the standards card with pinned editions when rules_version is present", () => {
    const withRules: DesignResponse = {
      ...RESP,
      result: {
        ...RESP.result,
        rules_version: { steel_design: "SANS 10162-1:2011", wind: "SANS 10160-3:2019" },
      },
    };
    render(<ResultsStep result={withRules} onRestart={vi.fn()} />);
    expect(screen.getByText("Provenance & standards")).toBeTruthy();
    expect(screen.getByText("SANS 10162-1:2011")).toBeTruthy();
    expect(screen.getByText("SANS 10160-3:2019")).toBeTruthy();
  });

  // FR-25/31 — editable cost per tonne
  it("recomputes the indicative cost when cost-per-tonne is edited", async () => {
    render(<ResultsStep result={RESP} onRestart={vi.fn()} />);
    const input = screen.getByLabelText("Cost per tonne (ZAR)");
    await userEvent.clear(input);
    await userEvent.type(input, "30000");
    // 1.234 t × R30,000/t = R37,020.
    expect(screen.getByText("R 37,020")).toBeTruthy();
  });

  // FR-32 — on-screen BMD/SFD
  it("renders the BMD/SFD diagrams when the result carries diagram data", () => {
    const withDiagram: DesignResponse = {
      ...RESP,
      result: {
        ...RESP.result,
        diagram: {
          combination: "ULS-1 (1.2G + 1.6Q)",
          nodes: {
            BL: [0, 0],
            EL: [0, 6],
            AP: [10, 7.76],
            ER: [20, 6],
            BR: [20, 0],
          },
          members: [
            {
              name: "column_left",
              label: "Col L",
              member: "column",
              start: [0, 0],
              end: [0, 6],
              length_m: 6,
              stations: [
                { pos_m: 0, x_m: 0, y_m: 0, axial_kn: -50, shear_kn: 10, moment_knm: 0 },
                { pos_m: 6, x_m: 0, y_m: 6, axial_kn: -50, shear_kn: 10, moment_knm: 60 },
              ],
            },
            {
              name: "rafter_left",
              label: "Rafter L",
              member: "rafter",
              start: [0, 6],
              end: [10, 7.76],
              length_m: 10.15,
              stations: [
                { pos_m: 0, x_m: 0, y_m: 6, axial_kn: -30, shear_kn: 8, moment_knm: 60 },
                { pos_m: 10.15, x_m: 10, y_m: 7.76, axial_kn: -30, shear_kn: -8, moment_knm: -40 },
              ],
            },
            {
              name: "rafter_right",
              label: "Rafter R",
              member: "rafter",
              start: [10, 7.76],
              end: [20, 6],
              length_m: 10.15,
              stations: [
                { pos_m: 0, x_m: 10, y_m: 7.76, axial_kn: -30, shear_kn: 8, moment_knm: -40 },
                { pos_m: 10.15, x_m: 20, y_m: 6, axial_kn: -30, shear_kn: -8, moment_knm: 60 },
              ],
            },
            {
              name: "column_right",
              label: "Col R",
              member: "column",
              start: [20, 6],
              end: [20, 0],
              length_m: 6,
              stations: [
                { pos_m: 0, x_m: 20, y_m: 6, axial_kn: -50, shear_kn: -10, moment_knm: 60 },
                { pos_m: 6, x_m: 20, y_m: 0, axial_kn: -50, shear_kn: -10, moment_knm: 0 },
              ],
            },
          ],
          max_abs_moment_knm: 60,
          max_abs_shear_kn: 10,
        },
      },
    };
    render(<ResultsStep result={withDiagram} onRestart={vi.fn()} />);
    expect(screen.getByText("Bending moment & shear force")).toBeTruthy();
    expect(screen.getByRole("img", { name: /bending moment: peak/i })).toBeTruthy();
    expect(screen.getByRole("img", { name: /shear force: peak/i })).toBeTruthy();
    expect(screen.getByText(/ULS-1/)).toBeTruthy();
  });
});
