"use client";

import Link, { useLinkStatus } from "next/link";

import { cn } from "@/lib/utils";

/**
 * A header nav link with instant click feedback.
 *
 * `useLinkStatus` (Next's navigation-pending signal) drives a fixed-size underline that fills in
 * while the destination loads, so a click registers immediately even before the new page arrives —
 * no layout shift (the track is always present; only its opacity/scale changes).
 */
function PendingUnderline() {
  const { pending } = useLinkStatus();
  return (
    <span
      aria-hidden
      className={cn(
        "bg-accent absolute -bottom-1 left-0 h-0.5 w-full origin-left rounded-full transition-transform duration-200",
        pending ? "scale-x-100" : "scale-x-0",
      )}
    />
  );
}

export function NavLink({
  href,
  children,
  active = false,
}: {
  href: string;
  children: React.ReactNode;
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "hover:text-accent relative transition-colors",
        active ? "text-foreground" : "text-muted",
      )}
    >
      {children}
      <PendingUnderline />
    </Link>
  );
}
