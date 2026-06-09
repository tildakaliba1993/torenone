"""Canonical TorenOne design tokens (dark theme, steel-blue brand).

This module is the single source of truth for colour. `web/design/tokens.css` mirrors it;
keep them in sync (run `python tools/torenone_tokens/tokens.py` to regenerate the CSS).

Brand intent: a strong steel-blue that reads trustworthy and authoritative, on a cool dark
base. All foreground/interactive tokens are verified against their background for WCAG AA
in `contrast.py` (and the test suite).
"""

from __future__ import annotations

COLORS: dict[str, str] = {
    # Neutrals (cool-tinted dark, Supabase-style)
    "bg": "#0E1116",              # app background
    "surface": "#14181F",         # panels, sidebar
    "surface-raised": "#1B212B",  # cards, modals, popovers
    "border": "#29313C",          # dividers, input borders
    "border-strong": "#3A4452",   # emphasis borders
    "text": "#E8ECF1",            # primary text
    "text-muted": "#9AA4B2",      # secondary text
    "text-subtle": "#6A7585",     # tertiary — LARGE/UI ONLY, never small body text
    # Brand steel-blue
    "primary": "#2F6FB0",         # primary button fill (white text)
    "primary-hover": "#3A7EC2",
    "primary-active": "#275E97",
    "accent": "#5AA2E8",          # links, interactive text, data highlights
    "ring": "#5AA2E8",            # keyboard focus ring
    "on-primary": "#FFFFFF",      # text/icon on primary & semantic fills (verify per fill)
    # Semantic status — used primarily as TEXT/ICON on the dark base.
    # When used as a FILL, pair with dark text (verified separately).
    "success": "#3FB950",         # check passes / utilisation OK
    "danger": "#F85149",          # FAILS / over-capacity
    "warning": "#D6A02A",         # near limit / review
}

# (foreground, background, min_ratio) — what the test suite enforces.
# 4.5 = AA normal text; 3.0 = AA large text / UI components.
CONTRAST_PAIRS: list[tuple[str, str, float]] = [
    ("text", "bg", 4.5),
    ("text", "surface", 4.5),
    ("text", "surface-raised", 4.5),
    ("text-muted", "bg", 4.5),
    ("text-muted", "surface-raised", 4.5),
    ("accent", "bg", 4.5),          # links on app background
    ("accent", "surface", 4.5),
    ("on-primary", "primary", 4.5),  # white label on primary button
    ("success", "bg", 4.5),          # status text on dark
    ("danger", "bg", 4.5),
    ("warning", "bg", 4.5),
    ("text-subtle", "bg", 3.0),      # large/UI only
    ("ring", "bg", 3.0),             # focus ring is a UI component
]


def to_css() -> str:
    """Render the tokens as CSS custom properties for the web app."""
    lines = [
        "/* GENERATED from tools/torenone_tokens/tokens.py — do not edit by hand. */",
        ":root {",
    ]
    for name, value in COLORS.items():
        lines.append(f"  --{name}: {value};")
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(to_css(), end="")
