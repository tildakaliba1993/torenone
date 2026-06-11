"""Second-order sway check — SANS 10162-1:2011 cl. 8.7.

Implements the U2 amplification factor method for a single-storey pinned-base portal frame.

Formula (cl. 8.7):
    U2 = 1 / (1 - ΣΔu·Cu / (ΣVu·h))

Where:
    ΣΔu  = storey lateral drift under factored loads including notional horizontal force (mm)
    ΣCu  = sum of factored axial compressive forces in the columns (kN)
    ΣVu  = sum of factored lateral shear in the storey = notional force H (kN)
    h    = storey height = eaves height (mm)

Notional horizontal force (cl. 8.7):
    H = 0.005 × (total factored gravity load contributed by the storey)  [kN]

Applied at the eaves level (single-storey portal).

Sway-sensitivity flag: U2 > 1.4 → frame requires second-order analysis (PROVISIONAL
threshold — CSA S16 basis; SANS 10162-1 cl. 8.7 does not state an explicit numerical
cutoff in the edition examined).

Unit convention: N/mm internally in the solver; kN at all public interfaces.
"""

from __future__ import annotations

import site
import sys

for _sp in site.getsitepackages() + [site.getusersitepackages()]:
    if _sp not in sys.path:
        sys.path.insert(0, _sp)


from torenone_kernel.analysis.plane_frame import (
    _COMBO,
    _add_section,
    _fix_out_of_plane,
    _new_model,
    _pin_support,
)
from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import SwaySensitivityResult
from torenone_kernel.sections.properties import SectionProperties

# Sway-sensitivity threshold (PROVISIONAL — CSA S16 basis; see module docstring)
_U2_SWAY_THRESHOLD = 1.4


class FrameUnstableError(ValueError):
    """Raised when θ ≥ 1.0, meaning the frame's geometric stiffness exceeds its elastic
    restoring stiffness — the U2 amplification method breaks down and the frame is
    structurally unstable under the given loading. The engineer must resize the frame.
    """


# ---------------------------------------------------------------------------
# Pure formula helper (testable without PyNite)
# ---------------------------------------------------------------------------

def u2_factor(
    drift_mm: float,
    total_vertical_kn: float,
    notional_force_kn: float,
    height_mm: float,
) -> float:
    """Compute the SANS 10162-1 cl. 8.7 sway amplification factor U2.

    Parameters
    ----------
    drift_mm          : lateral storey drift Δu under notional force (mm)
    total_vertical_kn : ΣCu — total factored axial load in columns (kN)
    notional_force_kn : ΣVu — notional horizontal force (kN)
    height_mm         : storey height h (mm)

    Returns
    -------
    U2 ≥ 1.0
    """
    if drift_mm == 0.0:
        return 1.0
    # θ = ΣΔu·ΣCu / (ΣVu·h)   — all in consistent units (kN & mm)
    theta = (drift_mm * total_vertical_kn) / (notional_force_kn * height_mm)
    if theta >= 1.0:
        raise FrameUnstableError(
            f"Stability index θ = {theta:.3f} ≥ 1.0: frame is geometrically unstable under "
            f"the given loading (P-Δ demand exceeds elastic stiffness). Resize the frame."
        )
    return 1.0 / (1.0 - theta)


# ---------------------------------------------------------------------------
# Portal sway analysis
# ---------------------------------------------------------------------------

def compute_sway_check(
    spec: FrameSpec,
    column_section: SectionProperties,
    rafter_section: SectionProperties,
    total_factored_gravity_kn: float,
    combination_name: str = "",
) -> SwaySensitivityResult:
    """Compute the SANS 10162-1 cl. 8.7 sway amplification factor for a pinned-base portal.

    Procedure:
    1. Compute notional horizontal force H = 0.005 × total_factored_gravity_kn (cl. 8.7).
    2. Apply H at the left eaves node in the +X direction.
    3. Run first-order elastic analysis.
    4. Extract lateral drift Δ at eaves (mm).
    5. Compute U2 and flag if sway-sensitive.

    Parameters
    ----------
    spec                    : frame geometry + material.
    column_section          : section properties for columns.
    rafter_section          : section properties for rafters.
    total_factored_gravity_kn : ΣCu = total factored vertical load on frame (kN).
    combination_name        : label for the result.
    """

    geom = spec.geometry
    span_mm      = geom.span_m          * 1_000.0
    eaves_h_mm   = geom.eaves_height_m  * 1_000.0
    apex_h_mm    = geom.apex_height_m   * 1_000.0
    half_span_mm = span_mm / 2.0

    # Notional horizontal force (N) — applied in +X at eaves
    H_kn = 0.005 * total_factored_gravity_kn
    H_N  = H_kn * 1_000.0

    m = _new_model()
    _add_section(m, "col_sec", column_section)
    _add_section(m, "raf_sec", rafter_section)

    m.add_node("BL",          0,          0, 0)
    m.add_node("EL",          0,  eaves_h_mm, 0)
    m.add_node("AP", half_span_mm, apex_h_mm, 0)
    m.add_node("ER",      span_mm, eaves_h_mm, 0)
    m.add_node("BR",      span_mm,          0, 0)

    _pin_support(m, "BL")
    _pin_support(m, "BR")
    _fix_out_of_plane(m, "EL")
    _fix_out_of_plane(m, "AP")
    _fix_out_of_plane(m, "ER")

    m.add_member("COL_L", "BL", "EL", "steel", "col_sec")
    m.add_member("RAF_L", "EL", "AP", "steel", "raf_sec")
    m.add_member("RAF_R", "AP", "ER", "steel", "raf_sec")
    m.add_member("COL_R", "ER", "BR", "steel", "col_sec")

    # Apply notional horizontal force at left eaves in +X direction
    m.add_node_load("EL", "FX", H_N, case="DL")
    m.add_load_combo(_COMBO, {"DL": 1.0})
    m.analyze_linear(log=False, check_stability=False)

    # Lateral drift at eaves (mm) — absolute value (force is +X)
    delta_mm = abs(float(m.nodes["EL"].DX[_COMBO]))

    U2 = u2_factor(
        drift_mm=delta_mm,
        total_vertical_kn=total_factored_gravity_kn,
        notional_force_kn=H_kn,
        height_mm=eaves_h_mm,
    )

    theta = 1.0 - 1.0 / U2 if U2 > 1.0 else 0.0

    return SwaySensitivityResult(
        combination=combination_name or "unnamed",
        U2=U2,
        stability_index=theta,
        eaves_drift_mm=delta_mm,
        notional_force_kn=H_kn,
        is_sway_sensitive=U2 > _U2_SWAY_THRESHOLD,
    )
