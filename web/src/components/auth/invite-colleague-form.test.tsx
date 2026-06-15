import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InviteColleagueForm } from "./invite-colleague-form";

describe("InviteColleagueForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("validates the email before invoking the action", async () => {
    const invite = vi.fn();
    render(<InviteColleagueForm invite={invite} />);
    await userEvent.click(screen.getByRole("button", { name: /send invite/i }));
    expect(await screen.findByText("Email is required")).toBeTruthy();
    expect(invite).not.toHaveBeenCalled();
  });

  it("calls the action and shows a success message", async () => {
    const invite = vi.fn().mockResolvedValue({});
    render(<InviteColleagueForm invite={invite} />);
    await userEvent.type(screen.getByLabelText(/colleague.s email/i), "new@firm.co.za");
    await userEvent.click(screen.getByRole("button", { name: /send invite/i }));
    await waitFor(() => expect(invite).toHaveBeenCalledWith({ email: "new@firm.co.za" }));
    expect(await screen.findByText(/invitation sent to new@firm.co.za/i)).toBeTruthy();
  });

  it("surfaces an action error (e.g. not the owner)", async () => {
    const invite = vi.fn().mockResolvedValue({ error: "Only the firm owner can invite colleagues." });
    render(<InviteColleagueForm invite={invite} />);
    await userEvent.type(screen.getByLabelText(/colleague.s email/i), "new@firm.co.za");
    await userEvent.click(screen.getByRole("button", { name: /send invite/i }));
    expect(await screen.findByText("Only the firm owner can invite colleagues.")).toBeTruthy();
  });
});
