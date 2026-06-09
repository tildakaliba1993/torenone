"""Design-system accessibility gate (Task 0.5).

Every defined token pair must meet its WCAG ratio. If a brand colour is changed and a pair
drops below threshold, CI fails — the dark theme stays accessible by construction.
"""

import pytest

from torenone_tokens.contrast import contrast_ratio, evaluate
from torenone_tokens.tokens import COLORS, CONTRAST_PAIRS


@pytest.mark.parametrize("fg,bg,required", CONTRAST_PAIRS, ids=[f"{a}_on_{b}" for a, b, _ in CONTRAST_PAIRS])
def test_token_pair_meets_wcag(fg: str, bg: str, required: float) -> None:
    ratio = contrast_ratio(COLORS[fg], COLORS[bg])
    assert ratio >= required, f"{fg} on {bg}: {ratio:.2f}:1 < required {required:.1f}:1"


def test_known_reference_ratios() -> None:
    # Black/white sanity check anchors the formula (WCAG: 21:1).
    assert round(contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0


def test_no_pair_silently_fails() -> None:
    assert all(ok for *_, ok in evaluate())
