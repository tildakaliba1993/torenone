"""The FrameSpec contract — a validated, immutable description of one steel portal frame.

This is the single input contract for the kernel AND the structured-output target for the AI
parsing layer. It is `frozen` (immutable -> deterministic) and forbids unknown fields, so a
misparse fails loudly instead of silently feeding a wrong design downstream (PRD FR-1/FR-3).

Engineering numbers are NOT computed here — only pure geometry (apex height, building length).
"""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from torenone_kernel.models.enums import BaseFixity, SteelGrade, TerrainCategory

_STRICT = ConfigDict(frozen=True, extra="forbid")


class FrameGeometry(BaseModel):
    """Geometry of a single-bay symmetric pitched portal frame."""

    model_config = _STRICT

    span_m: float = Field(gt=0, description="Clear span, eaves to eaves (m).")
    eaves_height_m: float = Field(gt=0, description="Column height to eaves (m).")
    roof_pitch_deg: float = Field(
        gt=0, le=45, description="Roof pitch (deg). >45 is out of MVP scope."
    )
    bay_spacing_m: float = Field(
        gt=0, description="Frame spacing = tributary width of one internal frame (m)."
    )
    number_of_bays: int = Field(ge=1, description="Number of bays along the building length.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def apex_height_m(self) -> float:
        return self.eaves_height_m + (self.span_m / 2.0) * math.tan(
            math.radians(self.roof_pitch_deg)
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def building_length_m(self) -> float:
        return self.bay_spacing_m * self.number_of_bays


class Materials(BaseModel):
    model_config = _STRICT
    steel_grade: SteelGrade = SteelGrade.S355JR


class Restraints(BaseModel):
    """Lateral restraint spacing for LTB checks. None => unrestrained (kernel treats conservatively)."""

    model_config = _STRICT
    rafter_restraint_spacing_m: Optional[float] = Field(
        default=None, gt=0, description="Purlin spacing restraining the rafter (m)."
    )
    column_restraint_spacing_m: Optional[float] = Field(
        default=None, gt=0, description="Girt spacing restraining the column (m)."
    )


class DeadLoadInputs(BaseModel):
    """Permanent (dead) load inputs. Steel self-weight is added by the kernel from chosen sections."""

    model_config = _STRICT
    roof_kpa: float = Field(
        ge=0, description="Roof permanent load incl. sheeting/purlins/insulation (kPa)."
    )
    services_kpa: float = Field(default=0.0, ge=0)
    wall_cladding_kpa: float = Field(default=0.0, ge=0)


class ImposedLoadInputs(BaseModel):
    model_config = _STRICT
    roof_access: bool = Field(
        default=False,
        description="Accessible roof? Drives the SANS 10160-2 imposed roof category (value computed by kernel).",
    )


class WindContext(BaseModel):
    model_config = _STRICT
    basic_wind_speed_ms: float = Field(
        gt=0, description="Basic wind speed from the SANS 10160-3 map (m/s)."
    )
    terrain_category: TerrainCategory = Field(description="SANS 10160-3 terrain category — VERIFY.")
    has_dominant_opening: bool = Field(
        default=False,
        description="Large dominant opening (e.g. roller door) => governing internal-pressure / uplift cases.",
    )


class FrameSpec(BaseModel):
    """The complete, validated input for one portal-frame design run (MVP scope)."""

    model_config = _STRICT

    geometry: FrameGeometry
    materials: Materials = Field(default_factory=Materials)
    base_fixity: BaseFixity = BaseFixity.PINNED
    restraints: Restraints = Field(default_factory=Restraints)
    dead: DeadLoadInputs
    imposed: ImposedLoadInputs = Field(default_factory=ImposedLoadInputs)
    wind: WindContext
