import { CreateProjectDialog } from "@/components/projects/create-project-dialog";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { createClient } from "@/lib/supabase/server";

export default async function ProjectsPage() {
  const supabase = await createClient();
  // RLS (Task 5.4) scopes this to the caller's own firm.
  const { data: projects } = await supabase
    .from("projects")
    .select("id, name, created_at")
    .order("created_at", { ascending: false });
  const rows = (projects ?? []) as Array<{ id: string; name: string; created_at: string }>;

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-10">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-muted">Steel-frame designs for your firm.</p>
        </div>
        {rows.length > 0 ? <CreateProjectDialog /> : null}
      </div>

      {rows.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
            <p className="text-sm text-muted">No projects yet — create one to start designing.</p>
            <CreateProjectDialog triggerLabel="Create your first project" />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((project) => (
                <TableRow key={project.id}>
                  <TableCell className="font-medium">{project.name}</TableCell>
                  <TableCell className="text-muted">
                    {new Date(project.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </main>
  );
}
