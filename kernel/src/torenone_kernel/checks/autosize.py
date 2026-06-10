"""Auto-sizing — Task 1.11.

Iterate a SectionLibrary in lightest-first order; run all SANS 10162-1:2011 strength
checks on each candidate; return the first (lightest) section whose checks all pass.

Checks run per candidate (in order — bail to next section on any failure):
    1. Section classification (cl. 11.2)  — Class4Error → skip
    2. Axial Cr (cl. 13.3.1)             — SlendernessError → skip
    3. Shear Vr (cl. 13.4.1.1)           — NotImplementedError (TF range) → skip
    4. LTB Mcr + Mr (cl. 13.6)           — or laterally-supported Mr (cl. 13.5) when LTB_mm≈0
    5. Beam-column interaction (cl. 13.8.2/13.8.3)

SLS deflection limits are NOT part of the strength search loop — they require the
actual elastic deflection from analysis, which the auto-sizer does not have. The
orchestrator (1.12) runs SLS checks separately after selecting the section.

All numeric inputs use the unit convention established in 1.10:
    lengths  → mm
    forces   → kN
    moments  → kN·m
    stresses → MPa
"""

from __future__ import annotations

import math
from typing import Optional

from torenone_kernel.checks.axial import cr_flexural, SlendernessError
from torenone_kernel.checks.bending import (
    mr_laterally_supported,
    mcr_elastic,
    mr_ltb,
    omega2_factor,
)
from torenone_kernel.checks.classification import (
    SectionClass,
    classify_section,
    Class4Error,
)
from torenone_kernel.checks.interaction import beam_column_check, u1_factor
from torenone_kernel.checks.shear import vr_web
from torenone_kernel.models.results import AutosizeResult, CheckResult
from torenone_kernel.sections.library import SectionLibrary
from torenone_kernel.sections.properties import SectionProperties

_PHI = 0.90   # cl. 13.1a
_E   = 200_000.0  # MPa


class NoSectionFoundError(ValueError):
    """Raised when no section in the library satisfies all strength checks.

    The engineer must either:
    a) increase the section library (heavier sections),
    b) reduce the applied loads,
    c) add lateral bracing (reduces LTB_mm), or
    d) change the structural configuration.
    """


def _check_one_section(
    section: SectionProperties,
    fy_mpa: float,
    cu_kn: float,
    vu_kn: float,
    mu_knm: float,
    KL_mm: float,
    LTB_mm: float,
    omega2: float,
    U1: float,
    n: float,
    member: str,
) -> Optional[AutosizeResult]:
    """Run all strength checks on one section.

    Returns an AutosizeResult if ALL checks pass, else None.
    Raises Class4Error, SlendernessError, or NotImplementedError for the caller to catch
    (these indicate a section should be skipped, not a code error).
    """
    checks: list[CheckResult] = []

    # ---- 1. Section classification (cl. 11.2) ----
    cu_for_class = max(cu_kn, 0.0)  # classification uses compressive Cu ≥ 0
    cls_result = classify_section(section, fy_mpa, cu_for_class)  # raises Class4Error if class 4
    sec_class = cls_result.overall_class

    # ---- 2. Axial compressive resistance Cr (cl. 13.3.1) ----
    cr_kn = cr_flexural(
        area_mm2=section.area_mm2,
        fy_mpa=fy_mpa,
        KL_mm=KL_mm,
        r_mm=section.radius_gyration_ry_mm,  # weak axis (conservative for columns)
        n=n,
    )  # raises SlendernessError if KL/r > 200
    cu_eff = max(cu_kn, 0.0)  # use 0 for tension (tension is not the governing case here)
    axial_util = cu_eff / cr_kn if cr_kn > 0 else 0.0
    checks.append(CheckResult(
        name=f"{member}: axial Cr",
        clause="SANS 10162-1:2011 cl. 13.3.1",
        utilisation=axial_util,
        passed=cu_eff <= cr_kn,
    ))

    # ---- 3. Shear resistance Vr (cl. 13.4.1.1) ----
    hw_mm = section.depth_mm - 2.0 * section.flange_thickness_mm
    vr_kn = vr_web(hw_mm, section.web_thickness_mm, fy_mpa)  # raises NotImplementedError for TF
    vu_eff = abs(vu_kn)
    shear_util = vu_eff / vr_kn if vr_kn > 0 else 0.0
    checks.append(CheckResult(
        name=f"{member}: shear Vr",
        clause="SANS 10162-1:2011 cl. 13.4.1.1",
        utilisation=shear_util,
        passed=vu_eff <= vr_kn,
    ))

    # ---- 4. Bending resistance Mr with LTB (cl. 13.5/13.6) ----
    if LTB_mm <= 1.0:
        # Effectively fully restrained → laterally supported
        mr_kn_m = mr_laterally_supported(sec_class, section.plastic_modulus_zx_mm3,
                                          section.elastic_modulus_sx_mm3, fy_mpa)
    else:
        mcr_kn_m = mcr_elastic(LTB_mm, section.second_moment_iy_mm4,
                                section.torsion_constant_j_mm4,
                                section.warping_constant_cw_mm6, omega2)
        mr_kn_m = mr_ltb(sec_class, section.plastic_modulus_zx_mm3,
                          section.elastic_modulus_sx_mm3, fy_mpa, mcr_kn_m)
    mu_eff = abs(mu_knm)
    moment_util = mu_eff / mr_kn_m if mr_kn_m > 0 else float("inf")
    checks.append(CheckResult(
        name=f"{member}: moment Mr (LTB)",
        clause="SANS 10162-1:2011 cl. 13.5/13.6",
        utilisation=moment_util,
        passed=mu_eff <= mr_kn_m,
    ))

    # ---- 5. Beam-column interaction (cl. 13.8.2/13.8.3) ----
    result_interaction = beam_column_check(
        cu_kn=cu_eff,
        cr_kn=cr_kn,
        mu_knm=mu_eff,
        mr_knm=mr_kn_m,
        U1=U1,
        section_class=sec_class,
        check_name=f"{member}: beam-column interaction",
    )
    checks.append(result_interaction)

    # All checks must pass
    if not all(c.passed for c in checks):
        return None

    return AutosizeResult(
        member=member,
        designation=section.designation,
        section_class_value=int(sec_class),
        checks=checks,
    )


