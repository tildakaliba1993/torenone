import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/app/(app)/projects/actions", () => ({
  renameProject: vi.fn(),
  deleteProject: vi.fn(),
}));

import { type ProjectItem, ProjectsManager } from "./projects-manager";

const PROJECTS: ProjectItem[] = Array.from({ length: 11 }, (_, i) => ({
  id: `p${i}`,
  name: i === 0 ? "Granger Bay warehouse" : `Project ${String(i).padStart(2, "0")}`,
  created_at: `2026-06-${String(10 + i).padStart(2, "0")}T10:00:00Z`,
}));

function rowNames() {
  return screen
    .getAllByRole("row")
    .slice(1) // drop header
    .map((r) => within(r).getAllByRole("cell")[0].textContent);
}

describe("ProjectsManager", () => {
  it("paginates — 8 per page", () => {
    render(<ProjectsManager projects={PROJECTS} />);
    expect(rowNames()).toHaveLength(8);
    expect(screen.getByText(/page 1 of 2/i)).toBeTruthy();
  });

  it("filters in real time as you type (no submit)", async () => {
    render(<ProjectsManager projects={PROJECTS} />);
    await userEvent.type(screen.getByRole("searchbox"), "granger");
    const names = rowNames();
    expect(names).toHaveLength(1);
    expect(names[0]).toMatch(/granger bay/i);
  });

  it("shows a no-match state for a search with no results", async () => {
    render(<ProjectsManager projects={PROJECTS} />);
    await userEvent.type(screen.getByRole("searchbox"), "zzzzz");
    expect(screen.getByText(/no projects match/i)).toBeTruthy();
  });
});
