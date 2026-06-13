import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Skeleton } from "./skeleton";

describe("Skeleton", () => {
  it("renders a pulsing placeholder", () => {
    render(<Skeleton />);
    expect(screen.getByTestId("skeleton").className).toContain("animate-pulse");
  });

  it("merges a custom className", () => {
    render(<Skeleton className="h-7 w-32" />);
    const el = screen.getByTestId("skeleton");
    expect(el.className).toContain("h-7");
    expect(el.className).toContain("w-32");
  });
});
