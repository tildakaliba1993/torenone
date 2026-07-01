import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/**
 * Shared, consistent loading primitives.
 *
 * Every authenticated route's `loading.tsx` composes these so the skeletons look identical to the
 * real page shells (same header/action/card rhythm) and identical to each other — one loading
 * language across the whole app. All entrances fade in, matching the page content transition.
 */

/** The <main> wrapper every page and its skeleton share (fade-in + column layout). */
export function PageShell({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <main className={cn("animate-fade-in flex w-full flex-col gap-6", className)}>{children}</main>
  );
}

/** Title (+ optional back-link eyebrow and subtitle) with an optional right-aligned action button. */
export function PageHeaderSkeleton({
  eyebrow = false,
  subtitle = true,
  action = true,
}: {
  eyebrow?: boolean;
  subtitle?: boolean;
  action?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex flex-col gap-2">
        {eyebrow ? <Skeleton className="h-3.5 w-24" /> : null}
        <Skeleton className="h-7 w-56" />
        {subtitle ? <Skeleton className="h-4 w-64" /> : null}
      </div>
      {action ? <Skeleton className="h-9 w-28 shrink-0" /> : null}
    </div>
  );
}

/** A card-shaped placeholder: a title bar plus a few body rows. */
export function CardSkeleton({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("border-border bg-surface flex flex-col gap-4 rounded-xl border p-5", className)}>
      <Skeleton className="h-5 w-40" />
      <div className="flex flex-col gap-3">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-full" />
        ))}
      </div>
    </div>
  );
}

/** A table-ish list of rows (used where the real page shows a run/design list). */
export function ListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="border-border bg-surface flex flex-col rounded-xl border">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "flex items-center justify-between gap-4 px-5 py-4",
            i > 0 && "border-border border-t",
          )}
        >
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <Skeleton className="h-6 w-16 shrink-0 rounded-full" />
        </div>
      ))}
    </div>
  );
}
