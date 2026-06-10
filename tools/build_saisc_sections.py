#!/usr/bin/env python3
"""Build the packaged SAISC section dataset from the official source PDF.

Usage:
    python tools/build_saisc_sections.py /path/to/section-properties-steel-profiles.pdf

Source (free): SAISC "Database of Structural Steel Sections".
This parses the two parallel-flange tables and writes
`kernel/src/torenone_kernel/sections/data/saisc_sections.json`:
  - I-sections (Parallel flange): IPE-AA, IPE (100–200), Universal Beams (UB)
  - H-sections (Parallel flange): Universal Columns (UC)

Unit conversion (published -> base mm) and SAISC notation mapping:
  A   [10^3 mm^2] -> area_mm2                 (×1e3)
  Ix  [10^6 mm^4] -> second_moment_ix_mm4     (×1e6)
  Iy  [10^6 mm^4] -> second_moment_iy_mm4     (×1e6)
  Zx  [10^3 mm^3] -> elastic_modulus_sx_mm3   (SAISC 'Z' = ELASTIC modulus)  (×1e3)
  Zplx[10^3 mm^3] -> plastic_modulus_zx_mm3   (SAISC 'Zpl' = PLASTIC modulus)(×1e3)
  J   [10^3 mm^4] -> torsion_constant_j_mm4   (×1e3)
  Cw  [10^9 mm^6] -> warping_constant_cw_mm6  (×1e9)

Every record is validated through `SectionProperties` before being written.

⚠️ Output is PROVISIONAL pending a registered engineer's spot-check sign-off
   against the official SAISC Red Book before the Phase 8 validation gate.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "kernel" / "src"))

from pypdf import PdfReader  # noqa: E402

from torenone_kernel.sections import SectionLibrary, SectionProperties  # noqa: E402

OUT = REPO / "kernel" / "src" / "torenone_kernel" / "sections" / "data" / "saisc_sections.json"
TARGETS = {"I-sections (Parallel flange)", "H-sections (Parallel flange)"}
STOP = ("flange)", "Hollow", "Cold-formed", "DATABASE", "Channel", "Angle")
# Column order after the designation (19 values):
# h b tw tf r1 m A Ix Zx rx Iy Zy ry J Cw Zplx Zply h/tf hw
H, B, TW, TF, _R1, M, A, IX, ZX, RX, IY, _ZY, RY, J, CW, ZPLX = range(16)


def _isnum(t: str) -> bool:
    try:
        float(t)
        return True
    except ValueError:
        return False


def parse(pdf_path: Path) -> list[dict[str, object]]:
    lines: list[str] = []
    for page in PdfReader(str(pdf_path)).pages:
        lines += (page.extract_text() or "").splitlines()

    records: list[dict[str, object]] = []
    awaiting = collecting = False
    family = None
    for raw in lines:
        s = raw.strip()
        if s in TARGETS:
            awaiting, collecting, family = True, False, s
            continue
        if awaiting:
            if "Designation" in s:
                awaiting, collecting = False, True
            continue
        if not collecting:
            continue
        if "Designation" in s or any(m in s for m in STOP):
            collecting = False
            continue
        toks = s.split()
        if len(toks) < 20 or not all(_isnum(t) for t in toks[-19:]):
            continue
        designation = " ".join(toks[:-19]).strip()
        if not designation or all(_isnum(t) for t in designation.split()):
            continue
        if "*" in s:  # Class 4 (out of MVP scope) — skip
            continue
        v = [float(t) for t in toks[-19:]]
        records.append(
            {
                "designation": designation,
                "mass_per_metre_kg_m": v[M],
                "area_mm2": v[A] * 1e3,
                "depth_mm": v[H],
                "width_mm": v[B],
                "web_thickness_mm": v[TW],
                "flange_thickness_mm": v[TF],
                "second_moment_ix_mm4": v[IX] * 1e6,
                "second_moment_iy_mm4": v[IY] * 1e6,
                "elastic_modulus_sx_mm3": v[ZX] * 1e3,
                "plastic_modulus_zx_mm3": v[ZPLX] * 1e3,
                "radius_gyration_rx_mm": v[RX],
                "radius_gyration_ry_mm": v[RY],
                "torsion_constant_j_mm4": v[J] * 1e3,
                "warping_constant_cw_mm6": v[CW] * 1e9,
                "_family": family,
            }
        )
    return records


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pdf_path = Path(sys.argv[1])
    records = parse(pdf_path)

    # Validate every record through the schema, and prove the library builds.
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in records]
    for r in clean:
        SectionProperties(**r)  # raises on any invalid value
    lib = SectionLibrary.from_records(clean)
    assert len(lib) == len(clean)

    payload = {
        "_meta": {
            "source": "SAISC — Database of Structural Steel Sections (free publication)",
            "source_file": pdf_path.name,
            "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "count": len(clean),
            "families": "I-sections parallel flange (IPE/IPE-AA/UB), H-sections parallel flange (UC)",
            "units": "base mm: mm, mm^2, mm^3, mm^4, mm^6",
            "notation": "SAISC Z=elastic modulus (->Sx); Zpl=plastic modulus (->Zx)",
            "status": "PROVISIONAL — pending registered-engineer spot-check sign-off vs SAISC Red Book (PRD Phase 8)",
        },
        "sections": clean,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {len(clean)} sections -> {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
