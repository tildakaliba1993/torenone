import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  CardSkeleton,
  ListSkeleton,
  PageHeaderSkeleton,
  PageShell,
} from "./page-skeleton";

describe("page skeletons", () => {
  it("PageShell fades content in", () => {
    const { container } = render(
      <PageShell>
        <div>content</div>
      </PageShell>,
    );
    const main = container.querySelector("main");
    expect(main?.className).toContain("animate-fade-in");
    expect(screen.getByText("content")).toBeTruthy();
  });

  it("PageHeaderSkeleton renders optional eyebrow, subtitle and action", () => {
    const { rerender } = render(<PageHeaderSkeleton eyebrow subtitle action />);
    expect(screen.getAllByTestId("skeleton").length).toBe(4); // eyebrow + title + subtitle + action

    rerender(<PageHeaderSkeleton eyebrow={false} subtitle={false} action={false} />);
    expect(screen.getAllByTestId("skeleton").length).toBe(1); // title only
  });

  it("CardSkeleton renders the requested number of body rows (+ a title bar)", () => {
    render(<CardSkeleton rows={3} />);
    expect(screen.getAllByTestId("skeleton").length).toBe(4);
  });

  it("ListSkeleton renders two placeholders per row", () => {
    render(<ListSkeleton rows={4} />);
    // 2 text lines + 1 badge per row
    expect(screen.getAllByTestId("skeleton").length).toBe(12);
  });
});
