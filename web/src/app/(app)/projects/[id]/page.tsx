import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { DesignsManager } from "@/components/projects/designs-manager";
import { type RunRow } from "@/components/projects/run-history";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, EmptyStateIcon } from "@/components/ui/empty-state";
import { LinkButton } from "@/components/ui/link-button";
import { createClient } from "@/lib/supabase/server";

interface RawRunRow {
  id: string;
  label: string | null;
  mode: string;
  passed: boolean | null;
  governing_utilisation: number | null;
  created_at: string;
  frame_spec: { geometry?: { span_m?: number; eaves_height_m?: number; roof_pitch_deg?: number } };
  reports: Array<{ storage_path: string }> | { storage_path: string } | null;
}

/** A short human label derived from the frame geometry, used when none was set. */
function derivedLabel(spec: RawRunRow["frame_spec"]): string {
  const g = spec?.geometry ?? {};
  if (g.span_m == null) return "Portal frame design";
  return `${g.span_m} m × ${g.eaves_height_m ?? "?"} m · ${g.roof_pitch_deg ?? "?"}°`;
}

export default async function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: project } = await supabase.from("projects").select("id, name").eq("id", id).single();
  if (!project) notFound();

  // RLS (Task 5.4) scopes both runs and the embedded reports to the firm. Search / filter /
  // sort / paginate happen client-side (real-time) over this set.
  const { data: runsData } = await supabase
    .from("runs")
    .select("id, label, mode, passed, governing_utilisation, created_at, frame_spec, reports(storage_path)")
    .eq("project_id", id)
    .order("created_at", { ascending: false })
    .limit(1000);

  const runs: RunRow[] = ((runsData ?? []) as RawRunRow[]).map((r) => ({
    id: r.id,
    rawLabel: r.label,
    label: r.label?.trim() || derivedLabel(r.frame_spec),
    mode: r.mode,
    passed: r.passed,
    governing_utilisation: r.governing_utilisation,
    created_at: r.created_at,
    storage_path: Array.isArray(r.reports)
      ? (r.reports[0]?.storage_path ?? null)
      : (r.reports?.storage_path ?? null),
  }));

  return (
    <main className="flex w-full flex-col gap-6">
      <header className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <Link href="/projects" className="text-accent text-xs hover:underline">
            ← Projects
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">{project.name}</h1>
        </div>
        <LinkButton href={`/projects/${project.id}/design/new`}>New design</LinkButton>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Designs</CardTitle>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <EmptyState
              className="border-0 bg-transparent py-10"
              icon={<EmptyStateIcon d="M4 6h16M4 12h10M4 18h7" />}
              title="No designs yet"
              description="Describe a frame — or upload a drawing — and TorenOne sizes and checks it end-to-end: members, connections, baseplates and footings."
              action={
                <LinkButton href={`/projects/${project.id}/design/new`}>New design</LinkButton>
              }
            />
          ) : (
            <DesignsManager runs={runs} projectId={project.id} />
          )}
        </CardContent>
      </Card>
    </main>
  );
}
