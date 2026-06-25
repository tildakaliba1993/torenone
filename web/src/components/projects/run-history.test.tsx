import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getEntitledReportUrl, openCalcPackageCheckout, push } = vi.hoisted(() => ({
  getEntitledReportUrl: vi.fn(),
  openCalcPackageCheckout: vi.fn(),
  push: vi.fn(),
}));
vi.mock("@/lib/billing/actions", () => ({
  getEntitledReportUrl: (runId: string) => getEntitledReportUrl(runId),
}));
vi.mock("@/lib/paddle/checkout", () => ({
  openCalcPackageCheckout: (opts: unknown) => openCalcPackageCheckout(opts),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
// The row actions call server actions — stub the module so the test stays client-only.
vi.mock("@/app/(app)/projects/[id]/actions", () => ({
  renameRun: vi.fn(),
  deleteRun: vi.fn(),
}));

import { type RunRow, RunHistory } from "./run-history";

const RUNS: RunRow[] = [
  {
    id: "run-1",
    label: "15 m × 5 m · 8°",
    rawLabel: null,
    mode: "design",
    passed: true,
    governing_utilisation: 0.82,
    created_at: "2026-06-13T10:00:00Z",
    storage_path: "firm-1/run-1.pdf",
  },
  {
    id: "run-2",
    label: "Woodstock — option B",
    rawLabel: "Woodstock — option B",
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
    render(<RunHistory runs={[]} projectId="p1" />);
    expect(screen.getByText(/no designs match/i)).toBeTruthy();
  });

  it("renders a row per run with mode, result and governing utilisation", () => {
    render(<RunHistory runs={RUNS} projectId="p1" />);
    expect(screen.getByText("15 m × 5 m · 8°")).toBeTruthy(); // derived label
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

  it("downloads an entitled run's PDF via a signed URL", async () => {
    getEntitledReportUrl.mockResolvedValue({ url: "https://signed.example/run-1.pdf" });
    render(<RunHistory runs={RUNS} projectId="p1" />);
    const firstRow = screen.getByText("design").closest("tr")!;
    await userEvent.click(within(firstRow).getByRole("button", { name: /pdf/i }));
    await waitFor(() => expect(getEntitledReportUrl).toHaveBeenCalledWith("run-1"));
    expect(window.open).toHaveBeenCalledWith(
      "https://signed.example/run-1.pdf",
      "_blank",
      "noopener,noreferrer",
    );
    expect(openCalcPackageCheckout).not.toHaveBeenCalled();
  });

  it("opens pay-as-you-go checkout when the firm is not entitled", async () => {
    getEntitledReportUrl.mockResolvedValue({
      needsPayment: true,
      email: "eng@firm.test",
      firmId: "firm-1",
    });
    render(<RunHistory runs={RUNS} projectId="p1" />);
    const firstRow = screen.getByText("design").closest("tr")!;
    await userEvent.click(within(firstRow).getByRole("button", { name: /pdf/i }));
    await waitFor(() =>
      expect(openCalcPackageCheckout).toHaveBeenCalledWith({
        email: "eng@firm.test",
        firmId: "firm-1",
        runId: "run-1",
      }),
    );
    expect(window.open).not.toHaveBeenCalled();
  });

  it("shows a dash when a run has no stored report", () => {
    render(<RunHistory runs={RUNS} projectId="p1" />);
    const secondRow = screen.getByText("check").closest("tr")!;
    // no PDF button in the report cell — a dash instead
    expect(within(secondRow).queryByRole("button", { name: /pdf/i })).toBeNull();
  });

  it("opens the design page when a row is clicked", async () => {
    render(<RunHistory runs={RUNS} projectId="p1" />);
    const firstRow = screen.getByText("design").closest("tr")!;
    await userEvent.click(firstRow);
    expect(push).toHaveBeenCalledWith("/projects/p1/runs/run-1");
  });

  it("does not open the design page when the PDF download is clicked", async () => {
    getEntitledReportUrl.mockResolvedValue({ url: "https://signed.example/run-1.pdf" });
    render(<RunHistory runs={RUNS} projectId="p1" />);
    const firstRow = screen.getByText("design").closest("tr")!;
    await userEvent.click(within(firstRow).getByRole("button", { name: /pdf/i }));
    expect(push).not.toHaveBeenCalled();
  });

  it("typing a space into the Rename dialog does not navigate or close the dialog", async () => {
    render(<RunHistory runs={RUNS} projectId="p1" />);
    const secondRow = screen.getByText("check").closest("tr")!;
    await userEvent.click(within(secondRow).getByRole("button", { name: /rename/i }));

    const input = await screen.findByLabelText(/design label/i);
    await userEvent.clear(input);
    await userEvent.type(input, "Woodstock Quarter");

    // The space must land in the field — not trigger the row's Enter/Space navigation.
    expect((input as HTMLInputElement).value).toBe("Woodstock Quarter");
    expect(push).not.toHaveBeenCalled();
    // Dialog is still open.
    expect(screen.getByText("Rename design")).toBeTruthy();
  });
});
