/**
 * Uniform horizontal page gutter for the authenticated app shell.
 * 120px left/right on desktop (per design), with smaller responsive fallbacks so the
 * app stays usable on narrow screens. Applied once in `(app)/layout.tsx` (header + content)
 * so every authed page has identical margins — pages must NOT add their own max-w/px clamp.
 * (Auth pages are intentionally exempt — they use a centered narrow card.)
 */
export const APP_GUTTER = "w-full px-6 sm:px-10 lg:px-[120px]";
