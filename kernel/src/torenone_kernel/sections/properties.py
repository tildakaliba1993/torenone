"""Steel section properties — the data a SANS 10162-1 design needs per section.

This is the *schema*. Authoritative values come from the SAISC Red Book and are loaded at
runtime (see library.py). No real section data ships in this module — only the typed contract.
All dimensional values are in millimetre units (mm, mm^2, mm^3, mm^4, mm^6).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_STRICT = ConfigDict(frozen=True, extra="forbid")


class SectionProperties(BaseModel):
    model_config = _STRICT

    designation: str = Field(min_length=1, description="e.g. 'IPE 400'")
    mass_per_metre_kg_m: float = Field(gt=0, description="Self-weight basis (kg/m).")
    area_mm2: float = Field(gt=0, description="Cross-sectional area A.")

    # Geometry (for section classification)
    depth_mm: float = Field(gt=0)
    width_mm: float = Field(gt=0)
    web_thickness_mm: float = Field(gt=0)
    flange_thickness_mm: float = Field(gt=0)

    # Flexural / axial properties
    second_moment_ix_mm4: float = Field(gt=0, description="Major-axis second moment of area Ix.")
    second_moment_iy_mm4: float = Field(gt=0, description="Minor-axis second moment of area Iy.")
    elastic_modulus_sx_mm3: float = Field(gt=0, description="Major-axis elastic section modulus.")
    plastic_modulus_zx_mm3: float = Field(gt=0, description="Major-axis plastic section modulus.")
    radius_gyration_rx_mm: float = Field(gt=0)
    radius_gyration_ry_mm: float = Field(gt=0)

    # Torsion / warping (for lateral-torsional buckling)
    torsion_constant_j_mm4: float = Field(gt=0)
    warping_constant_cw_mm6: float = Field(gt=0)
