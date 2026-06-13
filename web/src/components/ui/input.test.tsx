import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Input } from "./input";

describe("Input", () => {
  it("accepts typed input", async () => {
    render(<Input aria-label="span" />);
    const el = screen.getByLabelText("span") as HTMLInputElement;
    await userEvent.type(el, "15");
    expect(el.value).toBe("15");
  });

  it("forwards the placeholder and type", () => {
    render(<Input type="number" placeholder="Span (m)" aria-label="span" />);
    const el = screen.getByLabelText("span") as HTMLInputElement;
    expect(el.getAttribute("placeholder")).toBe("Span (m)");
    expect(el.getAttribute("type")).toBe("number");
  });
});
