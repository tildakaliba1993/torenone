"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ServiceError, getReportSignedUrl } from "@/lib/api/service";

/** Downloads a stored calc-package PDF via a short-lived Supabase signed URL (Task 6.7). */
export function ReportDownloadButton({
  storagePath,
  label = "PDF",
}: {
  storagePath: string | null;
  label?: string;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!storagePath) {
    return <span className="text-subtle">—</span>;
  }

  async function onClick() {
    setPending(true);
    setError(null);
    try {
      const url = await getReportSignedUrl(storagePath!);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Download failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <Button type="button" variant="secondary" size="sm" onClick={onClick} disabled={pending}>
        {pending ? "…" : label}
      </Button>
      {error ? (
        <span role="alert" className="text-xs text-danger">
          {error}
        </span>
      ) : null}
    </div>
  );
}
