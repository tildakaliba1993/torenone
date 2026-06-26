"use client";

import { useEffect, useRef, useState } from "react";

import { StatusBadge } from "@/components/status-badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { openFirmSubscriptionCheckout } from "@/lib/paddle/checkout";
import { paddleConfigured } from "@/lib/paddle/config";

export interface BillingState {
  email: string;
  firmId: string;
  isPilot: boolean;
  subscriptionStatus: string | null;
  /** Whether the no-credit-card complimentary window is still open (computed server-side). */
  complimentaryActive: boolean;
  /** ISO date the complimentary window ends (for display). */
  complimentaryUntil: string | null;
  /** Deep-link from the pricing page (?subscribe=firm) — auto-opens the checkout once. */
  autoSubscribe?: boolean;
}

export function BillingCard({
  email,
  firmId,
  isPilot,
  subscriptionStatus,
  complimentaryActive,
  complimentaryUntil,
  autoSubscribe = false,
}: BillingState) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoOpened = useRef(false);

  const configured = paddleConfigured();
  const subscribed = subscriptionStatus === "active" || subscriptionStatus === "trialing";
  const priceLabel = isPilot ? "R999/mo (pilot rate)" : "R1,650/mo";
  const ctaLabel = complimentaryActive
    ? `Continue at ${isPilot ? "R999" : "R1,650"}/mo`
    : `Subscribe — ${priceLabel}`;

  async function subscribe() {
    setBusy(true);
    setError(null);
    try {
      await openFirmSubscriptionCheckout({ email, firmId, pilot: isPilot });
    } catch {
      setError("Couldn’t open the checkout. Please try again in a moment.");
    } finally {
      setBusy(false);
    }
  }

  // Deep-linked from the pricing page (?subscribe=firm): open the checkout once, and strip the
  // param so a refresh doesn't reopen it.
  useEffect(() => {
    if (autoOpened.current || !autoSubscribe || !configured || subscribed || !firmId) return;
    autoOpened.current = true;
    window.history.replaceState(null, "", window.location.pathname);
    void openFirmSubscriptionCheckout({ email, firmId, pilot: isPilot }).catch(() =>
      setError("Couldn’t open the checkout. Please try again in a moment."),
    );
  }, [autoSubscribe, configured, subscribed, firmId, email, isPilot]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Billing</CardTitle>
        <CardDescription>
          Calculating and Check mode are always free. The Firm plan unlocks unlimited calc-package
          downloads for your whole firm.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-sm">
        <div className="flex items-center justify-between border-b border-border py-2">
          <span className="text-muted">Plan</span>
          <span className="flex items-center gap-2 font-medium">
            {subscribed ? (
              <StatusBadge status="pass">Firm plan</StatusBadge>
            ) : complimentaryActive ? (
              <StatusBadge status="review">Pilot trial</StatusBadge>
            ) : (
              "Free"
            )}
          </span>
        </div>

        {complimentaryActive && complimentaryUntil ? (
          <p className="text-muted">
            Your pilot trial is active until{" "}
            <span className="text-foreground font-medium">
              {new Date(complimentaryUntil).toLocaleDateString()}
            </span>
            . Test against your past projects — no credit card needed. Subscribe any time to keep
            unlimited downloads after it ends.
          </p>
        ) : null}

        {subscribed ? (
          <p className="text-muted">
            Your firm is on the Firm plan ({subscriptionStatus}). Manage or cancel any time —
            you’ll keep access until the end of the billing period.
          </p>
        ) : (
          <div className="flex flex-col items-start gap-2">
            {isPilot && !complimentaryActive ? (
              <p className="text-muted">
                As a pilot firm you keep the <span className="text-foreground">R999/mo</span>{" "}
                pilot rate, locked for your first year.
              </p>
            ) : null}
            <Button onClick={subscribe} loading={busy} disabled={!configured || busy}>
              {ctaLabel}
            </Button>
            {!configured ? (
              <p className="text-subtle text-xs">
                Billing isn’t configured in this environment yet.
              </p>
            ) : null}
            {error ? (
              <p role="alert" className="text-danger text-xs">
                {error}
              </p>
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
