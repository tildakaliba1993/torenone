import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CheckResult, FrameSpec, SectionChoice } from "@/lib/api/service";

import { DesignedFrame } from "./designed-frame";

const SPEC = {
  geometry: {
    span_m: 15, eaves_height_m: 5, roof_pitch_deg: 8, bay_spacing_m: 6,
    number_of_bays: 5, roof_type: "duopitch",
  },
} as unknown as FrameSpec;

const SECTIONS: SectionChoice[] = [
  { member: "column", designation: "203x133x30" },
  { member: "rafter", designation: "305x165x46" },
];

describe("DesignedFrame", () => {
  it("shows each member's governing utilisation and section", () => {
    const checks: CheckResult[] = [
      { name: "column: axial Cr", clause: "13.3", utilisation: 0.14, passed: true },
      { name: "column: moment Mr (LTB)", clause: "13.6", utilisation: 0.98, passed: true },
      { name: "rafter: beam-column interaction", clause: "13.8", utilisation: 0.89, passed: true },
      // Advisory wind check must NOT drive the member utilisation.
      { name: "column: moment Mr (LTB) [ULS-2 wind]", clause: "13.6", utilisation: 1.42, passed: false, informational: true },
    ];
    render(<DesignedFrame spec={SPEC} sections={SECTIONS} checks={checks} />);

    // Governing (max gating) utilisation per member — advisory 142% ignored.
    expect(screen.getByText("98%")).toBeTruthy();
    expect(screen.getByText("89%")).toBeTruthy();
    expect(screen.getAllByText("203x133x30").length).toBeGreaterThan(0);
    expect(screen.getAllByText("305x165x46").length).toBeGreaterThan(0);
  });

  it("renders nothing for invalid geometry", () => {
    const bad = { geometry: { span_m: 0, eaves_height_m: 0, roof_pitch_deg: 0 } } as unknown as FrameSpec;
    const { container } = render(<DesignedFrame spec={bad} sections={[]} checks={[]} />);
    expect(container.querySelector("svg")).toBeNull();
  });
});
