import type { Metadata } from "next";
import Link from "next/link";

import { LandingNav } from "@/components/landing/landing-nav";
import { SiteFooter } from "@/components/landing/sections";
import { LinkButton } from "@/components/ui/link-button";
import { APP_GUTTER } from "@/lib/layout";
import { REDBOOK_GROUPS, REDBOOK_SCOPE, REDBOOK_SUMMARY } from "@/lib/redbook";
import { absoluteUrl } from "@/lib/site";
import { CARD_SURFACE } from "@/lib/styles";

export const metadata: Metadata = {
  title: "Red Book validation — benchmarked against the SAISC Red Book",
  description:
    "TorenOne's deterministic engineering kernel, benchmarked against worked examples and tables " +
    "from the SAISC Southern African Steel Construction Handbook (the Red Book). See our computed " +
    "values beside the Red Book's published values.",
  alternates: { canonical: absoluteUrl("/validation") },
};

function deltaTone(delta: string): string {
  return delta === "match"
    ? "text-accent"
    : "text-muted";
}

export default function ValidationPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <LandingNav />
      <main className={`${APP_GUTTER} flex-1 py-16 sm:py-20`}>
        {/* Heading */}
        <header className="flex max-w-3xl flex-col gap-4">
          <p className="text-accent text-xs tracking-widest uppercase">Accuracy you can check</p>
          <h1 className="text-foreground text-3xl font-semibold tracking-tight sm:text-4xl">
            Benchmarked against the SAISC Red Book
          </h1>
          <p className="text-muted text-base leading-7">
            TorenOne&rsquo;s engineering kernel is deterministic — same inputs, same answer, every
            time. To prove it, we run it against worked examples and tables from the{" "}
            <span className="text-foreground">{REDBOOK_SUMMARY.reference}</span> and check every
            number. Below are our kernel&rsquo;s <span className="text-foreground">computed</span>{" "}
            values beside the Red Book&rsquo;s <span className="text-foreground">published</span>{" "}
            values, drawn from <span className="text-foreground">{REDBOOK_SUMMARY.checks} automated,
            must-pass checks</span> that run on every change.
          </p>
        </header>

        {/* Scope + responsibility */}
        <div className={`${CARD_SURFACE} mt-8 max-w-3xl rounded-2xl p-6`}>
          <p className="text-foreground text-sm font-medium">What this covers</p>
          <p className="text-muted mt-2 text-sm leading-6">{REDBOOK_SCOPE.covered}</p>
          <p className="text-muted mt-3 text-sm leading-6">
            <span className="text-foreground">Still being validated:</span> {REDBOOK_SCOPE.ongoing}
          </p>
          <p className="text-subtle mt-4 border-t border-border pt-4 text-xs leading-5">
            TorenOne is a computational aid, not a certifying authority. Every calculation package is
            reviewed, verified and stamped by your registered (Pr.Eng / ECSA) engineer, who remains
            the responsible agent for the design.
          </p>
        </div>

        {/* Benchmark tables */}
        <div className="mt-12 flex flex-col gap-8">
          {REDBOOK_GROUPS.map((group) => (
            <section key={group.title} className={`${CARD_SURFACE} rounded-2xl p-6 sm:p-7`}>
              <h2 className="text-foreground text-lg font-medium">{group.title}</h2>
              <p className="text-subtle mt-1 text-xs">{group.basis}</p>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[34rem] border-collapse text-sm">
                  <thead>
                    <tr className="text-subtle border-b border-border text-left text-xs uppercase tracking-wide">
                      <th className="py-2 pr-4 font-medium">Check</th>
                      <th className="py-2 pr-4 font-medium">Red Book</th>
                      <th className="py-2 pr-4 font-medium">TorenOne kernel</th>
                      <th className="py-2 font-medium">Δ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.rows.map((row) => (
                      <tr key={row.check} className="border-b border-border/50 last:border-0">
                        <td className="text-muted py-2.5 pr-4">{row.check}</td>
                        <td className="text-foreground py-2.5 pr-4 font-mono text-xs whitespace-nowrap">
                          {row.redbook}
                        </td>
                        <td className="text-foreground py-2.5 pr-4 font-mono text-xs whitespace-nowrap">
                          {row.kernel}
                        </td>
                        <td className={`py-2.5 font-mono text-xs whitespace-nowrap ${deltaTone(row.delta)}`}>
                          {row.delta}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
        </div>

        {/* Verify it yourself */}
        <section className={`${CARD_SURFACE} mt-8 max-w-3xl rounded-2xl p-6`}>
          <h2 className="text-foreground text-lg font-medium">Don&rsquo;t take our word for it</h2>
          <p className="text-muted mt-2 text-sm leading-6">
            Every row above is a committed, automated test. They run in our continuous-integration
            pipeline on every change, so a kernel update can never silently drift from the Red Book
            without a test going red. The numbers here are our kernel&rsquo;s output, not hand-typed
            targets.
          </p>
        </section>

        {/* CTA */}
        <div className="mt-12 flex flex-col items-start gap-4">
          <LinkButton href="/signup" size="lg">
            Try it on your own frame — free
          </LinkButton>
          <p className="text-subtle text-sm">
            Free to calculate and check.{" "}
            <Link href="/pricing" className="text-accent hover:underline">
              See pricing →
            </Link>
          </p>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
