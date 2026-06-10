"""Pinned code-rule editions.

These strings are stamped into every DesignResult and every report so that results are
reproducible and auditable (PRD NFR-3, FR-20). Pinning the edition means a future code
update can never silently change an existing report.

⚠️ VERIFY EDITIONS against the purchased SANS standards before the validation gate.
   The years below are best-known from public sources and MUST be confirmed by the
   registered engineer (co-founder) against the official documents.
"""

from __future__ import annotations

# Loading / actions
SANS_10160_1 = "2009 (DRAFT — confirm vs final)"  # Basis of design / load combinations
SANS_10160_2 = "VERIFY"  # Self-weight and imposed loads
SANS_10160_3 = "2019"    # Wind actions, Edition 2.1 (confirmed from the standard)

# Steel design
SANS_10162_1 = "2011"    # Limit-states design of hot-rolled steelwork — confirmed via public refs; VERIFY

# Section property data source
SECTION_DATA_SOURCE = "SAISC Red Book — VERIFY edition"


def as_dict() -> dict[str, str]:
    """Return the pinned editions for embedding in DesignResult / report metadata."""
    return {
        "SANS 10160-1": SANS_10160_1,
        "SANS 10160-2": SANS_10160_2,
        "SANS 10160-3": SANS_10160_3,
        "SANS 10162-1": SANS_10162_1,
        "section_data": SECTION_DATA_SOURCE,
    }
