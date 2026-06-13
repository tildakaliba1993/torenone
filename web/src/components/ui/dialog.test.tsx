import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "./dialog";

function Example() {
  return (
    <Dialog>
      <DialogTrigger>Open</DialogTrigger>
      <DialogContent>
        <DialogTitle>Confirm the spec</DialogTitle>
      </DialogContent>
    </Dialog>
  );
}

describe("Dialog", () => {
  it("is closed until the trigger is clicked", async () => {
    render(<Example />);
    expect(screen.queryByText("Confirm the spec")).toBeNull();
    await userEvent.click(screen.getByText("Open"));
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByText("Confirm the spec")).toBeTruthy();
  });

  it("closes via the accessible close button", async () => {
    render(<Example />);
    await userEvent.click(screen.getByText("Open"));
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByText("Confirm the spec")).toBeNull();
  });
});
