import { Suspense } from "react";

import Link from "next/link";

import { CreateProjectDialog } from "@/components/projects/create-project-dialog";
import { ProjectRowActions } from "@/components/projects/project-row-actions";
import { Card, CardContent } from "@/components/ui/card";
import { ListToolbar } from "@/components/ui/list-toolbar";
import { Pagination } from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { createClient } from "@/lib/supabase/server";

const PAGE_SIZE = 8;

type Search = { q?: string; sort?: string; page?: string };

export default async function ProjectsPage({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  const sp = await searchParams;
  const q = (sp.q ?? "").trim();
  const sort = sp.sort ?? "newest";
  const page = Math.max(1, Number(sp.page) || 1);
  const from = (page - 1) * PAGE_SIZE;

  const supabase = await createClient();
  // RLS (Task 5.4) scopes this to the caller's own firm.
  let query = supabase.from("projects").select("id, name, created_at", { count: "exact" });
  if (q) query = query.ilike("name", `%${q}%`);
  query =
    sort === "oldest"
      ? query.order("created_at", { ascending: true })
      : sort === "name"
        ? query.order("name", { ascending: true })
        : query.order("created_at", { ascending: false });

  const { data, count } = await query.range(from, from + PAGE_SIZE - 1);
  const rows = (data ?? []) as Array<{ id: string; name: string; created_at: string }>;
  const total = count ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasAnyProjects = total > 0 || q !== "";

  return (
    <main className="flex w-full flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-muted text-sm">Steel-frame designs for your firm.</p>
        </div>
        {hasAnyProjects ? <CreateProjectDialog /> : null}
      </div>

      {!hasAnyProjects ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
            <p className="text-muted text-sm">No projects yet — create one to start designing.</p>
            <CreateProjectDialog triggerLabel="Create your first project" />
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          <Suspense>
            <ListToolbar
              searchPlaceholder="Search projects…"
              selects={[
                {
                  param: "sort",
                  label: "Sort",
                  defaultValue: "newest",
                  options: [
                    { value: "newest", label: "Newest first" },
                    { value: "oldest", label: "Oldest first" },
                    { value: "name", label: "Name A–Z" },
                  ],
                },
              ]}
            />
          </Suspense>

          <Card>
            {rows.length === 0 ? (
              <CardContent className="text-muted py-12 text-center text-sm">
                No projects match &ldquo;{q}&rdquo;.
              </CardContent>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((project) => (
                    <TableRow key={project.id}>
                      <TableCell className="font-medium">
                        <Link
                          href={`/projects/${project.id}`}
                          className="hover:text-accent hover:underline"
                        >
                          {project.name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-muted">
                        {new Date(project.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <ProjectRowActions id={project.id} name={project.name} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>

          <Pagination page={page} pageCount={pageCount} total={total} params={sp} />
        </div>
      )}
    </main>
  );
}
