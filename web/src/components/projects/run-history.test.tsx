import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getReportSignedUrl, ServiceError } = vi.hoisted(() => {
  class ServiceError extends Error {}
  return { getReportSignedUrl: vi.fn(), ServiceError };
});
vi.mock("@/lib/api/service", () => ({
  getReportSignedUrl: (path: string) => getReportSignedUrl(path),
  ServiceError,
}));

import { type RunRow, RunHistory } from "./run-history";

const RUNS: RunRow[] = [
  {
    id: "run-1",
    mode: "design",
    passed: true,
    governing_utilisation: 0.82,
    created_at: "2026-06-13T10:00:00Z",
    storage_path: "firm-1/run-1.pdf",
  },
  {
    id: "run-2",
    mode: "check",
    passed: false,
    governing_utilisation: 1.14,
    created_at: "2026-06-12T09:00:00Z",
    storage_path: null,
  },
];

describe("RunHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "open").mockReturnValue(null);
  });

  it("shows an empty state when there are no runs", () => {
    render(<RunHistory runs={[]} />);
    expect(screen.getByText(/no design runs yet/i)).toBeTruthy();
  });

  it("renders a row per run with mode, result and governing utilisation", () => {
    render(<RunHistory runs={RUNS} />);
    expect(screen.getByText("design")).toBeTruthy();
    expect(screen.getByText("check")).toBeTruthy();
    expect(screen.getByText("0.82")).toBeTruthy();
    expect(screen.getByText("1.14")).toBeTruthy();
    // failing run shows a fail badge
    const passBadges = screen.getAllByText("pass");
    const failBadges = screen.getAllByText("fail");
    expect(passBadges.length).toBe(1);
    expect(failBadges.length).toBe(1);
  });

  it("downloads a run's PDF via a signed URL", async () => {
    getReportSignedUrl.mockResolvedValue("https://signed.example/run-1.pdf");
    render(<RunHistory runs={RUNS} />);
    const firstRow = screen.getByText("design").closest("tr")!;
    await userEvent.click(within(firstRow).getByRole("button", { name: /pdf/i }));
    await waitFor(() => expect(getReportSignedUrl).toHaveBeenCalledWith("firm-1/run-1.pdf"));
    expect(window.open).toHaveBeenCalledWith(
      "https://signed.example/run-1.pdf",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("shows a dash when a run has no stored report", () => {
    render(<RunHistory runs={RUNS} />);
    const secondRow = screen.getByText("check").closest("tr")!;
    // no PDF button in the report cell — a dash instead
    expect(within(secondRow).queryByRole("button", { name: /pdf/i })).toBeNull();
  });
});
