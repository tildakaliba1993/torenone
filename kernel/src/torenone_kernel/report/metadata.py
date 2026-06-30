"""Document metadata for the calc-package cover — admin data, NOT engineering data.

This lets the report present as a proper rational-design submission document (project,
client, responsible engineer, revision) without touching any engineering computation. Every
field is optional; absent fields simply do not render, so a run with no metadata is unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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
