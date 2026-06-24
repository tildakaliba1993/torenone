"use client";

import { useState } from "react";

import Link from "next/link";

import { Logo } from "@/components/brand/logo";
import { LinkButton } from "@/components/ui/link-button";
import { APP_GUTTER } from "@/lib/layout";

const LINKS = [
  { href: "/#how", label: "How it works" },
  { href: "/#features", label: "Features" },
  { href: "/pricing", label: "Pricing" },
];

/** Sticky marketing nav: brand + section links + auth buttons, with a hamburger menu on mobile. */
export function LandingNav() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <header className="border-border/60 bg-background/70 sticky top-0 z-50 border-b backdrop-blur-md">
      <div className={`${APP_GUTTER} flex h-16 items-center justify-between gap-4`}>
        <Link
          href="/"
          onClick={close}
          className="text-foreground flex items-center transition-opacity hover:opacity-80"
        >
          <Logo title="TorenOne — home" className="h-7 w-auto" />
        </Link>

        <nav aria-label="Primary" className="text-muted hidden items-center gap-8 text-sm md:flex">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="hover:text-foreground transition-colors">
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
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

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mobile-nav"
          className="border-border text-foreground hover:bg-surface-raised inline-flex size-9 items-center justify-center rounded-md border transition-colors md:hidden"
        >
          <HamburgerIcon open={open} />
        </button>
      </div>

      {open ? (
        <nav
          id="mobile-nav"
          aria-label="Mobile"
          className="border-border/60 bg-background/95 border-t backdrop-blur-md md:hidden"
        >
          <div className={`${APP_GUTTER} flex flex-col gap-1 py-4`}>
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                onClick={close}
                className="text-muted hover:text-foreground hover:bg-surface-raised rounded-md px-2 py-2.5 text-sm transition-colors"
              >
                {l.label}
              </Link>
            ))}
            <div className="mt-3 flex flex-col gap-2">
              <LinkButton
                href="/login"
                variant="outline"
                onClick={close}
                className="w-full justify-center"
              >
                Sign in
              </LinkButton>
              <LinkButton href="/signup" onClick={close} className="w-full justify-center">
                Get started
              </LinkButton>
            </div>
          </div>
        </nav>
      ) : null}
    </header>
  );
}

function HamburgerIcon({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="size-5" fill="none" aria-hidden>
      {open ? (
        <path
          d="M6 6l12 12M18 6L6 18"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      ) : (
        <path
          d="M4 7h16M4 12h16M4 17h16"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}
