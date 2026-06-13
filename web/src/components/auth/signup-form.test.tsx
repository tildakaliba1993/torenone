import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

const signUp = vi.fn();
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { signUp } }),
}));

import { SignupForm } from "./signup-form";

async function fillValid() {
  await userEvent.type(screen.getByLabelText("Firm name"), "Acme Structural");
  await userEvent.type(screen.getByLabelText("Email"), "owner@acme.co.za");
  await userEvent.type(screen.getByLabelText("Password"), "supersecret");
}

describe("SignupForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("requires firm name, email and an 8+ char password", async () => {
    render(<SignupForm />);
    await userEvent.type(screen.getByLabelText("Password"), "short");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByText("Firm name is required")).toBeTruthy();
    expect(screen.getByText("Email is required")).toBeTruthy();
    expect(screen.getByText("Password must be at least 8 characters")).toBeTruthy();
    expect(signUp).not.toHaveBeenCalled();
  });

  it("passes firm_name as signup metadata", async () => {
    signUp.mockResolvedValue({ data: { session: { access_token: "t" } }, error: null });
    render(<SignupForm />);
    await fillValid();
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => expect(signUp).toHaveBeenCalledTimes(1));
    const arg = signUp.mock.calls[0][0];
    expect(arg.email).toBe("owner@acme.co.za");
    expect(arg.options.data).toEqual({ firm_name: "Acme Structural" });
    expect(push).toHaveBeenCalledWith("/projects");
  });

  it("shows a confirm-your-email message when no session is returned", async () => {
    signUp.mockResolvedValue({ data: { session: null }, error: null });
    render(<SignupForm />);
    await fillValid();
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByText(/check your email/i)).toBeTruthy();
    expect(push).not.toHaveBeenCalled();
  });

  it("surfaces a signup error", async () => {
    signUp.mockResolvedValue({ data: { session: null }, error: { message: "User already registered" } });
    render(<SignupForm />);
    await fillValid();
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByText("User already registered")).toBeTruthy();
  });
});
