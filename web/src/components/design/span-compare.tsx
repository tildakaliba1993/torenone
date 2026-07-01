"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  type FrameSpec,
  type SpanComparison,
  type SpanOption,
  ServiceError,
  compareSpans,
} from "@/lib/api/service";
import { cn } from "@/lib/utils";

function tonnes(kg: number | null): string {
  return kg == null ? "—" : `${(kg / 1000).toFixed(2)} t`;
}

function sectionsLabel(o: SpanOption): string {
  const col = o.sections.find((s) => s.member === "column")?.designation;
  const raf = o.sections.find((s) => s.member === "rafter")?.designation;
  return col && raf ? `${col} / ${raf}` : "—";
}

/**
 * Topology (Path B): clear-span vs multi-span. On demand, the engine re-splits the building's WIDTH
 * into equal spans, designs each, and ranks by total steel — so the engineer can see whether internal
 * columns save steel. Any >1-span option is PROVISIONAL. Every number is kernel-computed.
 */
export function SpanCompare({
  getSpec,
  currentSpans,
  onApply,
  applyLabel = "Use",
}: {
  getSpec: () => FrameSpec | null;
  currentSpans: number;
  /** Apply the chosen split. May be async (e.g. re-run the design on the results page). */
  onApply: (numberOfSpans: number, spanM: number) => void | Promise<void>;
  /** Verb for the apply button (e.g. "Use" on Review, "Design this" on results). */
  applyLabel?: string;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SpanComparison | null>(null);
  const [applying, setApplying] = useState<number | null>(null);

  async function run() {
    const spec = getSpec();
    if (!spec) {
      setError("Enter valid geometry, loads and wind above first, then compare.");
      setData(null);
      return;
    }
    setPending(true);
    setError(null);
    try {
      setData(await compareSpans(spec));
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Couldn’t compare span splits.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="border-border bg-surface-raised flex flex-col gap-3 rounded-lg border p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <p className="text-foreground text-sm font-medium">Clear-span vs multi-span</p>
          <p className="text-muted text-xs">
            Split the building width with internal (valley) columns and see if it saves steel. Any
            multi-span option is PROVISIONAL until your engineer validates it.
          </p>
        </div>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => void run()}
          loading={pending}
          disabled={pending}
        >
          {pending ? "Comparing…" : data ? "Re-compare" : "Compare"}
        </Button>
      </div>

      {error ? (
        <p role="alert" className="text-danger text-sm font-medium">
          {error}
        </p>
      ) : null}

      {data ? (
        <div className="flex flex-col gap-2">
          <div className="border-border overflow-x-auto rounded-md border">
            <table className="w-full min-w-[34rem] text-left text-sm">
              <thead className="bg-surface text-subtle text-xs">
                <tr>
                  <th className="px-3 py-2 font-medium">Spans × width</th>
                  <th className="px-3 py-2 font-medium">Column / rafter</th>
                  <th className="px-3 py-2 font-medium">Total steel</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {data.options.map((o) => {
                  const isLightest = o.number_of_spans === data.lightest_passing_spans;
                  const isCurrent = o.number_of_spans === currentSpans;
                  return (
                    <tr key={o.number_of_spans} className={cn("border-border border-t", isLightest && "bg-success/5")}>
                      <td className="text-foreground px-3 py-2">
                        {o.number_of_spans} × {o.span_m.toFixed(1)} m
                        {o.is_baseline ? <span className="text-subtle"> · current</span> : null}
                      </td>
                      <td className="text-muted px-3 py-2">{sectionsLabel(o)}</td>
                      <td className="text-foreground px-3 py-2 tabular-nums">
                        {tonnes(o.total_primary_mass_kg)}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={cn(
                            "inline-block rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
                            !o.feasible
                              ? "text-subtle border-border"
                              : !o.passed
                                ? "text-danger border-danger/40 bg-danger/10"
                                : o.provisional
                                  ? "text-warning border-warning/40 bg-warning/10"
                                  : isLightest
                                    ? "text-success border-success/40 bg-success/10"
                                    : "text-muted border-border",
                          )}
                        >
                          {!o.feasible
                            ? "No section"
                            : !o.passed
                              ? "Fails"
                              : o.provisional
                                ? "Provisional"
                                : isLightest
                                  ? "Lightest ✓"
                                  : "Passes"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          loading={applying === o.number_of_spans}
                          onClick={async () => {
                            setApplying(o.number_of_spans);
                            try {
                              await onApply(o.number_of_spans, o.span_m);
                            } finally {
                              setApplying(null);
                            }
                          }}
                          disabled={!o.feasible || isCurrent || applying !== null}
                        >
                          {applying === o.number_of_spans
                            ? "Designing…"
                            : isCurrent
                              ? "In use"
                              : applyLabel}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <ul className="text-subtle list-disc pl-4 text-xs">
            {data.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
