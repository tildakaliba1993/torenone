import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/app/(app)/projects/[id]/actions", () => ({ renameRun: vi.fn(), deleteRun: vi.fn() }));
vi.mock("@/lib/billing/actions", () => ({ getEntitledReportUrl: vi.fn() }));
vi.mock("@/lib/payments/actions", () => ({ createPackageCheckout: vi.fn() }));
vi.mock("@/lib/payments/client", () => ({ beginCheckout: vi.fn() }));

import { type RunRow } from "./run-history";

import { DesignsManager } from "./designs-manager";

const RUNS: RunRow[] = [
  {
    id: "r1",
    label: "Granger Bay — option A",
    rawLabel: "Granger Bay — option A",
    mode: "design",
    passed: true,
    governing_utilisation: 0.82,
    created_at: "2026-06-13T10:00:00Z",
    storage_path: "firm-1/r1.pdf",
  },
  {
    id: "r2",
    label: "Woodstock shed",
    rawLabel: "Woodstock shed",
    mode: "check",
    passed: false,
    governing_utilisation: 1.14,
    created_at: "2026-06-12T09:00:00Z",
    storage_path: null,
  },
];

describe("DesignsManager", () => {
  it("searches the displayed label in real time", async () => {
    render(<DesignsManager runs={RUNS} projectId="p1" />);
    expect(screen.getByText("Granger Bay — option A")).toBeTruthy();
    expect(screen.getByText("Woodstock shed")).toBeTruthy();

    await userEvent.type(screen.getByRole("searchbox"), "woodstock");
    expect(screen.queryByText("Granger Bay — option A")).toBeNull();
    expect(screen.getByText("Woodstock shed")).toBeTruthy();
  });

  it("filters by result", async () => {
    render(<DesignsManager runs={RUNS} projectId="p1" />);
    // Select the "Result" filter → Fail
    const resultSelect = screen.getByRole("combobox", { name: /result/i });
    await userEvent.selectOptions(resultSelect, "fail");
    expect(screen.getByText("Woodstock shed")).toBeTruthy();
    expect(screen.queryByText("Granger Bay — option A")).toBeNull();
  });
});
