import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LandingNav } from "./landing-nav";

describe("LandingNav", () => {
  it("exposes the sign-in and get-started auth links", () => {
    render(<LandingNav />);
    expect(screen.getByRole("link", { name: /sign in/i }).getAttribute("href")).toBe("/login");
    expect(screen.getByRole("link", { name: /get started/i }).getAttribute("href")).toBe("/signup");
  });
});
