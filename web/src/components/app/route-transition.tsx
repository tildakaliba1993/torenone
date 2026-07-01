"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

/**
 * Makes in-app navigation feel alive instead of abrupt.
 *
 * Two coordinated touches, keyed on the committed route:
 *   1. a slim accent bar sweeps across the top when a new route arrives (a "page changed" flourish);
 *   2. the incoming page content fades in.
 *
 * The real "it's loading" feedback during the wait comes from each route's `loading.tsx` skeleton
 * (Next streams it instantly); this just polishes the arrival. Both respect prefers-reduced-motion
 * (the animations collapse to no-ops in globals.css).
 */
export function RouteTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sweeping, setSweeping] = useState(false);
  const firstRender = useRef(true);

  useEffect(() => {
    // Don't flash the bar on the very first paint — only on subsequent navigations.
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    setSweeping(true);
    const timer = setTimeout(() => setSweeping(false), 700);
    return () => clearTimeout(timer);
  }, [pathname]);

  return (
    <>
      {sweeping ? (
        <div className="pointer-events-none fixed inset-x-0 top-0 z-50 h-0.5 overflow-hidden">
          <div className="bg-accent animate-indeterminate h-full w-full origin-left rounded-full shadow-[0_0_8px_var(--color-accent)]" />
        </div>
      ) : null}
      <div key={pathname} className="animate-fade-in">
        {children}
      </div>
    </>
  );
}
