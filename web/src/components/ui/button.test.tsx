import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button } from "./button";

describe("Button", () => {
  it("renders its label as a button", () => {
    render(<Button>Run design</Button>);
    expect(screen.getByRole("button", { name: "Run design" })).toBeTruthy();
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("applies the requested variant's themed classes", () => {
    render(<Button variant="destructive">Delete</Button>);
    expect(screen.getByRole("button").className).toContain("bg-danger");
  });

  it("renders as the child element when asChild (e.g. a link)", () => {
    render(
      <Button asChild>
        <a href="https://example.com/docs">Projects</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "Projects" });
    expect(link.tagName).toBe("A");
    expect(link.className).toContain("bg-primary");
  });

  it("is disabled when the disabled prop is set", () => {
    render(<Button disabled>X</Button>);
    expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows a spinner and disables itself while loading", () => {
    render(<Button loading>Run design</Button>);
    const btn = screen.getByRole("button", { name: /run design/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(btn.getAttribute("aria-busy")).toBe("true");
    expect(btn.querySelector("svg")).toBeTruthy(); // spinner
  });

  it("passes a Slotted link through unchanged when asChild + loading", () => {
    // asChild must keep exactly one child (no injected spinner) — Radix Slot requires it.
    render(
      <Button asChild loading>
        <a href="https://example.com">Go</a>
      </Button>,
    );
    expect(screen.getByRole("link", { name: "Go" }).tagName).toBe("A");
  });
});
