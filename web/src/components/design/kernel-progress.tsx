"use client";

import { useEffect, useState } from "react";

import { Spinner } from "@/components/ui/spinner";

/**
 * Live "what the engine is doing" trace shown while a design runs (FR-32 trust).
 *
 * The kernel runs server-side as a single request (no streaming), but its pipeline is
 * deterministic and known — so we walk through the *real* stages it executes, advancing on
 * a timer and holding on the final stage until the response lands. This gives the engineer
 * an LLM-style sense of progress instead of a frozen button. Every line names the actual
 * SANS step the kernel performs.
 */
const STAGES = [
  "Deriving dead & imposed loads — SANS 10160-2",
  "Building ULS / SLS load combinations — SANS 10160-1",
  "Running first-order plane-frame analysis — PyNite FEA",
  "Sizing members & checking SANS 10162-1 (axial · shear · moment · LTB · interaction)",
  "Checking second-order sway sensitivity — cl. 8.7",
  "Designing connections, baseplate & pad footing",
  "Evaluating wind load combinations (advisory)",
  "Rendering the clause-referenced calc-package PDF",
] as const;

const STEP_MS = 1600;

export function KernelProgress() {
  // Start at 0 and advance, but never past the last stage — it holds there until the
  // server responds and this component unmounts.
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (active >= STAGES.length - 1) return;
    const t = setTimeout(() => setActive((i) => Math.min(i + 1, STAGES.length - 1)), STEP_MS);
    return () => clearTimeout(t);
  }, [active]);

  return (
    <div
      role="status"
      aria-live="polite"
      className="border-border bg-surface flex flex-col gap-2 rounded-md border p-4"
    >
      <p className="text-foreground flex items-center gap-2 text-sm font-medium">
        <Spinner className="text-accent" />
        Running the deterministic SANS kernel…
      </p>
      <ol className="mt-1 flex flex-col gap-1.5">
        {STAGES.map((stage, i) => {
          const done = i < active;
          const current = i === active;
          return (
            <li
              key={stage}
              className={`flex items-start gap-2 text-xs ${
                current ? "text-foreground" : done ? "text-muted" : "text-subtle"
              }`}
            >
              <span className="mt-0.5 w-3 shrink-0 text-center font-mono">
                {done ? "✓" : current ? "›" : "·"}
              </span>
              <span className={current ? "font-medium" : undefined}>{stage}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
