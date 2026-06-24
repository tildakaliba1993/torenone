import { CreateProjectDialog } from "@/components/projects/create-project-dialog";
import { type ProjectItem, ProjectsManager } from "@/components/projects/projects-manager";
import { Card, CardContent } from "@/components/ui/card";
import { createClient } from "@/lib/supabase/server";

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
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
            <p className="text-muted text-sm">No projects yet — create one to start designing.</p>
            <CreateProjectDialog triggerLabel="Create your first project" />
          </CardContent>
        </Card>
      ) : (
        <ProjectsManager projects={projects} />
      )}
    </main>
  );
}
