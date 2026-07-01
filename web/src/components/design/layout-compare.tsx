"use client";

import { useState } from "react";

import { Building3D } from "@/components/design/building-3d";
import { Button } from "@/components/ui/button";
import {
  type FrameSpec,
  type LayoutComparison,
  type LayoutOption,
  type SectionChoice,
  ServiceError,
  compareLayouts,
} from "@/lib/api/service";
import { cn } from "@/lib/utils";

function tonnes(kg: number | null): string {
  return kg == null ? "—" : `${(kg / 1000).toFixed(2)} t`;
}

function sectionsLabel(sections: SectionChoice[]): string {
  if (sections.length === 0) return "—";
  const rafter = sections.find((s) => s.member === "rafter")?.designation;
  const column = sections.find((s) => s.member === "column")?.designation;
  if (rafter && column) return `${column} / ${rafter}`;
  return sections.map((s) => s.designation).join(" / ");
}

function StatusBadge({ option, isLightest }: { option: LayoutOption; isLightest: boolean }) {
  const [label, tone] = !option.feasible
    ? ["No section fits", "text-subtle border-border"]
    : !option.passed
      ? ["Fails checks", "text-danger border-danger/40 bg-danger/10"]
      : isLightest
        ? ["Lightest ✓", "text-success border-success/40 bg-success/10"]
        : ["Passes", "text-muted border-border"];
  return (
    <span
      className={cn(
        "inline-block rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        tone,
      )}
    >
      {label}
    </span>
  );
}

/**
 * Topology (Path A): "how should this building be framed?" On demand, the deterministic engine
 * re-frames the SAME building with different numbers of portal frames, designs each, and ranks them
 * by total primary steel. The engineer picks a layout — every number comes from the kernel, not AI.
 */
export function LayoutCompare({
  getSpec,
  currentBays,
  onApply,
}: {
  /** Build a FrameSpec from the current form values, or null if geometry/loads aren't valid yet. */
  getSpec: () => FrameSpec | null;
  currentBays: number;
  onApply: (numberOfBays: number, baySpacingM: number) => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<LayoutComparison | null>(null);
  const [usedSpec, setUsedSpec] = useState<FrameSpec | null>(null);

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
      setData(await compareLayouts(spec));
      setUsedSpec(spec);
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Couldn’t compare framing options.");
    } finally {
      setPending(false);
    }
  }

  const [hoverBays, setHoverBays] = useState<number | null>(null);
  // Which layout the building preview shows: the hovered row, else the lightest passing option.
  const previewBays = hoverBays ?? data?.lightest_passing_bays ?? null;
  const preview =
    data && previewBays != null
      ? data.options.find((o) => o.number_of_bays === previewBays)
      : undefined;

  return (
    <div className="border-border bg-surface-raised flex flex-col gap-3 rounded-lg border p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <p className="text-foreground text-sm font-medium">Compare framing options</p>
          <p className="text-muted text-xs">
            See how many portal frames best suit this building. The engine designs each layout and
            ranks them by total steel — you pick. Nothing is committed until you apply one.
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
          {preview && usedSpec ? (
            <div className="border-border bg-surface rounded-md border p-3">
              <p className="text-muted mb-1 text-xs">
                {preview.number_of_bays === data.lightest_passing_bays
                  ? "Lightest option"
                  : "Previewing"}{" "}
                — {preview.number_of_frames} frames @ {preview.bay_spacing_m.toFixed(2)} m · drag to
                orbit, hover a row to preview
              </p>
              <Building3D
                spec={{
                  ...usedSpec,
                  geometry: {
                    ...usedSpec.geometry,
                    number_of_bays: preview.number_of_bays,
                    bay_spacing_m: preview.bay_spacing_m,
                  },
                }}
                sections={preview.sections}
                checks={[]}
                uniformUtil={preview.governing_utilisation}
              />
            </div>
          ) : null}
          <div className="border-border overflow-x-auto rounded-md border">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead className="bg-surface text-subtle text-xs">
                <tr>
                  <th className="px-3 py-2 font-medium">Frames</th>
                  <th className="px-3 py-2 font-medium">Bays × spacing</th>
                  <th className="px-3 py-2 font-medium">Column / rafter</th>
                  <th className="px-3 py-2 font-medium">Total steel</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {data.options.map((o) => {
                  const isLightest = o.number_of_bays === data.lightest_passing_bays;
                  const isCurrent = o.number_of_bays === currentBays;
                  const isPreview = o.number_of_bays === previewBays;
                  return (
                    <tr
                      key={o.number_of_bays}
                      onMouseEnter={() => setHoverBays(o.number_of_bays)}
                      onMouseLeave={() => setHoverBays(null)}
                      onFocus={() => setHoverBays(o.number_of_bays)}
                      tabIndex={0}
                      className={cn(
                        "border-border cursor-default border-t transition-colors",
                        isLightest && "bg-success/5",
                        isPreview && "bg-accent/10",
                      )}
                    >
                      <td className="text-foreground px-3 py-2 font-medium">{o.number_of_frames}</td>
                      <td className="text-muted px-3 py-2">
                        {o.number_of_bays} × {o.bay_spacing_m.toFixed(2)} m
                        {o.is_baseline ? (
                          <span className="text-subtle"> · current</span>
                        ) : null}
                      </td>
                      <td className="text-muted px-3 py-2">{sectionsLabel(o.sections)}</td>
                      <td className="text-foreground px-3 py-2 tabular-nums">
                        {tonnes(o.total_primary_mass_kg)}
                      </td>
                      <td className="px-3 py-2">
                        <StatusBadge option={o} isLightest={isLightest} />
                      </td>
                      <td className="px-3 py-2 text-right">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => onApply(o.number_of_bays, o.bay_spacing_m)}
                          disabled={!o.feasible || isCurrent}
                        >
                          {isCurrent ? "In use" : "Use"}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <ul className="text-subtle list-disc pl-4 text-xs">
            {data.notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
