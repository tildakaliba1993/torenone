"""The FrameSpec contract — a validated, immutable description of one steel portal frame.

This is the single input contract for the kernel AND the structured-output target for the AI
parsing layer. It is `frozen` (immutable -> deterministic) and forbids unknown fields, so a
misparse fails loudly instead of silently feeding a wrong design downstream (PRD FR-1/FR-3).

Engineering numbers are NOT computed here — only pure geometry (apex height, building length).
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, computed_field

from torenone_kernel.models.enums import BaseFixity, RoofType, SteelGrade, TerrainCategory

_STRICT = ConfigDict(frozen=True, extra="forbid")


class FrameGeometry(BaseModel):
    """Geometry of a single-bay pitched portal frame (symmetric duopitch, or mono-pitch)."""

    model_config = _STRICT

    span_m: float = Field(gt=0, description="Clear span, eaves to eaves (m).")
    eaves_height_m: float = Field(
        gt=0,
        description="Column height to eaves (m). For a mono-pitch roof this is the LOW eaves.",
    )
    roof_pitch_deg: float = Field(
        gt=0, le=45, description="Roof pitch (deg). >45 is out of MVP scope."
    )
    bay_spacing_m: float = Field(
        gt=0, description="Frame spacing = tributary width of one internal frame (m)."
    )
    number_of_bays: int = Field(ge=1, description="Number of bays along the building length.")
    roof_type: RoofType = Field(
        default=RoofType.DUOPITCH,
        description="Roof shape. DUOPITCH (symmetric, default) or MONOPITCH (single slope, "
        "PROVISIONAL — pending engineer validation).",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def apex_height_m(self) -> float:
        # Duopitch apex at mid-span. (Not used for mono-pitch — see high_eaves_height_m.)
        return self.eaves_height_m + (self.span_m / 2.0) * math.tan(
            math.radians(self.roof_pitch_deg)
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def high_eaves_height_m(self) -> float:
        # Mono-pitch high eaves, rising over the full span. (Unused for a duopitch.)
        return self.eaves_height_m + self.span_m * math.tan(math.radians(self.roof_pitch_deg))

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
    rafter_restraint_spacing_m: float | None = Field(
        default=None, gt=0, description="Purlin spacing restraining the rafter (m)."
    )
    column_restraint_spacing_m: float | None = Field(
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
        gt=0, description="Basic wind speed vb from the SANS 10160-3 map (m/s)."
    )
    terrain_category: TerrainCategory = Field(description="SANS 10160-3:2019 terrain category.")
    site_altitude_m: float = Field(
        default=0.0, ge=0, description="Site altitude above sea level (m) — for air density (Table 4)."
    )
    has_dominant_opening: bool = Field(
        default=False,
        description="Large dominant opening (e.g. roller door) => governing internal-pressure / uplift cases.",
    )


class FoundationInputs(BaseModel):
    """Inputs for the column baseplate + pad-footing design (Task 1.18)."""

    model_config = _STRICT
    allowable_bearing_kpa: float | None = Field(
        default=None,
        gt=0,
        description=(
            "Site allowable bearing pressure (kPa) — an engineer/geotechnical input. "
            "NEVER assumed: if omitted, the pad footing is not designed (members, "
            "connections and baseplate still are)."
        ),
    )
    concrete_fcu_mpa: float = Field(
        default=25.0,
        gt=0,
        description="Concrete cube strength fcu (MPa) for baseplate bearing + footing. "
        "Default 25 MPa (typical SA value).",
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
    foundation: FoundationInputs = Field(default_factory=FoundationInputs)
