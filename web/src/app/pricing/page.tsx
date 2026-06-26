import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { LandingNav } from "@/components/landing/landing-nav";
import { Reveal } from "@/components/landing/reveal";
import { SiteFooter } from "@/components/landing/sections";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { APP_GUTTER } from "@/lib/layout";
import { CARD_SURFACE } from "@/lib/styles";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "TorenOne pricing — free to calculate and check; pay only for the stamp-ready SANS calc package. R250 per calc package pay-as-you-go, or R1,650/mo for your whole firm. No per-seat licences.",
  alternates: { canonical: "/pricing" },
};

const CARD = `${CARD_SURFACE} flex h-full flex-col gap-5 rounded-2xl p-7`;

type Plan = {
  name: string;
  price: ReactNode;
  cadence?: string;
  tagline: string;
  features: string[];
  cta: { label: string; href: string };
  featured?: boolean;
  footnote?: string;
};

const PLANS: Plan[] = [
  {
    name: "Free",
    price: "R0",
    tagline: "Calculate and check, free. See the engine work before you pay a cent.",
    features: [
      "Describe a frame and run the full SANS kernel",
      "On-screen results — member sections, utilisations, tonnage",
      "Unlimited Check mode (verify your own sections)",
      "BMD/SFD diagrams and the deterministic audit trail",
    ],
    cta: { label: "Start free", href: "/signup" },
  },
  {
    name: "Pay as you go",
    price: "R250",
    cadence: "per calc package",
    tagline: "Pay only when you download a stamp-ready calculation package.",
    features: [
      "Everything in Free",
      "Full clause-referenced calc-package PDF",
      "Members, connections, baseplates & footings",
      "Re-downloads and minor revisions of that design — free",
    ],
    cta: { label: "Start free", href: "/signup" },
    featured: true,
  },
  {
    name: "Firm",
    price: "R1,650",
    cadence: "per month",
    tagline: "Your whole firm, unlimited. Less than one incumbent seat.",
    features: [
      "Unlimited calc packages",
      "Unlimited seats across your firm",
      "Full project & design history",
      "Priority compute and support",
    ],
    cta: { label: "Get the Firm plan", href: "/dashboard?subscribe=firm" },
  },
];

