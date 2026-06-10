"""Section classification — SANS 10162-1:2011 cl. 11.

Table 4 — Maximum width-to-thickness ratios: elements in flexural compression.

For I-sections (flange half-outstand b = width/2):
    Class 1: b/t ≤ 145/√fy   (VERIFIED vs Table 4)
    Class 2: b/t ≤ 170/√fy   (VERIFIED vs Table 4)
    Class 3: b/t ≤ 200/√fy   (VERIFIED vs Table 4)
    Class 4: b/t >  200/√fy  → out of scope — raise Class4Error

For I-section webs in flexural compression (Cu ≥ 0, axial load effect included):
    Class 1: h/t ≤ (1100/√fy)·(1 - 0.39·Cu/(φ·A·fy))   (VERIFIED vs Table 4)
    Class 2: h/t ≤ (1700/√fy)·(1 - 0.61·Cu/(φ·A·fy))   (VERIFIED vs Table 4)
    Class 3: h/t ≤ (1900/√fy)·(1 - 0.65·Cu/(φ·A·fy))   (VERIFIED vs Table 4)

Overall class = max(flange class, web class) — the governing element governs.

φ = 0.90  (cl. 13.1a, VERIFIED)
"""

from __future__ import annotations

import math
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from torenone_kernel.sections.properties import SectionProperties

_PHI = 0.90   # cl. 13.1a


class SectionClass(IntEnum):
    CLASS1 = 1
    CLASS2 = 2
    CLASS3 = 3


class Class4Error(ValueError):
    """Raised when a section is classified as Class 4.

    Class 4 sections are out of the MVP scope. The engineer must select a more compact
    section. (SANS 10162-1:2011 cl. 11.1.1d; see also 13.3.3 and 13.5c for Class 4 rules
    which are deferred post-MVP.)
    """


class ClassificationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    flange_class: SectionClass
    web_class: SectionClass
    overall_class: SectionClass
    flange_bt: float = Field(description="Actual half-flange outstand-to-thickness ratio.")
    web_ht: float    = Field(description="Actual clear web depth-to-thickness ratio.")
    fy_mpa: float
    clause: str = Field(default="SANS 10162-1:2011 cl. 11.2, Table 4")


def _flange_class(bt: float, fy: float) -> SectionClass:
    """Classify flange based on half-outstand b/t ratio (Table 4)."""
    sq = math.sqrt(fy)
    if bt <= 145.0 / sq:
        return SectionClass.CLASS1
    if bt <= 170.0 / sq:
        return SectionClass.CLASS2
    if bt <= 200.0 / sq:
        return SectionClass.CLASS3
    raise Class4Error(
        f"Flange b/t = {bt:.2f} exceeds class-3 limit {200/sq:.2f} (fy={fy} MPa). "
        "Class 4 sections are out of MVP scope — select a more compact section."
    )


def _web_class(ht: float, fy: float, cu_kn: float, area_mm2: float) -> SectionClass:
    """Classify web based on clear-depth h/t ratio and axial load Cu (Table 4).

    For pure bending (Cu = 0), the reduction factor = 1.0.
    For combined axial + bending, the limits tighten as Cu increases.
    """
    sq = math.sqrt(fy)
    phi_cy = _PHI * area_mm2 * fy / 1000  # kN  — φ·A·fy
    # Reduction factors from Table 4 formulas
    factor1 = max(1.0 - 0.39 * cu_kn / phi_cy, 0.0) if phi_cy > 0 else 1.0
    factor2 = max(1.0 - 0.61 * cu_kn / phi_cy, 0.0) if phi_cy > 0 else 1.0
    factor3 = max(1.0 - 0.65 * cu_kn / phi_cy, 0.0) if phi_cy > 0 else 1.0

    lim1 = (1100.0 / sq) * factor1
    lim2 = (1700.0 / sq) * factor2
    lim3 = (1900.0 / sq) * factor3

    if ht <= lim1:
        return SectionClass.CLASS1
    if ht <= lim2:
        return SectionClass.CLASS2
    if ht <= lim3:
        return SectionClass.CLASS3
    raise Class4Error(
        f"Web h/t = {ht:.2f} exceeds class-3 limit {lim3:.2f} (fy={fy} MPa, Cu={cu_kn} kN). "
        "Class 4 sections are out of MVP scope — select a more compact section."
    )


def classify_section(
    section: SectionProperties,
    fy_mpa: float,
    cu_kn: float = 0.0,
) -> ClassificationResult:
    """Classify an I-section per SANS 10162-1:2011 cl. 11.2, Table 4.

    Parameters
    ----------
    section : SectionProperties
    fy_mpa  : design yield stress (MPa)
    cu_kn   : factored axial compressive force (kN, ≥ 0). Use 0 for pure bending.

    Returns
    -------
    ClassificationResult — raises Class4Error if the section is Class 4.

    Width definitions (cl. 11.3.1c):
        b (flange outstand) = half of full nominal flange width = width/2
        t (flange thickness) = flange_thickness_mm

    Web clear depth (cl. 11.3.2c for rolled sections):
        hw = d - 2·tf  (clear distance between flanges)
    """
    b_half = section.width_mm / 2.0       # half-flange outstand (cl. 11.3.1c)
    bt = b_half / section.flange_thickness_mm

    hw = section.depth_mm - 2.0 * section.flange_thickness_mm   # cl. 11.3.2c
    ht = hw / section.web_thickness_mm

    fc = _flange_class(bt, fy_mpa)
    wc = _web_class(ht, fy_mpa, cu_kn, section.area_mm2)

    overall = SectionClass(max(fc, wc))
    return ClassificationResult(
        flange_class=fc,
        web_class=wc,
        overall_class=overall,
        flange_bt=bt,
        web_ht=ht,
        fy_mpa=fy_mpa,
    )
