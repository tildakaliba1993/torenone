import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Skeleton } from "./skeleton";

describe("Skeleton", () => {
  it("renders a shimmering placeholder", () => {
    render(<Skeleton />);
    const el = screen.getByTestId("skeleton");
    expect(el.className).toContain("animate-shimmer");
    expect(el.className).toContain("overflow-hidden");
  });

  it("falls back to a pulse when motion is reduced", () => {
    render(<Skeleton />);
    expect(screen.getByTestId("skeleton").className).toContain("motion-reduce:animate-pulse");
  });

  it("merges a custom className", () => {
    render(<Skeleton className="h-7 w-32" />);
    const el = screen.getByTestId("skeleton");
    expect(el.className).toContain("h-7");
    expect(el.className).toContain("w-32");
  });
});
