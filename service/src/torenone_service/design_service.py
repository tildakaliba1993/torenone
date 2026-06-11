"""Kernel dispatch for the /design route (Task 4.4).

Translates a :class:`~torenone_service.schemas.DesignRequest` into the right kernel
call (``design`` auto-sizing or ``check`` against supplied sections) and converts the
kernel's input-driven failures into a single :class:`DesignError` with a safe message.
A *failed* design (``result.passed is False``) is a normal result, not an error.
"""

from __future__ import annotations

from torenone_kernel.analysis.sway_check import FrameUnstableError
from torenone_kernel.checks.autosize import NoSectionFoundError
from torenone_kernel.design import DEFAULT_COST_RATE_ZAR_PER_KG, check, design
from torenone_kernel.models.results import DesignResult

from torenone_service.schemas import DesignRequest


class DesignError(Exception):
    """An input-driven failure to produce a design (mapped to HTTP 422)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def run_design(body: DesignRequest) -> DesignResult:
    """Run the kernel for *body*; raise :class:`DesignError` on input-driven failure."""
    rate = (
        body.cost_rate_zar_per_kg
        if body.cost_rate_zar_per_kg is not None
        else DEFAULT_COST_RATE_ZAR_PER_KG
    )

    if body.mode == "check":
        if not body.sections:
            raise DesignError("check mode requires a non-empty 'sections' list")
        try:
            return check(body.spec, body.sections, rate)
        except (KeyError, ValueError) as exc:
            raise DesignError(f"invalid sections: {exc}") from exc

    # mode == "design"
    try:
        return design(body.spec, rate)
    except NoSectionFoundError as exc:
        raise DesignError(
            "no section in the library satisfies this frame; "
            "try a different geometry or use check mode"
        ) from exc
    except FrameUnstableError as exc:
        raise DesignError(
            "the frame is geometrically unstable under the given loads"
        ) from exc
