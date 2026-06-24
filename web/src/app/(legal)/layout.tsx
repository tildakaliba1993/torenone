import Link from "next/link";

import { Logo } from "@/components/brand/logo";
import { APP_GUTTER } from "@/lib/layout";

/**
 * Shared shell for the legal pages (Terms, Privacy/PoPIA, Refund & Cancellation Policy).
 * Uses the same 120px app gutter as the rest of the site: brand header + a small legal
 * sub-nav, then the document body.
 */
export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className={`${APP_GUTTER} flex flex-1 flex-col gap-8 py-16`}>
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="text-foreground flex items-center transition-opacity hover:opacity-80"
        >
          <Logo title="TorenOne — home" className="h-6 w-auto" />
        </Link>
        <nav aria-label="Legal" className="flex gap-4 text-sm">
          <Link href="/terms" className="text-muted hover:underline">
            Terms
          </Link>
          <Link href="/privacy" className="text-muted hover:underline">
            Privacy
          </Link>
          <Link href="/refunds" className="text-muted hover:underline">
            Refunds
          </Link>
        </nav>
      </div>

      <article className="legal-prose flex flex-col gap-4 text-sm leading-6">{children}</article>
    </main>
  );
}
