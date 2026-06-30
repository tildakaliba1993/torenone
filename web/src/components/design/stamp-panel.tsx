"use client";

import { useState } from "react";

import { useRouter } from "next/navigation";

import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type RunStamp, ServiceError, stampRun } from "@/lib/api/service";

/**
 * Engineer review & e-stamp panel on a saved run. A registered engineer can apply their
 * e-stamp, which re-renders the calc package with the stamp. Records professional
 * responsibility — TorenOne is a computational aid, the engineer's review is the assurance.
 */
export function StampPanel({
  runId,
  stamp,
  canStamp,
}: {
  runId: string;
  stamp: RunStamp | null;
  /** True if the current user is a registered engineer (with an ECSA reg no) and run is unstamped. */
  canStamp: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onStamp() {
    setBusy(true);
    setError(null);
    try {
      await stampRun(runId);
      router.refresh();
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Couldn’t apply the stamp.");
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <CardTitle>Engineer review &amp; stamp</CardTitle>
          <StatusBadge status={stamp ? "pass" : "review"}>
            {stamp ? "stamped" : "pending review"}
          </StatusBadge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm">
        {stamp ? (
          <div className="border-success/40 bg-success/10 rounded-md border px-4 py-3">
            <p className="text-foreground font-medium">
              ✓ Stamped by {stamp.engineer_name} (ECSA {stamp.ecsa_reg_no})
            </p>
            <p className="text-muted mt-1">
              Stamped {stamp.stamped_at} (UTC). The engineer has accepted professional
              responsibility; the stamp is bound to report fingerprint{" "}
              <span className="font-mono text-xs">{stamp.fingerprint.slice(0, 16)}…</span> and is on
              the downloadable calc package.
            </p>
          </div>
        ) : canStamp ? (
          <>
            <p className="text-muted">
              Applying your e-stamp re-renders the calc package with your name, ECSA registration
              number and the date, and records that you — a registered engineer — have reviewed,
              verified and accepted professional responsibility for this design. Review every item
              flagged PROVISIONAL or out of scope first.
            </p>
            <Button onClick={onStamp} loading={busy} className="self-start">
              {busy ? "Stamping…" : "Review complete — apply my e-stamp"}
            </Button>
            {error ? (
              <p role="alert" className="text-danger text-sm font-medium">
                {error}
              </p>
            ) : null}
          </>
        ) : (
          <p className="text-muted">
            This design has not yet been stamped by a registered engineer. A registered engineer at
            your firm must review and stamp it before it is used in construction.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
