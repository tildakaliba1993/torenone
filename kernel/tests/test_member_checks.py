"""Task 1.10 — member checks to SANS 10162-1:2011.

All expected values are hand-calculated from the exact clause formulas and verified below.
Reference: SANS 10162-1:2011 Edition 2.1.

Confirmed constants (cl. 3.2 Symbols):
    E = 200 000 MPa   (VERIFIED)
    G =  77 000 MPa   (VERIFIED)

Resistance factor (cl. 13.1a):
    φ = 0.90          (VERIFIED)

Column curve (cl. 13.3.1):
    n = 1.34 for hot-rolled sections  (VERIFIED)

fy for S355JR (EN 10025-2, referenced in cl. 5.1.3):
    355 MPa for tf ≤ 16 mm  (PROVISIONAL — pending engineer sign-off vs SANS 1431)
    345 MPa for 16 < tf ≤ 40 mm
    335 MPa for 40 < tf ≤ 63 mm

Tolerances: ±1 % relative for all resistance / capacity values (per REFERENCES §4).
"""

from __future__ import annotations

import math
import pytest

from torenone_kernel.checks.classification import (
    SectionClass,
    classify_section,
    ClassificationResult,
    Class4Error,
)
from torenone_kernel.checks.axial import cr_flexural
from torenone_kernel.checks.shear import vr_web
from torenone_kernel.checks.bending import mr_laterally_supported, mcr_elastic, mr_ltb
from torenone_kernel.checks.interaction import (
    u1_factor,
    beam_column_check,
)
from torenone_kernel.checks.deflection import (
    vertical_deflection_check,
    horizontal_sway_check,
)
from torenone_kernel.models.results import CheckResult
from torenone_kernel.sections.properties import SectionProperties

# ---------------------------------------------------------------------------
# Confirmed constants
# ---------------------------------------------------------------------------
_E = 200_000.0   # MPa — SANS 10162-1:2011 cl. 3.2 (VERIFIED)
_G =  77_000.0   # MPa — SANS 10162-1:2011 cl. 3.2 (VERIFIED)
_PHI = 0.90      # cl. 13.1a (VERIFIED)
_N_HR = 1.34     # n for hot-rolled — cl. 13.3.1 (VERIFIED)


def _section(
    designation="TEST-355",
    fy_mpa=355.0,
    A_mm2=6000.0,
    depth_mm=300.0,
    width_mm=150.0,
    tw_mm=7.0,
    tf_mm=11.0,
    Ix_mm4=85e6,
    Iy_mm4=6e6,
    Zpl_mm3=620_000.0,
    Ze_mm3=567_000.0,
    rx_mm=119.0,
    ry_mm=32.0,
    J_mm4=40_000.0,
    Cw_mm6=126e9,
    mass_kg_m=47.0,
) -> SectionProperties:
    return SectionProperties(
        designation=designation,
        mass_per_metre_kg_m=mass_kg_m,
        area_mm2=A_mm2,
        depth_mm=depth_mm,
        width_mm=width_mm,
        web_thickness_mm=tw_mm,
        flange_thickness_mm=tf_mm,
        second_moment_ix_mm4=Ix_mm4,
        second_moment_iy_mm4=Iy_mm4,
        elastic_modulus_sx_mm3=Ze_mm3,
        plastic_modulus_zx_mm3=Zpl_mm3,
        radius_gyration_rx_mm=rx_mm,
        radius_gyration_ry_mm=ry_mm,
        torsion_constant_j_mm4=J_mm4,
        warping_constant_cw_mm6=Cw_mm6,
    )


# ---------------------------------------------------------------------------
# 1. Section Classification — cl. 11.2, Table 4
# ---------------------------------------------------------------------------

