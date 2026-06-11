"""Task 2.5 — Audit metadata in the rendered report (PRD FR-20).

FR-20: "Reports shall record the code-rule version used, the input spec,
and a timestamp for audit/reproducibility."

This module tests that every mandatory audit-metadata field is present and
correct in the rendered HTML.

Run with Python 3.9:
    PYTHONPATH="kernel/src:tools" python3 -m pytest kernel/tests/test_audit_metadata.py -q
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest

from torenone_kernel.design import design
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.report.renderer import render_html, report_fingerprint


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def spec():
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )


@pytest.fixture(scope="module")
def result(spec):
    return design(spec)


@pytest.fixture(scope="module")
def html(result):
    return render_html(result)


# ---------------------------------------------------------------------------
# 1. Timestamp — full ISO-8601 datetime (not just date)
# ---------------------------------------------------------------------------

class TestTimestamp:
    def test_timestamp_present_in_html(self, html):
        """The report must contain a full ISO-8601 timestamp (PRD FR-20)."""
        # ISO-8601 pattern: YYYY-MM-DDTHH:MM (with optional seconds / timezone)
        pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"
        assert re.search(pattern, html), (
            "No ISO-8601 datetime (YYYY-MM-DDTHH:MM) found in HTML. "
            "FR-20 requires a full timestamp, not just a date."
        )

    def test_timestamp_includes_utc_indicator(self, html):
        """Timestamp should carry timezone info (Z or +00:00) for unambiguous audit trail."""
        assert "Z" in html or "+00:00" in html or "UTC" in html, (
            "Timestamp has no UTC indicator (Z / +00:00 / UTC)"
        )

    def test_generated_at_label_present(self, html):
        """The report should label the timestamp with a human-readable field name."""
        html_lower = html.lower()
        assert "generated" in html_lower or "timestamp" in html_lower, (
            "No 'Generated' or 'Timestamp' label found near the datetime"
        )


# ---------------------------------------------------------------------------
# 2. Complete input spec echo (all FrameSpec fields)
# ---------------------------------------------------------------------------

class TestInputSpecEcho:
    """FR-20: the full input spec must be embedded so the report is self-contained."""

    def test_span_present(self, html, result):
        geom = result.frame_spec.geometry
        assert str(geom.span_m) in html, f"Span {geom.span_m} m not in HTML"

    def test_eaves_height_present(self, html, result):
        geom = result.frame_spec.geometry
        assert str(geom.eaves_height_m) in html

    def test_roof_pitch_present(self, html, result):
        geom = result.frame_spec.geometry
        assert str(geom.roof_pitch_deg) in html

    def test_bay_spacing_present(self, html, result):
        geom = result.frame_spec.geometry
        assert str(geom.bay_spacing_m) in html

    def test_number_of_bays_present(self, html, result):
        geom = result.frame_spec.geometry
        assert str(geom.number_of_bays) in html

    def test_dead_load_roof_kpa_present(self, html, result):
        dead = result.frame_spec.dead
        assert str(dead.roof_kpa) in html

    def test_services_kpa_present(self, html, result):
        dead = result.frame_spec.dead
        assert str(dead.services_kpa) in html

    def test_wind_speed_present(self, html, result):
        wind = result.frame_spec.wind
        assert str(wind.basic_wind_speed_ms) in html

    def test_terrain_category_present(self, html, result):
        wind = result.frame_spec.wind
        assert wind.terrain_category.value in html

    def test_steel_grade_present(self, html, result):
        assert result.frame_spec.materials.steel_grade.value in html

    def test_base_fixity_present(self, html, result):
        assert result.frame_spec.base_fixity.value in html


# ---------------------------------------------------------------------------
# 3. Rules version — all standards + versions present (PRD FR-20)
# ---------------------------------------------------------------------------

class TestRulesVersionInReport:
    def test_all_standard_keys_in_html(self, html, result):
        for key in result.rules_version:
            assert key in html, f"Standard key {key!r} not in HTML"

    def test_all_standard_versions_in_html(self, html, result):
        for key, val in result.rules_version.items():
            assert val in html, f"Version {val!r} for {key!r} not in HTML"

    def test_sans_10162_version_present(self, html):
        assert "SANS 10162-1" in html
        assert "2011" in html

    def test_rules_version_section_has_heading(self, html):
        """Must be in a labelled section — not just buried in a comment."""
        html_lower = html.lower()
        assert "standards" in html_lower or "rules version" in html_lower, (
            "No 'Standards' or 'Rules Version' heading found"
        )


# ---------------------------------------------------------------------------
# 4. Report fingerprint — deterministic SHA-256 hash of DesignResult
# ---------------------------------------------------------------------------

class TestReportFingerprint:
    def test_fingerprint_function_exported(self):
        """report_fingerprint() must be importable from renderer."""
        assert callable(report_fingerprint)

    def test_fingerprint_returns_hex_string(self, result):
        fp = report_fingerprint(result)
        assert isinstance(fp, str)
        # Valid hex (SHA-256 = 64 hex chars)
        assert re.fullmatch(r"[0-9a-f]{64}", fp), (
            f"Fingerprint is not 64-char lowercase hex: {fp!r}"
        )

    def test_fingerprint_deterministic(self, result):
        """Same DesignResult → same fingerprint (deterministic kernel guarantee)."""
        fp1 = report_fingerprint(result)
        fp2 = report_fingerprint(result)
        assert fp1 == fp2

    def test_different_result_different_fingerprint(self):
        """Different frame → different fingerprint."""
        spec_a = FrameSpec(
            geometry=FrameGeometry(span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
                                   bay_spacing_m=6.0, number_of_bays=5),
            dead=DeadLoadInputs(roof_kpa=0.20),
            wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
        )
        spec_b = FrameSpec(
            geometry=FrameGeometry(span_m=20.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
                                   bay_spacing_m=6.0, number_of_bays=5),
            dead=DeadLoadInputs(roof_kpa=0.20),
            wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
        )
        fp_a = report_fingerprint(design(spec_a))
        fp_b = report_fingerprint(design(spec_b))
        assert fp_a != fp_b, "Different frames produced identical fingerprints"

    def test_fingerprint_embedded_in_html(self, html, result):
        """The fingerprint must appear in the rendered HTML (PRD FR-20 audit trail)."""
        fp = report_fingerprint(result)
        # At minimum, a prefix of the fingerprint (first 12 chars) should appear
        assert fp[:12] in html, (
            f"Fingerprint prefix {fp[:12]!r} not found in HTML"
        )

    def test_fingerprint_is_sha256_of_json(self, result):
        """Verify the fingerprint matches SHA-256(JSON(result.model_dump(mode='json')))."""
        canonical = json.dumps(result.model_dump(mode="json"), sort_keys=True,
                               separators=(",", ":"))
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert report_fingerprint(result) == expected
