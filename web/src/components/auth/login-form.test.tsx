import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const refresh = vi.fn();
const searchParamsGet = vi.fn<(key: string) => string | null>(() => null);

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
  useSearchParams: () => ({ get: searchParamsGet }),
}));

const signInWithPassword = vi.fn();
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { signInWithPassword } }),
}));

import { LoginForm } from "./login-form";

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchParamsGet.mockReturnValue(null);
  });

  it("validates that email and password are required", async () => {
    render(<LoginForm />);
    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    expect(await screen.findByText("Email is required")).toBeTruthy();
    expect(screen.getByText("Password is required")).toBeTruthy();
    expect(signInWithPassword).not.toHaveBeenCalled();
  });

  it("rejects a malformed email", async () => {
    render(<LoginForm />);
    await userEvent.type(screen.getByLabelText("Email"), "not-an-email");
    await userEvent.type(screen.getByLabelText("Password"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    expect(await screen.findByText("Enter a valid email address")).toBeTruthy();
    expect(signInWithPassword).not.toHaveBeenCalled();
  });

  it("signs in and navigates to /dashboard on success", async () => {
    signInWithPassword.mockResolvedValue({ error: null });
    render(<LoginForm />);
    await userEvent.type(screen.getByLabelText("Email"), "eng@firm.co.za");
    await userEvent.type(screen.getByLabelText("Password"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    await waitFor(() =>
      expect(signInWithPassword).toHaveBeenCalledWith({
        email: "eng@firm.co.za",
        password: "secret123",
      }),
    );
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("honours the ?next redirect target", async () => {
    signInWithPassword.mockResolvedValue({ error: null });
    searchParamsGet.mockReturnValue("/projects");
    render(<LoginForm />);
    await userEvent.type(screen.getByLabelText("Email"), "eng@firm.co.za");
    await userEvent.type(screen.getByLabelText("Password"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/projects"));
  });

  it("surfaces the auth error and does not navigate", async () => {
    signInWithPassword.mockResolvedValue({ error: { message: "Invalid login credentials" } });
    render(<LoginForm />);
    await userEvent.type(screen.getByLabelText("Email"), "eng@firm.co.za");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    expect(await screen.findByText("Invalid login credentials")).toBeTruthy();
    expect(push).not.toHaveBeenCalled();
  });
});
