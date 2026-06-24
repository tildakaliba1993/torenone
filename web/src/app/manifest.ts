import type { MetadataRoute } from "next";

import { SITE_DESCRIPTION_SHORT, SITE_NAME, SITE_TAGLINE } from "@/lib/site";

/**
 * Web App Manifest — lets the app be installed/added to a home screen and supplies the
 * brand icons + theme to the OS. Served at /manifest.webmanifest and auto-linked by Next.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: `${SITE_NAME} — ${SITE_TAGLINE}`,
    short_name: SITE_NAME,
    description: SITE_DESCRIPTION_SHORT,
    start_url: "/",
    display: "standalone",
    background_color: "#0e1116",
    theme_color: "#0e1116",
    icons: [
      { src: "/icon.svg", type: "image/svg+xml", sizes: "any" },
      { src: "/icon-192.png", type: "image/png", sizes: "192x192" },
      { src: "/icon-512.png", type: "image/png", sizes: "512x512" },
      {
        src: "/icon-512.png",
        type: "image/png",
        sizes: "512x512",
        purpose: "maskable",
      },
    ],
  };
}