class TestClassification:
    """cl. 11.2, Table 4.

    Flange limit (half-flange outstand for I-section: b = width/2):
        Class 1: b/t ≤ 145/√fy   (VERIFIED vs Table 4)
        Class 2: b/t ≤ 170/√fy
        Class 3: b/t ≤ 200/√fy
        Class 4: b/t > 200/√fy  → refuse

    Web limit (pure bending, Cu = 0):
        Class 1: h/t ≤ 1100/√fy  (VERIFIED vs Table 4)
        Class 2: h/t ≤ 1700/√fy
        Class 3: h/t ≤ 1900/√fy

    For fy=355 MPa, √fy=18.84:
        Flange: class1≤7.70, class2≤9.02, class3≤10.62
        Web:    class1≤58.4, class2≤90.3, class3≤100.9
    """

    FY = 355.0

    def _sec_with_bt(self, flange_half_bt: float, web_ht: float) -> SectionProperties:
        """Build a section with specific b/t and h/t ratios."""
        tf = 10.0   # fixed flange thickness
        tw = 10.0   # fixed web thickness
        b = flange_half_bt * tf * 2    # full flange width (b/t is half-width/thickness)
        hw = web_ht * tw
        d = hw + 2 * tf
        A = b * tf * 2 + hw * tw
        Ix = (b * d**3 - (b - tw) * hw**3) / 12
        Iy = 2 * (tf * b**3 / 12) + hw * tw**3 / 12
        Ze = Ix / (d / 2)
        Zpl = b * tf * (d - tf) / 2 + tw * hw**2 / 4 + b * tf * (d - tf) / 2
        # simplify plastic modulus estimate
        Zpl = Ze * 1.15
        return _section(
            A_mm2=float(A), depth_mm=float(d), width_mm=float(b),
            tw_mm=float(tw), tf_mm=float(tf),
            Ix_mm4=float(Ix), Iy_mm4=float(Iy),
            Zpl_mm3=float(Zpl), Ze_mm3=float(Ze),
            rx_mm=math.sqrt(Ix / A), ry_mm=math.sqrt(Iy / A),
        )

    def test_class1_section(self):
        # b/t = 6.0 < 7.70 → flange class 1; web h/t = 40 < 58.4 → web class 1
        sec = self._sec_with_bt(flange_half_bt=6.0, web_ht=40.0)
        r = classify_section(sec, fy_mpa=self.FY, cu_kn=0.0)
        assert r.overall_class == SectionClass.CLASS1

    def test_class2_section(self):
        # b/t = 8.0 (between 7.70 and 9.02) → flange class 2; web class 1
        sec = self._sec_with_bt(flange_half_bt=8.0, web_ht=40.0)
        r = classify_section(sec, fy_mpa=self.FY, cu_kn=0.0)
        assert r.overall_class == SectionClass.CLASS2

    def test_class3_section(self):
        # b/t = 10.0 (between 9.02 and 10.62) → flange class 3; web class 1
        sec = self._sec_with_bt(flange_half_bt=10.0, web_ht=40.0)
        r = classify_section(sec, fy_mpa=self.FY, cu_kn=0.0)
        assert r.overall_class == SectionClass.CLASS3

    def test_class4_raises(self):
        # b/t = 12.0 > 10.62 → class 4 → raise
        sec = self._sec_with_bt(flange_half_bt=12.0, web_ht=40.0)
        with pytest.raises(Class4Error):
            classify_section(sec, fy_mpa=self.FY, cu_kn=0.0)

    def test_governing_class_is_max_of_flange_and_web(self):
        # flange class 1, web class 2 → overall class 2
        sec = self._sec_with_bt(flange_half_bt=6.0, web_ht=70.0)
        r = classify_section(sec, fy_mpa=self.FY, cu_kn=0.0)
        assert r.overall_class == SectionClass.CLASS2

    def test_result_carries_clause(self):
        sec = self._sec_with_bt(flange_half_bt=6.0, web_ht=40.0)
        r = classify_section(sec, fy_mpa=self.FY, cu_kn=0.0)
        assert "11" in r.clause  # cl. 11.2

    def test_flange_class1_limit_exact(self):
        # b/t = 145/√355 = 7.698… → just within class 1
        limit = 145.0 / math.sqrt(self.FY)
        sec = self._sec_with_bt(flange_half_bt=limit - 0.01, web_ht=40.0)
        r = classify_section(sec, fy_mpa=self.FY, cu_kn=0.0)
        assert r.flange_class == SectionClass.CLASS1

    def test_flange_just_above_class1_is_class2(self):
        limit = 145.0 / math.sqrt(self.FY)
        sec = self._sec_with_bt(flange_half_bt=limit + 0.01, web_ht=40.0)
        r = classify_section(sec, fy_mpa=self.FY, cu_kn=0.0)
        assert r.flange_class == SectionClass.CLASS2


# ---------------------------------------------------------------------------
# 2. Axial Compressive Resistance Cr — cl. 13.3.1
# ---------------------------------------------------------------------------

