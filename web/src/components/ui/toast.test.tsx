import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Toaster, toast } from "./toast";

describe("Toaster", () => {
  it("mounts without crashing", () => {
    const { container } = render(<Toaster />);
    expect(container).toBeTruthy();
  });

  it("exposes the toast() function", () => {
    expect(typeof toast).toBe("function");
  });
});
