"use client";

import { useRouter } from "next/navigation";

import { ReportDownloadButton } from "@/components/projects/report-download-button";
import { RunRowActions } from "@/components/projects/run-row-actions";
import { StatusBadge } from "@/components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export interface RunRow {
  id: string;
  label: string;
  rawLabel: string | null;
  mode: string;
  passed: boolean | null;
  governing_utilisation: number | null;
  created_at: string;
  storage_path: string | null;
}

/**
 * Per-project list of design runs. Each row is clickable and opens the generated design
 * page; the report download + rename/delete are separate, propagation-stopped actions.
 * Search / filter / sort / pagination are driven by the parent page (server-side).
 */
export function RunHistory({ runs, projectId }: { runs: RunRow[]; projectId: string }) {
  const router = useRouter();

  if (runs.length === 0) {
    return (
      <p className="text-muted text-sm">
        No designs match — adjust the filters, or start one with &ldquo;New design&rdquo;.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Design</TableHead>
          <TableHead>Date</TableHead>
          <TableHead>Mode</TableHead>
          <TableHead>Result</TableHead>
          <TableHead>Governing</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => {
          const open = () => router.push(`/projects/${projectId}/runs/${run.id}`);
          return (
            <TableRow
              key={run.id}
              role="link"
              tabIndex={0}
              onClick={open}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  open();
                }
              }}
              className="hover:bg-surface-raised focus-visible:bg-surface-raised cursor-pointer transition-colors focus-visible:outline-none"
            >
              <TableCell className="text-foreground font-medium">{run.label}</TableCell>
              <TableCell className="text-muted">
                {new Date(run.created_at).toLocaleDateString()}
              </TableCell>
              <TableCell className="capitalize">{run.mode}</TableCell>
              <TableCell>
                {run.passed === null ? (
                  <span className="text-subtle">—</span>
                ) : (
                  <StatusBadge status={run.passed ? "pass" : "fail"}>
                    {run.passed ? "pass" : "fail"}
                  </StatusBadge>
                )}
              </TableCell>
              <TableCell className="font-mono">
                {run.governing_utilisation != null ? run.governing_utilisation.toFixed(2) : "—"}
              </TableCell>
              <TableCell onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center justify-end gap-1">
                  <ReportDownloadButton storagePath={run.storage_path} />
                  <RunRowActions id={run.id} projectId={projectId} label={run.rawLabel ?? ""} />
                </div>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