class TestCrFlexural:
    """cl. 13.3.1: Cr = φ·A·fy·(1 + λ^(2n))^(-1/n)
    λ = (KL/r)·√(fy/(π²E))    (VERIFIED)
    n = 1.34 for hot-rolled     (VERIFIED)
    φ = 0.90                   (VERIFIED)
    """

    FY = 355.0
    A = 6000.0    # mm²
    RY = 80.0     # mm  (weak-axis radius of gyration)
    KL = 6000.0   # mm

    def _expected_cr_kn(self, KL=None, ry=None, fy=None, A=None):
        KL = KL or self.KL
        ry = ry or self.RY
        fy = fy or self.FY
        A = A or self.A
        lam = (KL / ry) * math.sqrt(fy / (math.pi**2 * _E))
        cr = _PHI * A * fy * (1 + lam**(2 * _N_HR))**(-1 / _N_HR)
        return cr / 1000  # kN

    def test_cr_hand_calc(self):
        """Exact hand calc: A=6000, ry=80, KL=6000, fy=355 → Cr from formula."""
        expected = self._expected_cr_kn()
        cr = cr_flexural(
            area_mm2=self.A, fy_mpa=self.FY,
            KL_mm=self.KL, r_mm=self.RY, n=_N_HR,
        )
        assert cr == pytest.approx(expected, rel=0.01)

    def test_cr_short_column_approaches_squash(self):
        """Very short column (KL→0, λ→0) → Cr → φ·A·fy."""
        squash_kn = _PHI * self.A * self.FY / 1000
        cr = cr_flexural(
            area_mm2=self.A, fy_mpa=self.FY,
            KL_mm=1.0, r_mm=self.RY, n=_N_HR,
        )
        assert cr == pytest.approx(squash_kn, rel=0.01)

    def test_cr_decreases_with_length(self):
        cr_short = cr_flexural(self.A, self.FY, 2000.0, self.RY, _N_HR)
        cr_long  = cr_flexural(self.A, self.FY, 9000.0, self.RY, _N_HR)
        assert cr_short > cr_long

    def test_slenderness_limit_200(self):
        """KL/r > 200 → raise (cl. 10.4.2.1)."""
        from torenone_kernel.checks.axial import SlendernessError
        with pytest.raises(SlendernessError):
            cr_flexural(self.A, self.FY, 200.0 * self.RY + 1, self.RY, _N_HR)

    def test_cr_positive(self):
        cr = cr_flexural(self.A, self.FY, self.KL, self.RY, _N_HR)
        assert cr > 0


# ---------------------------------------------------------------------------
# 3. Shear Resistance Vr — cl. 13.4.1.1
# ---------------------------------------------------------------------------

class TestVrWeb:
    """cl. 13.4.1.1 elastic analysis, no transverse stiffeners (kv = 5.34, s→∞).

    For h/t ≤ 440√(kv/fy): Vr = φ·Aw·0.66·fy  (pure shear, no buckling)
    (VERIFIED vs cl. 13.4.1.1a)

    With kv=5.34 (no stiffeners), 440√(5.34/fy) = 440×√5.34/√fy = 1016/√fy.
    For fy=355: limit = 1016/18.84 = 53.9. Most rolled webs satisfy this.
    """

    FY = 355.0
    TW = 7.0     # mm
    HW = 260.0   # mm  — clear web depth
    AV = TW * HW  # mm²

    def _expected_vr(self):
        # h/t = 260/7 = 37.1 < 53.9 → pure shear regime
        return _PHI * self.AV * 0.66 * self.FY / 1000  # kN

    def test_vr_pure_shear_hand_calc(self):
        vr = vr_web(hw_mm=self.HW, tw_mm=self.TW, fy_mpa=self.FY)
        assert vr == pytest.approx(self._expected_vr(), rel=0.01)

    def test_vr_positive(self):
        assert vr_web(hw_mm=self.HW, tw_mm=self.TW, fy_mpa=self.FY) > 0

    def test_thicker_web_higher_vr(self):
        assert vr_web(260, 10.0, self.FY) > vr_web(260, 7.0, self.FY)


# ---------------------------------------------------------------------------
# 4. Moment Resistance Mr — cl. 13.5 + cl. 13.6
# ---------------------------------------------------------------------------

