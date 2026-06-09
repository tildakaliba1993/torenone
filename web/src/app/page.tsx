import { StatusBadge } from "@/components/status-badge";

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
        <button
          type="button"
          className="bg-primary text-primary-foreground hover:bg-primary-hover focus-visible:ring-ring rounded px-4 py-2 text-sm font-medium focus-visible:ring-2 focus-visible:outline-none"
        >
          Start a design
        </button>
        <a href="#" className="text-accent text-sm hover:underline">
          View a sample calc package
        </a>
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
    </main>
  );
}
