import { Suspense } from "react";

import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { type RunRow, RunHistory } from "@/components/projects/run-history";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LinkButton } from "@/components/ui/link-button";
import { ListToolbar } from "@/components/ui/list-toolbar";
import { Pagination } from "@/components/ui/pagination";
import { createClient } from "@/lib/supabase/server";

const PAGE_SIZE = 8;

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

type Search = { q?: string; mode?: string; result?: string; sort?: string; page?: string };

/** A short human label derived from the frame geometry, used when none was set. */
function derivedLabel(spec: RawRunRow["frame_spec"]): string {
  const g = spec?.geometry ?? {};
  if (g.span_m == null) return "Portal frame design";
  return `${g.span_m} m × ${g.eaves_height_m ?? "?"} m · ${g.roof_pitch_deg ?? "?"}°`;
}

export default async function ProjectDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Search>;
}) {
  const { id } = await params;
  const sp = await searchParams;
  const q = (sp.q ?? "").trim();
  const mode = sp.mode ?? "all";
  const result = sp.result ?? "all";
  const sort = sp.sort ?? "newest";
  const page = Math.max(1, Number(sp.page) || 1);
  const from = (page - 1) * PAGE_SIZE;

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: project } = await supabase.from("projects").select("id, name").eq("id", id).single();
  if (!project) notFound();

  // RLS (Task 5.4) scopes both runs and the embedded reports to the caller's firm.
  let query = supabase
    .from("runs")
    .select(
      "id, label, mode, passed, governing_utilisation, created_at, frame_spec, reports(storage_path)",
      { count: "exact" },
    )
    .eq("project_id", id);

  if (q) query = query.ilike("label", `%${q}%`);
  if (mode === "design" || mode === "check") query = query.eq("mode", mode);
  if (result === "pass") query = query.eq("passed", true);
  if (result === "fail") query = query.eq("passed", false);

  query =
    sort === "oldest"
      ? query.order("created_at", { ascending: true })
      : sort === "util-desc"
        ? query.order("governing_utilisation", { ascending: false, nullsFirst: false })
        : sort === "util-asc"
          ? query.order("governing_utilisation", { ascending: true, nullsFirst: false })
          : query.order("created_at", { ascending: false });

  const { data: runsData, count } = await query.range(from, from + PAGE_SIZE - 1);

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

  const total = count ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtersActive = q !== "" || mode !== "all" || result !== "all";
  const hasAnyRuns = total > 0 || filtersActive;

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
        <CardContent className="flex flex-col gap-4">
          {!hasAnyRuns ? (
            <p className="text-muted text-sm">
              No designs yet — start one with &ldquo;New design&rdquo;.
            </p>
          ) : (
            <>
              <Suspense>
                <ListToolbar
                  searchPlaceholder="Search designs…"
                  selects={[
                    {
                      param: "mode",
                      label: "Mode",
                      defaultValue: "all",
                      options: [
                        { value: "all", label: "All modes" },
                        { value: "design", label: "Design" },
                        { value: "check", label: "Check" },
                      ],
                    },
                    {
                      param: "result",
                      label: "Result",
                      defaultValue: "all",
                      options: [
                        { value: "all", label: "All results" },
                        { value: "pass", label: "Pass" },
                        { value: "fail", label: "Fail" },
                      ],
                    },
                    {
                      param: "sort",
                      label: "Sort",
                      defaultValue: "newest",
                      options: [
                        { value: "newest", label: "Newest first" },
                        { value: "oldest", label: "Oldest first" },
                        { value: "util-desc", label: "Governing ↓" },
                        { value: "util-asc", label: "Governing ↑" },
                      ],
                    },
                  ]}
                />
              </Suspense>
              <RunHistory runs={runs} projectId={project.id} />
              <Pagination page={page} pageCount={pageCount} total={total} params={sp} />
            </>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
