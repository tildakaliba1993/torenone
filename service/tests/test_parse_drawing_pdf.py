"""PDF-plan support for drawings-in — render a PDF's first page to an image, then the vision path.

A real one-page PDF is generated with Pillow (no extra deps), so these exercise the actual
pypdfium2 render path end-to-end. The vision client is still mocked.

Run:
    PYTHONPATH="kernel/src:tools:service/src" .venv/bin/pytest service/tests/test_parse_drawing_pdf.py -q
"""

from __future__ import annotations

import io
import time
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from torenone_ai import (
    DrawingDecodeError,
    FrameSpecExtraction,
    coerce_drawing_to_image_url,
    coerce_drawing_to_images,
    image_data_url,
    parse_drawing,
    pdf_to_image_data_url,
    pdf_to_image_data_urls,
)
from torenone_kernel.models.enums import TerrainCategory
from torenone_service.ai_runtime import AIRuntime
from torenone_service.app import create_app
from torenone_service.auth import AuthConfig

SECRET = "test-supabase-jwt-secret-0123456789"
AUTH = AuthConfig(secret=SECRET)


def _tiny_pdf_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (240, 160), "white").save(buf, format="PDF")
    return buf.getvalue()


def _pdf_data_url() -> str:
    return image_data_url(_tiny_pdf_bytes(), "application/pdf")


def _multi_page_pdf_bytes(pages: int = 4) -> bytes:
    imgs = [Image.new("RGB", (240, 160), "white") for _ in range(pages)]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


# --- unit: PDF → image -----------------------------------------------------------------------

def test_pdf_renders_to_png_image_url() -> None:
    url = pdf_to_image_data_url(_tiny_pdf_bytes())
    assert url.startswith("data:image/png;base64,")


def test_coerce_passes_images_through_but_renders_pdf() -> None:
    assert coerce_drawing_to_image_url("data:image/png;base64,abc") == "data:image/png;base64,abc"
    assert coerce_drawing_to_image_url("https://x/y.png") == "https://x/y.png"
    assert coerce_drawing_to_image_url(_pdf_data_url()).startswith("data:image/png;base64,")


def test_malformed_pdf_raises_decode_error() -> None:
    with pytest.raises(DrawingDecodeError):
        coerce_drawing_to_image_url("data:application/pdf;base64,not-a-real-pdf!!!")


def test_multi_page_pdf_renders_first_pages_only() -> None:
    # A plan set's frame may not be on page 1; render the first few pages, capped.
    urls = pdf_to_image_data_urls(_multi_page_pdf_bytes(4), max_pages=3)
    assert len(urls) == 3
    assert all(u.startswith("data:image/png;base64,") for u in urls)
    # A single-page PDF yields exactly one image.
    assert len(coerce_drawing_to_images(_pdf_data_url())) == 1


def test_parse_drawing_sends_every_rendered_page() -> None:
    client = _FakeAIClient(_complete())
    pdf_url = image_data_url(_multi_page_pdf_bytes(3), "application/pdf")
    result = parse_drawing(pdf_url, client=client, model="gpt-5.5")
    assert result.is_complete
    blocks = [b for b in client.captured["input"][1]["content"] if b["type"] == "input_image"]
    assert len(blocks) == 3, "all rendered pages must reach the model"


# --- parse_drawing with a PDF (mock vision client) -------------------------------------------

class _FakeAIClient:
    def __init__(self, parsed: Any) -> None:
        captured: dict[str, Any] = {}
        self.captured = captured

        class _Responses:
            def parse(self, **kwargs: Any) -> Any:
                captured.update(kwargs)
                return SimpleNamespace(output_parsed=parsed)

        self.responses = _Responses()


def _complete() -> FrameSpecExtraction:
    return FrameSpecExtraction(
        span_m=20.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=6.0,
        number_of_bays=5, roof_dead_load_kpa=0.20, basic_wind_speed_ms=36.0,
        terrain_category=TerrainCategory.B,
    )


def test_parse_drawing_accepts_pdf_and_sends_a_rendered_image() -> None:
    client = _FakeAIClient(_complete())
    result = parse_drawing(_pdf_data_url(), client=client, model="gpt-5.5")
    assert result.is_complete and result.spec is not None
    # The model received a rendered PNG, not the raw PDF.
    image_block = next(b for b in client.captured["input"][1]["content"] if b["type"] == "input_image")
    assert image_block["image_url"].startswith("data:image/png;base64,")


# --- endpoint --------------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    now = int(time.time())
    token = jwt.encode(
        {"sub": "u1", "email": "e@f.co", "aud": "authenticated", "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _app(parsed: Any) -> TestClient:
    return TestClient(create_app(auth_config=AUTH, ai_runtime=AIRuntime(client=_FakeAIClient(parsed), model="gpt-5.5")))


def test_endpoint_accepts_pdf() -> None:
    resp = _app(_complete()).post(
        "/parse-drawing", json={"image_data_url": _pdf_data_url()}, headers=_headers()
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "complete"


def test_endpoint_malformed_pdf_is_422() -> None:
    bad = "data:application/pdf;base64,bm90LWEtcGRm"  # "not-a-pdf"
    resp = _app(_complete()).post(
        "/parse-drawing", json={"image_data_url": bad}, headers=_headers()
    )
    assert resp.status_code == 422
