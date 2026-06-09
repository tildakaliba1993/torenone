"""WCAG 2.1 contrast-ratio computation + a self-check for the TorenOne palette.

Run standalone (stdlib only) to verify the brand passes accessibility:

    python tools/torenone_tokens/contrast.py

Exits non-zero if any defined token pair fails its required ratio. Also used by the
pytest suite (tools/tests/test_contrast.py) so CI gates on it.
"""

from __future__ import annotations

import sys

from torenone_tokens.tokens import COLORS, CONTRAST_PAIRS


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _linearize(channel_8bit: int) -> float:
    c = channel_8bit / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    la, lb = relative_luminance(hex_a), relative_luminance(hex_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def evaluate() -> list[tuple[str, str, float, float, bool]]:
    """Return (fg, bg, ratio, required, passes) for every defined pair."""
    results = []
    for fg, bg, required in CONTRAST_PAIRS:
        ratio = contrast_ratio(COLORS[fg], COLORS[bg])
        results.append((fg, bg, ratio, required, ratio >= required))
    return results


def main() -> int:
    rows = evaluate()
    width = max(len(fg) + len(bg) for fg, bg, *_ in rows) + 6
    print("TorenOne design tokens — WCAG AA contrast check\n")
    all_pass = True
    for fg, bg, ratio, required, ok in rows:
        all_pass = all_pass and ok
        label = f"{fg} on {bg}"
        status = "PASS" if ok else "FAIL"
        print(f"  {label:<{width}} {ratio:5.2f}:1  (>= {required:.1f})  {status}")
    print("\n" + ("ALL PASS" if all_pass else "SOME FAILED -- adjust tokens"))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
