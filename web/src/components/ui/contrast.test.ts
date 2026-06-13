import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

/**
 * WCAG-AA contrast assertions for the design-system tokens (Design §B.8, PRD FR-19).
 * Reads the hex values straight from globals.css so the check tracks the real tokens.
 * Mirrors the kernel-side Python contrast gate (tools/tests/test_contrast.py).
 */
const css = fs.readFileSync(path.resolve(process.cwd(), "src/app/globals.css"), "utf8");

function token(name: string): string {
  const match = css.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`token --${name} not found in globals.css`);
  return match[1];
}

function channel(value: number): number {
  const s = value / 255;
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

function luminance(hex: string): number {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function contrast(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

describe("design tokens meet WCAG AA", () => {
  it("the contrast formula is correct (white on black = 21:1)", () => {
    expect(contrast("#ffffff", "#000000")).toBeCloseTo(21, 0);
  });

  const onBackground: Array<[string, number]> = [
    ["text", 4.5],
    ["text-muted", 4.5],
    ["accent", 4.5],
    ["success", 4.5],
    ["danger", 4.5],
    ["warning", 4.5],
  ];

  it.each(onBackground)("--%s on --bg is at least %d:1", (name, min) => {
    expect(contrast(token(name), token("bg"))).toBeGreaterThanOrEqual(min);
  });

  it("white text on the primary fill is AA (primary button)", () => {
    expect(contrast(token("on-primary"), token("primary"))).toBeGreaterThanOrEqual(4.5);
  });
});
