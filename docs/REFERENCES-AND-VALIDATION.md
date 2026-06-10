# TorenOne — Code Basis, Benchmark & Validation Tolerances

> How we feed the kernel correct engineering rules **legally**, the benchmark we validate against,
> and the tolerances that define "correct." Governed by the [PRD](./PRD.md).
>
> **Status:** v1.0 · **Last updated:** 2026-06-09

---

## 1. The legal/correctness position (read first)

SANS standards (SANS 10160, SANS 10162-1) are **copyrighted documents sold by the SABS**. We do
**not** reproduce or pirate them. Instead:

1. We implement the kernel from **publicly available worked examples and the codes' published
   lineage** (below), with every formula and coefficient **tagged with the SANS clause it
   implements**.
2. The registered engineer (co-founder) **verifies every clause and coefficient against the
   officially purchased standards** before the validation gate (Phase 8). Tags marked `VERIFY`
   in `rules_version.py` and the check modules are the checklist.

**This is not a shortcut — it's the correct engineering process:** the methods are well-documented
public knowledge; the authoritative numbers get confirmed against the official source by a Pr.Eng.

### Code lineage we exploit
| SANS code | Aligned with | Why it helps us |
|---|---|---|
| **SANS 10162-1** (steel, limit states) | **CSA S16** (Canada) | SANS 10162-1 is derived from CSA S16 — methods, classification, and resistance equations are near-identical. Abundant public CSA S16 worked examples. |
| **SANS 10160-3** (wind) | **EN 1991-1-4** (Eurocode) | Per SkyCiv and public refs, SANS 10160-3 is "similar to EN 1991-1-4, differing mainly on the basic wind-speed map and terrain categories." |
| **SANS 10160-1/-2** (basis, self-weight & imposed) | ISO 2394 / EN 1990–1991 | Partial-factor limit-state format is shared with Eurocode basis of design. |

> Implementation discipline: where SANS and its parent code differ (e.g. SA wind-speed map,
> terrain categories, partial factors), the **SANS value governs** and is the thing the co-founder
> must confirm. The parent-code example only validates the *method*, not the SA-specific numbers.

## 2. What the co-founder should acquire (one-time)
- [ ] **SANS 10160-1, -2, -3** and **SANS 10162-1** (official SABS copies) — for clause/coefficient verification.
- [ ] **SAISC "Design of Structural Steelwork to SANS 10162" (4th Edition)** — SA-authoritative, ships **worked examples and validated spreadsheets**; ideal independent cross-check for the validation gate. (saisc.co.za)
- [ ] **SAISC Red Book** section tables — source for the SAISC section property database (Task 1.2).
- [ ] Confirm exact **editions** to pin in `rules_version.py`.

## 3. The benchmark — "TorenOne Reference Frame v1"

The validation gate (PRD §10, Task 8.2) runs **one representative frame** end-to-end and asserts
our output matches a trusted reference within tolerance (§5). A fully-specified frame with locked
golden outputs is a better automated regression test than an informal past job — every number is
documented.

**Reference Frame v1 — a typical SA single-bay pitched-roof warehouse portal:**
| Parameter | Value (proposed) |
|---|---|
| Structural form | Single-bay symmetric pitched portal, **pinned bases** |
| Span | 24 m |
| Eaves height | 6 m |
| Roof pitch | 10° |
| Bay spacing | 6 m |
| Building length | 42 m (7 bays) |
| Cladding/roof | Sheeted roof and walls |
| Wind | Basic wind speed and terrain category per a defined SA location — **co-founder to fix** (e.g. Vb, Terrain Category B) |
| Imposed roof | Per SANS 10160-2 |
| Steel grade | S355JR (confirm) |
| Section series | Per the curated SAISC list (Task 1.2) |

> These dimensions are deliberately ordinary — the validation target must be the *typical* frame,
> not an unusual one. Co-founder to confirm/adjust to match the chosen reference design.

### How golden outputs are locked
- **Primary (authoritative):** co-founder designs Reference Frame v1 by hand and/or in **Prokon /
  the SAISC 4th-edition spreadsheet**, and records the reference member forces, deflections,
  utilisations, and final section sizes. These become the asserted values in `test_benchmark`.
- The benchmark inputs + golden outputs are committed as a fixture so the gate runs in CI forever.

