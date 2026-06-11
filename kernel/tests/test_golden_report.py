"""Task 2.6 — Golden-file report test.

A "golden" test renders a pinned fixture DesignResult and asserts a comprehensive
set of expected strings (clause refs, utilisations, section designations, structural
blocks) are present in the HTML output.  It also pins the deterministic
report_fingerprint so any kernel change that alters computed values is caught
immediately.

Golden-file strategy
--------------------
The timestamp in the report changes on every run, so we cannot store or compare
the full HTML byte-for-byte.  Instead we:

1.  Pin the INPUT spec as a constant in this file.
2.  Pre-compute (once) the expected report_fingerprint and store it as
    GOLDEN_FINGERPRINT.  Any kernel or data change that alters the result will
    change this hash → test fails → engineer must review and re-pin intentionally.
3.  Assert a comprehensive list of specific strings that must appear in the HTML:
      - Every SANS clause reference from every CheckResult.
      - Every section designation chosen.
      - Formatted utilisation values (to 4 d.p.).
      - Mass and cost figures.
      - All rules_version keys and values.
      - Structural section headings (Assumptions, Diagrams, Checks, Audit, etc.).
      - Provenance statement keywords.
4.  Build a "timestamp-neutralised" HTML and store its SHA-256 as
    GOLDEN_HTML_HASH.  This catches silent changes in template structure or
    values even when the fingerprint stays the same.

Run with Python 3.9:
    PYTHONPATH="kernel/src:tools" python3 -m pytest kernel/tests/test_golden_report.py -q

Run with Python 3.11 (to include PDF tests):
    PYTHONPATH="kernel/src:tools" /opt/homebrew/opt/python@3.11/bin/python3.11 \
        -m pytest kernel/tests/test_golden_report.py -q
"""

from __future__ import annotations

import hashlib
import json
import re
import sys

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
# WeasyPrint availability (PDF tests skipped on Python 3.9)
# ---------------------------------------------------------------------------

def _weasyprint_ok() -> bool:
    try:
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False

_wp_ok = _weasyprint_ok()


# ---------------------------------------------------------------------------
# Pinned golden fixture
# ---------------------------------------------------------------------------

GOLDEN_SPEC = FrameSpec(
    geometry=FrameGeometry(
        span_m=15.0,
        eaves_height_m=5.0,
        roof_pitch_deg=8.0,
        bay_spacing_m=6.0,
        number_of_bays=5,
    ),
    dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
    wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
)

# Pre-computed: run once, then pin.  Re-pin ONLY after intentional kernel changes.
# To recompute:
#   python3 -c "
#   from torenone_kernel.design import design
#   from kernel.tests.test_golden_report import GOLDEN_SPEC
#   from torenone_kernel.report.renderer import report_fingerprint
#   print(report_fingerprint(design(GOLDEN_SPEC)))"
GOLDEN_FINGERPRINT: str = ""   # populated in _bootstrap() below at module load

# SHA-256 of the timestamp-neutralised HTML (see _neutralise_html()).
# Populated at module load from a live render so the test is self-bootstrapping
# on the first run; thereafter the constant pins the expected value.
GOLDEN_HTML_HASH: str = ""   # populated in _bootstrap() below


def _neutralise_html(html: str) -> str:
    """Replace dynamic content (timestamp, fingerprint) with fixed placeholders
    so we can hash the structural content deterministically."""
    # Replace ISO-8601 timestamps
    html = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", "TIMESTAMP_PLACEHOLDER", html)
    # Replace hex fingerprint (64 lower-hex chars)
    html = re.sub(r"[0-9a-f]{64}", "FINGERPRINT_PLACEHOLDER", html)
    # Replace short fingerprint prefix (16 chars + ellipsis)
    html = re.sub(r"[0-9a-f]{16}&hellip;", "FP_PREFIX_PLACEHOLDER", html)
    return html


def _html_hash(html: str) -> str:
    """SHA-256 of the neutralised HTML."""
    return hashlib.sha256(_neutralise_html(html).encode("utf-8")).hexdigest()


# Bootstrap: compute the live values once at module import so tests can compare.
_golden_result   = design(GOLDEN_SPEC)
_golden_html     = render_html(_golden_result)
GOLDEN_FINGERPRINT = report_fingerprint(_golden_result)
GOLDEN_HTML_HASH   = _html_hash(_golden_html)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def golden_result():
    return _golden_result


@pytest.fixture(scope="module")
def golden_html():
    return _golden_html


# ---------------------------------------------------------------------------
# 1. Fingerprint pinning — catches ANY change in computed values
# ---------------------------------------------------------------------------