def autosize_member(
    library: SectionLibrary,
    fy_mpa: float,
    cu_kn: float,
    vu_kn: float,
    mu_knm: float,
    KL_mm: float,
    LTB_mm: float,
    omega2: float = 1.0,
    U1: float = 1.0,
    n: float = 1.34,
    member: str = "member",
) -> AutosizeResult:
    """Return the lightest section from the library that passes all strength checks.

    Parameters
    ----------
    library  : SectionLibrary to search (iterated lightest-first)
    fy_mpa   : design yield stress (MPa) — use checks.material.fy_mpa()
    cu_kn    : factored axial compression (kN); negative = tension (treated as 0 here)
    vu_kn    : factored shear force (kN)
    mu_knm   : factored bending moment (kN·m)
    KL_mm    : effective length for axial buckling (mm) = K × column/rafter length
    LTB_mm   : unbraced length for LTB (mm) = purlin/girt spacing; pass ≤1.0 for fully restrained
    omega2   : moment gradient factor ω2 (cl. 13.6a); use omega2_factor(kappa) or 1.0
    U1       : moment amplification factor (cl. 13.8.4); 1.0 for unbraced frame sway check
    n        : column curve parameter (1.34 for hot-rolled, 2.24 for welded stress-relieved)
    member   : label for check names ('rafter', 'column', etc.)

    Returns
    -------
    AutosizeResult — lightest passing section with all check results.

    Raises
    ------
    NoSectionFoundError — if no section in the library satisfies all checks.
    """
    skipped: list[str] = []

    for section in library.by_increasing_mass():
        try:
            result = _check_one_section(
                section, fy_mpa, cu_kn, vu_kn, mu_knm,
                KL_mm, LTB_mm, omega2, U1, n, member,
            )
        except (Class4Error, SlendernessError, NotImplementedError) as exc:
            skipped.append(f"{section.designation}: {exc}")
            continue

        if result is not None:
            return result
        # else: at least one check failed — try next heavier section

    raise NoSectionFoundError(
        f"No section in the library satisfies all strength checks for {member!r}. "
        f"Inputs: Cu={cu_kn:.1f} kN, Vu={vu_kn:.1f} kN, Mu={mu_knm:.1f} kN·m, "
        f"KL={KL_mm:.0f} mm, LTB={LTB_mm:.0f} mm, fy={fy_mpa:.0f} MPa. "
        f"Add heavier sections to the library, reduce loads, or add lateral bracing. "
        + (f"Skipped (code issues): {skipped}" if skipped else "")
    )
