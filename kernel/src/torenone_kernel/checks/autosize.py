"""Auto-sizing — Task 1.11 (code-agnostic).

Iterate a SectionLibrary in lightest-first order; run all member strength checks (via the active
``DesignCode``) on each candidate; return the first (lightest) section whose checks all pass.

Checks run per candidate (in order — bail to next section on any failure):
    1. Section classification         — Class4Error → skip
    2. Axial Cr (per-axis buckling)   — SlendernessError → skip
    3. Shear Vr                       — NotImplementedError (TF range) → skip
    4. Moment Mr (LTB or laterally supported)
    5. Beam-column interaction

The specific equations/factors/clauses come from the ``DesignCode`` (default: SANS 10162-1), so this
module is code-agnostic. SLS deflection limits are NOT part of the strength search loop — the
orchestrator (design.py) runs them separately after selecting the section.

All numeric inputs use the unit convention: lengths → mm, forces → kN, moments → kN·m, stresses → MPa.
"""

from __future__ import annotations

from torenone_kernel.checks.axial import SlendernessError
from torenone_kernel.checks.classification import Class4Error
from torenone_kernel.codes import DEFAULT_CODE, DesignCode
from torenone_kernel.models.results import AutosizeResult, CheckResult
from torenone_kernel.sections.library import SectionLibrary
from torenone_kernel.sections.properties import SectionProperties


class SectionIneligibleError(ValueError):
    """Raised by run_member_checks() when a section cannot be checked at all.

    Covers: Class4Error (section classification out of MVP scope),
    SlendernessError (KL/r > 200), and NotImplementedError (tension-field shear).
    The caller receives this instead of a partial check list; it should produce a
    diagnostic CheckResult with passed=False and the error message as detail.
    """


class NoSectionFoundError(ValueError):
    """Raised when no section in the library satisfies all strength checks.

    The engineer must either:
    a) increase the section library (heavier sections),
    b) reduce the applied loads,
    c) add lateral bracing (reduces LTB_mm), or
    d) change the structural configuration.
    """


def run_member_checks(
    section: SectionProperties,
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
    *,
    code: DesignCode = DEFAULT_CODE,
) -> list[CheckResult]:
    """Run all member strength checks on *section* (via *code*) and return every result.

    Unlike ``autosize_member``, this function:
    * **Always** returns the full check list — even when one or more checks fail.
    * Never skips sections silently.

    Raises
    ------
    SectionIneligibleError
        When the section cannot be checked at all: Class 4, slenderness KL/r > 200, or
        tension-field shear (not implemented in MVP). The caller should convert this to a
        diagnostic failed CheckResult if needed.
    """
    checks: list[CheckResult] = []

    # ---- 1. Section classification ----
    cu_for_class = max(cu_kn, 0.0)
    try:
        cls_result = code.classify(section, fy_mpa, cu_for_class)
    except Class4Error as exc:
        raise SectionIneligibleError(str(exc)) from exc
    sec_class = cls_result.overall_class

    # ---- 2. Axial compressive resistance Cr (weaker buckling axis) ----
    try:
        cr_kn = code.axial_resistance(section, fy_mpa, KL_mm, LTB_mm, n)
    except SlendernessError as exc:
        raise SectionIneligibleError(str(exc)) from exc
    cu_eff = max(cu_kn, 0.0)
    axial_util = cu_eff / cr_kn if cr_kn > 0 else 0.0
    checks.append(CheckResult(
        name=f"{member}: axial Cr",
        clause=code.clause("axial"),
        utilisation=axial_util,
        passed=cu_eff <= cr_kn,
    ))

    # ---- 3. Shear resistance Vr ----
    try:
        vr_kn = code.shear_resistance(section, fy_mpa)
    except NotImplementedError as exc:
        raise SectionIneligibleError(str(exc)) from exc
    vu_eff = abs(vu_kn)
    shear_util = vu_eff / vr_kn if vr_kn > 0 else 0.0
    checks.append(CheckResult(
        name=f"{member}: shear Vr",
        clause=code.clause("shear"),
        utilisation=shear_util,
        passed=vu_eff <= vr_kn,
    ))

    # ---- 4. Bending resistance Mr with LTB ----
    mr_kn_m = code.moment_resistance(section, sec_class, fy_mpa, LTB_mm, omega2)
    mu_eff = abs(mu_knm)
    moment_util = mu_eff / mr_kn_m if mr_kn_m > 0 else float("inf")
    checks.append(CheckResult(
        name=f"{member}: moment Mr (LTB)",
        clause=code.clause("moment"),
        utilisation=moment_util,
        passed=mu_eff <= mr_kn_m,
    ))

    # ---- 5. Beam-column interaction ----
    checks.append(code.beam_column_interaction(
        cu_kn=cu_eff,
        cr_kn=cr_kn,
        mu_knm=mu_eff,
        mr_knm=mr_kn_m,
        u1=U1,
        section_class=sec_class,
        check_name=f"{member}: beam-column interaction",
    ))

    return checks


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
    code: DesignCode,
) -> AutosizeResult | None:
    """Thin wrapper: run checks and return AutosizeResult if all pass, else None.

    Raises Class4Error, SlendernessError, or NotImplementedError (as
    SectionIneligibleError) for the autosize search loop to skip the section.
    """
    try:
        checks = run_member_checks(section, fy_mpa, cu_kn, vu_kn, mu_knm,
                                   KL_mm, LTB_mm, omega2, U1, n, member, code=code)
    except SectionIneligibleError as exc:
        # Re-raise the underlying cause so the autosize loop sees the original error type
        raise exc.__cause__ from None  # type: ignore[misc]

    if not all(c.passed for c in checks):
        return None
    return AutosizeResult(
        member=member,
        designation=section.designation,
        section_class_value=int(
            code.classify(section, fy_mpa, max(cu_kn, 0.0)).overall_class
        ),
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
    *,
    code: DesignCode = DEFAULT_CODE,
) -> AutosizeResult:
    """Return the lightest section from the library that passes all strength checks (per *code*).

    Parameters
    ----------
    library  : SectionLibrary to search (iterated lightest-first)
    fy_mpa   : design yield stress (MPa) — use code.material_fy()
    cu_kn    : factored axial compression (kN); negative = tension (treated as 0 here)
    vu_kn    : factored shear force (kN)
    mu_knm   : factored bending moment (kN·m)
    KL_mm    : effective length for axial buckling (mm) = K × column/rafter length
    LTB_mm   : unbraced length for LTB (mm) = purlin/girt spacing; pass ≤1.0 for fully restrained
    omega2   : moment gradient factor ω2; use code.moment_gradient_omega2(kappa) or 1.0
    U1       : moment amplification factor; 1.0 for unbraced frame sway check
    n        : column curve parameter (1.34 for hot-rolled, 2.24 for welded stress-relieved)
    member   : label for check names ('rafter', 'column', etc.)
    code     : the active DesignCode (default: SANS 10162-1)

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
                KL_mm, LTB_mm, omega2, U1, n, member, code,
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