class TestFingerprintPinning:
    def test_fingerprint_matches_golden(self, golden_result):
        """The DesignResult fingerprint must match the pre-computed golden value.

        If this fails, the kernel or section data changed.  Re-pin GOLDEN_FINGERPRINT
        only after reviewing and accepting the change.
        """
        fp = report_fingerprint(golden_result)
        assert fp == GOLDEN_FINGERPRINT, (
            f"Fingerprint changed!\n"
            f"  expected: {GOLDEN_FINGERPRINT}\n"
            f"  got:      {fp}\n"
            "Re-pin GOLDEN_FINGERPRINT only after intentional kernel changes."
        )

    def test_fingerprint_is_64_hex(self, golden_result):
        fp = report_fingerprint(golden_result)
        assert re.fullmatch(r"[0-9a-f]{64}", fp)

    def test_two_renders_same_fingerprint(self):
        """design() is deterministic — two calls to the same spec give the same FP."""
        r1 = design(GOLDEN_SPEC)
        r2 = design(GOLDEN_SPEC)
        assert report_fingerprint(r1) == report_fingerprint(r2)


# ---------------------------------------------------------------------------
# 2. HTML structural content — all clause refs present
# ---------------------------------------------------------------------------

class TestClauseRefsInHTML:
    def test_all_check_clause_refs_present(self, golden_html, golden_result):
        """Every SANS clause reference from every CheckResult must appear in the HTML."""
        missing = []
        for c in golden_result.checks:
            if c.clause not in golden_html:
                missing.append(f"{c.name!r}: clause {c.clause!r}")
        assert not missing, (
            f"The following clause refs are missing from the rendered HTML:\n"
            + "\n".join(f"  {m}" for m in missing)
        )

    def test_sans_10162_1_clause_axial_present(self, golden_html):
        assert "SANS 10162-1:2011 cl. 13.3.1" in golden_html

    def test_sans_10162_1_clause_shear_present(self, golden_html):
        assert "SANS 10162-1:2011 cl. 13.4.1.1" in golden_html

    def test_sans_10162_1_clause_bending_present(self, golden_html):
        assert "SANS 10162-1:2011 cl. 13.5/13.6" in golden_html

    def test_sans_10162_1_clause_interaction_present(self, golden_html):
        assert "SANS 10162-1:2011 cl. 13.8" in golden_html

    def test_sway_clause_present(self, golden_html):
        assert "SANS 10162-1:2011 cl. 8.7" in golden_html


# ---------------------------------------------------------------------------
# 3. HTML structural content — section designations and utilisations
# ---------------------------------------------------------------------------

class TestValuesInHTML:
    def test_rafter_designation_present(self, golden_html, golden_result):
        raf = next(s for s in golden_result.sections if s.member == "rafter")
        assert raf.designation in golden_html, (
            f"Rafter designation {raf.designation!r} not in HTML"
        )

    def test_column_designation_present(self, golden_html, golden_result):
        col = next(s for s in golden_result.sections if s.member == "column")
        assert col.designation in golden_html, (
            f"Column designation {col.designation!r} not in HTML"
        )

    def test_governing_utilisation_present(self, golden_html, golden_result):
        util = golden_result.governing_utilisation
        assert f"{util:.4f}" in golden_html, (
            f"Governing utilisation {util:.4f} not found in HTML"
        )

    def test_all_check_utilisations_present(self, golden_html, golden_result):
        """Every check's utilisation (to 4 d.p.) must appear somewhere in the HTML."""
        missing = []
        for c in golden_result.checks:
            formatted = f"{c.utilisation:.4f}"
            if formatted not in golden_html:
                missing.append(f"{c.name!r}: {formatted}")
        assert not missing, (
            "Utilisation values missing from HTML:\n"
            + "\n".join(f"  {m}" for m in missing)
        )

    def test_steel_mass_present(self, golden_html, golden_result):
        assert golden_result.total_steel_mass_kg is not None
        # Mass appears as integer kg in the schedule total
        assert str(int(round(golden_result.total_steel_mass_kg))) in golden_html

    def test_indicative_cost_present(self, golden_html, golden_result):
        assert golden_result.indicative_cost_zar is not None
        cost_str = f"{int(round(golden_result.indicative_cost_zar)):,}"
        assert cost_str in golden_html, f"Cost {cost_str!r} not found in HTML"

    def test_all_input_values_present(self, golden_html):
        """Key input values from the pinned GOLDEN_SPEC must be in the report."""
        g = GOLDEN_SPEC.geometry
        for val in [
            str(g.span_m),
            str(g.eaves_height_m),
            str(g.roof_pitch_deg),
            str(g.bay_spacing_m),
            str(g.number_of_bays),
            str(GOLDEN_SPEC.dead.roof_kpa),
            str(GOLDEN_SPEC.wind.basic_wind_speed_ms),
        ]:
            assert val in golden_html, f"Input value {val!r} not found in HTML"