### Per-module public cross-checks (independent method validation)
Used as additional regression tests so each kernel module is validated in isolation, not only at
the end:
| Module | Public worked-example source(s) |
|---|---|
| Wind (SANS 10160-3) | SkyCiv SANS 10160 wind documentation; published SA wind worked examples (e.g. the 50×25×5 m, Vb 40 m/s industrial-building example) |
| Loads & combinations (SANS 10160-1/-2) | SANS 10160 lecture/worked materials; SA university course examples |
| Plane-frame analysis | Standard portal-frame statics worked examples (any reputable structures textbook) |
| Member checks (SANS 10162-1) | CSA S16 worked examples (method-identical); SAISC 4th-edition examples |

## 4. Tolerances — the definition of "correct" (recommended)

These tolerances are what `test_benchmark` and the regression suite assert. They balance "tight
enough to catch real errors" against "loose enough for legitimate rounding / modelling choices."

| Quantity | Tolerance | Rationale |
|---|---|---|
| **Wind pressures / applied loads** | **±2%** | Deterministic from code formulas; small differences only from rounding of coefficients. |
| **Member forces (M, V, N)** | **±2%** | Elastic analysis is deterministic; differences come from minor modelling/rounding. |
| **Deflections (SLS)** | **±5%** | More sensitive to section-property rounding and stiffness assumptions. |
| **Utilisation ratios** | **±5%** | Compound of forces + resistances; small input deltas accumulate. |
| **Section selection (auto-size)** | **Exact match**, or at most **±1 adjacent size** *with a documented reason* | The end-deliverable; a different section is a red flag unless explained (e.g. reference used a non-stocked size). |
| **Classification (Class 1–3)** | **Exact** | Discrete; must match. |
| **Pass/Fail of each check** | **Exact** | A check that flips pass↔fail is a hard failure of the gate. |

Rules:
- A benchmark/regression test **fails the build** if any quantity exceeds its tolerance.
- Tolerances are encoded as constants in the test suite, reviewed and signed off by the co-founder.
- Class 4 sections are **out of scope** (PRD §6.2) — the kernel refuses them rather than approximating.

## 5. Provisional code values sourced (pending engineer sign-off)
Values sourced from free, authoritative references to unblock development in sequence. Each is
flagged PROVISIONAL in code and MUST be confirmed by the registered engineer against the official
SANS standard before the Phase 8 validation gate.

| Value | Sourced value | Source (free, authoritative) | Used in |
|---|---|---|---|
| Imposed roof load — **inaccessible** roof (SANS 10160-2 Table 5) | **0.4 kN/m²** (400 N/m²) UDL | SANS 10160-2:2011 Table 5; confirmed peer-reviewed in *J. SAICE* (SciELO S1021-20192021000100005); corroborated across multiple references | `loads/imposed.py` (Task 1.5) |
| **Load combination factors** (γG 1.2/0.9, STR-P 1.35, imposed 1.6, wind 1.3, SLS γG 1.1; ψ0=0 inaccessible roof) | as listed | ⚠️ **DRAFT SANS 10160-1:2009** (Table 3/2, eq. 6/7/10) — **confirm vs FINAL published standard** | `loads/combinations.py` (Task 1.7) |

> Concentrated roof load (~1.0 kN, local element checks) noted but out of scope for the frame UDL.
> Accessible-roof categories not yet sourced — out of MVP scope (the module raises rather than guessing).

## 6. Open items (block the validation gate until closed)
- [ ] Co-founder fixes Reference Frame v1's wind location (Vb, terrain) and steel grade.
- [ ] Co-founder produces the golden reference outputs (Prokon / SAISC spreadsheet / hand calc).
- [ ] Confirm SANS editions → update `rules_version.py` (remove `VERIFY`).
- [x] Section data for v1 — **loaded** from the official free SAISC "Database of Structural Steel Sections" (64 sections: IPE-AA/IPE 100–200, UB, UC), cross-checked against known published values. **PROVISIONAL** pending the engineer's spot-check sign-off below. Confirm intended steel grade (e.g. S355).
- [ ] Sign off the **provisional code values** in §5 (imposed roof load 0.4 kN/m²; SANS 10160-1 wind/steel values).
- [ ] ⚠️ Confirm the **SANS 10160-1 load-combination factors** against the **FINAL published standard** (ours are from the DRAFT — §5 / SOURCES E9).
- [ ] Sign off the tolerance table above.
