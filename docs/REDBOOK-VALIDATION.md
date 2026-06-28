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
| Compression resistance Cr | Ch 4 | `test_redbook_compression.py` | ⏳ planned |
| Flexural resistance Mr (+ LTB) | Ch 5 | `test_redbook_flexure.py` | ⏳ planned |
| Classification | Ch 11 / Table 4 | `test_redbook_classification.py` | ⏳ planned |
| Beam-column interaction | Ch 4/5 | `test_redbook_interaction.py` | ⏳ planned |
| Bolts + end-plate (edition-aware) | Ch 6/7 | `test_redbook_connections.py` | ⏳ planned |
| Baseplate | Ch 7/12 | `test_redbook_baseplate.py` | ⏳ planned |

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
