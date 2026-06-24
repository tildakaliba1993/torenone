import type { MetadataRoute } from "next";

import { absoluteUrl } from "@/lib/site";

/**
 * sitemap.xml — the publicly indexable surface only (marketing landing, auth entry
 * points and the legal pages). Authenticated app routes are intentionally excluded
 * (they're also disallowed in robots.ts).
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return [
    { url: absoluteUrl("/"), lastModified, changeFrequency: "weekly", priority: 1 },
    { url: absoluteUrl("/pricing"), lastModified, changeFrequency: "monthly", priority: 0.9 },
    { url: absoluteUrl("/login"), lastModified, changeFrequency: "monthly", priority: 0.6 },
    { url: absoluteUrl("/signup"), lastModified, changeFrequency: "monthly", priority: 0.8 },
    { url: absoluteUrl("/terms"), lastModified, changeFrequency: "yearly", priority: 0.3 },
    { url: absoluteUrl("/privacy"), lastModified, changeFrequency: "yearly", priority: 0.3 },
    { url: absoluteUrl("/refunds"), lastModified, changeFrequency: "yearly", priority: 0.3 },
  ];
}
