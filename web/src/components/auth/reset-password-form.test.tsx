import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

const updateUser = vi.fn();
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { updateUser } }),
}));

import { ResetPasswordForm } from "./reset-password-form";

describe("ResetPasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("enforces the 10-char policy and rejects short passwords", async () => {
    render(<ResetPasswordForm />);
    await userEvent.type(screen.getByLabelText("New password"), "short");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "short");
    await userEvent.click(screen.getByRole("button", { name: /update password/i }));
    expect(await screen.findByText("Password must be at least 10 characters")).toBeTruthy();
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("requires the two passwords to match", async () => {
    render(<ResetPasswordForm />);
    await userEvent.type(screen.getByLabelText("New password"), "supersecret1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "different123");
    await userEvent.click(screen.getByRole("button", { name: /update password/i }));
    expect(await screen.findByText("Passwords do not match")).toBeTruthy();
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("updates the password and shows the done state", async () => {
    updateUser.mockResolvedValue({ error: null });
    render(<ResetPasswordForm />);
    await userEvent.type(screen.getByLabelText("New password"), "supersecret1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "supersecret1");
    await userEvent.click(screen.getByRole("button", { name: /update password/i }));
    await waitFor(() => expect(updateUser).toHaveBeenCalledWith({ password: "supersecret1" }));
    expect(await screen.findByText(/password has been updated/i)).toBeTruthy();
  });

  it("surfaces an error (e.g. no active recovery session)", async () => {
    updateUser.mockResolvedValue({ error: { message: "Auth session missing" } });
    render(<ResetPasswordForm />);
    await userEvent.type(screen.getByLabelText("New password"), "supersecret1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "supersecret1");
    await userEvent.click(screen.getByRole("button", { name: /update password/i }));
    expect(await screen.findByText("Auth session missing")).toBeTruthy();
  });
});
