"""Result contracts — the typed outputs each kernel stage produces.

Pure structure + safety-relevant aggregation. No engineering values are defined here; modules
that compute them (loads, analysis, checks) populate these models, validated against worked
examples. All models are frozen and reject unknown fields.
"""

from __future__ import annotations

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
