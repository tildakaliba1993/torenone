"use client";

import { useMemo, useState } from "react";

import { type RunRow, RunHistory } from "@/components/projects/run-history";
import { FilterSelect } from "@/components/ui/filter-select";
import { Pager } from "@/components/ui/pager";
import { SearchInput } from "@/components/ui/search-input";

const PAGE_SIZE = 8;

/**
 * Designs (runs) list with real-time client-side search (on the displayed label), filter
 * (mode / result), sort, and pagination. RunHistory renders the current page slice.
 */
export function DesignsManager({ runs, projectId }: { runs: RunRow[]; projectId: string }) {
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("all");
  const [result, setResult] = useState("all");
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);

  const reset = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPage(1);
  };

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    const num = (x: number | null) => (x == null ? -1 : x);
    const rows = runs.filter((r) => {
      if (term && !r.label.toLowerCase().includes(term)) return false;
      if (mode !== "all" && r.mode !== mode) return false;
      if (result === "pass" && r.passed !== true) return false;
      if (result === "fail" && r.passed !== false) return false;
      return true;
    });
    return [...rows].sort((a, b) =>
      sort === "oldest"
        ? a.created_at.localeCompare(b.created_at)
        : sort === "util-desc"
          ? num(b.governing_utilisation) - num(a.governing_utilisation)
          : sort === "util-asc"
            ? num(a.governing_utilisation) - num(b.governing_utilisation)
            : b.created_at.localeCompare(a.created_at),
    );
  }, [runs, q, mode, result, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const slice = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <SearchInput value={q} onChange={reset(setQ)} placeholder="Search designs…" />
        <FilterSelect
          label="Mode"
          value={mode}
          onChange={reset(setMode)}
          options={[
            { value: "all", label: "All modes" },
            { value: "design", label: "Design" },
            { value: "check", label: "Check" },
          ]}
        />
        <FilterSelect
          label="Result"
          value={result}
          onChange={reset(setResult)}
          options={[
            { value: "all", label: "All results" },
            { value: "pass", label: "Pass" },
            { value: "fail", label: "Fail" },
          ]}
        />
        <FilterSelect
          label="Sort"
          value={sort}
          onChange={reset(setSort)}
          options={[
            { value: "newest", label: "Newest first" },
            { value: "oldest", label: "Oldest first" },
            { value: "util-desc", label: "Governing ↓" },
            { value: "util-asc", label: "Governing ↑" },
          ]}
        />
      </div>

      {filtered.length === 0 ? (
        <p className="text-muted text-sm">No designs match your search and filters.</p>
      ) : (
        <RunHistory runs={slice} projectId={projectId} />
      )}

      <Pager page={current} pageCount={pageCount} total={filtered.length} onPage={setPage} />
    </div>
  );
}
