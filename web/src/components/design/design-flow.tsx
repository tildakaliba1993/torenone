"use client";

import { useState } from "react";

import Link from "next/link";

import { DescribeStep } from "@/components/design/describe-step";
import { ResultsStep } from "@/components/design/results-step";
import { ReviewStep } from "@/components/design/review-step";
import { type DesignResponse, type FrameSpec } from "@/lib/api/service";

/**
 * Multi-step design flow: Describe (6.4) → Review/Run (6.5) → Results (6.6).
 * The parsed spec and design result are held in client state across steps.
 */
export function DesignFlow({ projectId, projectName }: { projectId: string; projectName: string }) {
  const [spec, setSpec] = useState<FrameSpec | null>(null);
  const [result, setResult] = useState<DesignResponse | null>(null);

  const step: "describe" | "review" | "results" = result ? "results" : spec ? "review" : "describe";
  const stepLabel = step === "describe" ? "Describe" : step === "review" ? "Review & run" : "Results";

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <Link href={`/projects/${projectId}`} className="text-xs text-accent hover:underline">
          ← Back to project
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">New design</h1>
        <p className="text-sm text-muted">
          {projectName} · {stepLabel}
        </p>
      </header>

      {step === "describe" ? <DescribeStep onComplete={(res) => setSpec(res.spec)} /> : null}

      {step === "review" && spec ? (
        <ReviewStep
          spec={spec}
          projectId={projectId}
          onComplete={setResult}
          onBack={() => setSpec(null)}
        />
      ) : null}

      {step === "results" && result ? (
        <ResultsStep
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
