"""Task 2.3 — Matplotlib geometry and BMD/SFD diagrams.

Public API
----------
frame_geometry_png(spec: FrameSpec) -> bytes
    Portal frame outline with node labels and key dimensions.

bmd_sfd_png(result: DesignResult) -> bytes
    Bending moment diagram (BMD) + shear force diagram (SFD) for the
    governing ULS-1 combination, re-computed from the DesignResult spec
    and chosen sections.

Both functions return PNG bytes (deterministic — no timestamps).

Design constraints
------------------
- No arithmetic here.  All force values come from PortalAnalysis (the kernel).
- Re-runs analysis internally; results must agree with the design run.
- Matplotlib backend set to Agg (non-interactive) for server-side rendering.
"""

from __future__ import annotations

import io
from typing import Any

import matplotlib

matplotlib.use("Agg")   # non-interactive backend — must be set before pyplot import
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from torenone_kernel.analysis.diagram_data import compute_frame_diagram  # noqa: E402
from torenone_kernel.models.frame_spec import FrameSpec  # noqa: E402
from torenone_kernel.models.results import DesignResult  # noqa: E402
from torenone_kernel.sections.library import SectionLibrary  # noqa: E402

# ---------------------------------------------------------------------------
# Brand colours (matching template.html.jinja2)
# ---------------------------------------------------------------------------
_BRAND       = "#1B3A57"
_BRAND_LIGHT = "#2D5F8A"
_PASS_GREEN  = "#166534"
_FAIL_RED    = "#991B1B"
_GRID_GREY   = "#D1D5DB"
_BMD_FILL    = "#BFDBFE"   # light-blue fill for bending moment area
_SFD_FILL    = "#FDE68A"   # amber fill for shear area
_FRAME_LINE  = _BRAND
_FONT_SIZE   = 8

_DPI = 150   # dots per inch — good resolution for print-quality PDF
_N_SAMPLES = 50   # sample points per member for BMD/SFD curves

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _frame_nodes(spec: FrameSpec) -> dict[str, tuple[float, float]]:
    """Return global (X, Y) coordinates for the 5 portal frame nodes (m)."""
    g = spec.geometry
    half = g.span_m / 2.0
    return {
        "BL": (0.0,      0.0),
        "EL": (0.0,      g.eaves_height_m),
        "AP": (half,     g.apex_height_m),
        "ER": (g.span_m, g.eaves_height_m),
        "BR": (g.span_m, 0.0),
    }


def _member_coords(
    nodes: dict[str, tuple[float, float]], member: tuple[str, str]
) -> tuple[float, float, float, float]:
    """Return (x_i, y_i, x_j, y_j) for a member defined by (node_i_name, node_j_name)."""
    xi, yi = nodes[member[0]]
    xj, yj = nodes[member[1]]
    return xi, yi, xj, yj


