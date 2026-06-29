"""The `DesignCode` interface — the seam that makes the kernel code-agnostic.

A *design code* bundles everything that differs between national steel codes: the section
classification rules, the member-resistance equations, the resistance factors and their clause
references, the load combinations, the material yield values, and the section catalogue. The
orchestrator (`design.py`, `checks/autosize.py`) depends only on this interface, so adding a new
code (e.g. AISC 360) is a new subclass — not a rewrite.

The first implementation is `codes.sans10162.SANS10162`, which delegates to the existing,
Red-Book-validated `checks/*` functions (the SANS maths is unchanged). Each code is responsible
for its own clause strings and units.

Out-of-scope signalling (kept identical to the pre-refactor behaviour): an implementation may
raise ``Class4Error`` (classification out of scope), ``SlendernessError`` (KL/r over the limit),
or ``NotImplementedError`` (e.g. tension-field shear) from the relevant method; the auto-sizer
catches these to skip a section.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from torenone_kernel.checks.classification import ClassificationResult, SectionClass
from torenone_kernel.models.enums import SteelGrade
from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import CheckResult, LoadCombination
from torenone_kernel.sections.library import SectionLibrary
from torenone_kernel.sections.properties import SectionProperties


class DesignCode(ABC):
    """A pluggable national steel design code. See module docstring."""

    #: Stable identifier, e.g. "SANS10162".
    id: str
    #: Unit system the code's published values use ("metric" | "imperial").
    unit_system: str

    @abstractmethod
    def rules_version(self) -> dict[str, str]:
        """Pinned standard editions, stamped into every result/report for auditability."""

    # --- Inputs: material, sections, load combinations ----------------------------------------
    @abstractmethod
    def section_library(self) -> SectionLibrary:
        """The catalogue of sections the auto-designer may choose from."""

    @abstractmethod
    def material_fy(self, grade: SteelGrade, thickness_mm: float) -> float:
        """Design yield stress fy (MPa) for the steel grade and element thickness."""

    @abstractmethod
    def load_combinations(self, spec: FrameSpec) -> tuple[LoadCombination, ...]:
        """The ULS + SLS factored load combinations for this code."""

    # --- Member design operations -------------------------------------------------------------
    @abstractmethod
    def classify(
        self, section: SectionProperties, fy_mpa: float, cu_kn: float
    ) -> ClassificationResult:
        """Section classification. Raises when the section is out of scope (e.g. Class 4)."""

    @abstractmethod
    def axial_resistance(
        self, section: SectionProperties, fy_mpa: float, kl_mm: float, ltb_mm: float, n: float
    ) -> float:
        """Factored axial compressive resistance Cr (kN), the weaker of the two buckling axes.

        ``kl_mm`` is the full member effective length (major axis); ``ltb_mm`` is the
        lateral-restraint spacing that braces the minor axis (full length when ≤ 1).
        """

    @abstractmethod
    def shear_resistance(self, section: SectionProperties, fy_mpa: float) -> float:
        """Factored shear resistance Vr (kN)."""

    @abstractmethod
    def moment_resistance(
        self,
        section: SectionProperties,
        section_class: SectionClass,
        fy_mpa: float,
        ltb_mm: float,
        omega2: float,
    ) -> float:
        """Factored moment resistance Mr (kN·m), including lateral-torsional buckling."""

    @abstractmethod
    def moment_gradient_omega2(self, kappa: float) -> float:
        """Moment-gradient factor for the LTB resistance."""

    @abstractmethod
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
        """Combined axial + bending interaction check (returns a CheckResult with its clause)."""

    # --- Reference strings + limits -----------------------------------------------------------
    @abstractmethod
    def clause(self, key: str) -> str:
        """Clause reference for a member check. Keys: 'axial', 'shear', 'moment'."""

    @abstractmethod
    def deflection_limit_fraction(self) -> int:
        """SLS vertical-deflection limit denominator (e.g. 240 → span/240)."""
