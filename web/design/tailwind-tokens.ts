/**
 * TorenOne Tailwind theme preset — maps the canonical design tokens
 * (tools/torenone_tokens/tokens.py, mirrored in web/design/tokens.css) to Tailwind
 * colour utilities. Import into the Next.js tailwind.config when the web app is
 * scaffolded (Task 0.3 / Phase 6).
 *
 * Colours reference the CSS variables so the single source of truth stays the token file.
 */
import type { Config } from "tailwindcss";

export const torenoneColors = {
  bg: "var(--bg)",
  surface: "var(--surface)",
  "surface-raised": "var(--surface-raised)",
  border: "var(--border)",
  "border-strong": "var(--border-strong)",
  text: "var(--text)",
  "text-muted": "var(--text-muted)",
  "text-subtle": "var(--text-subtle)",
  primary: {
    DEFAULT: "var(--primary)",
    hover: "var(--primary-hover)",
    active: "var(--primary-active)",
    foreground: "var(--on-primary)",
  },
  accent: "var(--accent)",
  ring: "var(--ring)",
  success: "var(--success)",
  danger: "var(--danger)",
  warning: "var(--warning)",
} as const;

export const torenonePreset: Partial<Config> = {
  theme: {
    extend: {
      colors: torenoneColors,
      borderRadius: { sm: "4px", DEFAULT: "6px", md: "6px", lg: "8px" },
      fontFamily: {
        sans: ["Geist Sans", "Inter", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
};

export default torenonePreset;
