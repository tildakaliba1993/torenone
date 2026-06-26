import Link from "next/link";
import type { ReactNode } from "react";

import { Logo } from "@/components/brand/logo";
import { Reveal } from "@/components/landing/reveal";
import { LinkButton } from "@/components/ui/link-button";
import { APP_GUTTER } from "@/lib/layout";
import { CARD_SURFACE } from "@/lib/styles";

/** Shared card surface + hover used by EVERY card on the site (landing + pricing). */
const LANDING_CARD = CARD_SURFACE;

/* ----------------------------------------------------------------- Trust bar */

const STANDARDS = ["SANS 10162-1:2011", "SANS 10160 series", "SANS 10100-1", "EN 10025-2"];

export function TrustBar() {
  return (
    <section className="border-border/60 border-y">
      <div className={`${APP_GUTTER} flex flex-col items-center gap-6 py-10`}>
        <Reveal>
          <p className="text-subtle text-center text-xs tracking-wide uppercase">
            Computed against the standards your Pr.Eng already trusts
          </p>
        </Reveal>
        <Reveal delay={80}>
          <div className="flex flex-wrap items-center justify-center gap-3">
            {STANDARDS.map((s) => (
              <span
                key={s}
                className="border-border bg-surface text-muted rounded-lg border px-4 py-2 font-mono text-xs"
              >
                {s}
              </span>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------- Stats */

const STATS = [
  { value: "Minutes", caption: "from a brief to a calc package — not days" },
  { value: "100%", caption: "clause-referenced and traceable to SANS" },
  { value: "0", caption: "engineering numbers guessed by AI" },
];

export function Stats() {
  return (
    <section className={`${APP_GUTTER} py-20 sm:py-24`}>
      <div className="grid gap-10 sm:grid-cols-3">
        {STATS.map((s, i) => (
          <Reveal key={s.value} delay={i * 100} className="text-center">
            <p className="text-accent text-5xl font-semibold tracking-tight sm:text-6xl">{s.value}</p>
            <p className="text-muted mx-auto mt-3 max-w-[15rem] text-sm leading-6">{s.caption}</p>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ----------------------------------------------------------------- Features */

const FEATURES = [
  {
    title: "Plain-English brief",
    body: "Describe your frame in a sentence. The AI extracts a typed spec — and is architecturally forbidden from guessing an engineering number.",
    icon: <PathIcon d="M4 6h16M4 12h10M4 18h7" />,
  },
  {
    title: "Deterministic SANS kernel",
    body: "Loads, analysis and every code check are computed by a tested, version-pinned engine. Same inputs, same answer — every single time.",
    icon: <PathIcon d="m12 3 8 4v5c0 4.5-3.2 7.6-8 9-4.8-1.4-8-4.5-8-9V7z" />,
  },
  {
    title: "The whole frame",
    body: "Members, eaves & apex moment connections, column baseplates and pad footings — sized and checked end-to-end, not just the rafters.",
    icon: <PathIcon d="M4 20V8l8-5 8 5v12M4 20h16M9 20v-6h6v6" />,
  },
  {
    title: "Stamp-ready calc package",
    body: "A clause-referenced PDF with diagrams, show-your-working and an audit fingerprint. Your engineer reviews, verifies and stamps.",
    icon: <PathIcon d="M7 3h7l4 4v14H7zM14 3v4h4M9.5 13l2 2 3.5-4" />,
  },
  {
    title: "Check mode",
    body: "Already chose your sections? Verify them against every SANS clause in seconds — the lower-liability path where you stay the author.",
    icon: <PathIcon d="m5 12 4 4 10-10" />,
  },
  {
    title: "Built for firms",
    body: "Multi-tenant with strict per-firm isolation, owner-invited teams and a full run history. Your projects and reports stay yours.",
    icon: <PathIcon d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6m8 10v-2a4 4 0 0 0-3-3.9M16 5.1A3 3 0 0 1 16 11" />,
  },
];

export function Features() {
  return (
    <section id="features" className={`${APP_GUTTER} scroll-mt-20 py-20 sm:py-24`}>
      <Reveal>
        <SectionHeading
          eyebrow="What you get"
          title="Built for real engineering work"
          subtitle="Not a chatbot that sounds confident — a structural engine that does the work and shows its working."
        />
      </Reveal>
      <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <Reveal key={f.title} delay={(i % 3) * 80}>
            <div className={`${LANDING_CARD} group h-full rounded-2xl p-6`}>
              <IconTile>{f.icon}</IconTile>
              <h3 className="text-foreground mt-5 text-lg font-medium">{f.title}</h3>
              <p className="text-muted mt-2 text-sm leading-6">{f.body}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* -------------------------------------------------------------- How it works */

const STEPS = [
  {
    n: "1",
    title: "Describe",
    body: "Open TorenOne and describe the frame in plain English. The AI turns it into a typed, reviewable specification — never inventing a value.",
  },
  {
    n: "2",
    title: "Review & confirm",
    body: "Check the inputs on an editable form with a live elevation sketch. You stay the authoritative pilot — nothing computes until you confirm.",
  },
  {
    n: "3",
    title: "Get the calc package",
    body: "The deterministic kernel runs the full SANS design — loads, analysis, members, connections, foundations — and hands you a stamp-ready PDF.",
  },
];

export function HowItWorks() {
  return (
    <section id="how" className="border-border/60 scroll-mt-20 border-y">
      <div className={`${APP_GUTTER} py-20 sm:py-24`}>
        <Reveal>
          <SectionHeading
            eyebrow="How it works"
            title="From a sentence to a stamp-ready package"
            subtitle="Three steps. Minutes, not days."
          />
        </Reveal>
        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <Reveal key={s.n} delay={i * 110}>
              <div className={`${LANDING_CARD} h-full rounded-2xl p-7`}>
                <span className="border-accent/40 text-accent bg-accent/10 flex size-10 items-center justify-center rounded-full border font-mono text-sm font-semibold">
                  {s.n}
                </span>
                <h3 className="text-foreground mt-5 text-lg font-medium">{s.title}</h3>
                <p className="text-muted mt-2 text-sm leading-6">{s.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* --------------------------------------------------------- Why it's different */

export function WhyDifferent() {
  return (
    <section id="why" className={`${APP_GUTTER} scroll-mt-20 py-20 sm:py-24`}>
      <Reveal>
        <div className={`${LANDING_CARD} relative overflow-hidden rounded-3xl p-10 sm:p-14`}>
          <div
            aria-hidden
            className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-[radial-gradient(closest-side,var(--accent),transparent)] opacity-10 blur-2xl"
          />
          <p className="text-accent text-xs tracking-widest uppercase">Why it&rsquo;s different</p>
          <h2 className="text-foreground mt-4 max-w-3xl text-2xl font-semibold tracking-tight sm:text-3xl">
            You don&rsquo;t need another chatbot.
            <br className="hidden sm:block" /> You need calcs you can stamp.
          </h2>
          <p className="text-muted mt-5 max-w-3xl text-base leading-7">
            Portal frames have been designed the same way for twenty years — by hand, in
            spreadsheets and desktop software built in the 2000s. Slow, manual, impossible to scale.
            And generic AI can&rsquo;t replace it: it guesses, and{" "}
            <span className="text-foreground">you can&rsquo;t stamp a guess</span>.
          </p>
          <p className="text-muted mt-4 max-w-3xl text-base leading-7">
            TorenOne is built <span className="text-foreground">AI-native from the ground up</span>,
            not a chatbot bolted onto a legacy interface. Your plain-English brief goes to a
            deterministic, version-pinned structural engine — validated clause-by-clause against the
            SANS standards. Reproducible. Cited. Stamp-ready. It&rsquo;s the workflow the incumbents
            can&rsquo;t retrofit onto twenty-year-old software, and the one your firm can finally
            trust. <span className="text-foreground">Accuracy is the product.</span>
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            {[
              "AI-native — not bolted onto a 2000s UI",
              "Deterministic — you can stamp it",
              "Replaces the spreadsheet, not your judgement",
            ].map((t) => (
              <span
                key={t}
                className="border-border bg-surface-raised text-muted rounded-full border px-3 py-1.5 text-xs"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      </Reveal>
    </section>
  );
}

/* ----------------------------------------------------------------- Final CTA */

export function FinalCta() {
  return (
    <section className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[420px] w-[760px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(closest-side,var(--accent),transparent)] opacity-[0.12] blur-2xl"
      />
      <div className={`${APP_GUTTER} flex flex-col items-center gap-7 py-24 text-center sm:py-32`}>
        <Reveal>
          <h2 className="text-foreground max-w-3xl text-3xl font-semibold tracking-tight sm:text-5xl">
            Stop hand-cranking portal frames.
          </h2>
        </Reveal>
        <Reveal delay={100}>
          <p className="text-muted max-w-xl text-base leading-7">
            Built for South African structural engineering firms designing single-bay steel portal
            frames. Lead with Check mode, scale with full Design mode.
          </p>
        </Reveal>
        <Reveal delay={180}>
          <LinkButton
            href="/signup"
            size="lg"
            className="shadow-[0_0_44px_-8px_var(--accent)] transition-shadow hover:shadow-[0_0_56px_-6px_var(--accent)]"
          >
            Start designing — free
          </LinkButton>
        </Reveal>
        <Reveal delay={260}>
          <p className="text-subtle text-sm">
            Now onboarding pilot firms — validate against your past projects free, no credit card.{" "}
            <Link href="/pricing" className="text-accent hover:underline">
              See pilot pricing →
            </Link>
          </p>
        </Reveal>
      </div>
    </section>
  );
}

/* ----------------------------------------------------------------- Footer */

export function SiteFooter() {
  return (
    <footer className="border-border/60 border-t">
      <div className={`${APP_GUTTER} flex flex-col items-center gap-3 py-12 text-center`}>
        <Link href="/" className="text-foreground transition-opacity hover:opacity-80">
          <Logo title="TorenOne — home" className="mb-1 h-7 w-auto" />
        </Link>
        <p className="text-muted text-sm">
          TorenOne — the AI structural engineer for SANS steel portal frames.
        </p>
        <p className="text-subtle text-xs">© 2026 TorenOne. All rights reserved.</p>
        <div className="text-subtle mt-1 flex flex-wrap items-center justify-center gap-4 text-xs">
          <Link href="/pricing" className="hover:text-foreground transition-colors">
            Pricing
          </Link>
          <span aria-hidden>·</span>
          <Link href="/terms" className="hover:text-foreground transition-colors">
            Terms
          </Link>
          <span aria-hidden>·</span>
          <Link href="/privacy" className="hover:text-foreground transition-colors">
            Privacy
          </Link>
          <span aria-hidden>·</span>
          <Link href="/refunds" className="hover:text-foreground transition-colors">
            Refunds
          </Link>
        </div>
      </div>
    </footer>
  );
}

/* ------------------------------------------------------------ small helpers */

function SectionHeading({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex max-w-2xl flex-col gap-3">
      <p className="text-accent text-xs tracking-widest uppercase">{eyebrow}</p>
      <h2 className="text-foreground text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h2>
      <p className="text-muted text-base leading-7">{subtitle}</p>
    </div>
  );
}

function IconTile({ children }: { children: ReactNode }) {
  return (
    <span className="border-accent/30 bg-accent/10 text-accent flex size-11 items-center justify-center rounded-xl border transition-colors group-hover:bg-[color-mix(in_srgb,var(--accent)_18%,transparent)]">
      {children}
    </span>
  );
}

function PathIcon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" className="size-5" fill="none" aria-hidden>
      <path d={d} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