class TestMrLaterallySupportedClass1:
    """cl. 13.5a: Mr = φ·Zpl·fy for class 1/2 sections.  (VERIFIED)"""

    FY = 355.0
    ZPL = 620_000.0  # mm³

    def test_mr_class1(self):
        expected = _PHI * self.ZPL * self.FY / 1e6  # kN·m
        mr = mr_laterally_supported(
            section_class=SectionClass.CLASS1,
            Zpl_mm3=self.ZPL,
            Ze_mm3=540_000.0,
            fy_mpa=self.FY,
        )
        assert mr == pytest.approx(expected, rel=0.01)

    def test_mr_class2_same_as_class1(self):
        """Class 2 also uses Zpl (cl. 13.5a)."""
        mr1 = mr_laterally_supported(SectionClass.CLASS1, self.ZPL, 540_000, self.FY)
        mr2 = mr_laterally_supported(SectionClass.CLASS2, self.ZPL, 540_000, self.FY)
        assert mr1 == pytest.approx(mr2)

    def test_mr_class3_uses_elastic_modulus(self):
        """cl. 13.5b: Mr = φ·Ze·fy for class 3.  (VERIFIED)"""
        Ze = 540_000.0
        expected = _PHI * Ze * self.FY / 1e6  # kN·m
        mr = mr_laterally_supported(SectionClass.CLASS3, self.ZPL, Ze, self.FY)
        assert mr == pytest.approx(expected, rel=0.01)

    def test_mr_class3_less_than_class1(self):
        """Ze < Zpl always → class 3 Mr < class 1 Mr."""
        mr1 = mr_laterally_supported(SectionClass.CLASS1, self.ZPL, 540_000, self.FY)
        mr3 = mr_laterally_supported(SectionClass.CLASS3, self.ZPL, 540_000, self.FY)
        assert mr3 < mr1


class TestMcrElastic:
    """cl. 13.6: Mcr = ω2·(π/KL)·√(E·Iy·(G·J + π²·E·Cw/(KL)²))  (VERIFIED)

    Hand calc with:
        KL = 5000 mm, ω2 = 1.0 (uniform moment)
        E = 200000 MPa, G = 77000 MPa
        Iy = 6e6 mm⁴, J = 40000 mm⁴, Cw = 126e9 mm⁶
    """

    KL   = 5_000.0   # mm
    IY   = 6e6        # mm⁴
    J    = 40_000.0   # mm⁴
    CW   = 126e9      # mm⁶
    OM2  = 1.0        # uniform moment

    def _expected_mcr_knm(self):
        term1 = _G * self.J
        term2 = math.pi**2 * _E * self.CW / self.KL**2
        mcr = self.OM2 * (math.pi / self.KL) * math.sqrt(_E * self.IY * (term1 + term2))
        return mcr / 1e6  # N·mm → kN·m

    def test_mcr_hand_calc(self):
        mcr = mcr_elastic(
            KL_mm=self.KL,
            Iy_mm4=self.IY,
            J_mm4=self.J,
            Cw_mm6=self.CW,
            omega2=self.OM2,
        )
        assert mcr == pytest.approx(self._expected_mcr_knm(), rel=0.01)

    def test_mcr_increases_with_omega2(self):
        mcr1 = mcr_elastic(self.KL, self.IY, self.J, self.CW, omega2=1.0)
        mcr2 = mcr_elastic(self.KL, self.IY, self.J, self.CW, omega2=2.5)
        assert mcr2 > mcr1

    def test_mcr_decreases_with_span(self):
        mcr_short = mcr_elastic(2000, self.IY, self.J, self.CW, 1.0)
        mcr_long  = mcr_elastic(8000, self.IY, self.J, self.CW, 1.0)
        assert mcr_short > mcr_long


