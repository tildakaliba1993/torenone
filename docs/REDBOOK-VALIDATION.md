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

## Second authority — Mahachi, *Design of Structural Steelwork to SANS 10162* (CSIR, 2004)

A second, independent accredited source: a Pr.Eng-authored, professor-reviewed textbook of fully
worked SANS 10162 design examples. Suite: `kernel/tests/validation/textbook/`. Where the Red Book
gives section data + capacity tables, this gives worked *design* answers — so two respected SA
authorities now independently confirm the same kernel output.

| Check | Function | Textbook (Mahachi) | Kernel | Δ |
|---|---|---|---|---|
| Compression Cr (E4.3, 356×171×67, 300W, KL=6 m) | `cr_flexural` | 589 kN | 589 | exact |
| Moment Mr, laterally supported (E5.1, 457×191×98) | `mr_laterally_supported` | 602 kN·m | 602 | exact |
| Shear Vr (E5.1, 457×191×98) | `vr_web` | 950 kN | 950 | exact (overall-depth basis) |
| Classification (E5.1 / E4.3) | `classify_section` | Class 1 / not Class 4 | match | — |
| LTB critical moment Mcr (E6.1, 305×305×118) | `mcr_elastic` | 7 400 kN·m | 7 400 | exact |
| Moment-gradient ω2 (E6.1, κ=0.75) | `omega2_factor` | 2.5 | 2.5 | exact |
| **Beam-column interaction (E6.1)** — cl. 13.8.1, all 3 modes | `beam_column_check` | 0.930 / 0.72 / 0.994 | 0.931 / 0.719 / 0.995 | ≤0.2% |

The beam-column interaction (E6.1) is the check the Red Book lacked — now validated end-to-end from
an accredited source. (Note: the kernel floors the U1 amplification at 1.0, correct for our
*unbraced* portals; the book's *braced* overall-member check uses the unfloored U1 — the raw U1
formula matches the book at 0.417, and `beam_column_check` is validated with the book's U1 values.)

**Strengthens the shear-area flag (below):** the textbook's E5.1 computes the shear area as
**overall depth × tw** — the *same* basis as the Red Book Ex 5.3. **Two independent authorities now
agree** the shear area uses the overall depth, while the kernel pipeline uses the (more conservative)
clear web depth. This makes the co-founder's decision on that item near-trivial: adopt the
overall-depth basis (both authorities) — recommended, pending his sign-off.

### Column base — E7.13 (axial only) + E7.14 (axial + moment) — 2026-06-29

The textbook works **both** column-base cases numerically (the Red Book §4.2.2 pointed to the Green
Book and gave no worked answer, so this is the first published benchmark we have for the base). New
module `foundations/baseplate_sans.py` implements the textbook's SANS 10100 / BS 5950 effective-area
method and **reproduces every published output to the millimetre** (suite:
`kernel/tests/validation/textbook/test_textbook_column_base.py`, 7 must-pass tests):

| Check | Textbook (Mahachi) | Kernel | Δ |
|---|---|---|---|
| **E7.13** Bearing Br = 0.4·fcu (25 MPa) | 10 MPa | 10 | exact |
| E7.13 Effective area required | 90 000 mm² | 90 000 | exact |
| E7.13 Projection a (quadratic root) | 56.4 mm | 56.4 | exact |
| E7.13 Plate thickness | 18.5 → **20 mm** | 18.8 → 20 | ≤2% |
| **E7.14** Eccentricity e = M/N (> d/6 → tension) | 1333 mm | 1333 | exact |
| E7.14 Stress-block depth d2 | 135 mm | 135 | exact |
| E7.14 Concrete compression Cu | 497 kN | 497 | exact |
| E7.14 Holding-down bolt tension Tu | 299 kN | 299 | exact |
| E7.14 Bolt area required An → bolt | 519 mm² → **M30** | 519 → M30 | exact |
| E7.14 Plate thickness (max of sides) | 33.7 → **35 mm** | 33.7 → 35 | ≤1% |
| E7.14 Gusset Mr / Vr (2×16 mm) | 129.6 / 1710 | 129.6 / 1710 | exact |
| E7.14 Welds (E80XX) | 14 mm / 8 mm fillet | 14 / 8 | exact |

Planned additions (next increments): LTB beam (E5.2) as a second LTB source, and bolted/welded
shear connections (E7.1–E7.12) as a second source for the end-plate connection.

## Method items for the co-founder (not component-benchmarkable — method choices, need sign-off)

These are **not** simple data/formula checks the suite can settle; each is a modelling-method choice
where the kernel and the Red Book differ (or the kernel is explicitly PROVISIONAL). Listed with the
specific divergence so the registered engineer can adjudicate quickly. Same posture as the wind and
shear-Av-basis flags — do not change without sign-off.

### Baseplate / column base — VERIFICATION CARD (decision for the registered engineer)

**The situation.** The kernel ships **two** column-base implementations:
- `foundations/baseplate.py` — the **AISC-style** model currently in the live design path (elastic
  pressure block, 0.85·f'c cylinder bearing, US cantilever-overhang plate sizing).
- `foundations/baseplate_sans.py` (NEW, 2026-06-29) — the **SANS 10100 / BS 5950 effective-area**
  method used by **both** SA authorities (Mahachi §7.9 *and* Red Book §4.2.2). It reproduces the
  textbook's worked Examples E7.13 + E7.14 to the millimetre (table above). **PROVISIONAL; not yet
  wired into the live path.**

The two methods diverge at every step and give different numbers:

| Aspect | Kernel (AISC-style, live) | Both SA authorities (`baseplate_sans`) |
|---|---|---|
| Bearing strength | φc·0.85·f'c = 0.6·0.85·25 = **12.75 MPa** (cylinder f'c) | **Br = 0.4·fcu** = 10 MPa @25, 8 MPa @20 (cube) |
| Plate thickness | plastic `Mr=φ·fy·t²/4` on an AISC cantilever (0.95·d / 0.80·bf) | effective-area `t = a·√(3p/(φ·fy))` |
| Base + moment | elastic peak pressure N/A + M/Z | rectangular concrete **stress block** (solve d2; Tu = Cu − Pu) |
| Anchor tension | steel-code `0.75·φar·Ab(shank)·fu` (φar=0.67) | concrete-code `φar·An(stress-area)·fu` (SANS 10100 cl. 25.2.2.1) |

**Decision needed (🔴 — only the registered engineer may settle this):** adopt the SANS/textbook
method (`baseplate_sans`, now validated against a published SA authority) as the production column
base, replacing the AISC-style model? Recommended — it makes our shipped method identical to two SA
authorities, the easiest possible sign-off. On approval: wire `baseplate_sans` into the `DesignCode`
seam (`codes/sans10162.py` `design_baseplate`) and retire/keep the AISC model as a cross-check.

### End-plate moment connection (`connections/moment_endplate.py`) — Red Book Ch 7.9
Kernel uses a simplified T-stub / flange-force-couple method, flagged PROVISIONAL in its docstring.
The Red Book Ch 7.9 gives a tabulated design-check procedure. Benchmarking is only meaningful once the
registered engineer signs off the *method*; the bolt primitives it relies on are already validated.

### Beam-column interaction (`checks/interaction.py`) — validated at component level
The kernel's `beam_column_check` is *uniaxial* (in-plane portal bending). The Red Book's only worked
example (Ex 4.3) is a *biaxial* multi-storey column, so it is not a 1:1 source. The inputs that feed
the interaction (Cr, Mr) are validated above; a true end-to-end interaction check belongs at the
**frame level** — the whole-frame gate (`benchmarks.py`) or a dedicated single-bay portal example.
