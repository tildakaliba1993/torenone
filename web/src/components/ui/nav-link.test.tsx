import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NavLink } from "./nav-link";

describe("NavLink", () => {
  it("renders an anchor to the destination with its label", () => {
    render(<NavLink href="/projects">Projects</NavLink>);
    const link = screen.getByRole("link", { name: /projects/i });
    expect(link.getAttribute("href")).toBe("/projects");
  });

  it("marks the active link with foreground text", () => {
    render(<NavLink href="/projects" active>Projects</NavLink>);
    expect(screen.getByRole("link", { name: /projects/i }).className).toContain("text-foreground");
  });
});
