"""SANS 10162-1 design code — the first `DesignCode` implementation.

A thin adapter over the existing, Red-Book-validated `checks/*` functions: the South African
maths is unchanged, just expressed through the common `DesignCode` interface. Load combinations,
material yield and section data come from their existing modules. See `codes/base.py`.
"""

from __future__ import annotations

from torenone_kernel.checks.axial import cr_flexural
from torenone_kernel.checks.bending import (
    mcr_elastic,
    mr_laterally_supported,
    mr_ltb,
    omega2_factor,
)
from torenone_kernel.checks.classification import (
    ClassificationResult,
    SectionClass,
    classify_section,
)
from torenone_kernel.checks.interaction import beam_column_check
from torenone_kernel.checks.material import fy_mpa
from torenone_kernel.checks.shear import vr_web
from torenone_kernel.codes.base import DesignCode
from torenone_kernel.loads.combinations import load_combinations
from torenone_kernel.models.enums import SteelGrade
from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import CheckResult, LoadCombination
from torenone_kernel.rules_version import as_dict as _rules_version
from torenone_kernel.sections.library import SectionLibrary
from torenone_kernel.sections.properties import SectionProperties

_CLAUSES = {
    "axial": "SANS 10162-1:2011 cl. 13.3.1",
    "shear": "SANS 10162-1:2011 cl. 13.4.1.1",
    "moment": "SANS 10162-1:2011 cl. 13.5/13.6",
}


class SANS10162(DesignCode):
    """SANS 10162-1:2011 — limit-states design of hot-rolled steelwork (South Africa)."""

    id = "SANS10162"
    unit_system = "metric"

    def rules_version(self) -> dict[str, str]:
        return _rules_version()

    # --- Inputs -------------------------------------------------------------------------------
    def section_library(self) -> SectionLibrary:
        return SectionLibrary.load_default()

    def material_fy(self, grade: SteelGrade, thickness_mm: float) -> float:
        return fy_mpa(grade, thickness_mm)

    def load_combinations(self, spec: FrameSpec) -> tuple[LoadCombination, ...]:
        return load_combinations(spec)

    # --- Member design operations -------------------------------------------------------------
    def classify(
        self, section: SectionProperties, fy_mpa: float, cu_kn: float
    ) -> ClassificationResult:
        return classify_section(section, fy_mpa, cu_kn)

    def axial_resistance(
        self, section: SectionProperties, fy_mpa: float, kl_mm: float, ltb_mm: float, n: float
    ) -> float:
        # Flexural buckling resistance is the weaker of the two axes (cl. 13.3.1): major axis over
        # the full length (rx); minor axis over the lateral-restraint spacing (ry), since the
        # purlins/girts that prevent LTB also brace minor-axis buckling. Full length when unbraced.
        minor_kl_mm = ltb_mm if ltb_mm > 1.0 else kl_mm
        cr_major = cr_flexural(section.area_mm2, fy_mpa, kl_mm, section.radius_gyration_rx_mm, n)
        cr_minor = cr_flexural(section.area_mm2, fy_mpa, minor_kl_mm, section.radius_gyration_ry_mm, n)
        return min(cr_major, cr_minor)

    def shear_resistance(self, section: SectionProperties, fy_mpa: float) -> float:
        hw_mm = section.depth_mm - 2.0 * section.flange_thickness_mm
        return vr_web(hw_mm, section.web_thickness_mm, fy_mpa)

    def moment_resistance(
        self,
        section: SectionProperties,
        section_class: SectionClass,
        fy_mpa: float,
        ltb_mm: float,
        omega2: float,
    ) -> float:
        if ltb_mm <= 1.0:
            return mr_laterally_supported(
                section_class, section.plastic_modulus_zx_mm3, section.elastic_modulus_sx_mm3, fy_mpa
            )
        mcr_kn_m = mcr_elastic(
            ltb_mm,
            section.second_moment_iy_mm4,
            section.torsion_constant_j_mm4,
            section.warping_constant_cw_mm6,
            omega2,
        )
        return mr_ltb(
            section_class,
            section.plastic_modulus_zx_mm3,
            section.elastic_modulus_sx_mm3,
            fy_mpa,
            mcr_kn_m,
        )

    def moment_gradient_omega2(self, kappa: float) -> float:
        return omega2_factor(kappa)

    def beam_column_interaction(
        self,
        cu_kn: float,
        cr_kn: float,
        mu_knm: float,
        mr_knm: float,
        u1: float,
        section_class: SectionClass,
        check_name: str,
    ) -> CheckResult:
        return beam_column_check(
            cu_kn=cu_kn,
            cr_kn=cr_kn,
            mu_knm=mu_knm,
            mr_knm=mr_knm,
            U1=u1,
            section_class=section_class,
            check_name=check_name,
        )

    # --- Reference strings + limits -----------------------------------------------------------
    def clause(self, key: str) -> str:
        return _CLAUSES[key]

    def deflection_limit_fraction(self) -> int:
        return 240