def _png_bytes(fig: Figure) -> bytes:
    """Render a Matplotlib figure to PNG bytes and close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Public: frame geometry diagram
# ---------------------------------------------------------------------------

def frame_geometry_png(spec: FrameSpec) -> bytes:
    """Render the portal frame outline with node labels and dimensions.

    Returns deterministic PNG bytes (no timestamps embedded).
    """
    nodes = _frame_nodes(spec)
    g = spec.geometry

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_aspect("equal")
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    # Frame outline (polygon)
    xs = [nodes["BL"][0], nodes["EL"][0], nodes["AP"][0], nodes["ER"][0], nodes["BR"][0]]
    ys = [nodes["BL"][1], nodes["EL"][1], nodes["AP"][1], nodes["ER"][1], nodes["BR"][1]]
    ax.plot(xs, ys, color=_FRAME_LINE, linewidth=2.0, solid_capstyle="round",
            solid_joinstyle="round")

    # Support symbols (triangles for pins)
    for node_name in ("BL", "BR"):
        xn, yn = nodes[node_name]
        _draw_pin(ax, xn, yn)

    # Node labels
    offsets = {
        "BL": (-0.25, -0.35),
        "EL": (-0.50, +0.10),
        "AP": (+0.00, +0.20),
        "ER": (+0.25, +0.10),
        "BR": (+0.10, -0.35),
    }
    for name, (xn, yn) in nodes.items():
        dx, dy = offsets[name]
        ax.text(xn + dx, yn + dy, name, fontsize=_FONT_SIZE, color=_BRAND,
                ha="center", va="center", fontweight="bold")

    # Dimension annotations
    _dim_arrow(ax, 0, -0.6, g.span_m, -0.6,
               f"Span = {g.span_m:.1f} m", color=_BRAND_LIGHT)
    _dim_arrow(ax, -0.7, 0, -0.7, g.eaves_height_m,
               f"Eaves\n{g.eaves_height_m:.1f} m", color=_BRAND_LIGHT, vertical=True)
    _dim_arrow(ax, g.span_m / 2 + 0.1, g.eaves_height_m,
               g.span_m / 2 + 0.1, g.apex_height_m,
               f"Rise\n{(g.apex_height_m - g.eaves_height_m):.2f} m",
               color=_BRAND_LIGHT, vertical=True)

    # Pitch annotation
    ax.text(g.span_m * 0.3, (g.eaves_height_m + g.apex_height_m) / 2 + 0.1,
            f"{g.roof_pitch_deg:.1f}°",
            fontsize=_FONT_SIZE, color=_BRAND_LIGHT, style="italic")

    ax.set_xlim(-1.2, g.span_m + 1.2)
    ax.set_ylim(-1.0, g.apex_height_m + 1.0)
    ax.set_xlabel("X (m)", fontsize=_FONT_SIZE, color=_BRAND)
    ax.set_ylabel("Y (m)", fontsize=_FONT_SIZE, color=_BRAND)
    ax.set_title("Portal Frame Geometry", fontsize=10, color=_BRAND, fontweight="bold", pad=8)
    ax.tick_params(labelsize=_FONT_SIZE - 1, colors=_BRAND)
    for spine in ax.spines.values():
        spine.set_edgecolor(_GRID_GREY)
    ax.grid(True, color=_GRID_GREY, linewidth=0.4, linestyle="--")

    fig.tight_layout()
    return _png_bytes(fig)


def _draw_pin(ax: Axes, x: float, y: float, size: float = 0.2) -> None:
    """Draw a pin support symbol (downward triangle) at (x, y)."""
    tri = mpatches.FancyArrow(
        x, y, 0, 0,
        width=0.001, head_width=size, head_length=size * 0.6,
        color=_BRAND, length_includes_head=True,
    )
    ax.add_patch(tri)
    # Horizontal line under triangle
    ax.plot([x - size * 0.7, x + size * 0.7], [y - size * 0.6, y - size * 0.6],
            color=_BRAND, linewidth=1.2)


def _dim_arrow(
    ax: Axes,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    label: str,
    color: str = _BRAND_LIGHT,
    vertical: bool = False,
) -> None:
    """Draw a dimension line between (x1,y1) and (x2,y2) with a centred label."""
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="<->", color=color, lw=0.8),
    )
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ha = "right" if vertical else "center"
    va = "center" if vertical else "bottom"
    offset = (-0.15, 0) if vertical else (0, 0.1)
    ax.text(mx + offset[0], my + offset[1], label,
            fontsize=_FONT_SIZE - 1, color=color, ha=ha, va=va)


# ---------------------------------------------------------------------------
# Public: BMD + SFD diagram
# ---------------------------------------------------------------------------

def bmd_sfd_png(result: DesignResult) -> bytes:
    """Render Bending Moment Diagram + Shear Force Diagram for the governing ULS-1 combo.

    The analysis is re-run from DesignResult.frame_spec + chosen sections.
    Values are in kN·m (moments) and kN (shears).

    Returns deterministic PNG bytes.
    """
    spec = result.frame_spec
    g = spec.geometry

    # Single source of truth: the SAME sampled BMD/SFD data the web UI consumes
    # (DesignResult.diagram). design()/check() already computed it; fall back to
    # computing it for hand-built results that have no diagram attached.
    if result.diagram is not None:
        diagram = result.diagram
    else:
        lib = SectionLibrary.load_default()
        sec_map = {s.member: lib.get(s.designation) for s in result.sections}
        diagram = compute_frame_diagram(spec, sec_map["column"], sec_map["rafter"])

    nodes_global = {name: np.array(xy) for name, xy in diagram.nodes.items()}
    member_curves: list[dict[str, Any]] = [
        {
            "label": md.label,
            "global_pos": np.array([[s.x_m, s.y_m] for s in md.stations]),  # (N, 2) m
            "moments": np.array([s.moment_knm for s in md.stations]),        # kN·m
            "shears": np.array([s.shear_kn for s in md.stations]),           # kN
            "length_m": md.length_m,
        }
        for md in diagram.members
    ]

    # ---- Plot ----
    fig, (ax_bmd, ax_sfd) = plt.subplots(
        2, 1, figsize=(10, 7),
        facecolor="white",
    )
    for ax in (ax_bmd, ax_sfd):
        ax.set_facecolor("white")
        ax.set_aspect("equal")
        ax.grid(True, color=_GRID_GREY, linewidth=0.4, linestyle="--", zorder=0)
        for spine in ax.spines.values():
            spine.set_edgecolor(_GRID_GREY)
        ax.tick_params(labelsize=_FONT_SIZE - 1, colors=_BRAND)

    # Scale: pick a common scale factor so diagrams look proportional
    max_m = max(np.max(np.abs(mc["moments"])) for mc in member_curves)
    max_v = max(np.max(np.abs(mc["shears"]))  for mc in member_curves)
    frame_height = g.apex_height_m
    scale_m = frame_height * 0.4 / (max_m if max_m > 0 else 1.0)   # m per kN·m
    scale_v = frame_height * 0.4 / (max_v if max_v > 0 else 1.0)   # m per kN

    _draw_bmd_sfd(ax_bmd, member_curves, nodes_global, "moments", scale_m,
                  "BMD (kN·m)", _BMD_FILL, g)
    _draw_bmd_sfd(ax_sfd, member_curves, nodes_global, "shears",  scale_v,
                  "SFD (kN)",   _SFD_FILL, g)

    # Key value annotations
    for mc in member_curves:
        idx_max = np.argmax(np.abs(mc["moments"]))
        m_val = mc["moments"][idx_max]
        pt = mc["global_pos"][idx_max]
        ax_bmd.text(pt[0], pt[1] + m_val * scale_m * 0.5,
                    f"{m_val:.1f}", fontsize=_FONT_SIZE - 2, color=_BRAND,
                    ha="center", va="center", zorder=5)

        idx_max_v = np.argmax(np.abs(mc["shears"]))
        v_val = mc["shears"][idx_max_v]
        pt_v = mc["global_pos"][idx_max_v]
        ax_sfd.text(pt_v[0], pt_v[1] + v_val * scale_v * 0.5,
                    f"{v_val:.1f}", fontsize=_FONT_SIZE - 2, color=_BRAND,
                    ha="center", va="center", zorder=5)

    # Titles
    combo_label = diagram.combination
    ax_bmd.set_title(
        f"Bending Moment Diagram — {combo_label}",
        fontsize=10, color=_BRAND, fontweight="bold", pad=6,
    )
    ax_sfd.set_title(
        f"Shear Force Diagram — {combo_label}",
        fontsize=10, color=_BRAND, fontweight="bold", pad=6,
    )
    for ax in (ax_bmd, ax_sfd):
        ax.set_xlabel("X (m)", fontsize=_FONT_SIZE, color=_BRAND)
        ax.set_ylabel("Y (m)", fontsize=_FONT_SIZE, color=_BRAND)

    fig.tight_layout(h_pad=1.5)
    return _png_bytes(fig)


def _draw_bmd_sfd(
    ax: Axes,
    member_curves: list[dict[str, Any]],
    nodes_global: dict[str, Any],
    value_key: str,
    scale: float,
    title: str,
    fill_color: str,
    g: Any,
) -> None:
    """Draw frame outline + filled force diagram (BMD or SFD) on *ax*.

    The force values are offset perpendicular to each member axis, plotted on the
    tension/compression face (conventional: plotted on tension side for moments).
    """
    # Draw frame outline
    outline_x = [nodes_global[n][0] for n in ("BL", "EL", "AP", "ER", "BR")]
    outline_y = [nodes_global[n][1] for n in ("BL", "EL", "AP", "ER", "BR")]
    ax.plot(outline_x, outline_y, color=_FRAME_LINE, linewidth=1.5, zorder=3,
            solid_capstyle="round")

    for mc in member_curves:
        gpos = mc["global_pos"]           # (N, 2) in metres
        vals = mc[value_key]              # moments (kN·m) or shears (kN)

        # Unit vector along member direction
        di = gpos[-1] - gpos[0]
        di /= np.linalg.norm(di) + 1e-12

        # Perpendicular (normal) unit vector — 90° CCW
        ni = np.array([-di[1], di[0]])

        # Offset positions: baseline + scaled value * normal
        # Sign: positive moments plotted in "ni" direction (inside frame for portal)
        offsets = gpos + np.outer(vals * scale, ni)  # (N, 2)

        # Fill between baseline (gpos) and offset curve
        ax.fill(
            np.concatenate([gpos[:, 0], offsets[::-1, 0]]),
            np.concatenate([gpos[:, 1], offsets[::-1, 1]]),
            color=fill_color, alpha=0.6, zorder=1,
        )
        # Outline of diagram
        ax.plot(offsets[:, 0], offsets[:, 1],
                color=_BRAND_LIGHT, linewidth=0.8, zorder=2)
        # Tick lines at salient points
        for i in [0, len(gpos) // 2, -1]:
            ax.plot(
                [gpos[i, 0], offsets[i, 0]],
                [gpos[i, 1], offsets[i, 1]],
                color=_BRAND, linewidth=0.5, alpha=0.5, zorder=2,
            )

    # Pin supports
    for node_name in ("BL", "BR"):
        xn, yn = nodes_global[node_name]
        _draw_pin(ax, xn, yn, size=0.18)

    # Axis limits with padding
    ax.set_xlim(-1.0, g.span_m + 1.0)
    ax.set_ylim(-0.8, g.apex_height_m + 1.2)
