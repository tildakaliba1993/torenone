"use client";

import { useState } from "react";

import Link from "next/link";

import { StatusBadge } from "@/components/status-badge";
import { DescribeStep } from "@/components/design/describe-step";
import { ReviewStep } from "@/components/design/review-step";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type DesignResponse, type FrameSpec } from "@/lib/api/service";

/**
 * Multi-step design flow (Task 6.4 Describe → Task 6.5 Review/Run → Task 6.6
 * Results). The parsed spec and design result are held in client state and
 * handed forward through the steps.
 */
export function DesignFlow({ projectId, projectName }: { projectId: string; projectName: string }) {
  const [spec, setSpec] = useState<FrameSpec | null>(null);
  const [result, setResult] = useState<DesignResponse | null>(null);

  const step: "describe" | "review" | "results" = result ? "results" : spec ? "review" : "describe";

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <Link href="/projects" className="text-xs text-accent hover:underline">
          ← Projects
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">New design</h1>
        <p className="text-sm text-muted">
          {projectName} · {step === "describe" ? "Describe" : step === "review" ? "Review & run" : "Results"}
        </p>
      </header>

      {step === "describe" ? (
        <DescribeStep onComplete={(res) => setSpec(res.spec)} />
      ) : null}

      {step === "review" && spec ? (
        <ReviewStep
          spec={spec}
          projectId={projectId}
          onComplete={setResult}
          onBack={() => setSpec(null)}
        />
      ) : null}

      {step === "results" && result ? (
        <ResultsPreview
          result={result}
          onRestart={() => {
            setResult(null);
            setSpec(null);
          }}
        />
      ) : null}
    </main>
  );
}

function ResultsPreview({
  result,
  onRestart,
}: {
  result: DesignResponse;
  onRestart: () => void;
}) {
  const { result: design, report } = result;
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Design complete</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          <div className="flex items-center gap-3">
            <StatusBadge status={design.passed ? "pass" : "fail"}>
              {design.passed ? "All checks pass" : "Some checks fail"}
            </StatusBadge>
            {typeof design.governing_utilisation === "number" ? (
              <span className="font-mono text-muted">
                governing {design.governing_utilisation.toFixed(2)}
              </span>
            ) : null}
          </div>
          <p className="text-muted">
            A calc-package PDF was generated and stored (report {report.report_id.slice(0, 8)}…).
          </p>
        </CardContent>
      </Card>

      <div className="rounded-md border border-dashed border-border-strong p-4 text-sm text-muted">
        The full results screen — utilisation tables for members, connections, baseplates &amp;
        footing, plus <span className="font-medium text-foreground">Download calc package (PDF)</span>{" "}
        — arrives in the next step.
      </div>

      <div>
        <Button variant="secondary" onClick={onRestart}>
          Start another design
        </Button>
      </div>
    </div>
  );
}
