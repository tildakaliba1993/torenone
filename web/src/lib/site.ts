/**
 * Canonical site metadata — the single source of truth for SEO across the app
 * (root metadata, OpenGraph/Twitter cards, sitemap, robots, manifest).
 *
 * The production origin can be overridden per environment with NEXT_PUBLIC_SITE_URL
 * (e.g. the Netlify preview URL); it falls back to the live custom domain.
 */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://torenone.com"
).replace(/\/$/, "");

export const SITE_NAME = "TorenOne";

export const SITE_TAGLINE = "The AI structural engineer";

export const SITE_DESCRIPTION =
  "TorenOne turns a plain-English brief into a code-checked, review-ready SANS calculation package for single-bay steel portal frames — members, connections, baseplates and footings, computed by a deterministic engineering kernel, not an AI guess. In minutes, not days.";

/** Compact description for social cards (keep well under ~200 chars). */
export const SITE_DESCRIPTION_SHORT =
  "Describe a steel portal frame; get a clause-referenced, stamp-ready SANS calculation package in minutes — computed by a deterministic engineering kernel, not an AI guess.";

export const SITE_KEYWORDS = [
  "structural engineering software",
  "steel portal frame design",
  "SANS 10162-1",
  "SANS 10160",
  "AI structural engineer",
  "portal frame calculator",
  "South Africa structural engineering",
  "steel frame design software",
  "calculation package",
  "Pr.Eng",
  "ECSA",
  "structural analysis",
];

/** Absolute URL helper for metadata fields that require a fully-qualified URL. */
export function absoluteUrl(path = "/"): string {
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
