import type { Metadata } from "next";
import Link from "next/link";

import { Logo } from "@/components/brand/logo";

export const metadata: Metadata = {
  title: { default: "Sign in", template: "%s · TorenOne" },
  // Auth utility screens add no SEO value and shouldn't surface in search.
  robots: { index: false, follow: false },
};

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-6 py-12">
      {/* Ambient brand glow, matching the landing page */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 left-1/2 -z-10 h-[440px] w-[680px] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,var(--accent),transparent)] opacity-[0.10] blur-2xl"
      />
      <Link
        href="/"
        className="text-foreground mb-8 flex items-center transition-opacity hover:opacity-80"
      >
        <Logo title="TorenOne — home" className="h-8 w-auto" />
      </Link>
      <div className="w-full max-w-md">{children}</div>
      <p className="text-subtle mt-8 max-w-sm text-center text-xs leading-5">
        Every number cited to a SANS clause · the registered engineer stays the authority.
      </p>
    </main>
  );
}
