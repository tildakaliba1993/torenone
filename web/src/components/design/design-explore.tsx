"use client";

import { useState } from "react";

import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  type AgentAlternative,
  type AgentConstraints,
  type AgentDesignOutcome,
  type DesignResponse,
  type DesignResult,
  ServiceError,
  runDesign,
  runDesignAgent,
} from "@/lib/api/service";

function fmtZar(value: number): string {
  return `R ${Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`;
}

/**
 * Agentic exploration panel — additive, opt-in (one click, so it never spends on mount).
 *
 * The AI orchestrates the deterministic kernel and proposes input levers; every number shown
 * here comes from the kernel (the source of truth), and the current design is always the
 * baseline, so an option can never be worse. Choosing an option replays it through the normal
 * design path (`runDesign`) to produce the stamped calc package.
 */
export function DesignExplore({
  design,
  projectId,
  onUse,
}: {
  design: DesignResult;
  projectId: string;
  onUse: (response: DesignResponse) => void;
}) {
  const [phase, setPhase] = useState<"idle" | "loading" | "done">("idle");
  const [outcome, setOutcome] = useState<AgentDesignOutcome | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applyingIdx, setApplyingIdx] = useState<number | null>(null);

  const [stockText, setStockText] = useState("");
  const [maxDepth, setMaxDepth] = useState("");

  function buildConstraints(): AgentConstraints | null {
    const allowed = stockText
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    const depth = maxDepth.trim() === "" ? null : Number(maxDepth.trim());
    const constraints: AgentConstraints = {};
    if (allowed.length > 0) constraints.allowed_sections = allowed;
    if (depth != null && Number.isFinite(depth) && depth > 0) constraints.max_depth_mm = depth;
    return constraints.allowed_sections || constraints.max_depth_mm != null ? constraints : null;
  }

  async function onExplore() {
    setError(null);
    setPhase("loading");
    try {
      const result = await runDesignAgent(design.frame_spec, buildConstraints());
      setOutcome(result);
      setPhase("done");
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Couldn’t explore options just now.");
      setPhase("idle");
    }
  }

  async function onUseAlternative(alt: AgentAlternative, idx: number) {
    setApplyingIdx(idx);
    setError(null);
    try {
      const response = await runDesign({
        spec: alt.result.frame_spec,
        mode: alt.mode,
        sections: alt.sections ?? null,
        project_id: projectId,
      });
      onUse(response);
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Couldn’t apply that option.");
    } finally {
      setApplyingIdx(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Explore better options</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-sm">
        <p className="text-muted">
          The design assistant tries alternative inputs (closer bracing, or sections you have in
          stock) and lets the kernel cost each one. Every figure is kernel-computed — the assistant
          never sizes anything itself, and the design above stays the safe default.
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <label htmlFor="stock-sections" className="text-xs text-muted">
              Only use these sections (optional, comma-separated)
            </label>
            <Input
              id="stock-sections"
              placeholder="e.g. IPE 360, IPE 400, IPE 450"
              value={stockText}
              onChange={(e) => setStockText(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="max-depth" className="text-xs text-muted">
              Max member depth (optional, mm)
            </label>
            <Input
              id="max-depth"
              type="number"
              inputMode="decimal"
              placeholder="e.g. 400"
              value={maxDepth}
              onChange={(e) => setMaxDepth(e.target.value)}
            />
          </div>
        </div>

        <Button onClick={onExplore} loading={phase === "loading"} className="self-start">
          {phase === "loading" ? "Exploring…" : "Explore options"}
        </Button>

        {error ? (
          <p role="alert" className="text-sm font-medium text-danger">
            {error}
          </p>
        ) : null}

        {outcome ? (
          <div className="flex flex-col gap-4">
            {outcome.narrative ? <p className="text-foreground">{outcome.narrative}</p> : null}

            {outcome.alternatives.length === 0 ? (
              <p className="text-muted">
                No better option than the current design was found — it stands.
              </p>
            ) : (
              <div className="flex flex-col gap-3">
                {outcome.alternatives.map((alt, idx) => (
                  <AlternativeCard
                    key={idx}
                    alt={alt}
                    recommended={idx === outcome.recommended_index}
                    applying={applyingIdx === idx}
                    disabled={applyingIdx != null}
                    onUse={() => onUseAlternative(alt, idx)}
                  />
                ))}
              </div>
            )}

            {outcome.notes.length > 0 ? (
              <ul className="list-disc pl-5 text-xs text-subtle">
                {outcome.notes.map((note, i) => (
                  <li key={i}>{note}</li>
                ))}
              </ul>
            ) : null}

            {!outcome.used_llm ? (
              <p className="text-xs text-subtle">
                The design assistant wasn’t available, so only the standard design is shown.
              </p>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function AlternativeCard({
  alt,
  recommended,
  applying,
  disabled,
  onUse,
}: {
  alt: AgentAlternative;
  recommended: boolean;
  applying: boolean;
  disabled: boolean;
  onUse: () => void;
}) {
  const r = alt.result;
  const rafter = r.sections.find((s) => s.member === "rafter")?.designation ?? "—";
  const column = r.sections.find((s) => s.member === "column")?.designation ?? "—";
  return (
    <div className="flex flex-col gap-3 rounded-md border border-border p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium">{alt.label}</p>
        <div className="flex items-center gap-2">
          {recommended ? (
            <span className="inline-flex items-center rounded-full border border-accent/40 bg-accent/10 px-2.5 py-0.5 text-xs font-medium text-accent">
              Recommended
            </span>
          ) : null}
          <StatusBadge status={r.passed ? "pass" : "fail"}>
            {r.passed ? "passes" : "fails"}
          </StatusBadge>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-4">
        <Stat label="rafter" value={rafter} />
        <Stat label="column" value={column} />
        <Stat label="governing" value={r.governing_utilisation.toFixed(2)} />
        {r.total_steel_tonnes != null ? (
          <Stat label="steel" value={`${r.total_steel_tonnes.toFixed(2)} t`} />
        ) : null}
        {r.indicative_cost_zar != null ? (
          <Stat label="indicative cost" value={fmtZar(r.indicative_cost_zar)} />
        ) : null}
      </dl>

      {alt.trade_off_note ? <p className="text-muted">{alt.trade_off_note}</p> : null}
      {alt.rationale ? <p className="text-xs text-subtle">{alt.rationale}</p> : null}

      <Button
        variant="secondary"
        className="self-start"
        loading={applying}
        disabled={disabled}
        onClick={onUse}
      >
        {applying ? "Applying…" : "Use this design"}
      </Button>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-muted capitalize">{label}</dt>
      <dd className="font-mono">{value}</dd>
    </div>
  );
}
