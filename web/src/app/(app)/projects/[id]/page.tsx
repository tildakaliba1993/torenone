import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { type RunRow, RunHistory } from "@/components/projects/run-history";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createClient } from "@/lib/supabase/server";

interface RawRunRow {
  id: string;
  mode: string;
  passed: boolean | null;
  governing_utilisation: number | null;
  created_at: string;
  reports: Array<{ storage_path: string }> | { storage_path: string } | null;
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

  // RLS (Task 5.4) scopes both runs and the embedded reports to the caller's firm.
  const { data: runsData } = await supabase
    .from("runs")
    .select("id, mode, passed, governing_utilisation, created_at, reports(storage_path)")
    .eq("project_id", id)
    .order("created_at", { ascending: false });

  const runs: RunRow[] = ((runsData ?? []) as RawRunRow[]).map((r) => ({
    id: r.id,
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
          <Link href="/projects" className="text-xs text-accent hover:underline">
            ← Projects
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">{project.name}</h1>
        </div>
        <Button asChild>
          <Link href={`/projects/${project.id}/design/new`}>New design</Link>
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Design runs</CardTitle>
        </CardHeader>
        <CardContent>
          <RunHistory runs={runs} />
        </CardContent>
      </Card>
    </main>
  );
}
