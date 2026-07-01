"use client";

import type { CheckResult } from "@/lib/api/service";
import { cn } from "@/lib/utils";

/**
 * The full clause-by-clause breakdown for one member (column or rafter) — opened by clicking that
 * member in the 3D model or the 2D frame. Every row is a kernel check: SANS clause, utilisation bar,
 * pass/advisory. Ties the picture to the audit — 🟢, pure presentation of kernel output.
 */

type MemberKind = "column" | "rafter";

function bandColor(util: number): string {
  if (util > 1.0) return "var(--danger)";
  if (util >= 0.85) return "var(--warning)";
  return "var(--success)";
}

export function MemberInspector({
  kind,
  checks,
  onClose,
}: {
  kind: MemberKind;
  checks: CheckResult[];
  onClose: () => void;
}) {
  const own = checks
    .filter((c) => c.name.toLowerCase().startsWith(`${kind}:`))
    .sort((a, b) => b.utilisation - a.utilisation);

  return (
    <div className="border-accent/40 bg-surface flex flex-col gap-3 rounded-lg border p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-foreground text-sm font-medium capitalize">{kind} — all checks</p>
        <button
          type="button"
          onClick={onClose}
          className="text-subtle hover:text-foreground text-xs underline-offset-2 hover:underline"
        >
          Close
        </button>
      </div>

      {own.length === 0 ? (
        <p className="text-subtle text-sm">No checks recorded for this member.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {own.map((c, i) => {
            const pct = Math.round(c.utilisation * 100);
            const barPct = Math.min(c.utilisation, 1) * 100;
            return (
              <li key={i} className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="text-foreground">
                    {c.name.replace(/^[^:]+:\s*/, "")}
                    <span className="text-subtle"> · {c.clause}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="text-muted tabular-nums">{pct}%</span>
                    <span
                      className={cn(
                        "rounded-full border px-1.5 py-0.5 text-xs font-medium whitespace-nowrap",
                        c.informational
                          ? "text-warning border-warning/40 bg-warning/10"
                          : c.passed
                            ? "text-success border-success/40 bg-success/10"
                            : "text-danger border-danger/40 bg-danger/10",
                      )}
                    >
                      {c.informational ? "advisory" : c.passed ? "pass" : "fail"}
                    </span>
                  </span>
                </div>
                <div className="bg-surface-raised h-1.5 w-full overflow-hidden rounded-full">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${barPct}%`, backgroundColor: bandColor(c.utilisation) }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
