"use client";

import { useRouter } from "next/navigation";

import { ReportDownloadButton } from "@/components/projects/report-download-button";
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
  mode: string;
  passed: boolean | null;
  governing_utilisation: number | null;
  created_at: string;
  storage_path: string | null;
}

/**
 * Per-project list of past design runs (Task 6.7). Each row is clickable and opens the
 * generated design page (`/projects/[id]/runs/[runId]`); the PDF download stays a
 * separate, propagation-stopped action.
 */
export function RunHistory({ runs, projectId }: { runs: RunRow[]; projectId: string }) {
  const router = useRouter();

  if (runs.length === 0) {
    return <p className="text-sm text-muted">No design runs yet — start one with “New design”.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Date</TableHead>
          <TableHead>Mode</TableHead>
          <TableHead>Result</TableHead>
          <TableHead>Governing</TableHead>
          <TableHead>Report</TableHead>
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
              className="cursor-pointer transition-colors hover:bg-surface-raised focus-visible:bg-surface-raised focus-visible:outline-none"
            >
              <TableCell className="text-muted">
                {new Date(run.created_at).toLocaleString()}
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
              {/* Stop propagation so downloading the PDF doesn't also open the run page. */}
              <TableCell onClick={(e) => e.stopPropagation()}>
                <ReportDownloadButton storagePath={run.storage_path} />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
