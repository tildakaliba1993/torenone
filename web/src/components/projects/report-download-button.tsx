"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { getEntitledReportUrl } from "@/lib/billing/actions";
import { openCalcPackageCheckout } from "@/lib/paddle/checkout";

/**
 * Downloads a stored calc-package PDF — but only when the firm is entitled (subscription,
 * complimentary trial, or a paid PAYG credit). When not entitled, opens the R250 pay-as-you-go
 * checkout for that design; the webhook then unlocks it and the next click downloads.
 */
export function ReportDownloadButton({
  runId,
  storagePath,
  label = "PDF",
}: {
  runId: string;
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
      const res = await getEntitledReportUrl(runId);
      if ("url" in res) {
        window.open(res.url, "_blank", "noopener,noreferrer");
      } else if ("needsPayment" in res) {
        await openCalcPackageCheckout({ email: res.email, firmId: res.firmId, runId });
      } else {
        setError(res.error);
      }
    } catch {
      setError("Download failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <Button type="button" variant="secondary" size="sm" onClick={onClick} loading={pending}>
        {label}
      </Button>
      {error ? (
        <span role="alert" className="text-xs text-danger">
          {error}
        </span>
      ) : null}
    </div>
  );
}
