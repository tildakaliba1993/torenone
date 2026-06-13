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

/** Per-project list of past design runs with their stored PDFs (Task 6.7). */
export function RunHistory({ runs }: { runs: RunRow[] }) {
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
        {runs.map((run) => (
          <TableRow key={run.id}>
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
            <TableCell>
              <ReportDownloadButton storagePath={run.storage_path} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
