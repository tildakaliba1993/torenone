"""Validation-session runner — drive the co-founder validation gate from the terminal.

During the Phase 8 validation session (``docs/VALIDATION_GUIDE.md``) you read a past
frame's numbers off the drawing and compare TorenOne's output to the engineer's original.
This script does exactly that, with no web app and no code: type the worksheet numbers,
optionally the sections the engineer actually used, and it prints a side-by-side report —
then emits a ready-to-paste ``BenchmarkCase`` for ``kernel/tests/validation/benchmarks.py``
so a frame he signs off becomes a permanent regression test.

Example::

    python tools/validate_frame.py \\
        --span 24 --eaves 7 --pitch 7 --bay 6 --bays 8 \\
        --roof-dead 0.20 --wind 36 --terrain B --bearing 200 \\
        --rafter 457x191x67 --column 457x191x82 --name "Pretoria warehouse (2021)"
"""

from __future__ import annotations

import argparse

from torenone_kernel.design import check, design
from torenone_kernel.models.enums import SteelGrade, TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FoundationInputs,
    FrameGeometry,
    FrameSpec,
    ImposedLoadInputs,
    Materials,
    Restraints,
    WindContext,
)
from torenone_kernel.models.results import DesignResult, SectionChoice


def build_spec(args: argparse.Namespace) -> FrameSpec:
    """Assemble a FrameSpec from the worksheet numbers (the inputs an engineer reads off a drawing)."""
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=args.span,
            eaves_height_m=args.eaves,
            roof_pitch_deg=args.pitch,
            bay_spacing_m=args.bay,
            number_of_bays=args.bays,
        ),
        materials=Materials(steel_grade=SteelGrade(args.grade)),
        restraints=Restraints(
            rafter_restraint_spacing_m=args.rafter_restraint,
            column_restraint_spacing_m=args.column_restraint,
        ),
        dead=DeadLoadInputs(
            roof_kpa=args.roof_dead,
            services_kpa=args.services,
            wall_cladding_kpa=args.wall,
        ),
        imposed=ImposedLoadInputs(roof_access=args.roof_access),
        wind=WindContext(
            basic_wind_speed_ms=args.wind,
            terrain_category=TerrainCategory(args.terrain),
            site_altitude_m=args.altitude,
            has_dominant_opening=args.dominant_opening,
        ),
        foundation=FoundationInputs(
            allowable_bearing_kpa=args.bearing,
            concrete_fcu_mpa=args.fcu,
        ),
    )


def _governing_check(result: DesignResult) -> str:
    """The gating (non-advisory) check with the highest utilisation — what governs the design."""
    gating = [c for c in result.checks if not getattr(c, "informational", False)]
    if not gating:
        return "—"
    top = max(gating, key=lambda c: c.utilisation)
    return f"{top.name} ({top.clause}) = {top.utilisation:.3f}"


def _summary(label: str, result: DesignResult) -> str:
    sections = ", ".join(f"{s.member}={s.designation}" for s in result.sections)
    mass = result.total_steel_mass_kg
    return (
        f"  {label}\n"
        f"    sections      : {sections}\n"
        f"    governing     : {result.governing_utilisation:.3f}  "
        f"({'PASS' if result.passed else 'FAIL'})\n"
        f"    governing chk : {_governing_check(result)}\n"
        f"    steel mass    : {mass:.0f} kg" + (f" ({mass / 1000:.3f} t)\n" if mass else "\n")
    )


