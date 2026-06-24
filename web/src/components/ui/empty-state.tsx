import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Shared empty-state / first-run panel: an accent icon tile, a title, a short description,
 * optional supporting content (e.g. a how-it-works strip) and a primary action.
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  children,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "border-border bg-surface flex flex-col items-center gap-5 rounded-2xl border px-6 py-14 text-center",
        className,
      )}
    >
      {icon ? (
        <span className="border-accent/30 bg-accent/10 text-accent flex size-12 items-center justify-center rounded-xl border">
          {icon}
        </span>
      ) : null}
      <div className="flex max-w-md flex-col gap-1.5">
        <h2 className="text-foreground text-lg font-semibold">{title}</h2>
        {description ? <p className="text-muted text-sm leading-6">{description}</p> : null}
      </div>
      {children}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}

export function EmptyStateIcon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" className="size-6" fill="none" aria-hidden>
      <path d={d} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
