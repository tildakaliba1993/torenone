"use client";

import { useRouter } from "next/navigation";

import { ResultsStep } from "@/components/design/results-step";
import { type DesignResponse, type ReportMetadata } from "@/lib/api/service";

/**
 * Client wrapper for the saved-run viewer: renders the read-only results AND the
 * agentic "Explore better options" panel, so a better design can be explored from any
 * saved run at any time. Choosing an option generates its calc package (a new run) and
 * navigates to it — where Explore is available again.
 */
export function RunResults({
  result,
  projectId,
  reportMetadata,
}: {
  result: DesignResponse;
  projectId: string;
  /** Project-level document metadata, baked into any calc package generated from an option. */
  reportMetadata?: ReportMetadata;
}) {
  const router = useRouter();
  return (
    <ResultsStep
      result={result}
      projectId={projectId}
      reportMetadata={reportMetadata}
      onUseAlternative={(response) =>
        router.push(`/projects/${projectId}/runs/${response.report.run_id}`)
      }
    />
  );
}
