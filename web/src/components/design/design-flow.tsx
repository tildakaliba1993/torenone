"use client";

import { useEffect, useState } from "react";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { DescribeStep } from "@/components/design/describe-step";
import { ResultsStep } from "@/components/design/results-step";
import { ReviewStep } from "@/components/design/review-step";
import {
  type DesignResponse,
  type FrameSpec,
  type ReportMetadata,
  warmService,
} from "@/lib/api/service";

/**
 * Multi-step design flow: Describe (6.4) → Review/Run (6.5) → Results (6.6).
 * The parsed spec and design result are held in client state across steps.
 */
export function DesignFlow({
  projectId,
  projectName,
  initialReportMetadata,
}: {
  projectId: string;
  projectName: string;
  /** Project-level document metadata — pre-fills the Review card and seeds the run metadata. */
  initialReportMetadata?: ReportMetadata;
}) {
  const router = useRouter();
  const [spec, setSpec] = useState<FrameSpec | null>(null);
  const [result, setResult] = useState<DesignResponse | null>(null);
  const [reportMetadata, setReportMetadata] = useState<ReportMetadata | undefined>(
    initialReportMetadata,
  );

  // The run is persisted by the engineering service (not a Next action), so invalidate
  // the client Router Cache once it lands — otherwise the project's run history shows
  // a stale (empty) list when the engineer navigates back.
  function onDesignComplete(response: DesignResponse) {
    setResult(response);
    router.refresh();
  }

  const step: "describe" | "review" | "results" = result ? "results" : spec ? "review" : "describe";
  const stepLabel = step === "describe" ? "Describe" : step === "review" ? "Review & run" : "Results";

  // The engineering service is scale-to-zero on Fly. Wake it as the engineer starts the flow
  // and again on the Review step (in case it idled back to sleep while inputs were edited), so
  // Parse / Run design never pays a cold start that surfaces as "couldn't reach the service".
  useEffect(() => {
    if (step === "describe" || step === "review") void warmService();
  }, [step]);

  return (
    <main className="flex w-full flex-col gap-6">
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
          onComplete={onDesignComplete}
          onReportMetadata={setReportMetadata}
          initialReportMetadata={initialReportMetadata}
          onBack={() => setSpec(null)}
        />
      ) : null}

      {step === "results" && result ? (
        <ResultsStep
          result={result}
          projectId={projectId}
          onUseAlternative={onDesignComplete}
          reportMetadata={reportMetadata}
          onRestart={() => {
            setResult(null);
            setSpec(null);
          }}
        />
      ) : null}
    </main>
  );
}
