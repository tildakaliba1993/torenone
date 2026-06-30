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

export const SITE_TAGLINE = "The AI structural design agent";

export const SITE_DESCRIPTION =
  "TorenOne is an AI structural design agent for single-bay SANS steel portal frames. Describe the frame or upload a drawing — the agent drafts the design and runs every SANS check on a deterministic engineering kernel (members, connections, baseplates and footings), then hands you a clause-referenced, stamp-ready calculation package. You review, confirm and stamp. Minutes, not days.";

/** Compact description for social cards (keep well under ~200 chars). */
export const SITE_DESCRIPTION_SHORT =
  "An AI structural design agent for SANS steel portal frames. Describe it or upload a drawing; get a clause-referenced, stamp-ready calc package — computed by a deterministic kernel, confirmed by you.";

export const SITE_KEYWORDS = [
  "AI structural design agent",
  "AI structural engineer",
  "structural engineering software",
  "steel portal frame design",
  "drawing to structural design",
  "SANS 10162-1",
  "SANS 10160",
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
