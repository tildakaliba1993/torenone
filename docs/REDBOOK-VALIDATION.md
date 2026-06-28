# SAISC Red Book — kernel component validation

> Independent benchmark of the kernel's isolated, clause-tagged functions against published values
> from the **SAISC Southern African Steel Construction Handbook ("Red Book"), 8th ed. 2013** (based
> on SANS 10162-1). This is the **component** validation path — co-founder-independent, **must-pass**
> — complementary to the whole-frame gate in `kernel/tests/validation/benchmarks.py` (which still
> awaits the co-founder's past designs). See `docs/REFERENCES-AND-VALIDATION.md` for tolerances and
> the copyright/legal posture; only numeric facts are encoded (no Red Book text/tables reproduced).

**Tests:** `kernel/tests/validation/redbook/` (`cases.py` + `test_redbook_*.py`). Run:
`PYTHONPATH=kernel/src:tools .venv/bin/pytest kernel/tests/validation/redbook -q`.

**⚠️ Edition note.** Red Book 8th ed. is based on SANS 10162-1:**2005**; the kernel implements
**2011**. Section geometry and the cl. 13.3/13.5/13.6 member-resistance equations are stable across
these editions; **bolt/connection** clauses are not (the Red Book re-aligned Ch 6/7 to the SAISC
Green Book). Connection mismatches are recorded as edition/basis differences, not "fixed" toward the
older edition.

## Coverage

| Area | Source | Suite | Status |
|---|---|---|---|
| Section properties (IPE-AA, IPE, UB, UC) | Tables 2.9, 2.10 | `test_redbook_sections.py` | ✅ 11 sections, ≤1% |
| Compression resistance Cr | Ch 4 (Ex 4.1, 4.3) | `test_redbook_compression.py` | ✅ 3 cases, ≤1.5% |
| Flexural resistance Mr — supported + LTB | Ch 4/5 (Ex 4.3, 5.1, 5.2) | `test_redbook_flexure.py` | ✅ 5 cases, ≤1% |
| Classification (flexure) | §5.1.3 / Table 5.3 | `test_redbook_classification.py` | ✅ 15 sections incl. Class 4 |
| Shear resistance Vr (formula) | Ch 5 (Ex 5.3) | `test_redbook_shear.py` | ✅ 1 case (Av basis flagged) |
| Bolt resistances (tension/shear/bearing) | Table 7.2 | `test_redbook_connections.py` | ✅ M16–M30 × 8.8/10.9 |
| Beam-column interaction | Ch 4 (Ex 4.3) | `test_redbook_interaction.py` | ⚠️ deferred (biaxial example vs uniaxial kernel — best at frame level) |
| End-plate moment connection | Ch 7.9 | — | ⏳ provisional method (engineer sign-off) |
| Baseplate | Ch 4.2 | — | ⏳ needs worked answer extracted |

## Findings & fixes

### Sections (Tables 2.9 / 2.10) — 2026-06-28
Benchmarked 11 sections spanning IPE-AA, IPE, Universal Beams and Universal Columns (area, depth,
width, web/flange thickness, Ix, Iy, Sx=Ze, Zplx=Zpl, rx, ry, J, Cw) at ±1%. The packaged dataset
(`sections/data/saisc_sections.json`, parsed from SAISC's free "Database of Structural Steel
Sections") matched the printed Red Book **except** three values, all on the 203×133 UBs — **fixed**
to the Red Book 8th ed. (Table 2.9), independently corroborated by the UK Advance UB tables:

| Section | Field | Was (kernel) | Now (Red Book) | Δ | Effect |
|---|---|---|---|---|---|
| 203×133×25 | web thickness | 5.8 mm | **5.7 mm** | −1.8% | web class h/t, shear Aw |
| 203×133×25 | torsion J | 62 100 mm⁴ | **59 000 mm⁴** | −5.3% | LTB Mcr (G·J term) |
| 203×133×30 | web thickness | 6.3 mm | **6.4 mm** | +1.6% | web class h/t, shear Aw |

Evidence: for 203×133×30 the kernel's J already matched the Red Book exactly (103 000), and every
IPE/UC J/Cw matched at ≤1%, so the 203×133×25 J was an isolated data slip rather than a systematic
formula difference. Stored Ix/Z/area are not recomputed from these inputs, so the corrections are
self-consistent.

**For the co-founder (within-tolerance, not changed):** the same two UBs show minor source
differences vs the Red Book that fall inside ±1% and were left as-is — mass (25.3 vs 25.1; 29.8 vs
30.0) and width (133.4 vs 133.2; 133.8 vs 133.9). Worth a full dataset reconciliation at section
sign-off; this suite now guards every benchmarked value going forward.

### Member resistances (Ch 4 + Ch 5) — 2026-06-28
Benchmarked the kernel's isolated check functions against Red Book worked examples. **No logic
bugs** — every value reproduced the Red Book within tolerance:

| Check | Function | Red Book | Kernel | Δ |
|---|---|---|---|---|
| Compression Cr (Ex 4.1, 203×133×30, KL=2000) | `cr_flexural` | 834 kN | 842 | +1.0% |
| Compression Crx/Cry (Ex 4.3, 305×305×118) | `cr_flexural` | 4510 / 3890 | 4506 / 3894 | <0.1% |
| Moment Mrx/Mry supported (Ex 4.3) | `mr_laterally_supported` | 614 / 281 | 614 / 281 | exact |
| LTB Mcr (Ex 5.2, 533×210×122, KL=5 m, ω2=1.75) | `mcr_elastic` | 1625 kN·m | 1626 | <0.1% |
| LTB Mr (Ex 5.2 / Ex 5.1) | `mr_ltb` | 929 / 317 | 936 / 317 | ≤0.8% |
| Classification, flexure (Table 5.3) | `classify_section` | 15 sections | all match | — |

Classification highlight: the kernel reproduces every class in Table 5.3 exactly, including the
two Class-3 sections (203×203×46, 305×305×97) and correctly **rejects 152×152×23 as Class 4**
(out of MVP scope). Fed fy = 350 MPa to match the Red Book's Grade-350 basis.

**⚠️ FLAG for the co-founder — shear area basis (not a bug; kernel is conservative).** Red Book
Ex 5.3 computes the shear area as **overall depth × tw** (Vr = 1050 kN for 533×210×82). The kernel
(`checks/shear.py`) uses the **clear web depth** hw = d − 2·tf, giving ≈1002 kN — about **4–5% more
conservative**. The kernel docstring cites SANS 10162-1 cl. 13.4.1.1 ("tw·h"); whether *h* means
overall or clear depth is a code-interpretation call. The Vr formula itself is correct (fed the
overall-depth basis it returns 1040 kN, within 1% of the Red Book; the small residual is the
kernel's inelastic web-buckling reduction just past the h/t limit, which the Red Book table omits).
Decision deferred to the registered engineer — same posture as the wind-gating call. Changing it
would make designs *less* conservative, so it must not be flipped without sign-off.

### Bolt resistances (Table 7.2) — 2026-06-28
Benchmarked `connections/bolts.py` (tension, single/double shear with threads in the shear plane,
bearing per mm) for Class 8.8 and 10.9, sizes M16–M30, against Red Book Table 7.2.

**Edition concern resolved:** despite the Red Book being SANS 10162-1:2005-based, its bolt factors
**match the kernel's 2011 values exactly** — no edition drift for bolts (the connection code was
already corrected against the official SANS PDF in a prior session). All shear/tension/bearing
values agree to <1%.

**Kernel bug found + fixed — M16-8.8 tensile strength.** The kernel applied a flat fu = 830 MPa to
all Class 8.8 bolts, but per **ISO 898-1**, Class 8.8 has fu = **800 MPa for d ≤ 16 mm** (830 only
for d > 16 mm) — confirmed by Red Book Table 7.2 (M16-8.8 tension = 96.5 kN, not ~100). The kernel
overstated M16-8.8 resistances by ~3.8% (unconservative). Fixed via `_bolt_fu_mpa()` in `bolts.py`
(8.8 → 800 if d ≤ 16). Low practical impact (M16 is not in the auto-designer's `STANDARD_BOLTS`),
but now correct and guarded. The fix is *more* conservative.

**Red Book typo (kernel correct):** Table 7.2 prints M24-10.9 bearing = 27.7 kN/mm, but bearing is
grade-independent (M24-8.8 = 22.7; 3·φbr·d·fu with d=24, fu=470 = 22.67). The 27.7 is an apparent
2↔7 transposition; the suite asserts the correct 22.7.

**Basis note (not a bug):** Table 7.2 bearing uses ply fu = 470 MPa (EN/S355JR min); the kernel's
design pipeline uses 480 MPa (SANS Table 6). The benchmark feeds 470 to test the formula; the
SANS-vs-EN plate-fu choice is the engineer's to confirm.

### Still open
- **Beam-column interaction** — the Red Book's only worked example (Ex 4.3) is *biaxial*; the kernel
  check is *uniaxial* (in-plane portal). Components (Cr, Mr) are validated; a true interaction check
  belongs at frame level (the whole-frame gate or a dedicated portal example).
- **End-plate moment connection** (Ch 7.9) — the kernel uses a simplified T-stub/flange-couple
  method flagged PROVISIONAL; validation needs the registered engineer's method sign-off.
- **Baseplate** (Ch 4.2) — needs the Red Book's worked thickness answer extracted to benchmark
  `check_baseplate`/`design_baseplate`.
