import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BuildingFrames } from "./building-frames";

describe("BuildingFrames", () => {
  it("captions the frame count and bay spacing", () => {
    render(<BuildingFrames numberOfFrames={5} span={15} eaves={5} pitch={8} baySpacingM={6} />);
    expect(screen.getByText(/5 portal frames @ 6\.00 m/)).toBeTruthy();
  });

  it("caps the drawn frames but reports the true count", () => {
    render(<BuildingFrames numberOfFrames={14} span={20} eaves={6} pitch={5} baySpacingM={5} />);
    expect(screen.getByText(/14 portal frames/)).toBeTruthy();
    expect(screen.getByText(/showing 10/)).toBeTruthy();
    // Only 10 frame outlines are drawn (polylines), regardless of the true count.
    const outlines = document.querySelectorAll("polyline");
    expect(outlines.length).toBe(10);
  });

  it("renders nothing for invalid geometry", () => {
    const { container } = render(
      <BuildingFrames numberOfFrames={0} span={0} eaves={0} pitch={0} />,
    );
    expect(container.querySelector("svg")).toBeNull();
  });
});