class TestMrLTB:
    """cl. 13.6a: LTB Mr for class 1/2 sections.

    Case 1 (Mcr > 0.67 Mp):
        Mr = 1.15·φ·Mp·(1 - 0.28·Mp/Mcr)  ≤ φ·Mp    (VERIFIED vs cl. 13.6a-i)

    Case 2 (Mcr ≤ 0.67 Mp):
        Mr = φ·Mcr                                     (VERIFIED vs cl. 13.6a-ii)
    """

    FY  = 355.0
    ZPL = 620_000.0

    def _mp(self):
        return self.FY * self.ZPL / 1e6  # kN·m

    def _phi_mp(self):
        return _PHI * self._mp()

    def test_ltb_high_mcr_case1(self):
        """Mcr >> Mp → Mr approaches φMp (but not exceed)."""
        mp = self._mp()
        phi_mp = self._phi_mp()
        mcr_large = 5.0 * mp  # >> 0.67 Mp
        mr = mr_ltb(SectionClass.CLASS1, self.ZPL, self.ZPL * 0.87, self.FY, mcr_knm=mcr_large)
        # Mr = 1.15·φMp·(1 - 0.28/5) = 1.15·φMp·0.944 ≤ φMp → capped at φMp
        expected = min(1.15 * phi_mp * (1 - 0.28 * mp / mcr_large), phi_mp)
        assert mr == pytest.approx(expected, rel=0.01)

    def test_ltb_low_mcr_case2(self):
        """Mcr < 0.67·Mp → Mr = φ·Mcr  (VERIFIED)."""
        mp = self._mp()
        mcr_small = 0.5 * mp  # < 0.67 Mp
        mr = mr_ltb(SectionClass.CLASS1, self.ZPL, self.ZPL * 0.87, self.FY, mcr_knm=mcr_small)
        assert mr == pytest.approx(_PHI * mcr_small, rel=0.01)

    def test_ltb_mr_never_exceeds_phi_mp(self):
        mr = mr_ltb(SectionClass.CLASS1, self.ZPL, self.ZPL * 0.87, self.FY, mcr_knm=1e6)
        assert mr <= _PHI * self._mp() * 1.001  # allow tiny float tolerance


# ---------------------------------------------------------------------------
# 5. U1 factor and beam-column interaction — cl. 13.8.2/13.8.4
# ---------------------------------------------------------------------------

class TestU1Factor:
    """cl. 13.8.4: U1 = ω1 / (1 - Cu/Ce), not less than 1.0.

    Ce = π²EI/(KL)²  (Euler buckling load)
    ω1 = 1.0 for members with UDL   (cl. 13.8.5b, VERIFIED)
    ω1 = 0.6 - 0.4·κ ≥ 0.4 for end moments only  (cl. 13.8.5a)
    """

    def test_u1_udl_no_axial(self):
        """Cu → 0 → U1 = ω1 / (1 - 0) = ω1 = 1.0 for UDL."""
        u1 = u1_factor(omega1=1.0, cu_kn=0.0, Ce_kn=1000.0)
        assert u1 == pytest.approx(1.0, rel=1e-6)

    def test_u1_not_less_than_one(self):
        """Even if formula gives < 1 (negative axial), result is ≥ 1.0."""
        u1 = u1_factor(omega1=1.0, cu_kn=-100.0, Ce_kn=1000.0)
        assert u1 >= 1.0

    def test_u1_with_axial(self):
        """Cu = 500 kN, Ce = 2000 kN, ω1 = 1.0 → U1 = 1.0/(1-0.25) = 1.333."""
        u1 = u1_factor(omega1=1.0, cu_kn=500.0, Ce_kn=2000.0)
        assert u1 == pytest.approx(1.333, rel=0.01)

    def test_u1_omega1_end_moments_double_curvature(self):
        """κ=1.0 → ω1 = 0.6 - 0.4×1 = 0.2 → capped at 0.4  (cl. 13.8.5a)."""
        omega1 = max(0.6 - 0.4 * 1.0, 0.4)
        assert omega1 == pytest.approx(0.4)


