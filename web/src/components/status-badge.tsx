import type { ReactNode } from "react";

export type CheckStatus = "pass" | "fail" | "review";

const VARIANTS: Record<
  CheckStatus,
  { label: string; icon: string; className: string }
> = {
  pass: {
    label: "PASS",
    icon: "✓",
    className: "text-success border-success/40 bg-success/10",
  },
  fail: {
    label: "FAIL",
    icon: "✕",
    className: "text-danger border-danger/40 bg-danger/10",
  },
  review: {
    label: "REVIEW",
    icon: "⚠",
    className: "text-warning border-warning/40 bg-warning/10",
  },
};

/**
 * Status indicator for calc checks.
 *
 * SAFETY (PRD FR-19): status is NEVER conveyed by colour alone — every badge
 * carries an icon and a text label, and exposes an accessible `role="status"`
 * with an aria-label. Human lives depend on this being unambiguous.
 */
export function StatusBadge({
  status,
  children,
}: {
  status: CheckStatus;
  children?: ReactNode;
}) {
  const { label, icon, className } = VARIANTS[status];
  const accessibleLabel = children ? `${label}: ${children}` : label;
  return (
    <span
      role="status"
      aria-label={accessibleLabel}
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 font-mono text-xs ${className}`}
    >
      <span aria-hidden="true">{icon}</span>
      <span>{children ?? label}</span>
    </span>
  );
}
