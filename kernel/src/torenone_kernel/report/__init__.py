"""TorenOne report engine — Tasks 2.1 (HTML template) + 2.2 (PDF rendering).

Public API:
    render_html(result: DesignResult) -> str   — Jinja2 HTML report
    render_pdf(result: DesignResult) -> bytes  — WeasyPrint PDF (requires Python 3.11 + pango)
"""
from torenone_kernel.report.renderer import render_html, render_pdf

__all__ = ["render_html", "render_pdf"]
