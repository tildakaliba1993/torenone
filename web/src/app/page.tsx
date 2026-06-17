import Link from "next/link";

import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-10 px-6 py-24">
      <header className="flex flex-col gap-3">
        <span className="text-accent font-mono text-xs tracking-widest uppercase">
          TorenOne
        </span>
        <h1 className="text-3xl font-semibold tracking-tight">
          The AI structural engineer
        </h1>
        <p className="text-muted max-w-xl text-sm leading-6">
          Describe a steel portal frame; get a code-checked, review-ready SANS
          calculation package in minutes. Every number is computed by a
          deterministic, tested kernel — the AI never guesses.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-4">
        <Button asChild size="lg">
          <Link href="/signup">Start a design</Link>
        </Button>
        <Link href="/login" className="text-accent text-sm hover:underline">
          Sign in
        </Link>
      </div>

      <section className="border-border bg-surface-raised flex flex-col gap-3 rounded-lg border p-5">
        <span className="text-subtle text-xs tracking-wide uppercase">
          Design-system check — status is never colour-only
        </span>
        <div className="flex flex-wrap gap-3">
          <StatusBadge status="pass">Moment 0.78</StatusBadge>
          <StatusBadge status="review">Deflection 0.96</StatusBadge>
          <StatusBadge status="fail">LTB 1.14</StatusBadge>
        </div>
      </section>

      <footer className="text-subtle mt-auto flex gap-4 text-xs">
        <Link href="/terms" className="hover:underline">
          Terms
        </Link>
        <Link href="/privacy" className="hover:underline">
          Privacy
        </Link>
      </footer>
    </main>
  );
}
