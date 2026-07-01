import { cn } from "@/lib/utils";

/**
 * Shimmer placeholder for loading states.
 *
 * A soft base tint with a sweeping highlight (via an ::after gradient) reads as "content is on its
 * way" rather than a static block. Falls back to a gentle pulse when the user prefers reduced motion.
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      data-testid="skeleton"
      className={cn(
        "relative isolate overflow-hidden rounded-md bg-surface-raised",
        // sweeping highlight
        "after:absolute after:inset-0 after:-translate-x-full after:animate-shimmer",
        "after:bg-gradient-to-r after:from-transparent after:via-foreground/[0.07] after:to-transparent",
        // reduced-motion: no sweep, gentle pulse instead
        "motion-reduce:after:hidden motion-reduce:animate-pulse",
        className,
      )}
    />
  );
}
