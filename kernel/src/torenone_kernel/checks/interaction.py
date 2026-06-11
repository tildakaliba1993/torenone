"""Combined axial compression and bending — SANS 10162-1:2011 cl. 13.8.

Beam-column interaction for class 1 and class 2 I-shaped sections (cl. 13.8.2).
Overall member strength (unbraced portal — U1x = 1.0 per cl. 13.8.2b):

    Cu/Cr + 0.85 · U1 · Mu/Mr ≤ 1.0      (VERIFIED vs cl. 13.8.2, overall member strength)

U1 factor (cl. 13.8.4):
    U1 = ω1 / (1 − Cu/Ce)  ≥ 1.0
    Ce = π²·E·I / (KL)²    (Euler buckling load, kN)
    ω1 = 1.0 for members with distributed loads (cl. 13.8.5b, VERIFIED)
    ω1 = 0.6 − 0.4·κ ≥ 0.4 for end-moment-only case (cl. 13.8.5a, VERIFIED)

For unbraced frames, U1x = U1y = 1.0 is used for the translational (sway) moment check
(cl. 13.8.2b). The U1 factor computed here applies to the gravity-induced (non-sway) moment.

The check returns a CheckResult with utilisation and pass/fail — every result carries a clause
reference (PRD FR-18).
"""

from __future__ import annotations

from torenone_kernel.checks.classification import SectionClass
from torenone_kernel.models.results import CheckResult

_E   = 200_000.0   # MPa — cl. 3.2 (VERIFIED)
_PHI = 0.90        # cl. 13.1a (VERIFIED)


def u1_factor(omega1: float, cu_kn: float, Ce_kn: float) -> float:
    """Compute U1 (cl. 13.8.4).

    U1 = ω1 / (1 − Cu/Ce)  ≥ 1.0

    Parameters
    ----------
    omega1 : moment gradient factor (cl. 13.8.5)
    cu_kn  : factored axial compression Cu (kN); ≤ 0 (tension) treated as 0
    Ce_kn  : Euler buckling load Ce = π²EI/(KL)² (kN)

    Returns
    -------
    U1 ≥ 1.0
    """
    cu = max(cu_kn, 0.0)   # tension members: cu = 0 for this factor
    denom = 1.0 - cu / Ce_kn if Ce_kn > 0 else 1.0
    denom = max(denom, 1e-6)  # guard against division by zero
    return max(omega1 / denom, 1.0)


def beam_column_check(
    cu_kn: float,
    cr_kn: float,
    mu_knm: float,
    mr_knm: float,
    U1: float,
    section_class: SectionClass,
    check_name: str = "beam-column interaction",
) -> CheckResult:
    """Overall member strength interaction check (cl. 13.8.2, unbraced frame).

    For class 1 and class 2 I-shaped sections:
        utilisation = Cu/Cr + 0.85 · U1 · Mu/Mr  ≤ 1.0

    For class 3 sections (cl. 13.8.3):
        utilisation = Cu/Cr + U1 · Mu/Mr  ≤ 1.0  (no 0.85 factor)

    Parameters
    ----------
    cu_kn         : factored axial compression (kN)
    cr_kn         : factored compressive resistance (kN) from cr_flexural()
    mu_knm        : factored bending moment (kN·m)
    mr_knm        : factored moment resistance (kN·m) from mr_ltb() or mr_laterally_supported()
    U1            : moment amplification factor (cl. 13.8.4); use 1.0 for unbraced sway check
    section_class : governs the interaction coefficient (0.85 for class 1/2; 1.0 for class 3)
    check_name    : label for the CheckResult

    Returns
    -------
    CheckResult with clause = "SANS 10162-1:2011 cl. 13.8.2"
    """
    axial_ratio  = cu_kn / cr_kn if cr_kn > 0 else float("inf")
    moment_ratio = mu_knm / mr_knm if mr_knm > 0 else float("inf")

    if section_class in (SectionClass.CLASS1, SectionClass.CLASS2):
        # cl. 13.8.2 — overall member strength
        utilisation = axial_ratio + 0.85 * U1 * moment_ratio
        clause = "SANS 10162-1:2011 cl. 13.8.2 (overall member strength, class 1/2)"
    else:
        # cl. 13.8.3 — all other sections
        utilisation = axial_ratio + U1 * moment_ratio
        clause = "SANS 10162-1:2011 cl. 13.8.3 (overall member strength, class 3)"

    return CheckResult(
        name=check_name,
        clause=clause,
        utilisation=utilisation,
        passed=utilisation <= 1.0,
    )
