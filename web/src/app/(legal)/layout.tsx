import Link from "next/link";

/**
 * Shared shell for the legal pages (Terms §2.2, Privacy/PoPIA §2.3). Renders a
 * prominent DRAFT banner — these documents are drafts pending review by a qualified
 * attorney and are NOT yet legally binding.
 */
export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-16">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-accent text-sm hover:underline">
          ← TorenOne
        </Link>
        <div className="flex gap-4 text-sm">
          <Link href="/terms" className="text-muted hover:underline">
            Terms
          </Link>
          <Link href="/privacy" className="text-muted hover:underline">
            Privacy
          </Link>
        </div>
      </div>

      <div
        role="note"
        className="border-warning/40 bg-warning/10 text-warning rounded-md border px-4 py-3 text-sm"
      >
        <strong>Draft — not legal advice.</strong> This document is a working draft pending
        review by a qualified South African attorney. It is not yet legally binding and must
        not be relied upon until finalised. Placeholders in [brackets] need completion.
      </div>

      <article className="legal-prose flex flex-col gap-4 text-sm leading-6">{children}</article>
    </main>
  );
}
