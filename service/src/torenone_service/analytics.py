"""Minimal product-analytics signal (Task 5.4).

A design run is the core product event. We don't ship a third-party analytics SDK
(no extra dependency, no PII leaving the box); instead we emit one structured log
line per completed design — ``event="design_run"`` — carrying exactly the fields the
pilot needs to answer *how many designs ran, the pass/fail rate, and the latency*
(Phase-9 evidence). The :mod:`logging_config` JSON formatter promotes every field to a
top-level key, so a log collector can aggregate them without parsing the message.

No PII: only the opaque ``user_id`` (already in the JWT ``sub``) is included — never the
email, the description, or the frame_spec.
"""

from __future__ import annotations

from typing import Any

from torenone_kernel.models.results import DesignResult

DESIGN_EVENT = "design_run"


def design_event_fields(
    *,
    user_id: str,
    mode: str,
    result: DesignResult,
    duration_ms: float,
    report_id: str | None = None,
) -> dict[str, Any]:
    """Build the structured fields for a completed-design analytics event.

    Captures the Task-5.4 signal: pass/fail (``passed``), the governing utilisation,
    the tonnage, the section count, and end-to-end latency (``duration_ms``).
    """
    return {
        "event": DESIGN_EVENT,
        "user_id": user_id,
        "mode": mode,
        "passed": result.passed,
        "governing_utilisation": result.governing_utilisation,
        "total_steel_tonnes": result.total_steel_tonnes,
        "section_count": len(result.sections),
        "duration_ms": duration_ms,
        "report_id": report_id,
    }
