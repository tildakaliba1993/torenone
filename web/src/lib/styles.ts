/**
 * Canonical card surface + hover used by EVERY presentational card across the site
 * (landing sections and the pricing page), so the interaction — lift, border, accent
 * glow and 300ms timing — is identical everywhere. Radius and padding are applied
 * per-use (e.g. `rounded-2xl p-6`), never the hover/transition.
 */
export const CARD_SURFACE =
  "border-border bg-surface border transition-all duration-300 hover:-translate-y-1 hover:border-[var(--border-strong)] hover:shadow-[0_0_40px_-18px_var(--accent)]";
