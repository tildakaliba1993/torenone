"""Document metadata for the calc-package cover — admin data, NOT engineering data.

This lets the report present as a proper rational-design submission document (project,
client, responsible engineer, revision) without touching any engineering computation. Every
field is optional; absent fields simply do not render, so a run with no metadata is unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Stamp(BaseModel):
    """A registered engineer's e-stamp recorded on a calc package — professional sign-off.

    Rendered in the sign-off block when present. ``fingerprint`` ties the stamp to the exact
    ``DesignResult`` it was applied to (tamper-evidence): if the design changes, its fingerprint
    changes and no longer matches the stamp. This records that a named, ECSA-registered engineer
    has accepted professional responsibility — it is NOT a claim that TorenOne validated anything.
    """

    model_config = ConfigDict(extra="forbid")

    engineer_name: str = Field(min_length=1)
    ecsa_reg_no: str = Field(min_length=1)
    stamped_at: str = Field(min_length=1, description="ISO-8601 UTC datetime the stamp was applied.")
    fingerprint: str = Field(min_length=1, description="report_fingerprint(result) at stamp time.")


class ReportMetadata(BaseModel):
    """Optional cover-sheet / document-control fields for a calc package."""

    model_config = ConfigDict(extra="forbid")

    project_name: str | None = None
    client: str | None = None
    project_number: str | None = None
    site_address: str | None = None
    engineer_name: str | None = None
    engineer_reg_no: str | None = None
    revision: str | None = None

    def has_any(self) -> bool:
        """True if at least one field is filled (drives whether the cover block renders)."""
        return any(
            (value or "").strip()
            for value in (
                self.project_name,
                self.client,
                self.project_number,
                self.site_address,
                self.engineer_name,
                self.engineer_reg_no,
                self.revision,
            )
        )
