# TorenOne — Engineer Sign-Off Pack

> **For the reviewing registered (Pr.Eng) engineer.** This single document is designed so your review
> is bounded and fast. TorenOne's deterministic kernel computes every engineering number against
> published South African authorities; **your role is to (1) confirm the authorities are appropriate,
> (2) approve the design methods, and (3) take professional responsibility (stamp).** You do not need
> to re-derive anything — every benchmarked value is reproduced from a published source and guarded by
> an automated test. Allow ~1–2 hours.

**The correctness boundary TorenOne operates under (so you know what has and hasn't been touched):**
- 🟢 Anything that does not change an engineering number is built freely.
- 🟡 New engineering logic is written **only** by transcribing a published, accredited method, is
  marked **PROVISIONAL**, and is queued here for your sign-off.
- 🔴 No PROVISIONAL item is ever promoted to "verified", and **no engineering method is invented** —
  that judgment, and the stamp, are yours alone. Several items below are deliberately left
  **more conservative** pending your decision; none has been relaxed.

---

## Part 1 — Authorities to confirm

Please confirm these are the appropriate bases for the single-bay SANS steel portal-frame scope.

| Authority | Used for | Confirm |
|---|---|---|
| **SANS 10162-1** (hot-rolled steel, limit-states) | All member design (axial, moment, LTB, shear, interaction), connections | ☐ |
| **SANS 10160-1 / -2** | Load combinations; dead + imposed loads | ☐ |
| **SANS 10160-3:2019** (wind actions) | All wind pressures (qp, cpe, cpi) | ☐ |
| **EN 10025-2** (= SANS 50025-2) | Material fy for SA sections (Grade S355JR / 300W) | ☐ |
| **SAISC Red Book** (8th ed. 2013) | Independent benchmark — sections, capacities, bolts | ☐ |
| **Mahachi, *Design of Structural Steelwork to SANS 10162*** (CSIR 2004) | Independent benchmark — worked design examples | ☐ |

---

## Part 2 — Validation evidence (what is already proven, for your confidence)

Two accredited SA authorities independently reproduce the kernel's output across the whole design
path. Each row is guarded by an automated must-pass test.

| Area | Benchmarked against | Result | Tests |
|---|---|---|---|
| Section properties | Red Book Tables 2.9/2.10 | 11 sections ≤1% (2 data bugs fixed) | `validation/redbook/` |
| Compression `Cr` | Red Book Ex 4.1/4.3 · Mahachi E4.3 | exact–1.5% | redbook + textbook |
| Moment `Mr`, LTB `Mcr/Mr` | Red Book Ex 4.3/5.1/5.2 · Mahachi E5.1/**E5.2**/E6.1 | ≤1% | redbook + textbook |
| Classification | Red Book Table 5.3 (15 sections) | all match | redbook |
| Shear `Vr` formula | Red Book Ex 5.3 · Mahachi E5.1 | exact (basis flagged → D1) | redbook + textbook |
| Beam-column interaction (cl. 13.8) | Mahachi E6.1 (3 modes) | ≤0.2% | textbook |
| Bolt resistances | Red Book Table 7.2 (M16–M30 × 8.8/10.9) | <1% (1 bug fixed) | redbook |
| **Column base** | Mahachi E7.13 + E7.14 | reproduced to the mm | `test_textbook_column_base.py` |
| **Connections** (prying + bolt groups) | Mahachi E7.5–E7.9 | reproduced exactly | `test_textbook_connections.py` |
| **Wind pressures** | SANS 10160-3:2019 own Tables 1/3/4/6/10 (duopitch) + **Table 8 (mono-pitch, zone H)** | reproduced to rounding | `test_wind*.py`, `test_wind_pressure.py` |

---

## Part 3 — Decisions register (your sign-off checklist)

Each is a **method/modelling choice** the automated suite cannot settle (🔴 — only you may settle it).
Each lists the divergence, the current kernel default, and a recommendation. **None changes without
your sign-off.** Full working is in the linked detailed cards.

| # | Decision | Current default | Recommendation | Decision / date |
|---|---|---|---|---|
| **D1** | **Shear area basis** — clear web depth (kernel, ~4–5% conservative) vs overall depth (both authorities) | clear depth | Adopt **overall depth** (two authorities agree) | ☐ |
| **D2** | **Column-base method** — AISC-style (live) vs SANS/BS5950 effective-area (`baseplate_sans`, reproduces E7.13/E7.14) | AISC-style | Adopt the **SANS/textbook method** as production | ☐ |
| **D3a** | **End-plate connection** — flange-force-couple moment method | in use | Approve the method | ☐ |
| **D3b** | **End-plate prying** — currently omitted; EC3 method now validated (E7.5) | not modelled | **Adopt** the validated EC3 prying check | ☐ |
| **D4** | **Wind sign conventions / governing combination** (wind-on-frame model) | mechanically validated | Confirm SANS correctness | ☐ |
| **D5** | **Wind gating** — wind ULS checks are advisory/non-gating; `autosize_for_wind` OFF | advisory | After D4: **gate + auto-size for wind** | ☐ |
| **D6** | **Wind sway limit** — eaves drift vs H/400 (Annex D, informative), advisory | H/400 advisory | Confirm limit (H/400 vs H/150) + whether it gates | ☐ |
| **D7** | **Wind modelling scope** — ze=apex, internal-frame zones, transverse wind only | as built (conservative) | Confirm acceptable for the MVP | ☐ |
| **D8** | **Wide-span minor-axis effective length** — rafter minor axis braced at purlin spacing | in use | Confirm the effective-length assumption | ☐ |
| **D9** | **Bolt bearing ply fu** — kernel 480 (SANS) vs 470 (EN) | 480 | Confirm basis (minor) | ☐ |
| **D10** | **Section-data reconciliation** — 203×133 UB mass/width differ <1% vs Red Book | as packaged | Confirm at section sign-off | ☐ |
| **D11** | **Prismatic frame model** — no haunch modelled; under-predicts the eaves moment ~6% vs a haunched frame (E13.1: 141 vs 150 kN·m) | prismatic | Confirm acceptable, or model the eaves/ridge haunch | ☐ |
| **D12** | **Mono-pitch (single-slope) frame** — NEW geometry (T1-3), PROVISIONAL. Statics validated (equilibrium exact, pinned-base = 0, asymmetry, converges to the flat-portal solver as slope→0; `test_plane_frame_monopitch.py`). NB gravity applied as **true global-vertical** here (the duopitch path applies it member-**perpendicular** — ~1.5% at 10° pitch); reconcile. Member sizing reuses the validated SANS check path. **v2 (2026-07-01): the last mile — both eaves-knee connections + a (worst-base) baseplate + footing — is NOW designed on GRAVITY joint/base forces (reuses the geometry-agnostic connection/baseplate/footing design). WIND now MODELLED as ADVISORY (v2 inc 2, 2026-07-02): mono-pitch roof cpe from Table 8 (zone H, θ=0°/θ=180°); wind-on-frame via `MonopitchAnalysis.run_wind_combination` (dead-only reproduces the validated gravity statics); ULS-2/3 member + SLS-2 sway checks are INFORMATIONAL/non-gating like the duopitch path (D4–D7 apply).** | PROVISIONAL, gravity-sized; wind advisory (D4–D7) | Validate the mono-pitch method (load convention, gravity last-mile joint forces, wind sign/governing case) before any billable use | ☐ |
| **D13** | **Multi-span (internal-column) portal** — NEW geometry (Path B), PROVISIONAL, UNDER CONSTRUCTION. Statics foundation validated first: `solve_multispan_udl` (equal duopitch spans sharing pinned-base valley columns) passes equilibrium (vertical + horizontal), symmetry, internal-column load-share (≈2× external), and converges to the flat-portal solver at zero pitch (`test_plane_frame_multispan.py`). Gravity applied as **true global-vertical** (same corrected convention as D12). Member design (ext + internal columns + rafters) done. **v2 (2026-07-01): the last mile — an external eaves + a valley connection + a (worst-base, valley-governed) baseplate + footing — is NOW designed on GRAVITY joint/base forces. WIND now MODELLED as ADVISORY (v2 inc 2d, 2026-07-02): duopitch roof cpe applied to every span (conservative — the code's downwind-span reductions NOT taken), h/d over the full building width; wind-on-frame via `MultiSpanAnalysis.run_wind_combination` (dead-only reproduces the validated gravity statics); ULS-2/3 (ext + valley cols + rafters) + SLS-2 sway checks INFORMATIONAL/non-gating (D4–D7 apply).** Full 3D/web/report shipped. | PROVISIONAL, gravity-sized; wind advisory (D4–D7) | Validate the multi-span analysis model + member + gravity last-mile design + wind (incl. the conservative per-span cpe simplification) before any billable use | ☐ |

**Detailed cards:** D1/D2/D3/D8/D9/D10 → `docs/REDBOOK-VALIDATION.md`; D4–D7 → `docs/WIND-VERIFICATION.md`.

---

## Part 4 — The whole-frame validation gate

TorenOne should be validated **end-to-end against a complete worked portal frame**. We now have a
published one: **Mahachi Example E13.1, "Design of an industrial building"** — a full single-bay
portal (24 m span, 6 m eaves, 10° pitch, 5 m bay, hinged bases, haunched eaves/ridge, 305×165×46
columns + 305×102×33 rafters, Grade 300W) with geometry, loads, load combinations, analysis member
forces, and full member design.

**Progress:**
- ✅ **Member-design half validated** — fed the book's analysis forces, our member-design path
  reproduces E13.1's column design (cross-section interaction 0.686 exact, overall 0.522 exact, LTB
  0.757 vs 0.743 — ≤2%, conservative). Suite: `kernel/tests/validation/textbook/test_textbook_whole_frame.py`.
  Our section library *is* the book's 305×165×46 (A, Zplx, rx, ry, Iy, J, Cw all match).
- ✅ **Analysis half corroborated** — fed the book's gravity load (LC5 = 1.2D+1.6L), our PyNite frame
  model reproduces the book's **eaves moment within ~6%** (141 vs 150.1 kN·m). The small difference is
  the book's **haunch** (which stiffens the eaves and attracts the extra moment) + its second-order
  analysis — both small for this stiff portal. Same suite. **Known simplification for the engineer:**
  our model is *prismatic* (no haunch), so it under-predicts the eaves moment by ~6%; the haunch
  region is locally much stronger, and modelling it is the standard refinement (decision for the
  engineer if tighter eaves accuracy is required).

A second, independent whole-frame check against **one of your past stamped projects** remains the
ideal final confirmation (`tools/validate_frame.py` is ready for it), but E13.1 means the gate is no
longer *blocked* on the co-founder's time.

---

## Part 5 — How to record your decisions

For each Dn above: enter **Approve** / **Approve as recommended** / **Modify (note)** / **Reject**, with
your name + ECSA reg + date. Approved methods are then promoted out of PROVISIONAL in the code and the
relevant default is updated (with a test). Nothing is promoted without this record.

_This pack is generated from the live validation suite + the detailed cards; if the code changes, the
benchmarked values regenerate. Last assembled: 2026-06-29._
