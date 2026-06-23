import Link from "next/link";

import { ProductPreview } from "@/components/landing/product-preview";
import { Reveal } from "@/components/landing/reveal";
import { Button } from "@/components/ui/button";
import { APP_GUTTER } from "@/lib/layout";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Ambient hero glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 left-1/2 -z-10 h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,var(--accent),transparent)] opacity-[0.12] blur-2xl"
      />
      <div className={`${APP_GUTTER} grid items-center gap-12 py-20 lg:grid-cols-2 lg:gap-16 lg:py-28`}>
        {/* Graphic — left */}
        <Reveal className="order-last lg:order-first">
          <ProductPreview />
        </Reveal>

        {/* Copy — right */}
        <div className="flex flex-col gap-6">
          <Reveal>
            <span className="border-border bg-surface text-muted inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1 text-xs">
              <span className="bg-success size-1.5 rounded-full" />
              Built on the South African National Standards
            </span>
          </Reveal>

          <Reveal delay={80}>
            <h1 className="text-foreground text-4xl font-semibold tracking-tight sm:text-5xl xl:text-6xl">
              Describe the frame.
              <br />
              <span className="text-accent">TorenOne engineers it.</span>
            </h1>
          </Reveal>

          <Reveal delay={160}>
            <p className="text-muted max-w-xl text-base leading-7">
              TorenOne turns a plain-English brief into a fully code-checked SANS calc package —
              members, connections, baseplates and footings — computed by a{" "}
              <span className="text-foreground">deterministic engineering kernel</span>, not an AI
              guess. Review, confirm, and download a stamp-ready report in minutes.
            </p>
          </Reveal>

          <Reveal delay={240}>
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Button
                asChild
                size="lg"
                className="shadow-[0_0_36px_-8px_var(--accent)] transition-shadow hover:shadow-[0_0_48px_-6px_var(--accent)]"
              >
                <Link href="/signup">Start designing</Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="#how">See how it works</Link>
              </Button>
            </div>
          </Reveal>

          <Reveal delay={320}>
            <p className="text-subtle text-xs">
              Every number cited to a SANS clause · the registered engineer stays the authority.
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
