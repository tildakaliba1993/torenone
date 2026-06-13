"use client";

import { useState } from "react";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DescribeStep } from "@/components/design/describe-step";
import { type FrameSpec, type ParseAssumption } from "@/lib/api/service";

/**
 * Multi-step design flow (Task 6.4 builds the Describe step; the Review/Run
 * step and Results step land in Tasks 6.5/6.6). The parsed spec is held in
 * client state and handed forward through the steps.
 */
export function DesignFlow({ projectName }: { projectId: string; projectName: string }) {
  const [spec, setSpec] = useState<FrameSpec | null>(null);
  const [assumptions, setAssumptions] = useState<ParseAssumption[]>([]);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <Link href="/projects" className="text-xs text-accent hover:underline">
          ← Projects
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">New design</h1>
        <p className="text-sm text-muted">{projectName}</p>
      </header>

      {spec === null ? (
        <DescribeStep
          onComplete={(result) => {
            setSpec(result.spec);
            setAssumptions(result.assumptions);
          }}
        />
      ) : (
        <ReviewPreview
          spec={spec}
          assumptions={assumptions}
          onBack={() => {
            setSpec(null);
            setAssumptions([]);
          }}
        />
      )}
    </main>
  );
}

function ReviewPreview({
  spec,
  assumptions,
  onBack,
}: {
  spec: FrameSpec;
  assumptions: ParseAssumption[];
  onBack: () => void;
}) {
  const g = spec.geometry;
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>We understood your frame</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 text-sm">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
            <Row label="Span" value={`${g.span_m} m`} />
            <Row label="Eaves height" value={`${g.eaves_height_m} m`} />
            <Row label="Roof pitch" value={`${g.roof_pitch_deg}°`} />
            <Row label="Bay spacing" value={`${g.bay_spacing_m} m`} />
            <Row label="Number of bays" value={String(g.number_of_bays)} />
          </dl>
          {assumptions.length > 0 ? (
            <div className="flex flex-col gap-1">
              <p className="font-medium text-foreground">Assumptions we made</p>
              <ul className="flex flex-col gap-1 text-muted">
                {assumptions.map((a, i) => (
                  <li key={i}>• {a.note}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="rounded-md border border-dashed border-border-strong p-4 text-sm text-muted">
        Editable spec review &amp; <span className="font-medium text-foreground">Run design</span>{" "}
        arrive in the next step.
      </div>

      <div>
        <Button variant="secondary" onClick={onBack}>
          Back to description
        </Button>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-mono">{value}</dd>
    </>
  );
}
