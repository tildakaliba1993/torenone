"""Load combinations per SANS 10160-1 (PRD FR-8).

✅ VERIFIED against the **FINAL published SANS 10160-1:2011 (Ed 1.1, Amdt 1)** PDF
(2026-06-15) — Table 3 (ULS partial factors, p.38), Table 2 (ψ factors, p.34), eq. (6)/(7)
(cl. 7.3.2) and eq. (10) (cl. 8.3.1). The previously-PROVISIONAL draft factors were confirmed;
the SLS wind factor was corrected (see below).

ULS (STR), Table 3: eq. (6) fundamental, eq. (7) dominant-permanent (STR-P).
  permanent γG = 1.2 (unfavourable) / 0.9 (favourable); STR-P γG = 1.35.
  imposed γQ = 1.6; wind γQ = 1.3.  [Table 3 footnote c: γF = 1.5 for *slender non-redundant*
  structures with significant cross-wind response — out of MVP scope (quasi-static portal).]
SLS irreversible, eq. (10) (cl. 8.3.1.1): γG = 1.1 (unfavourable) / 1.0 (favourable);
  γQ = 1.0 for imposed; **γQ = 0.6 for wind**.

For an INACCESSIBLE roof (category H) the imposed combination factor ψ0 = 0, and wind as an
accompanying action has ψ0 = 0 (Table 2) — so imposed and wind never act together as accompanying
actions; each is considered only as the leading variable. (Accessible roofs are out of MVP scope.)
"""

from __future__ import annotations

from torenone_kernel.models.enums import LimitState
from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import LoadCombination

# SANS 10160-1:2011 (final, Ed 1.1 + Amdt 1) partial factors — VERIFIED vs the standard.
GAMMA_G_UNFAVOURABLE = 1.2  # Table 3, self-weight STR (unfavourable)
GAMMA_G_FAVOURABLE = 0.9  # Table 3, self-weight STR (favourable — e.g. wind uplift)
GAMMA_G_STR_P = 1.35  # Table 3, self-weight STR-P (dominant permanent), eq. (7)
GAMMA_Q_IMPOSED = 1.6  # Table 3, imposed loads STR
GAMMA_Q_WIND = 1.3  # Table 3, wind action STR (footnote c: 1.5 for slender cross-wind — n/a)
GAMMA_G_SLS_UNFAVOURABLE = 1.1  # eq. (10), irreversible SLS (unfavourable permanent)
GAMMA_Q_SLS = 1.0  # eq. (10), irreversible SLS — imposed
GAMMA_Q_SLS_WIND = 0.6  # eq. (10), irreversible SLS — wind (cl. 8.3.1.1)

_CLAUSE = "SANS 10160-1:2011 Table 3 + eq. (6)/(7)/(10)"


def load_combinations(spec: FrameSpec) -> tuple[LoadCombination, ...]:
    """ULS + SLS combinations for the portal frame (inaccessible roof; ψ0 = 0 for imposed & wind)."""
    if spec.imposed.roof_access:
        raise NotImplementedError(
            "Accessible roofs are out of MVP scope — their imposed category / ψ0 factors differ."
        )
    return (
        # --- ULS (STR) ---
        LoadCombination(
            name="ULS-1 gravity (imposed leading) [SANS 10160-1 eq.6]",
            limit_state=LimitState.ULS,
            factors={"dead": GAMMA_G_UNFAVOURABLE, "imposed": GAMMA_Q_IMPOSED},
        ),
        LoadCombination(
            name="ULS-2 wind (permanent unfavourable) [eq.6]",
            limit_state=LimitState.ULS,
            factors={"dead": GAMMA_G_UNFAVOURABLE, "wind": GAMMA_Q_WIND},
        ),
        LoadCombination(
            name="ULS-3 wind uplift (permanent favourable) [eq.6]",
            limit_state=LimitState.ULS,
            factors={"dead": GAMMA_G_FAVOURABLE, "wind": GAMMA_Q_WIND},
        ),
        LoadCombination(
            name="ULS-4 STR-P dominant permanent [eq.7]",
            limit_state=LimitState.ULS,
            factors={"dead": GAMMA_G_STR_P, "imposed": 1.0},
        ),
        # --- SLS (eq. 10, irreversible) ---
        LoadCombination(
            name="SLS-1 gravity (apex deflection) [eq.10]",
            limit_state=LimitState.SLS,
            factors={"dead": GAMMA_G_SLS_UNFAVOURABLE, "imposed": GAMMA_Q_SLS},
        ),
        LoadCombination(
            name="SLS-2 wind (eaves sway) [eq.10]",
            limit_state=LimitState.SLS,
            factors={"dead": GAMMA_G_SLS_UNFAVOURABLE, "wind": GAMMA_Q_SLS_WIND},
        ),
    )
