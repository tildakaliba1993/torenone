import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { RunResults } from "@/components/design/run-results";
import { StampPanel } from "@/components/design/stamp-panel";
import { ReportDownloadButton } from "@/components/projects/report-download-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type DesignResponse,
  type DesignResult,
  type ReportMetadata,
  type RunStamp,
} from "@/lib/api/service";
import { createClient } from "@/lib/supabase/server";

interface RawRun {
  id: string;
  mode: string;
  result: DesignResult | null;
  stamp?: RunStamp | null;
  reports: Array<{ storage_path: string }> | { storage_path: string } | null;
}

/** A past design run, rendered on-screen (the generated design page) — opened from history. */
export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string; runId: string }>;
}) {
  const { id, runId } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // RLS (Task 5.4) scopes the project + run to the caller's firm; a foreign id → notFound.
  // select("*") stays resilient before the report_metadata migration is applied.
  const { data: project } = await supabase.from("projects").select("*").eq("id", id).single();
  if (!project) notFound();

  // select("*, ...") stays resilient before the runs.stamp migration is applied.
  const { data: runData } = await supabase
    .from("runs")
    .select("*, reports(storage_path)")
    .eq("id", runId)
    .eq("project_id", id)
    .single();
  if (!runData) notFound();

  const run = runData as RawRun;

  // The caller's registered-engineer status decides whether they may stamp. select("*") so this
  // is resilient before the profiles engineer-columns migration is applied.
  const { data: me } = await supabase.from("profiles").select("*").eq("id", user.id).single();
  const isRegisteredEngineer = Boolean(
    (me as { is_registered_engineer?: boolean } | null)?.is_registered_engineer &&
      (me as { ecsa_reg_no?: string | null } | null)?.ecsa_reg_no,
  );
  const stamp = (run.stamp as RunStamp | null) ?? null;
  const storagePath = Array.isArray(run.reports)
    ? (run.reports[0]?.storage_path ?? null)
    : (run.reports?.storage_path ?? null);

  const header = (
    <header className="flex flex-col gap-1">
      <Link href={`/projects/${id}`} className="text-xs text-accent hover:underline">
        ← {project.name}
      </Link>
      <h1 className="text-2xl font-semibold tracking-tight">Design</h1>
      <p className="text-sm text-muted">
        {project.name} · {run.mode === "check" ? "Check" : "Design"} run
      </p>
    </header>
  );

  // Runs created before on-screen results were saved have no `result` — offer the PDF.
  if (!run.result) {
    return (
      <main className="flex w-full flex-col gap-6">
        {header}
        <Card>
          <CardHeader>
            <CardTitle>On-screen view unavailable</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-start gap-3 text-sm text-muted">
            <p>
              This run was created before on-screen results were saved. You can still download its
              calc package.
            </p>
            <ReportDownloadButton
              runId={runId}
              storagePath={storagePath}
              label="Download calc package (PDF)"
            />
          </CardContent>
        </Card>
      </main>
    );
  }

  const response: DesignResponse = {
    result: run.result,
    report: {
      run_id: run.id,
      report_id: run.id,
      storage_path: storagePath ?? "",
      content_type: "application/pdf",
      size_bytes: 0,
    },
  };

  return (
    <main className="flex w-full flex-col gap-6">
      {header}
      <StampPanel runId={runId} stamp={stamp} canStamp={isRegisteredEngineer && !stamp} />
      <RunResults
        result={response}
        projectId={id}
        reportMetadata={(project.report_metadata as ReportMetadata | null) ?? undefined}
      />
    </main>
  );
}
