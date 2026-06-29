# Wind — verification card (for the registered engineer)

> **Purpose.** Shrink the co-founder's wind review from "validate all of wind" to confirming a small
> set of judgment calls. This card separates **what is already benchmarked against the authoritative
> standard** (no judgment needed — just confirm the standard is the right one) from **the few
> modelling-method decisions that genuinely need a registered engineer** (🟡/🔴 on the correctness
> boundary). Same posture as the baseplate card in `docs/REDBOOK-VALIDATION.md`.

**Code basis.** The kernel implements **SANS 10160-3:2019** (the current SA wind-actions code,
Edition 2.1), transcribed clause-by-clause from the official standard (held in `standards/`).

**Why neither textbook is used for wind.** Two SA authorities were checked and neither can validate
the wind engine:
- The **Mahachi textbook** (our second authority for steel *members*) computes wind to
  **SANS 10160:1989** — three editions and a complete method-rewrite behind the current code (it uses
  `Vz = kz·V`, `qz = kp·Vz²`, terrain categories 1–4; the 2019 code uses peak velocity pressure
  `qp = ½·ρ·vp²`, terrain categories A–D, Eurocode-aligned). Its worked wind example (E2.3) therefore
  **cannot** validate our engine.
- The **SAISC Red Book** (8th ed. 2013) is a steelwork *handbook* (sections, members, bolting,
  connections, purlins, crane gantries) — it **has no wind/loading design chapter** and works no wind
  example (it lists SANS 10160-3 only as an input standard; the handbook states "it is not a
  textbook").

So the authority for wind is the **SANS 10160-3:2019 standard itself**, which our test suite checks
against directly (below). An independent *worked-example* second authority would require a dedicated
SA wind-loading publication (e.g. an SAISC/Goliger wind-loading guide) — not currently in hand.

---

## A. Already validated against the standard's own published tables (no judgment needed)

The wind **pressure engine** reproduces the standard's own tables to within their printed rounding.
This is a *primary-source* benchmark (the rulebook itself), stronger than any textbook example.

| Quantity | Clause / Table (SANS 10160-3:2019) | Test (oracle = the standard) |
|---|---|---|
| Roughness factor `cr(z)` (4 terrain cats × 15 heights) | Table 3 / cl. 7.3 | `test_wind.py::test_roughness_factor_reproduces_sans_table_3` |
| Wind-profile parameters `zg, zo, zc, α` | Table 1 | `test_wind.py::test_table1_parameters_are_the_sans_values` |
| Air density `ρ` vs altitude | Table 4 | `test_wind.py::test_air_density_table4_points_and_interpolation` |
| Peak wind speed `vp = cr·co·vb,peak` | eq. 3–5 | `test_wind.py::test_peak_wind_speed_uses_cr_and_unit_peak_factor` |
| Peak velocity pressure `qp = ½·ρ·vp²` | eq. 6 / cl. 7.4 | `test_wind.py::test_peak_velocity_pressure` |
| Wall external coefficients `cpe` (zones D/E) | Table 6 / cl. 8.3 | `test_wind_pressure.py::test_wall_cpe_matches_table_6` |
| Lack-of-correlation factor | cl. 8.3.2.4 | `test_wind_pressure.py::test_lack_of_correlation_factor` |
| Duopitch-roof coefficients `cpe` (zones H/I, pitch interp.) | Table 10 / cl. 8.3 | `test_wind_pressure.py` (roof rows) |
| Internal pressure `cpi` (enclosed + dominant opening) | cl. 8.3.4 | `test_wind_pressure.py` |
| Net surface pressure `qp·(cpe − cpi)` → member UDL | cl. 8.3 | `test_wind_loads.py` |

**Engineer action for Section A:** confirm only that **SANS 10160-3:2019 is the appropriate wind
code** for our scope. The numbers above are the code's own values — nothing to re-derive.

---

## B. Decisions that need the registered engineer (the actual remaining wind work)

These are **method/modelling choices**, not data the test suite can settle. Each is listed with the
specific question, the current kernel default, and a recommendation. **Per company law, only the
registered engineer may settle these (🔴 — do not change without sign-off).**

### B1 — Wind-on-frame sign conventions & governing load case
- **What.** Wind pressures are applied to the PyNite portal frame as the ULS-2 / ULS-3 combinations
  and members are *checked* under them (`PortalAnalysis.run_wind_combination`,
  `design.py::_wind_combination_checks`). The mechanics are validated (equilibrium, net uplift,
  windward/leeward asymmetry — `test_plane_frame_wind.py`), but **whether the sign conventions and
  which combination governs are correct per SANS is an engineering-judgment call.**
- **Question for the engineer.** Confirm the windward-pressure / leeward-suction / roof-uplift
  sign convention and that the worst-case combination is being picked.

### B2 — Should wind checks GATE the design (and auto-size for wind)?
- **Current default.** Wind ULS checks are **ADVISORY / non-gating** — they report a utilisation but
  do **not** fail the design or drive member sizing. Members are auto-sized on **gravity only**;
  `design(autosize_for_wind=True)` exists (sizes for the gravity+wind envelope) but is **OFF by
  default**. (Reason: once the accurate area-dependent imposed roof load landed, gravity-sized
  members failed the *provisional* wind checks; rather than fail designs on an unvalidated wind
  model, the wind ULS checks were made advisory.)
- **Question for the engineer.** Once B1 is confirmed: flip `autosize_for_wind` default to **True**
  (size + gate on wind) and expose it via the service/API? **Recommended once B1 is signed off.**

### B3 — Serviceability sway limit (eaves drift)
- **Current default.** SLS-2 wind sway (eaves lateral drift) is checked against **H/400** (Annex D,
  which is *informative*) and reported **ADVISORY / non-gating**. A standard 15 m frame drifts
  ≈ 45 mm ≈ 3.6 × H/400.
- **Question for the engineer.** Confirm the appropriate limit (**H/400 vs H/150**) and whether sway
  should **gate** the design.

### B4 — Modelling scope / conservatism assumptions (confirm acceptable)
- Reference height `ze = apex (ridge) height` — uniform pressure over height (low-rise h ≤ b);
  conservative (higher `qp`).
- Internal-frame zones only (walls D/E, roof H/I); **gable-edge zones and near-flat roofs deferred**.
- Frame application is **transverse wind (θ = 0°)** only; longitudinal (θ = 90°) pressures are
  computed but not yet pushed through the frame.
- **Question for the engineer.** Confirm these scope/conservatism assumptions are acceptable for the
  single-bay portal MVP, or flag which must be closed before live use.

---

## Summary for the engineer

- **Section A (pressures):** validated against the 2019 standard's own tables — just confirm the code
  is appropriate. *No re-derivation needed.*
- **Section B (4 items):** the real wind sign-off — sign conventions (B1), gate/auto-size decision
  (B2), sway limit (B3), scope assumptions (B4). Settling B1 unlocks B2.

**Master document:** these wind items are D4–D7 in the engineer sign-off pack
(`docs/SIGN-OFF-PACK.md`), alongside the baseplate (D2), end-plate connection (D3), and shear-area
(D1) cards in `docs/REDBOOK-VALIDATION.md`.
