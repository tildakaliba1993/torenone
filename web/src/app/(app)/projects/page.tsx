import type { Metadata } from "next";

import { CreateProjectDialog } from "@/components/projects/create-project-dialog";
import { type ProjectItem, ProjectsManager } from "@/components/projects/projects-manager";
import { EmptyState, EmptyStateIcon } from "@/components/ui/empty-state";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Projects" };

const FIRST_RUN_STEPS = [
  { n: "1", title: "Describe", body: "Tell TorenOne about the frame in plain English." },
  { n: "2", title: "Review", body: "Confirm the inputs on an editable form — you stay the pilot." },
  { n: "3", title: "Get the calc package", body: "A clause-referenced SANS report, ready to review." },
];

export default async function ProjectsPage() {
  const supabase = await createClient();
  // RLS (Task 5.4) scopes this to the caller's own firm. Search/sort/paginate happen
  // client-side (real-time) over this set.
  const { data } = await supabase
    .from("projects")
    .select("id, name, created_at")
    .order("created_at", { ascending: false })
    .limit(1000);
  const projects = (data ?? []) as ProjectItem[];

  return (
    <main className="flex w-full flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-muted text-sm">Steel-frame designs for your firm.</p>
        </div>
        {projects.length > 0 ? <CreateProjectDialog /> : null}
      </div>

      {projects.length === 0 ? (
        <EmptyState
          icon={<EmptyStateIcon d="M4 20V8l8-5 8 5v12M4 20h16M9 20v-6h6v6" />}
          title="Design your first portal frame"
          description="Describe a single-bay steel portal frame in plain English and get a clause-referenced SANS calculation package in minutes. Free to start — you stay the responsible engineer."
          action={<CreateProjectDialog triggerLabel="Create your first project" />}
        >
          <div className="mt-2 grid w-full max-w-2xl gap-3 sm:grid-cols-3">
            {FIRST_RUN_STEPS.map((s) => (
              <div key={s.n} className="border-border bg-surface-raised rounded-xl border p-4 text-left">
                <span className="border-accent/40 text-accent bg-accent/10 flex size-7 items-center justify-center rounded-full border font-mono text-xs font-semibold">
                  {s.n}
                </span>
                <p className="text-foreground mt-3 text-sm font-medium">{s.title}</p>
                <p className="text-muted mt-1 text-xs leading-5">{s.body}</p>
              </div>
            ))}
          </div>
        </EmptyState>
      ) : (
        <ProjectsManager projects={projects} />
      )}
    </main>
  );
}
