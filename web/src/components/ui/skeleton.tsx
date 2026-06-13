import { cn } from "@/lib/utils";

/** Shimmer placeholder for loading states (Task 6.8). */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      data-testid="skeleton"
      className={cn("animate-pulse rounded-md bg-surface-raised", className)}
    />
  );
}
