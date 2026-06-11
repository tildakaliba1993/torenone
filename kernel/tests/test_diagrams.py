"""Task 2.3 — Matplotlib geometry + BMD/SFD diagrams.

Run with Python 3.11 (matplotlib is installed there):
    PYTHONPATH="kernel/src:tools" /opt/homebrew/opt/python@3.11/bin/python3.11 \
        -m pytest kernel/tests/test_diagrams.py -q

Tests verify the public API:
    frame_geometry_png(spec: FrameSpec) -> bytes
    bmd_sfd_png(result: DesignResult) -> bytes

Both return PNG bytes (start with the 8-byte PNG signature).
"""

from __future__ import annotations

import struct

import pytest
from torenone_kernel.design import design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.report.diagrams import bmd_sfd_png, frame_geometry_png

_PNG_SIG = b"\x89PNG\r\n\x1a\n"  # RFC 2083 PNG signature


# ---------------------------------------------------------------------------
# Shared fixtures
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


# ---------------------------------------------------------------------------
# Task 2.3a — Frame geometry diagram
# ---------------------------------------------------------------------------

class TestFrameGeometryPng:
    def test_returns_bytes(self, spec):
        png = frame_geometry_png(spec)
        assert isinstance(png, bytes)

    def test_starts_with_png_signature(self, spec):
        png = frame_geometry_png(spec)
        assert png[:8] == _PNG_SIG, f"Not a PNG; got: {png[:8]!r}"

    def test_non_empty(self, spec):
        png = frame_geometry_png(spec)
        assert len(png) > 2_000, f"PNG suspiciously small: {len(png)} bytes"

    def test_png_has_valid_ihdr(self, spec):
        """IHDR chunk must be present immediately after PNG signature."""
        png = frame_geometry_png(spec)
        # PNG signature (8) + IHDR length (4) + 'IHDR' (4) = 16 bytes minimum
        assert len(png) >= 16
        ihdr_name = png[12:16]
        assert ihdr_name == b"IHDR", f"IHDR chunk not found; got: {ihdr_name!r}"

    def test_two_calls_same_result(self, spec):
        """Geometry diagram is deterministic (no timestamps from Matplotlib)."""
        png1 = frame_geometry_png(spec)
        png2 = frame_geometry_png(spec)
        assert png1 == png2, "frame_geometry_png is not deterministic"

    def test_different_span_different_png(self):
        """Different span → different image content."""
        s1 = FrameSpec(
            geometry=FrameGeometry(span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
                                   bay_spacing_m=6.0, number_of_bays=5),
            dead=DeadLoadInputs(roof_kpa=0.20),
            wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
        )
        s2 = FrameSpec(
            geometry=FrameGeometry(span_m=20.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
                                   bay_spacing_m=6.0, number_of_bays=5),
            dead=DeadLoadInputs(roof_kpa=0.20),
            wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
        )
        assert frame_geometry_png(s1) != frame_geometry_png(s2)

    def test_image_width_reasonable(self, spec):
        """PNG width should be in the expected range for a report diagram (400–2400 px)."""
        png = frame_geometry_png(spec)
        # IHDR width at bytes 16-20 (big-endian uint32)
        width = struct.unpack(">I", png[16:20])[0]
        assert 400 <= width <= 2400, f"PNG width {width} outside expected range"


# ---------------------------------------------------------------------------
# Task 2.3b — BMD + SFD diagram
# ---------------------------------------------------------------------------

class TestBmdSfdPng:
    def test_returns_bytes(self, result):
        png = bmd_sfd_png(result)
        assert isinstance(png, bytes)

    def test_starts_with_png_signature(self, result):
        png = bmd_sfd_png(result)
        assert png[:8] == _PNG_SIG, f"Not a PNG; got: {png[:8]!r}"

    def test_non_empty(self, result):
        png = bmd_sfd_png(result)
        assert len(png) > 5_000, f"PNG suspiciously small: {len(png)} bytes"

    def test_png_has_valid_ihdr(self, result):
        png = bmd_sfd_png(result)
        assert len(png) >= 16
        assert png[12:16] == b"IHDR"

    def test_deterministic(self, result):
        """Same DesignResult → identical PNG bytes."""
        png1 = bmd_sfd_png(result)
        png2 = bmd_sfd_png(result)
        assert png1 == png2, "bmd_sfd_png is not deterministic"

    def test_different_result_different_png(self):
        """Different frame → different diagram."""
        spec_a = FrameSpec(
            geometry=FrameGeometry(span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
                                   bay_spacing_m=6.0, number_of_bays=5),
            dead=DeadLoadInputs(roof_kpa=0.20),
            wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
        )
        spec_b = FrameSpec(
            geometry=FrameGeometry(span_m=20.0, eaves_height_m=6.0, roof_pitch_deg=5.0,
                                   bay_spacing_m=6.0, number_of_bays=5),
            dead=DeadLoadInputs(roof_kpa=0.20),
            wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
        )
        assert bmd_sfd_png(design(spec_a)) != bmd_sfd_png(design(spec_b))

    def test_image_width_reasonable(self, result):
        png = bmd_sfd_png(result)
        width = struct.unpack(">I", png[16:20])[0]
        assert 400 <= width <= 2400, f"PNG width {width} outside expected range"
