import Link from "next/link";

import { Button } from "@/components/ui/button";

/**
 * Prev/Next pagination that preserves the current search/filter/sort query params.
 * Server component — renders Links; the page re-queries the next range server-side.
 */
export function Pagination({
  page,
  pageCount,
  total,
  params,
}: {
  page: number;
  pageCount: number;
  total: number;
  params: Record<string, string | undefined>;
}) {
  if (pageCount <= 1) return null;

  const href = (p: number) => {
    const sp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v && k !== "page") sp.set(k, v);
    }
    sp.set("page", String(p));
    return `?${sp.toString()}`;
  };

  return (
    <div className="flex items-center justify-between gap-4 pt-2">
      <span className="text-muted text-xs">
        Page {page} of {pageCount} · {total} total
      </span>
      <div className="flex gap-2">
        {page > 1 ? (
          <Button asChild variant="outline" size="sm">
            <Link href={href(page - 1)} scroll={false}>
              Previous
            </Link>
          </Button>
        ) : (
          <Button variant="outline" size="sm" disabled>
            Previous
          </Button>
        )}
        {page < pageCount ? (
          <Button asChild variant="outline" size="sm">
            <Link href={href(page + 1)} scroll={false}>
              Next
            </Link>
          </Button>
        ) : (
          <Button variant="outline" size="sm" disabled>
            Next
          </Button>
        )}
      </div>
    </div>
  );
}
