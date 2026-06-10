"""Result contracts — the typed outputs each kernel stage produces.

Pure structure + safety-relevant aggregation. No engineering values are defined here; modules
that compute them (loads, analysis, checks) populate these models, validated against worked
examples. All models are frozen and reject unknown fields.
"""

from __future__ import annotations

import types
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from torenone_kernel.models.enums import LimitState, LoadType
from torenone_kernel.models.frame_spec import FrameSpec

_STRICT = ConfigDict(frozen=True, extra="forbid")


class LoadCase(BaseModel):
    model_config = _STRICT
    name: str = Field(min_length=1)
    load_type: LoadType
    description: Optional[str] = None


class LoadCombination(BaseModel):
    """A limit-state load combination. `factors` maps load-case name -> partial factor.

    The factor *values* are filled by the SANS 10160-1 module (verified). This contract only
    guarantees the shape and that a combination references at least one case.
    """

    model_config = _STRICT
    name: str = Field(min_length=1)
    limit_state: LimitState
    factors: dict[str, float]

    @field_validator("factors")
    @classmethod
    def _non_empty(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("a load combination must reference at least one load case")
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def referenced_cases(self) -> tuple[str, ...]:
        return tuple(self.factors.keys())


class MemberForces(BaseModel):
    """Internal forces at a named location (e.g. 'column base', 'eaves', 'apex')."""

    model_config = _STRICT
    location: str = Field(min_length=1)
    axial_kn: float
    shear_kn: float
    moment_knm: float


class AnalysisResult(BaseModel):
    model_config = _STRICT
    combination: str = Field(min_length=1)
    forces: list[MemberForces] = Field(min_length=1)


class CheckResult(BaseModel):
    """One code check. Every check MUST cite its clause (PRD FR-18)."""

    model_config = _STRICT
    name: str = Field(min_length=1)
    clause: str = Field(min_length=1, description="SANS clause reference for this check.")
    utilisation: float = Field(ge=0, description="Demand / capacity.")
    passed: bool
    detail: Optional[str] = None


class SectionChoice(BaseModel):
    model_config = _STRICT
    member: str = Field(min_length=1)        # e.g. "rafter" | "column"
    designation: str = Field(min_length=1)   # e.g. "IPE 400"


class DeadLoadResult(BaseModel):
    """Characteristic permanent (dead) loads as line loads on the frame members.

    Carries a breakdown (roof area load, tributary width, self-weights) so the audit /
    "show-your-working" view (PRD FR-26) can show how each line load was derived.
    """

    model_config = _STRICT
    rafter_udl_kn_per_m: float = Field(ge=0, description="Total dead UDL on the rafter.")
    column_self_weight_kn_per_m: float = Field(ge=0)
    wall_cladding_udl_kn_per_m: float = Field(ge=0, description="Cladding dead load on the column.")
    # Breakdown (for transparency / audit)
    roof_area_load_kpa: float = Field(ge=0, description="Roof permanent area load (sheeting + services).")
    rafter_self_weight_kn_per_m: float = Field(ge=0)
    tributary_width_m: float = Field(gt=0, description="Frame spacing (typical internal frame).")


class ImposedLoadResult(BaseModel):
    """Characteristic imposed (variable) roof load as a line load on the rafter.

    Carries the category + clause citation for the audit / "show-your-working" view (FR-26).
    The underlying code value is PROVISIONAL (see loads/imposed.py and REFERENCES doc).
    """

    model_config = _STRICT
    roof_udl_kn_per_m: float = Field(ge=0, description="Imposed UDL on the rafter.")
    roof_imposed_kpa: float = Field(ge=0, description="Characteristic imposed roof load (area).")
    tributary_width_m: float = Field(gt=0)
    category: str = Field(min_length=1, description="Roof category description.")
    clause: str = Field(min_length=1, description="SANS clause/table reference.")


class AutosizeResult(BaseModel):
    """Output of the auto-sizing search (Task 1.11).

    Contains the lightest section from the library that passes all strength checks,
    together with every check result so the engineer can review utilisations.
    """

    model_config = _STRICT
    member: str = Field(min_length=1, description="'rafter' or 'column'.")
    designation: str = Field(min_length=1, description="Chosen section designation.")
    section_class_value: int = Field(ge=1, le=3, description="SANS 10162-1 cl. 11 class (1, 2, or 3).")
    checks: list[CheckResult] = Field(min_length=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def max_utilisation(self) -> float:
        return max(c.utilisation for c in self.checks)

    @property
    def section(self) -> types.SimpleNamespace:
        """Convenience accessor: r.section.designation == r.designation."""
        return types.SimpleNamespace(designation=self.designation)


class SwaySensitivityResult(BaseModel):
    """Second-order sway check result — SANS 10162-1:2011 cl. 8.7.

    U2 = 1/(1 − ΣΔu·Cu/(ΣVu·h))

    Sway-sensitivity threshold U2 > 1.4 is the CSA S16 basis value. SANS 10162-1 cl. 8.7
    does not state an explicit numerical cutoff; **this threshold is PROVISIONAL** pending
    registered-engineer sign-off.
    """

    model_config = _STRICT
    combination: str = Field(min_length=1)
    U2: float = Field(ge=1.0, description="SANS 10162-1 cl. 8.7 sway amplification factor.")
    stability_index: float = Field(
        ge=0.0, description="θ = ΣΔu·Cu/(ΣVu·h) = 1 − 1/U2."
    )
    eaves_drift_mm: float = Field(ge=0.0, description="Lateral sway at eaves under notional force (mm).")
    notional_force_kn: float = Field(gt=0.0, description="0.005 × total factored gravity (cl. 8.7).")
    is_sway_sensitive: bool = Field(
        description="True if U2 > 1.4 (PROVISIONAL threshold — CSA S16 basis)."
    )


class DesignResult(BaseModel):
    """The full output of a design run: input echo, chosen sections, checks, audit metadata."""

    model_config = _STRICT
    frame_spec: FrameSpec
    sections: list[SectionChoice] = Field(min_length=1)
    checks: list[CheckResult]
    rules_version: dict[str, str]
    warnings: tuple[str, ...] = ()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        # SAFETY: an empty check set must never report a pass.
        return bool(self.checks) and all(c.passed for c in self.checks)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def governing_utilisation(self) -> float:
        return max((c.utilisation for c in self.checks), default=0.0)
