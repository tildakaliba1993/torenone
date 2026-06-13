import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

const createProject = vi.fn();
vi.mock("@/app/(app)/projects/actions", () => ({
  createProject: (input: { name: string }) => createProject(input),
}));

import { CreateProjectDialog } from "./create-project-dialog";

describe("CreateProjectDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("opens the dialog and requires a project name", async () => {
    render(<CreateProjectDialog />);
    await userEvent.click(screen.getByRole("button", { name: "New project" }));
    expect(await screen.findByRole("dialog")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: /create project/i }));
    expect(await screen.findByText("Project name is required")).toBeTruthy();
    expect(createProject).not.toHaveBeenCalled();
  });

  it("creates the project and refreshes on success", async () => {
    createProject.mockResolvedValue({});
    render(<CreateProjectDialog />);
    await userEvent.click(screen.getByRole("button", { name: "New project" }));
    await userEvent.type(screen.getByLabelText("Project name"), "Woodstock warehouse");
    await userEvent.click(screen.getByRole("button", { name: /create project/i }));
    await waitFor(() =>
      expect(createProject).toHaveBeenCalledWith({ name: "Woodstock warehouse" }),
    );
    expect(refresh).toHaveBeenCalled();
  });

  it("surfaces a server error and does not refresh", async () => {
    createProject.mockResolvedValue({ error: "A project with that name already exists" });
    render(<CreateProjectDialog />);
    await userEvent.click(screen.getByRole("button", { name: "New project" }));
    await userEvent.type(screen.getByLabelText("Project name"), "Duplicate");
    await userEvent.click(screen.getByRole("button", { name: /create project/i }));
    expect(await screen.findByText("A project with that name already exists")).toBeTruthy();
    expect(refresh).not.toHaveBeenCalled();
  });
});
