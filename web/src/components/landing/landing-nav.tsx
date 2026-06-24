import Link from "next/link";

import { Logo } from "@/components/brand/logo";
import { LinkButton } from "@/components/ui/link-button";
import { APP_GUTTER } from "@/lib/layout";

/** Sticky marketing nav: brand + section links + auth buttons (Sign in / Get started). */
export function LandingNav() {
  return (
    <header className="border-border/60 bg-background/70 sticky top-0 z-50 border-b backdrop-blur-md">
      <div className={`${APP_GUTTER} flex h-16 items-center justify-between gap-4`}>
        <Link
          href="/"
          className="text-foreground flex items-center transition-opacity hover:opacity-80"
        >
          <Logo title="TorenOne — home" className="h-7 w-auto" />
        </Link>

        <nav className="text-muted hidden items-center gap-8 text-sm md:flex">
          <Link href="/#how" className="hover:text-foreground transition-colors">
            How it works
          </Link>
          <Link href="/#features" className="hover:text-foreground transition-colors">
            Features
          </Link>
          <Link href="/pricing" className="hover:text-foreground transition-colors">
            Pricing
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          <LinkButton href="/login" variant="ghost" size="sm">
            Sign in
          </LinkButton>
          <LinkButton
            href="/signup"
            size="sm"
            className="shadow-[0_0_28px_-6px_var(--accent)] transition-shadow hover:shadow-[0_0_36px_-4px_var(--accent)]"
          >
            Get started
          </LinkButton>
        </div>
      </div>
    </header>
  );
}
