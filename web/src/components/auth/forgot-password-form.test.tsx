import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const resetPasswordForEmail = vi.fn();
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { resetPasswordForEmail } }),
}));

import { ForgotPasswordForm } from "./forgot-password-form";

describe("ForgotPasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("validates the email before calling Supabase", async () => {
    render(<ForgotPasswordForm />);
    await userEvent.click(screen.getByRole("button", { name: /send reset link/i }));
    expect(await screen.findByText("Email is required")).toBeTruthy();
    expect(resetPasswordForEmail).not.toHaveBeenCalled();
  });

  it("sends the reset email and shows the confirmation state", async () => {
    resetPasswordForEmail.mockResolvedValue({ error: null });
    render(<ForgotPasswordForm />);
    await userEvent.type(screen.getByLabelText("Email"), "owner@acme.co.za");
    await userEvent.click(screen.getByRole("button", { name: /send reset link/i }));
    await waitFor(() => expect(resetPasswordForEmail).toHaveBeenCalledTimes(1));
    expect(resetPasswordForEmail.mock.calls[0][0]).toBe("owner@acme.co.za");
    expect(await screen.findByText(/password-reset link is on its way/i)).toBeTruthy();
  });

  it("surfaces a Supabase error", async () => {
    resetPasswordForEmail.mockResolvedValue({ error: { message: "rate limit exceeded" } });
    render(<ForgotPasswordForm />);
    await userEvent.type(screen.getByLabelText("Email"), "owner@acme.co.za");
    await userEvent.click(screen.getByRole("button", { name: /send reset link/i }));
    expect(await screen.findByText("rate limit exceeded")).toBeTruthy();
  });
});
