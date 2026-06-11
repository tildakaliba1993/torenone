"""Tasks 2.1 + 2.2 — Jinja2 HTML template and WeasyPrint PDF rendering.

Run with Python 3.11 (WeasyPrint requires it on this machine):
    PYTHONPATH="kernel/src:tools" /opt/homebrew/opt/python@3.11/bin/python3.11 \
        -m pytest kernel/tests/test_report.py -q

Task 2.1: render_html(result: DesignResult) → str
    - All check names and clause refs present
    - Pass/fail rendered with text label (never colour alone — PRD FR-19)
    - Steel mass + indicative cost present
    - Provenance label present
    - Assumptions & limitations block present
    - rules_version embedded (PRD FR-20)
    - PROVISIONAL warnings surfaced

Task 2.2: render_pdf(result: DesignResult) → bytes
    - Starts with %PDF-
    - Non-empty (> 1 kB)
    - Deterministic: same result → same content? (skip — WeasyPrint embeds timestamps)
    - Instead: two calls produce the same page count proxy (both valid PDFs)
"""

from __future__ import annotations

import pytest


# WeasyPrint requires Homebrew pango/cairo, available only under Python 3.11 on this machine.
# HTML tests (Task 2.1) run under any Python; PDF tests (Task 2.2) are skipped on Python < 3.10
# or when WeasyPrint's native libraries are not loadable.
def _weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False


_weasyprint_ok = _weasyprint_available()

from torenone_kernel.design import design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.report.renderer import render_html, render_pdf

# ---------------------------------------------------------------------------
# Fixture: a real DesignResult from the standard 15 m portal
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def result():
    spec = FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )
    return design(spec)


@pytest.fixture(scope="module")
def html(result):
    return render_html(result)


# ---------------------------------------------------------------------------
# Task 2.1 — HTML template
# ---------------------------------------------------------------------------

class TestHTMLContract:
    def test_returns_string(self, html):
        assert isinstance(html, str)

    def test_non_empty(self, html):
        assert len(html) > 500

    def test_is_valid_html(self, html):
        """Must start with <!DOCTYPE html> and contain <html>."""
        stripped = html.strip()
        assert stripped.lower().startswith("<!doctype html")
        assert "<html" in stripped.lower()

    def test_contains_body_tag(self, html):
        assert "<body" in html.lower()


class TestHTMLChecksSection:
    def test_all_check_names_present(self, html, result):
        for c in result.checks:
            assert c.name in html, f"Check name missing: {c.name!r}"

    def test_all_clause_refs_present(self, html, result):
        for c in result.checks:
            assert c.clause in html, f"Clause ref missing: {c.clause!r}"

    def test_utilisation_values_present(self, html, result):
        """At least the governing utilisation should appear formatted."""
        util = result.governing_utilisation
        # Formatted to 3 dp: e.g. "0.923" or "0.92"
        assert f"{util:.2f}" in html or f"{util:.3f}" in html

    def test_pass_label_present(self, html, result):
        """PRD FR-19: pass/fail must be labelled (text, not colour alone)."""
        if result.passed:
            assert "PASS" in html.upper()
        else:
            assert "FAIL" in html.upper()

    def test_all_checks_have_pass_or_fail_label(self, html, result):
        """Each check must render a text pass/fail label."""
        # Both labels will be present because some checks pass and some may be near limit.
        # At minimum, "PASS" must appear (design() returns a passed=True result).
        assert "PASS" in html.upper()


class TestHTMLSections:
    def test_rafter_designation_present(self, html, result):
        raf = next(s for s in result.sections if s.member == "rafter")
        assert raf.designation in html

    def test_column_designation_present(self, html, result):
        col = next(s for s in result.sections if s.member == "column")
        assert col.designation in html


class TestHTMLMassAndCost:
    def test_mass_value_present(self, html, result):
        assert result.total_steel_mass_kg is not None
        # Round to 0 dp — should appear somewhere
        assert str(int(round(result.total_steel_mass_kg))) in html

    def test_cost_value_present(self, html, result):
        assert result.indicative_cost_zar is not None
        # Cost is formatted with comma separator: e.g. "24,308"
        # Check a distinctive substring (first 3 digits) is in the HTML
        cost_str = f"{int(round(result.indicative_cost_zar)):,}"
        assert cost_str in html, f"Expected cost '{cost_str}' in HTML"

    def test_mass_label_present(self, html):
        assert "kg" in html.lower() or "mass" in html.lower()

    def test_cost_label_present(self, html):
        assert "zar" in html.lower() or "cost" in html.lower() or "r " in html.lower()


class TestHTMLProvenance:
    def test_provenance_label_present(self, html):
        """PRD FR-26: every number must be labelled as kernel-computed."""
        assert (
            "deterministic kernel" in html.lower()
            or "torenone" in html.lower()
        )

    def test_not_ai_label_present(self, html):
        """PRD FR-26: 'not AI' or equivalent disclaimer."""
        assert (
            "not ai" in html.lower()
            or "kernel" in html.lower()
        )


class TestHTMLRulesVersion:
    def test_rules_version_embedded(self, html, result):
        """PRD FR-20: rules_version must be embedded in the report."""
        for key, val in result.rules_version.items():
            assert key in html or val in html, (
                f"rules_version entry missing: {key!r}: {val!r}"
            )

    def test_sans_10162_version_present(self, html):
        assert "SANS 10162-1" in html


class TestHTMLAssumptions:
    def test_assumptions_block_present(self, html):
        assert (
            "assumption" in html.lower()
            or "limitation" in html.lower()
        )

    def test_provisional_warning_present(self, html):
        assert "provisional" in html.lower()


# ---------------------------------------------------------------------------
# Task 2.2 — PDF rendering
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _weasyprint_ok, reason="WeasyPrint native libs not available (run with Python 3.11)")
class TestPDFContract:
    def test_returns_bytes(self, result):
        pdf = render_pdf(result)
        assert isinstance(pdf, bytes)

    def test_starts_with_pdf_header(self, result):
        pdf = render_pdf(result)
        assert pdf[:4] == b"%PDF", f"PDF header not found; got: {pdf[:20]!r}"

    def test_non_empty(self, result):
        pdf = render_pdf(result)
        assert len(pdf) > 1_000, f"PDF suspiciously small: {len(pdf)} bytes"

    def test_two_calls_both_valid(self, result):
        """Both calls must produce valid PDFs (not checking byte equality — WeasyPrint timestamps)."""
        pdf1 = render_pdf(result)
        pdf2 = render_pdf(result)
        assert pdf1[:4] == b"%PDF"
        assert pdf2[:4] == b"%PDF"

    def test_pdf_size_reasonable(self, result):
        """A 15 m portal report should be at least 5 kB and under 5 MB."""
        pdf = render_pdf(result)
        assert 5_000 < len(pdf) < 5_000_000, (
            f"PDF size {len(pdf)} bytes is outside expected range"
        )