def _benchmark_snippet(args: argparse.Namespace, autosized: DesignResult) -> str:
    raf = args.rafter or next((s.designation for s in autosized.sections if s.member == "rafter"), "")
    col = args.column or next((s.designation for s in autosized.sections if s.member == "column"), "")
    opt = []
    if args.services:
        opt.append(f"            services_kpa={args.services},")
    if args.wall:
        opt.append(f"            wall_cladding_kpa={args.wall},")
    if args.bearing is not None:
        opt.append(f"            allowable_bearing_kpa={args.bearing},")
    if args.rafter_restraint is not None:
        opt.append(f"            rafter_restraint_m={args.rafter_restraint},")
    if args.column_restraint is not None:
        opt.append(f"            column_restraint_m={args.column_restraint},")
    extra = ("\n" + "\n".join(opt)) if opt else ""
    return (
        "    BenchmarkCase(\n"
        f'        name="{args.name}",\n'
        f'        source="{args.source}",\n'
        "        spec=make_spec(\n"
        f"            span_m={args.span},\n"
        f"            eaves_height_m={args.eaves},\n"
        f"            roof_pitch_deg={args.pitch},\n"
        f"            bay_spacing_m={args.bay},\n"
        f"            number_of_bays={args.bays},\n"
        f"            roof_dead_kpa={args.roof_dead},\n"
        f"            basic_wind_speed_ms={args.wind},\n"
        f'            terrain_category="{args.terrain}",\n'
        f'            steel_grade="{args.grade}",' + extra + "\n"
        "        ),\n"
        f'        original_rafter="{raf}",\n'
        f'        original_column="{col}",\n'
        "        # expected_governing_utilisation=<the original's governing ratio>,\n"
        "        # expected_steel_mass_kg=<per-frame steel mass, kg>,\n"
        "    ),"
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # Required geometry + loads (read off the drawing).
    p.add_argument("--span", type=float, required=True, help="clear span (m)")
    p.add_argument("--eaves", type=float, required=True, help="eaves height (m)")
    p.add_argument("--pitch", type=float, required=True, help="roof pitch (deg)")
    p.add_argument("--bay", type=float, required=True, help="bay spacing (m)")
    p.add_argument("--bays", type=int, required=True, help="number of bays")
    p.add_argument("--roof-dead", type=float, required=True, help="roof dead load (kPa)")
    p.add_argument("--wind", type=float, required=True, help="basic wind speed (m/s)")
    p.add_argument("--terrain", choices=["A", "B", "C", "D"], required=True, help="terrain category")
    # Optional inputs (sensible defaults match the app).
    p.add_argument("--services", type=float, default=0.0, help="services load (kPa)")
    p.add_argument("--wall", type=float, default=0.0, help="wall cladding (kPa)")
    p.add_argument("--roof-access", action="store_true", help="roof is accessible")
    p.add_argument("--altitude", type=float, default=0.0, help="site altitude (m)")
    p.add_argument("--dominant-opening", action="store_true", help="has a dominant opening")
    p.add_argument("--grade", choices=["S275JR", "S355JR"], default="S355JR", help="steel grade")
    p.add_argument("--bearing", type=float, default=None, help="allowable bearing (kPa); omit to skip footing")
    p.add_argument("--fcu", type=float, default=25.0, help="concrete fcu (MPa)")
    p.add_argument("--rafter-restraint", type=float, default=None, help="rafter restraint spacing (m)")
    p.add_argument("--column-restraint", type=float, default=None, help="column restraint spacing (m)")
    # The engineer's original design (optional — enables the side-by-side check).
    p.add_argument("--rafter", default=None, help="rafter section the engineer actually used, e.g. 457x191x67")
    p.add_argument("--column", default=None, help="column section the engineer actually used")
    p.add_argument("--name", default="Untitled frame", help="benchmark name")
    p.add_argument("--source", default="<project ref / engineer / software>", help="where the original came from")
    args = p.parse_args()

    spec = build_spec(args)
    autosized = design(spec)

    print("\n================ TorenOne validation runner ================")
    print(
        f"Frame: {args.span} m span x {args.eaves} m eaves x {args.pitch} deg x "
        f"{args.bay} m bay x {args.bays} bays | grade {args.grade} | "
        f"wind {args.wind} m/s terrain {args.terrain}"
    )
    print("\nKernel DESIGN mode (auto-sized — the lightest adequate sections):")
    print(_summary("kernel auto-size", autosized))

    if args.rafter and args.column:
        original = [
            SectionChoice(member="rafter", designation=args.rafter),
            SectionChoice(member="column", designation=args.column),
        ]
        checked = check(spec, original)
        print("Kernel CHECK mode (the engineer's ACTUAL sections — compare to the hand-calc):")
        print(_summary(f"original: rafter={args.rafter}, column={args.column}", checked))
        verdict = (
            "the kernel agrees the built design is adequate"
            if checked.governing_utilisation <= 1.0
            else "the kernel flags the built design as overstressed — investigate"
        )
        print(f"  -> {verdict}.\n")

    if autosized.warnings:
        print("Warnings / advisory notes:")
        for w in autosized.warnings:
            print(f"  - {w}")
        print()

    print("Once your co-founder signs this off, paste into BENCHMARKS in")
    print("kernel/tests/validation/benchmarks.py to lock it in as a permanent test:\n")
    print(_benchmark_snippet(args, autosized))
    print("\n===========================================================\n")


if __name__ == "__main__":
    main()
