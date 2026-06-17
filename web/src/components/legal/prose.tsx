/** Minimal prose primitives for the legal pages (Terms §2.2, Privacy §2.3). */
import type { ReactNode } from "react";

export function LegalTitle({ title, updated }: { title: string; updated: string }) {
  return (
    <header className="flex flex-col gap-1">
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
      <p className="text-subtle text-xs">{updated}</p>
    </header>
  );
}

export function H2({ children }: { children: ReactNode }) {
  return <h2 className="text-foreground mt-4 text-base font-semibold">{children}</h2>;
}

export function P({ children }: { children: ReactNode }) {
  return <p className="text-muted">{children}</p>;
}

export function UL({ children }: { children: ReactNode }) {
  return <ul className="text-muted flex list-disc flex-col gap-1 pl-5">{children}</ul>;
}
