"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { ProjectRowActions } from "@/components/projects/project-row-actions";
import { Card, CardContent } from "@/components/ui/card";
import { FilterSelect } from "@/components/ui/filter-select";
import { Pager } from "@/components/ui/pager";
import { SearchInput } from "@/components/ui/search-input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export interface ProjectItem {
  id: string;
  name: string;
  created_at: string;
}

const PAGE_SIZE = 8;

/** Projects list with real-time (client-side) search, sort and pagination. */
export function ProjectsManager({ projects }: { projects: ProjectItem[] }) {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    const rows = term ? projects.filter((p) => p.name.toLowerCase().includes(term)) : projects;
    const sorted = [...rows].sort((a, b) =>
      sort === "oldest"
        ? a.created_at.localeCompare(b.created_at)
        : sort === "name"
          ? a.name.localeCompare(b.name)
          : b.created_at.localeCompare(a.created_at),
    );
    return sorted;
  }, [projects, q, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const slice = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          value={q}
          onChange={(v) => {
            setQ(v);
            setPage(1);
          }}
          placeholder="Search projects…"
        />
        <FilterSelect
          label="Sort"
          value={sort}
          onChange={(v) => {
            setSort(v);
            setPage(1);
          }}
          options={[
            { value: "newest", label: "Newest first" },
            { value: "oldest", label: "Oldest first" },
            { value: "name", label: "Name A–Z" },
          ]}
        />
      </div>

      <Card>
        {filtered.length === 0 ? (
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
              {slice.map((project) => (
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

      <Pager page={current} pageCount={pageCount} total={filtered.length} onPage={setPage} />
    </div>
  );
}