export default function PricingPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <LandingNav />
      <main className="flex-1">
        <section className={`${APP_GUTTER} py-16 sm:py-20`}>
          <Reveal className="mx-auto flex max-w-2xl flex-col items-center gap-4 text-center">
            <p className="text-accent text-xs tracking-widest uppercase">Pricing</p>
            <h1 className="text-foreground text-4xl font-semibold tracking-tight sm:text-5xl">
              Free to calculate. Pay for the calc package.
            </h1>
            <p className="text-muted max-w-xl text-base leading-7">
              We charge for the finished work — not for a seat. Run the engine, check your sections
              and see the numbers for free; pay only when you need the stamp-ready calculation
              package to submit. Marginal, transparent, and a fraction of an incumbent licence.
            </p>
          </Reveal>

          <div className="mx-auto mt-14 grid max-w-5xl gap-5 lg:grid-cols-3">
            {PLANS.map((plan, i) => (
              <Reveal key={plan.name} delay={i * 90}>
                <div className={`${CARD} ${plan.featured ? "ring-accent/40 ring-1" : ""}`}>
                  <div className="flex items-center justify-between">
                    <h2 className="text-foreground text-lg font-medium">{plan.name}</h2>
                    {plan.featured ? (
                      <span className="border-accent/40 text-accent bg-accent/10 rounded-full border px-2.5 py-0.5 text-xs">
                        Most popular
                      </span>
                    ) : null}
                  </div>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-foreground text-4xl font-semibold tracking-tight">
                      {plan.price}
                    </span>
                    {plan.cadence ? (
                      <span className="text-subtle text-sm">{plan.cadence}</span>
                    ) : null}
                  </div>
                  <p className="text-muted text-sm leading-6">{plan.tagline}</p>
                  <ul className="flex flex-col gap-2">
                    {plan.features.map((f) => (
                      <li key={f} className="text-muted flex items-start gap-2 text-sm leading-6">
                        <span className="text-accent mt-0.5 shrink-0">✓</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-auto flex flex-col gap-2">
                    <LinkButton
                      href={plan.cta.href}
                      variant={plan.featured ? "primary" : "outline"}
                      className="w-full justify-center"
                    >
                      {plan.cta.label}
                    </LinkButton>
                    {plan.footnote ? (
                      <p className="text-subtle text-center text-xs leading-5">{plan.footnote}</p>
                    ) : null}
                  </div>
                </div>
              </Reveal>
            ))}
          </div>

          {/* Founding firms — invitation/pilot offer, no card */}
          <Reveal className="mx-auto mt-10 max-w-3xl">
            <div className={`${CARD_SURFACE} ring-accent/30 rounded-2xl p-7 text-center ring-1 sm:p-9`}>
              <p className="text-accent text-xs tracking-widest uppercase">Founding firms</p>
              <h2 className="text-foreground mt-3 text-xl font-semibold tracking-tight sm:text-2xl">
                Validate against your past projects — free, no card.
              </h2>
              <p className="text-muted mx-auto mt-3 max-w-xl text-sm leading-7">
                We’re onboarding a small group of South African firms as founding partners. Run your
                finished projects through TorenOne <span className="text-foreground">free for a
                month — no card needed</span>, then lock in{" "}
                <span className="text-foreground">R999/mo for your first year</span> (vs R1,650
                standard). You only enter a card if and when you choose to continue.
              </p>
              <div className="mt-6">
                <Button asChild variant="outline">
                  <a href="mailto:admin@torenone.com?subject=TorenOne%20founding%20firm">
                    Apply to be a founding firm
                  </a>
                </Button>
              </div>
            </div>
          </Reveal>

          <Reveal className="mx-auto mt-8 max-w-5xl">
            <p className="text-subtle text-center text-xs leading-5">
              Prices in South African Rand, excl. VAT where applicable. Payments are processed by our
              reseller (Merchant of Record). See our{" "}
              <Link href="/refunds" className="hover:text-foreground underline">
                Refund &amp; Cancellation Policy
              </Link>
              .
            </p>
          </Reveal>
        </section>

        {/* Comparison / why */}
        <section className="border-border/60 border-y">
          <div className={`${APP_GUTTER} py-16`}>
            <Reveal className="mx-auto max-w-3xl text-center">
              <h2 className="text-foreground text-2xl font-semibold tracking-tight sm:text-3xl">
                One firm subscription costs less than a single incumbent seat
              </h2>
              <p className="text-muted mx-auto mt-4 max-w-2xl text-base leading-7">
                Legacy packages charge per engineer, per year, whether or not you finish a design.
                TorenOne charges for the outcome — the calc package — so the price tracks the value:
                roughly two days of junior-engineer time saved on every portal frame.
              </p>
            </Reveal>
          </div>
        </section>

        {/* FAQ */}
        <section className={`${APP_GUTTER} py-16 sm:py-20`}>
          <div className="mx-auto grid max-w-4xl gap-5 sm:grid-cols-2">
            {FAQ.map((item, i) => (
              <Reveal key={item.q} delay={(i % 2) * 80}>
                <div className={`${CARD_SURFACE} h-full rounded-2xl p-6`}>
                  <h3 className="text-foreground text-base font-medium">{item.q}</h3>
                  <p className="text-muted mt-2 text-sm leading-6">{item.a}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* Final CTA — mirrors the landing page's closing CTA */}
        <section className="relative overflow-hidden">
          <div
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-1/2 -z-10 h-[420px] w-[760px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(closest-side,var(--accent),transparent)] opacity-[0.12] blur-2xl"
          />
          <div
            className={`${APP_GUTTER} flex flex-col items-center gap-7 py-24 text-center sm:py-28`}
          >
            <Reveal>
              <h2 className="text-foreground max-w-3xl text-3xl font-semibold tracking-tight sm:text-5xl">
                Run your next frame — free.
              </h2>
            </Reveal>
            <Reveal delay={100}>
              <p className="text-muted max-w-xl text-base leading-7">
                Describe a frame, run the SANS kernel and see the sized sections and utilisations at no
                cost. You only pay when you download the stamp-ready calc package — no seats, no
                licences, no lock-in.
              </p>
            </Reveal>
            <Reveal delay={180}>
              <LinkButton
                href="/signup"
                size="lg"
                className="shadow-[0_0_44px_-8px_var(--accent)] transition-shadow hover:shadow-[0_0_56px_-6px_var(--accent)]"
              >
                Create your free account
              </LinkButton>
            </Reveal>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

const FAQ: { q: string; a: ReactNode }[] = [
  {
    q: "Do I pay every time I run a design?",
    a: "No. Running the kernel, viewing results and Check mode are free and unlimited. You only pay when you download the stamp-ready calc-package PDF for a design.",
  },
  {
    q: "What counts as one calc package?",
    a: "One finalised design. Once you've paid for a design, re-downloads and minor revisions of that same design are free — you're never charged twice for the same frame.",
  },
  {
    q: "Is it really per firm, not per seat?",
    a: "Yes. The Firm plan covers everyone at your practice. We don't sell per-engineer licences — that's the incumbent model we're replacing.",
  },
  {
    q: "Who is the responsible engineer?",
    a: "You are. TorenOne is a computational aid; every output must be reviewed, verified and stamped by an ECSA-registered person who accepts professional responsibility.",
  },
  {
    q: "Can I cancel anytime?",
    a: (
      <>
        Yes — cancel the Firm subscription whenever you like and you won&rsquo;t be charged again. See
        our <Link href="/refunds" className="text-accent hover:underline">Refund &amp; Cancellation Policy</Link>.
      </>
    ),
  },
  {
    q: "How do payments work?",
    a: "Payments are handled by our Merchant of Record, who processes the transaction and issues your invoice. Your card statement will show their name.",
  },
];
