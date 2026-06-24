import type { MetadataRoute } from "next";

import { absoluteUrl } from "@/lib/site";

/**
 * robots.txt — allow crawling of the public marketing + legal surface, but keep the
 * authenticated app (projects, dashboard, account) and auth utility routes out of the
 * index. Those pages require a session and only redirect crawlers to /login.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/projects",
        "/dashboard",
        "/reset-password",
        "/forgot-password",
        "/auth/",
        "/design-system",
        "/api/",
      ],
    },
    sitemap: absoluteUrl("/sitemap.xml"),
    host: absoluteUrl("/"),
  };
}
