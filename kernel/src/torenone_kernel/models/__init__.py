"""Kernel domain models (Pydantic). Public contract for the kernel and the AI parsing layer."""

from torenone_kernel.models.enums import (
    BaseFixity,
    LimitState,
    LoadType,
    SteelGrade,
    TerrainCategory,
)
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    ImposedLoadInputs,
    Materials,
    Restraints,
    WindContext,
)
from torenone_kernel.models.results import (
    AnalysisResult,
    CheckResult,
    DesignResult,
    LoadCase,
    LoadCombination,
    MemberForces,
    SectionChoice,
)

__all__ = [
    # enums
    "BaseFixity",
    "SteelGrade",
    "TerrainCategory",
    "LimitState",
    "LoadType",
    # input contract
    "FrameGeometry",
    "Materials",
    "Restraints",
    "DeadLoadInputs",
    "ImposedLoadInputs",
    "WindContext",
    "FrameSpec",
    # result contracts
    "LoadCase",
    "LoadCombination",
    "MemberForces",
    "AnalysisResult",
    "CheckResult",
    "SectionChoice",
    "DesignResult",
]