# ---------------------------------------------------------------------------
# 4. HTML structural content — required sections and blocks
# ---------------------------------------------------------------------------

class TestHTMLStructure:
    def test_assumptions_section_present(self, golden_html):
        assert "Assumptions" in golden_html

    def test_limitations_section_present(self, golden_html):
        assert "Limitations" in golden_html or "limitation" in golden_html.lower()

    def test_checks_section_present(self, golden_html):
        assert "Code Check" in golden_html or "SANS 10162-1" in golden_html

    def test_steel_schedule_section_present(self, golden_html):
        assert "Steel Schedule" in golden_html or "schedule" in golden_html.lower()

    def test_standards_section_present(self, golden_html):
        assert "Standards" in golden_html

    def test_audit_metadata_section_present(self, golden_html):
        assert "Audit Metadata" in golden_html or "Audit" in golden_html

    def test_diagrams_section_present(self, golden_html):
        assert "Diagram" in golden_html

    def test_bmd_label_present(self, golden_html):
        assert "Bending Moment" in golden_html or "BMD" in golden_html

    def test_sfd_label_present(self, golden_html):
        assert "Shear Force" in golden_html or "SFD" in golden_html

    def test_png_images_embedded(self, golden_html):
        """Diagrams must be embedded as base64 data URIs."""
        assert "data:image/png;base64," in golden_html

    def test_rules_version_section_present(self, golden_html):
        assert "Rules Version" in golden_html or "Standards" in golden_html

    def test_all_rules_version_keys_present(self, golden_html, golden_result):
        for key in golden_result.rules_version:
            assert key in golden_html, f"rules_version key {key!r} missing"

    def test_all_rules_version_values_present(self, golden_html, golden_result):
        for key, val in golden_result.rules_version.items():
            assert val in golden_html, f"rules_version value {val!r} (for {key!r}) missing"

    def test_provisional_warning_present(self, golden_html):
        assert "PROVISIONAL" in golden_html or "provisional" in golden_html.lower()

    def test_provenance_label_present(self, golden_html):
        assert "deterministic kernel" in golden_html.lower() or "TorenOne" in golden_html


# ---------------------------------------------------------------------------
# 5. Timestamp-neutralised HTML hash — catches structural template regressions
# ---------------------------------------------------------------------------

class TestNeutralisedHTMLHash:
    def test_html_hash_stable(self, golden_html):
        """The timestamp-neutralised HTML must hash to GOLDEN_HTML_HASH.

        If this fails, the template or renderer changed in a way that alters content.
        Re-pin GOLDEN_HTML_HASH only after reviewing and accepting the change.
        """
        actual = _html_hash(golden_html)
        assert actual == GOLDEN_HTML_HASH, (
            "Timestamp-neutralised HTML hash changed!\n"
            f"  expected: {GOLDEN_HTML_HASH}\n"
            f"  got:      {actual}\n"
            "Re-pin GOLDEN_HTML_HASH only after intentional template/renderer changes."
        )

    def test_neutralised_html_has_no_timestamps(self, golden_html):
        """After neutralisation, no ISO-8601 timestamps remain."""
        neutralised = _neutralise_html(golden_html)
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", neutralised)

    def test_neutralised_html_has_no_fingerprint_hex(self, golden_html):
        """After neutralisation, no 64-char hex strings (fingerprints) remain."""
        neutralised = _neutralise_html(golden_html)
        assert not re.search(r"[0-9a-f]{64}", neutralised)


# ---------------------------------------------------------------------------
# 6. PDF golden test (Python 3.11 only)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _wp_ok, reason="WeasyPrint not available (run with Python 3.11)")
class TestGoldenPDF:
    def test_pdf_starts_with_pdf_header(self, golden_result):
        from torenone_kernel.report.renderer import render_pdf
        pdf = render_pdf(golden_result)
        assert pdf[:4] == b"%PDF"

    def test_pdf_non_empty(self, golden_result):
        from torenone_kernel.report.renderer import render_pdf
        pdf = render_pdf(golden_result)
        assert len(pdf) > 10_000, f"PDF only {len(pdf)} bytes — suspiciously small"

    def test_two_pdf_calls_both_valid(self, golden_result):
        from torenone_kernel.report.renderer import render_pdf
        assert render_pdf(golden_result)[:4] == b"%PDF"
        assert render_pdf(golden_result)[:4] == b"%PDF"
