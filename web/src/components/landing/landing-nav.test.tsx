import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { LandingNav } from "./landing-nav";

describe("LandingNav", () => {
  it("exposes the sign-in and get-started auth links", () => {
    render(<LandingNav />);
    expect(screen.getByRole("link", { name: /sign in/i }).getAttribute("href")).toBe("/login");
    expect(screen.getByRole("link", { name: /get started/i }).getAttribute("href")).toBe("/signup");
  });

  it("toggles a mobile navigation menu via the hamburger", async () => {
    render(<LandingNav />);
    // Closed by default — no mobile menu in the DOM.
    expect(screen.queryByRole("navigation", { name: /mobile/i })).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: /open menu/i }));
    const mobile = screen.getByRole("navigation", { name: /mobile/i });
    expect(within(mobile).getByRole("link", { name: /pricing/i }).getAttribute("href")).toBe(
      "/pricing",
    );
    expect(within(mobile).getByRole("link", { name: /sign in/i })).toBeTruthy();

    await userEvent.click(screen.getByRole("button", { name: /close menu/i }));
    expect(screen.queryByRole("navigation", { name: /mobile/i })).toBeNull();
  });
});