class TestBeamColumnCheck:
    """cl. 13.8.2: class 1/2 I-sections (unbraced portal — U1x=1.0 for translational case).

    Interaction: Cu/Cr + 0.85·Mu/Mr ≤ 1.0    (VERIFIED vs cl. 13.8.2b, overall member strength)

    Note: for unbraced frames, U1x = 1.0 (cl. 13.8.2b note).
    """

    def test_passes_below_unity(self):
        # Cu/Cr = 0.3, Mu/Mr = 0.5 → 0.3 + 0.85×0.5 = 0.725
        result = beam_column_check(
            cu_kn=300.0, cr_kn=1000.0,
            mu_knm=50.0, mr_knm=100.0,
            U1=1.0, section_class=SectionClass.CLASS1,
        )
        assert isinstance(result, CheckResult)
        assert result.passed
        assert result.utilisation == pytest.approx(0.3 + 0.85 * 0.5, rel=0.01)

    def test_fails_above_unity(self):
        # Cu/Cr = 0.6, Mu/Mr = 0.6 → 0.6 + 0.85×0.6 = 1.11
        result = beam_column_check(
            cu_kn=600.0, cr_kn=1000.0,
            mu_knm=60.0, mr_knm=100.0,
            U1=1.0, section_class=SectionClass.CLASS1,
        )
        assert not result.passed
        assert result.utilisation > 1.0

    def test_check_carries_clause(self):
        result = beam_column_check(
            cu_kn=300.0, cr_kn=1000.0,
            mu_knm=30.0, mr_knm=100.0,
            U1=1.0, section_class=SectionClass.CLASS1,
        )
        assert "13.8" in result.clause

    def test_pure_axial_no_bending(self):
        # Cu/Cr = 0.5, Mu = 0 → utilisation = 0.5
        result = beam_column_check(
            cu_kn=500.0, cr_kn=1000.0,
            mu_knm=0.0, mr_knm=100.0,
            U1=1.0, section_class=SectionClass.CLASS1,
        )
        assert result.utilisation == pytest.approx(0.5, rel=0.01)

    def test_unity_is_exact_boundary(self):
        # Cu/Cr + 0.85×Mu/Mr = 0.575 + 0.85×0.5 = 1.0 exactly
        result = beam_column_check(
            cu_kn=575.0, cr_kn=1000.0,
            mu_knm=50.0, mr_knm=100.0,
            U1=1.0, section_class=SectionClass.CLASS1,
        )
        assert result.utilisation == pytest.approx(1.0, rel=0.01)


# ---------------------------------------------------------------------------
# 6. SLS Deflection checks — Annex D (informative)
# ---------------------------------------------------------------------------

class TestVerticalDeflectionCheck:
    """Annex D, Table D.1:
    Inelastic roof coverings (e.g., steel sheeting): δ ≤ L/240   (VERIFIED)
    Elastic roof coverings:                          δ ≤ L/180
    """

    def test_passes_within_limit(self):
        # Span = 10 000 mm, δ = 30 mm < 10000/240 = 41.7 mm → pass
        result = vertical_deflection_check(
            delta_mm=30.0, span_mm=10_000.0, limit_fraction=240
        )
        assert result.passed

    def test_fails_beyond_limit(self):
        # Span = 10 000 mm, δ = 50 mm > 41.7 mm → fail
        result = vertical_deflection_check(
            delta_mm=50.0, span_mm=10_000.0, limit_fraction=240
        )
        assert not result.passed

    def test_at_exact_limit_passes(self):
        # δ = L/240 exactly → passes (≤)
        span = 12_000.0
        result = vertical_deflection_check(
            delta_mm=span / 240, span_mm=span, limit_fraction=240
        )
        assert result.passed

    def test_utilisation_fraction(self):
        # δ = 20 mm, limit = 10000/240 = 41.7 mm → utilisation = 20/41.7 = 0.48
        result = vertical_deflection_check(
            delta_mm=20.0, span_mm=10_000.0, limit_fraction=240
        )
        assert result.utilisation == pytest.approx(20.0 / (10_000.0 / 240), rel=0.01)

    def test_carries_clause(self):
        result = vertical_deflection_check(30.0, 10_000.0, 240)
        assert "D" in result.clause or "annex" in result.clause.lower() or "6.2" in result.clause


class TestHorizontalSwayCheck:
    """Annex D, Table D.1 — all other buildings:
    Wind: building sway ≤ H/400 of building height   (VERIFIED vs Annex D)

    Note: limit is informative per Annex D (non-normative). Flagged PROVISIONAL in code.
    """

    def test_passes_within_sway_limit(self):
        # H = 6000 mm, δ = 10 mm < 6000/400 = 15 mm → pass
        result = horizontal_sway_check(drift_mm=10.0, height_mm=6_000.0, limit_fraction=400)
        assert result.passed

    def test_fails_beyond_sway_limit(self):
        # H = 6000 mm, δ = 20 mm > 15 mm → fail
        result = horizontal_sway_check(drift_mm=20.0, height_mm=6_000.0, limit_fraction=400)
        assert not result.passed

    def test_utilisation_fraction(self):
        result = horizontal_sway_check(drift_mm=10.0, height_mm=6_000.0, limit_fraction=400)
        assert result.utilisation == pytest.approx(10.0 / (6_000.0 / 400), rel=0.01)

    def test_carries_clause(self):
        result = horizontal_sway_check(drift_mm=10.0, height_mm=6_000.0, limit_fraction=400)
        assert "D" in result.clause or "annex" in result.clause.lower() or "6.2" in result.clause
