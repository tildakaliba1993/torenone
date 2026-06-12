# TorenOne — Tasks & Implementation Plan

> The single source of truth for **what we are building and how far along we are.** Update in real time: when a task is done and its tests pass, mark it `[x]`. Governed by the [PRD](./PRD.md) and [Design & Architecture](./DESIGN-ARCHITECTURE.md).
>
> **Status:** v1.1 · **Last updated:** 2026-06-12 (2.8 done — report renders connections/baseplate/footing/tonnage; last-mile complete end-to-end; next: resume Phase 4 (4.5) → Phase 5)

---

## How to use this document

**Status legend:** `[ ]` not started · `[~]` in progress · `[x]` done (tests pass) · `[!]` blocked

**The TDD rule (non-negotiable — human lives are at stake):**
1. Write the test first (with the expected value from a worked example, hand calc, or the benchmark project).
2. Run it — watch it fail.
3. Implement until it passes.
4. **A task is only `[x]` when its tests are written AND passing in CI.** No exceptions for kernel logic.

**Discipline rule:** if work isn't in this plan, it isn't in the MVP. New ideas go to §Backlog (out of scope), not into a phase.

---

## Progress dashboard

| Phase | Title | Status |
|---|---|---|
| 0 | Foundations & project setup | `[x]` |
| 1 | Core engineering kernel (TDD) | `[~]` |
| 2 | Report engine | `[x]` |
| 3 | AI orchestration layer | `[x]` |
| 4 | Engineering service (FastAPI) + auth | `[x]` |
| 5 | Supabase backend (data + RLS) | `[~]` |
| 6 | Frontend (design system + screens) | `[ ]` |
| 7 | Integration & end-to-end | `[ ]` |
| 8 | Validation gate & hardening | `[ ]` |
| 9 | Pilot & YC readiness | `[ ]` |

> **Scope addition (2026-06-11, advisor-aligned) — "complete the wedge."** We are *completing the single-bay portal frame end-to-end* (connections, baseplates, footing, tonnage cost) so the engineer never leaves TorenOne — not broadening to new structures. New work folds into the existing phases: **kernel last mile → Phase 1 ext (1.15–1.18)**, **report → 2.8**, **frontend spec-review + visual feedback + cost/ton → 6.5/6.6**. Check mode (#5) and tonnage/cost (#4, partial) are already shipped.
>
> **Execution order from here:** finish the in-flight Phase 4 service core (**4.5 error handling**) → **kernel last mile (1.15–1.18)** → **report 2.8** → resume the normal sequence (Phase 5 Supabase, Phase 6 frontend …). This keeps everything green and never reopens already-passing work destructively.

---

## Phase 0 — Foundations & project setup
*Goal: repos, tooling, CI, and the design tokens in place so all later work is test-gated and consistent.*

- [x] **0.1 Repositories & structure**
  - [x] Monorepo created (`kernel/`, `service/`, `web/`, `tools/`, `docs/`); git initialised. **Decision: monorepo** (recorded in README).
  - [x] READMEs link to PRD / Design / Tasks / References.
- [x] **0.2 Python tooling (kernel + service)**
  - [x] `pyproject.toml` (requires-python ≥3.11), `ruff` + `mypy` (strict) configured.
  - [x] `pytest` + `pytest-cov` configured; pytest pathing for `kernel/src` + `tools`.
- [x] **0.3 Frontend tooling**
  - [x] Next.js 16.2.7 + TypeScript + Tailwind v4 scaffolded in `web/` (pinned to stable — create-next-app had pulled a preview); `eslint` + `prettier` (+ `prettier-plugin-tailwindcss`).
  - [x] `vitest` + React Testing Library (jsdom) — **3 unit tests passing**; `playwright` configured with a smoke E2E (executes from Phase 7).
- [x] **0.4 CI (GitHub Actions)**
  - [x] `.github/workflows/ci.yml`: **Python job** (ruff + mypy + pytest, coverage gate) and **Web job** (npm ci → lint → typecheck → test → build) on every PR; merge blocked on red.
- [x] **0.5 Design system foundation**
  - [x] Steel-blue + neutral + semantic tokens — canonical `tools/torenone_tokens/tokens.py` → `web/design/tokens.css`, mapped into Tailwind v4 `@theme` in `globals.css` (dark-first).
  - [x] Geist Sans / Geist Mono wired via `next/font` in the root layout.
  - [x] First component `StatusBadge` (icon + label + colour — PRD FR-19) with tests; landing page renders the tokens.
  - [x] **Test:** WCAG-AA contrast check **passing (13/13)**; web app **builds, type-checks, lints, unit-tests** green.
  - [ ] ↪ **Moved to Phase 6:** `shadcn/ui` registry init + Supabase UI auth/storage component pulls — done when building those screens, themed to our tokens (avoids clobbering the verified palette before any screen needs it).
- [x] **0.6 Secrets & config** — `.env.example` (secrets server-side only); `.gitignore` excludes real env; **[PROJECT-SETUP.md](./PROJECT-SETUP.md)** documents full Supabase/Vercel/GitHub isolation.

**Acceptance: MET.** Kernel/tools suite green (17 tests); web app scaffolded and green (lint + types + 3 unit tests + production build); tokens render with verified AA contrast; CI gates both stacks; project fully isolated. Only deferred item is the per-screen shadcn / Supabase-UI component pulls (correctly Phase 6).

---

## Phase 1 — Core engineering kernel (TDD) · *the moat*
*Goal: a deterministic, version-pinned, fully-tested Python package that turns a `FrameSpec` into a verified `DesignResult`. Build strictly test-first.*

- [x] **1.1 Domain models (Pydantic)**
  - [x] `FrameSpec` (geometry, materials, base fixity, restraints, dead/imposed/wind context) — frozen + `extra="forbid"`; computed geometry (apex height, building length).
  - [x] Validation: reject invalid geometry, unknown fields, mutation (PRD FR-1/FR-3). **Tested.**
  - [x] Result contracts: `LoadCase`, `LoadCombination`, `MemberForces`, `AnalysisResult`, `CheckResult` (clause required — FR-18), `SectionChoice`, `DesignResult` (passed/governing-utilisation aggregation; **empty checks never vacuously pass**). **27 model tests passing.**
- [x] **1.2 Section database (SAISC)**
  - [x] `SectionProperties` schema + `SectionLibrary` (lookup, dedupe, lightest-first ordering, JSON loader, `load_default()`).
  - [x] Real data loaded from the official **SAISC "Database of Structural Steel Sections"** (free PDF) via a documented, re-runnable parser (`tools/build_saisc_sections.py`): **64 sections** — IPE-AA/IPE 100–200, Universal Beams, Universal Columns; 0 Class-4. Provenance + units in the data file `_meta`.
  - [x] **Spot-check tests** vs independently-known published values (IPE/UC area, Ix, elastic *and* plastic moduli, ry, J, Cw) — 8 tests passing.
  - [ ] ⏳ **Final sign-off (Phase 8 gate, non-blocking):** registered engineer spot-checks the dataset vs the SAISC Red Book; data is flagged **PROVISIONAL** until then.
- [x] **1.3 Rules versioning** — `rules_version.py` (pinned editions + `as_dict()`), tested. Stamping into `DesignResult` wires in at 1.12. *(Editions still marked `VERIFY` pending the official standards.)*
- [x] **1.4 Dead loads** — member self-weight (mass × g) + roof/services/cladding area loads × tributary width → `DeadLoadResult` (with breakdown for the audit view). Code-agnostic; SANS partial factors deferred to 1.7. **5 tests, hand-calc verified.**
- [x] **1.5 Imposed roof loads (SANS 10160-2)** — inaccessible-roof UDL = 0.4 kN/m² (Table 5) × tributary → `ImposedLoadResult` (with category + clause for the audit view). Value **PROVISIONAL** (sourced from a free peer-reviewed reference; pending engineer sign-off — REFERENCES §5). Accessible roofs out of scope (raise). **4 tests.**
- [x] **1.6 Wind loads (SANS 10160-3:2019)** *(highest-risk; built in layers — all done & validated vs the standard's tables)*
  - [x] **Velocity/pressure engine (1.6a)** — full **SANS 10160-3:2019** method: terrain params (Table 1, all of A/B/C/D), power-law `cr(z)=1.36((z'−zo)/(zg−zo))^α`, `vb,peak=1.0·vb`, peak wind speed `vp`, `qp=½ρvp²`, air density vs altitude (Table 4). **Validated against the standard's own Table 3** (4×15 cells) + 10 tests. *(Real values from the official standard — earlier "PENDING terrain" now resolved.)*
  - [x] **External pressure coefficients (1.6b)**
    - [x] **Vertical walls** — `cpe,10` zones D/E vs h/d + lack-of-correlation factor (**Table 6 + cl. 8.3.2.4**). Validated exactly vs Table 6; 7 tests.
    - [x] **Duopitch roof** — zones **H** (windward) & **I** (leeward) `cpe,10`, pitch 5–45°, both windward branches (uplift + downforce) (**Table 10, θ=0°**). Validated vs Table 10 + cross-checked vs EN 1991-1-4 Table 7.4a; 7 tests. *(Internal-frame scope; gable-edge F/G, ridge J, near-flat <5° deferred post-MVP.)*
  - [x] **Internal pressure coefficients (1.6c)** — enclosed (+0.2/−0.3, cl. 8.3.9.6 NOTE 2) + dominant-opening (0.75/0.90·cpe, eq. 14/15) with the favourable cpi=0 case (cl. 8.3.9.1); windward dominant opening drives uplift. 4 tests. *(μ/Figure-16 refinement deferred.)*
  - [x] **Frame line loads (1.6d)** — `wind_loads(spec)`: ze=apex → qp → net `qp·(cpe−cpi)` → windward/leeward column & rafter UDLs, enumerated over cpi cases × roof branches → `WindLoadResult`. qp hand-verified; uplift case + dominant-opening uplift explicitly tested. 5 tests.
- [x] **1.7 Load combinations (SANS 10160-1)** — `load_combinations(spec)`: ULS STR (eq.6/7) + SLS (eq.10) with Table 3 factors (γG 1.2/0.9, STR-P 1.35; imposed 1.6, wind 1.3; SLS γG 1.1). Inaccessible-roof ψ0=0 ⇒ imposed/wind never combine; explicit favourable-permanent **uplift** combo. 6 tests. ⚠️ **PROVISIONAL — from the DRAFT SANS 10160-1; confirm factors vs the final standard** (SOURCES/REFERENCES).
- [x] **1.8 2D plane-frame analysis**
  - [x] Integrate **PyNite** (PyNiteFEA 1.6.2); build the portal model (columns, rafters, apex, pinned bases).
  - [x] Solve first-order linear elastic per combination → M, V, N at col-bases, eaves, apex.
  - [x] **Tests (14):** exact validation — simply-supported beam UDL, cantilever point load, pinned-base portal stiffness-method; PortalAnalysis contract (symmetry, vertical equilibrium, zero base moment, correct locations). All 14 passing. Unit convention: N/mm internally; kN/kN·m in AnalysisResult.
- [x] **1.9 Second-order / sway check** — SANS 10162-1:2011 cl. 8.7 U2 amplification factor.
  - [x] `u2_factor()` — pure formula U2 = 1/(1−θ); raises `FrameUnstableError` for θ ≥ 1.0.
  - [x] `compute_sway_check()` — applies notional H = 0.005×gravity at eaves, runs first-order PyNite analysis, extracts drift, returns `SwaySensitivityResult`.
  - [x] Sway-sensitive flag: U2 > 1.4 (PROVISIONAL — CSA S16 basis; SANS 10162-1 cl. 8.7 does not state an explicit cutoff in text examined — engineer sign-off required).
  - [x] **Tests (17):** exact U2 formula; θ=0.2→U2=1.25, θ=0.5→U2=2.0; cantilever derivation cross-check; portal integration — notional force, U2≥1, stiff not sensitive, slender sensitive, U2 increases with gravity, θ≥1 raises, stability index consistent. All passing.
- [x] **1.10 Member checks (SANS 10162-1)** — each its own module + test:
  - [x] Section classification (Class 1–3; **refuse Class 4** with clear message) — `checks/classification.py`; cl. 11.2 Table 4; flange b/t and web h/t limits with Cu effect. **8 tests.**
  - [x] Axial resistance — `checks/axial.py`; cl. 13.3.1 Cr=φ·A·fy·(1+λ²ⁿ)^(-1/n), n=1.34 hot-rolled; slenderness limit KL/r≤200 (raises SlendernessError). **5 tests.**
  - [x] Shear resistance — `checks/shear.py`; cl. 13.4.1.1 elastic analysis, Vr=φ·Av·0.66·fy (pure shear regime, kv=5.34 no stiffeners). **3 tests.**
  - [x] Moment resistance — `checks/bending.py`; cl. 13.5 laterally supported (class 1/2=Zpl, class 3=Ze); cl. 13.6 LTB (Mcr formula, case 1/2 dispatch). **9 tests.**
  - [x] Combined axial+bending interaction — `checks/interaction.py`; cl. 13.8.2 (class 1/2: Cu/Cr+0.85·U1·Mu/Mr≤1); U1 factor cl. 13.8.4. **9 tests.**
  - [x] SLS deflection — `checks/deflection.py`; Annex D Table D.1 vertical L/240 (inelastic covering) + horizontal H/400 sway (informative, flagged). **8 tests.**
  - [x] Steel material fy — `checks/material.py`; fy(S355JR, t≤16)=355 MPa etc. (PROVISIONAL — EN 10025-2, engineer sign-off required).
  - [x] Every `CheckResult` carries SANS clause reference + utilisation. **Tested.** Total new: **44 tests**.
- [x] **1.11 Auto-sizing** — `checks/autosize.py`: `autosize_member(library, fy_mpa, cu_kn, vu_kn, mu_knm, KL_mm, LTB_mm, ...)` → `AutosizeResult`. Iterates `by_increasing_mass()`, runs all SANS 10162-1 strength checks (classification, axial Cr, shear Vr, moment Mr/LTB, beam-column interaction); raises `NoSectionFoundError` if none pass. `AutosizeResult` carries designation, section_class_value, full check list + computed `passed`/`max_utilisation`. Added `section` convenience property for test access. **16 tests** — mini-library (TINY fails Mu, MEDIUM passes), lightest verification, real 64-section SAISC library smoke tests. All passing.
- [x] **1.12 Orchestrator** — `design.py`: `design(spec) → DesignResult`. Full pipeline: dead+imposed loads → ULS-1 iterative sizing (≤5 iterations converging rafter+column sections) → SLS-1 vertical deflection via FEA (PyNite apex DY, Annex D L/240) → sway sensitivity (cl. 8.7) → DesignResult with all checks + warnings. Post-sizing deflection upgrade loop advances rafter to next heavier section when deflection governs. `node_displacements()` method added to `PortalAnalysis` for FEA deflections. Out-of-scope: wind combos + K≠1 effective lengths (both in warnings). **13 tests** covering contract, correctness, determinism. All passing. Total: 214 tests.
- [x] **1.13 Determinism & reproducibility** — `test_determinism.py`: systematic multi-fixture proof. Three frame specs (15m standard, 20m wide, 12m restrained). Tests: (a) two calls identical `_json_dump()` per spec; (b) byte-identical `json.dumps(sort_keys=True)`; (c) `model_dump(mode="json")` round-trip lossless; (d) `rules_version` complete (all 5 standard keys present, non-empty, matches `rules_version.as_dict()`); (e) input-sensitivity — 4 parametric checks confirm different specs give different results. **26 tests.** All passing. Total: 240 tests.
- [x] **1.14 Check mode + material readout** *(competitive — PRD FR-24/25)*
  - [x] `check(spec, sections, cost_rate_zar_per_kg) → DesignResult` — engineer supplies section designations; kernel runs full SANS 10162-1 checks (classification, axial, shear, moment/LTB, interaction, sway, SLS deflection) without auto-sizing. `FrameUnstableError` from tiny sections is caught and reported as a failed CheckResult with diagnostic detail.
  - [x] `total_steel_mass_kg` (2 × rafter-half-len × raf_kg/m + 2 × eaves_h × col_kg/m) and `indicative_cost_zar` (mass × rate, default R20/kg PROVISIONAL) added to `DesignResult` with `Optional[float]` defaults (no existing tests broken). Both `design()` and `check()` populate them.
  - [x] Refactored `autosize.py`: extracted `run_member_checks()` (public, always returns checks even on failure) from `_check_one_section`; introduced `SectionIneligibleError` wrapper for Class4/slenderness/TF errors.
  - [x] `DEFAULT_COST_RATE_ZAR_PER_KG = 20.0` exported from `design.py` for test/audit use.
  - [x] **23 new tests** in `test_check_mode.py`: contract, correctness (passing/failing sections), check-vs-design pass-fail consistency, mass formula, cost formula, custom rate. **263 total passing.**

### Phase 1 extension — "the last mile" (connections, foundations, costing) · *scope addition 2026-06-11 (advisor-aligned)*
*Goal: complete the **single-bay portal frame** end-to-end so the engineer never leaves TorenOne to finish this structure. Scope-limited to this one frame — NOT a general connection/foundation designer (PRD §6.2). Same discipline as Phase 1: test-first, every value transcribed from the SANS PDFs in `standards/` or flagged **PROVISIONAL** pending co-founder sign-off; numbers come from kernel functions only. Re-uses the PyNite member/base forces already computed.*

- [x] **1.15 Connections — eaves (knee) + apex (SANS 10162-1)** — `connections/` (`bolts.py` + `moment_endplate.py`): bolted end-plate moment connection by the **flange-force-couple** method. Bolt resistances Tr/Vr/Br (cl. 13.12), combined tension+shear (elliptical), end-plate plastic bending (T-stub), flange fillet weld (cl. 13.13.2.2) — each a `CheckResult` with clause ref + utilisation. `design_moment_connection()` auto-selects from a bolt × plate × weld ladder (returns the strongest-tried with failing utils if unsatisfiable) → `ConnectionDesignResult` (`location`, `description`, checks, `passed`, `max_utilisation`). **Scope-limited to the eaves + apex joints.** ⚠️ **All coefficients PROVISIONAL** (SANS 10162-1 PDF absent from `standards/`; flange-couple is a simplified method without prying/yield-line modes 2-3) — flagged in every clause string + `SOURCES.md`, pending registered-engineer sign-off. **20 tests** (`kernel/tests/test_connections.py`): bolt resistances pinned by hand-calc (M20 8.8 Tr=117.6/Vr=94.08 kN, M24 10.9 Tr=211.8), demand/capacity logic (tension/shear/combined/axial), huge-moment fails, auto-design passes for the standard eaves/apex, escalation, unsatisfiable→failing strongest, determinism, clause/PROVISIONAL refs. *(Wired into `design()`/`check()` + report in 1.18/2.8.)* All passing (ruff + mypy clean). Full suite: **634 passed**.
- [x] **1.16 Column baseplates (SANS 10162-1)** — `foundations/baseplate.py`: `check_baseplate()` → 4 `CheckResult`s (concrete bearing via elastic N+M pressure block; plate cantilever bending; anchor tension from moment-couple + uplift; anchor shear) for **pinned and fixed** bases. `design_baseplate()` auto-sizes plate overhang × thickness × anchor from a ladder → `BaseplateDesignResult` (`base_fixity`/`description`/checks/`passed`/`max_utilisation`); returns strongest-tried with failing utils if unsatisfiable. Pinned (M≈0) reduces to bearing + plate + nominal anchors; fixed adds the moment. ⚠️ **All coefficients PROVISIONAL** (φc=0.65, 0.85·f'c bearing, AISC overhang factors, anchor-tension ignores axial relief = conservative; default f'c=25 MPa) — flagged in clauses + `SOURCES.md`, pending engineer sign-off. **14 tests** (`kernel/tests/test_baseplate.py`): bearing cap 13.8125 MPa, pinned bearing/shear hand-calcs, moment raises bearing+anchor tension, uplift→anchor tension, huge axial fails, auto-design pinned/fixed pass, escalation, unsatisfiable→strongest, determinism. All passing (ruff + mypy clean). Full suite: **648 passed**.
- [x] **1.17 Pad footings (SANS 10100-1)** — `foundations/pad_footing.py`: `check_pad_footing()` → 5 `CheckResult`s (soil bearing service+self-wt vs **engineer-supplied allowable pressure, never assumed**; max shear at column face; punching on the 1.5d perimeter; one-way shear; flexure→reinforcement) and `design_pad_footing()` auto-sizes plan (from bearing) → thickness → reinforcement ladders → `PadFootingDesignResult`, strongest-tried if unsatisfiable. ✅ **Re-implemented & VERIFIED against SANS 10100-1 (SABS 0100-1 Ed. 2.2)** now that the user supplied the PDF (in `standards/`): flexure stress block 0.67fcu/γc + lever arm z≤0.95d + K'=0.156 (cl. 4.3.3); **design concrete shear vc = (0.75/γm)(fcu/25)^⅓(100As/bd)^⅓(400/d)^¼, γm=1.4 (cl. 4.3.4 eq. 2)** — replaced the earlier nominal vc; v_max=min(0.75√fcu,4.75) (cl. 4.3.4.1); bending at column face + uniform pressure (cl. 4.10.2); punching at perimeter (cl. 4.10.4.4); min reinforcement 0.13 % (cl. 4.11.4). Allowable bearing is an engineer geotechnical input; material defaults (fcu=25/fy=450/cover=50 mm) typical, durability-cover + full detailing remain the engineer's check. *(The `FrameSpec` allowable-bearing input is added in 1.18 integration.)* **22 tests** (`kernel/tests/test_pad_footing.py`): SANS formula pins (vc eq.2, v_max, K'), bearing/face-shear hand-calcs, one-way uses vc, min-reinforcement floor, sensitivities, auto-design, determinism, **no PROVISIONAL flag remains on concrete checks**. All passing (ruff + mypy clean). Full suite: **670 passed**.
- [x] **1.18 Last-mile integration + costing/tonnage** — `DesignResult` extended with `connections: tuple[ConnectionDesignResult,…]` (eaves+apex), `baseplate: BaseplateDesignResult | None`, `footing: PadFootingDesignResult | None`, and computed `total_steel_tonnes` (= mass/1000). New `FrameSpec.foundation` (`FoundationInputs`: `allowable_bearing_kpa` **None by default — never assumed**; `concrete_fcu_mpa`=25). `_design_last_mile()` re-runs the ULS-1 (joint/base forces) + SLS-1 (service base axial for bearing) analyses on the **final** sections and designs eaves/apex connections + baseplate (always) + pad footing (only if allowable bearing supplied; else a clear warning). Every detail check is **appended to `DesignResult.checks`**, so `passed`/`governing_utilisation` span the whole frame unchanged; structured fields drive the report (2.8). Wired into **both** `design()` and `check()`. The report's code-checks table + governing util now render the detail checks (4 dp). **13 tests** (`kernel/tests/test_last_mile.py`): foundation inputs, two connections, baseplate, footing skipped/designed, standard-frame-all-pass, tonnage, detail-checks-appended, aggregate passed/governing, check-mode last mile, determinism. Standard 15 m frame: governing 0.986 (apex connection), footing 600×300 Y12@200. All passing (ruff + mypy clean). Full suite: **683 passed**.

**Acceptance (Phase 1 + extension): MET.** Full kernel runs **including connections, baseplates, footing, tonnage**; determinism holds; member + connection (PROVISIONAL, SANS 10162-1 not in worktree) + baseplate (PROVISIONAL) + footing (**VERIFIED** SANS 10100-1) checks carry clause refs; all PROVISIONAL items flagged in `SOURCES.md` + reports.

**Acceptance (Phase 1 + extension):** full kernel runs **including connections, baseplates, footing, tonnage**; ≥95% coverage; all checks carry clause refs; determinism test passes; every PROVISIONAL item is flagged in `SOURCES.md` + the report.

---

## Phase 2 — Report engine
*Goal: a clause-referenced, engineer-grade calc-package PDF from a `DesignResult`.*

- [x] **2.1 Template** — Jinja2 HTML/CSS report matching Design §B.7 (cover, assumptions, loads, combinations, results, checks, schedule, diagrams, limitations).
- [x] **2.2 PDF rendering** — WeasyPrint HTML→PDF; brand styling, monospaced numbers.
- [x] **2.3 Diagrams** — Matplotlib geometry + BMD/SFD.
- [x] **2.4 Status rendering** — pass/fail/near-limit via icon + label + colour (never colour alone). **Test.**
- [x] **2.5 Audit metadata** — rules version, input spec, timestamp embedded (PRD FR-20). **Test.**
- [x] **2.6 Golden-file test** — render a fixture `DesignResult`; assert key values + clause refs present in output.
- [x] **2.7 Competitive-advantage report features** *(PRD FR-25/26/27)*
  - [x] Line-by-line **audit / "show-your-working"** layout (assumptions → loads → combinations → checks → section). Section 8 in report with characteristic loads, ULS-1 factored UDLs, analysis forces (M/V/N at eaves/apex/base), per-member capacity tables (Cr, Vr, Mcr, Mr). **41 tests.**
  - [x] **Provenance label** — every number marked "computed by deterministic kernel, not AI".
  - [x] **Assumptions & limitations** block (assumed / out-of-scope / engineer-must-verify).
  - [x] **Steel mass + indicative cost** readout. **Test:** golden-file asserts each block is present.
- [x] **2.8 Last-mile report sections** — report now has dedicated sections: **6. Connection Design** (eaves + apex), **7. Column Baseplate**, **8. Pad Footing** (or a "not designed — no allowable bearing" note), each with the design forces + a clause-referenced checks table (pass/fail + utilisation via a reusable `checks_table` Jinja macro); **9. Steel Schedule, Tonnage & Cost** now shows **total steel tonnage** (FR-25). The main member code-checks table (§5) is filtered to member checks (renderer `_DETAIL_CHECK_PREFIXES`), so the detail checks render once in their own sections (no duplication); sections renumbered (Standards 10, Show-Your-Working 11, Audit 12). Template sections guard `None`/empty (hand-built results render safely). Golden-file test auto-bootstraps (no manual re-pin needed). **8 tests** (`kernel/tests/test_last_mile_report.py`): connection/baseplate/footing sections + checks present, SANS 10100-1 cited, footing-omitted note, tonnage rendered, cost present, no-duplication. Two brittle pre-existing report tests fixed (4-dp governing format; comma-grouped area). All passing (ruff + mypy clean; 3.11 PDF path green). Full suite: **691 passed**.

**Acceptance:** a `DesignResult` produces a correct, branded PDF — members **+ connections + baseplates + footing + tonnage cost** — with every number traceable to a clause. **Phase 2 complete (incl. last-mile).**

**Acceptance:** a `DesignResult` produces a correct, branded PDF with every number (members **+ connections + baseplates + footing + tonnage cost**) traceable to a clause.

---

## Phase 3 — AI orchestration layer
*Goal: text → typed `FrameSpec`, clarifying questions, and report narrative — with the LLM unable to compute numbers.*

- [x] **3.1 OpenAI client** — server-side `gpt-5.5` (`gpt-5.4-mini` fallback) via the `openai` SDK; key + model read from env (`OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_FALLBACK_MODEL`). `AIConfig.from_env()` validates presence; key is redacted in `repr`/`str`/`safe_dict()` and never serialised. Lazy SDK import so config is testable without the package. **23 tests** (`service/tests/test_ai_config.py`): key read from env, missing/blank-key raises, repr/str/safe_dict redact the key (no raw key anywhere), model defaults + overrides, base_url handling, frozen/immutable, server-side-only env-name guard (no `NEXT_PUBLIC_`), client factory wires key/base_url. All passing on Python 3.11 (ruff + mypy clean). Full suite: **447 passed**.
- [x] **3.2 Spec parsing** — OpenAI Structured Outputs (`responses.parse(..., text_format=FrameSpecExtraction)`); apply documented defaults; **never silently guess** (PRD FR-2). `service/src/torenone_ai/parsing.py`: the LLM fills an **all-nullable** `FrameSpecExtraction` (null = not stated); a deterministic `build_frame_spec()` then (a) **flags every missing required field** (span, eaves, pitch, bay spacing, #bays, roof dead load, wind speed, terrain) — never assumed; (b) applies documented defaults for optional fields, each recorded as an explicit `Assumption`; (c) validates into the real `FrameSpec` (range checks → `errors`). `ParseResult` carries `spec` / `missing` / `assumptions` / `errors` with `is_complete` + `needs_clarification`. OpenAI client injected → fully testable without network/key. System prompt hard-forbids guessing/calculation. **31 tests** (`service/tests/test_parsing.py`): complete→spec, all-missing flagged, single-missing, terrain-not-guessed, defaults-as-assumptions, stated-optional-not-assumed, validation errors (pitch>45, negative span, zero bays), fake-client wiring (model/text_format/text forwarded), null-output never fabricates, deterministic mapping. All passing (Python 3.11; ruff + mypy clean — service now in the mypy gate). Full suite: **478 passed**.
- [x] **3.3 Clarifying questions** — when input is ambiguous, return a question, not a guess. `service/src/torenone_ai/clarify.py`: `clarifying_questions(result)` turns a `ParseResult`'s `missing`/`errors` into typed `ClarifyingQuestion`s (field, question, kind `missing`/`invalid`, unit, enum options) — **deterministically, no LLM** (guarantees we ask about exactly the missing fields with correct units/options; terrain offers A/B/C/D, never guessed). `clarification_prompt(result)` renders a numbered user-facing message (or `None` if complete). **19 tests** (`service/tests/test_clarify.py`): complete→no questions, all-missing→one Q per required field in canonical order, single-missing, units (m/kPa/m·s⁻¹), terrain enum options, invalid-value correction questions, ask-never-guess (no spec but questions), prompt formatting, determinism. All passing (Python 3.11; ruff + mypy clean). Full suite: **497 passed**.
- [x] **3.4 Narrative generation** — prose only; **numbers injected from kernel**, not generated. `service/src/torenone_ai/narrative.py` uses **slot substitution**: `build_narrative_facts(result)` is the sole number source (all kernel-derived); the model writes prose with `{slot}` placeholders and **no digits**; `assert_prose_has_no_literal_numbers()` rejects any model output containing a digit (architectural guard); `render_narrative()` substitutes kernel facts and rejects invented slots. `deterministic_narrative()` builds the whole narrative from facts with no LLM (safe fallback + proof). **24 tests** (`service/tests/test_narrative.py`) incl. the headline guard: after removing every kernel fact value from the final text, **zero digits remain** (no number came from the model); a model-authored number (`"0.95"`) raises `NarrativeGuardError`; invented slots raise `NarrativeError`. All passing (Python 3.11; ruff + mypy clean). Full suite: **521 passed**.
- [x] **3.5 Guardrail test** — adversarial inputs (nonsense, out-of-scope, contradictory) handled gracefully (PRD FR-3, §9). Added an **out-of-scope guard**: `FrameSpecExtraction.in_scope`/`out_of_scope_reason` let the model flag non-portal-frame requests (multi-storey, concrete, bridge, truss, crane, multi-bay); `build_frame_spec()` then returns an `out_of_scope` `ParseResult` (refuse with reason) instead of asking portal questions. System prompt also nulls contradictory values and defines scope. **22 tests** (`service/tests/test_guardrails.py`): nonsense→ask (no crash), unparseable→graceful, out-of-scope→refuse-with-reason (no questions, even with stated dimensions), contradictory→nulled→asked, invalid/out-of-range→reported-not-clamped (parametrised), scope-guard doesn't block valid frames, and a robustness sweep asserting every adversarial category yields a graceful `ParseResult` (never an exception, never a fabricated spec). All passing (ruff + mypy clean). Full suite: **543 passed**.

**Acceptance:** parsing reliable on a sample set; LLM provably cannot emit engineering numbers (3.4 guard); out-of-scope handled (3.5). **Phase 3 complete.**

---

## Phase 4 — Engineering service (FastAPI) + auth
*Goal: the HTTP service that ties AI + kernel + report together, secured by Supabase JWT.*

- [x] **4.1 App skeleton** — FastAPI app, health check, structured logging. `service/src/torenone_service/`: `create_app()` factory (no import-time side effects beyond logging), `GET /health` liveness endpoint (`{status, service, version}`), and per-request structured-logging middleware (method/path/status/duration_ms). `logging_config.py` = stdout JSON formatter that promotes any `extra={}` to top-level fields (container-friendly; no secrets logged). `main.py` = ASGI entrypoint (`uvicorn torenone_service.main:app`). Deps: fastapi + uvicorn (service extra), httpx (dev, TestClient). **13 tests** (`service/tests/test_app.py`): health 200 + shape, GET-only (405), 404, OpenAPI served, JSON formatter (valid JSON / extra fields / exc_info / single-line), `configure_logging` idempotent single-handler, request middleware emits structured fields + valid JSON. All passing (Python 3.11; ruff + mypy clean — service now in the mypy gate). Full suite: **556 passed**.
- [x] **4.2 JWT verification** — verify Supabase JWT on every protected route; reject invalid. `service/src/torenone_service/auth.py`: `AuthConfig` (HS256 secret from `SUPABASE_JWT_SECRET`, audience `authenticated` from `SUPABASE_JWT_AUD`; secret redacted in repr/str); `decode_token()` verifies signature + expiry + audience + required `exp`/`sub` claims → `AuthenticatedUser(user_id, email, role)` or `AuthError`; `require_user` FastAPI dependency (HTTPBearer) → 401 on missing/invalid/expired, 503 if unconfigured. Protected `GET /me` route added; `/health` stays public. App stores `auth_config` on `app.state` (injectable for tests; loaded from env otherwise). **27 tests** (`service/tests/test_auth.py`): decode unit (valid/expired/bad-sig/wrong-aud/missing-sub/missing-exp/garbage/aud-disabled), `/me` valid→200, rejects (missing/non-Bearer/expired/bad-sig/wrong-aud/garbage→401, WWW-Authenticate header, no secret leak), unconfigured→503 (health still 200), `AuthConfig.from_env` + redaction. ruff `extend-immutable-calls` added for FastAPI `Depends` (B008). All passing (Python 3.11; ruff + mypy clean). Full suite: **583 passed**.
- [x] **4.3 `POST /parse`** — text → `FrameSpec` (+ clarifying questions). Protected route (`require_user`) that runs the Phase 3 parsing layer: `ParseRequest{description}` → `parse_description()` → `ParseResponse` with a `status` of `complete` (spec + assumptions), `needs_clarification` (questions + missing), `invalid` (errors + correction questions), or `out_of_scope` (scope_note). OpenAI client built once from `AIConfig` and held on `app.state.ai_runtime` (injectable in tests via `create_app(ai_runtime=...)`; 503 if no key). Sync route so the blocking OpenAI call stays off the event loop; auth resolved before AI runtime (401 precedes 503). Assumption values normalised to JSON scalars. `service/src/torenone_service/{ai_runtime,schemas}.py`. **11 tests** (`service/tests/test_parse_route.py`): complete→spec+assumptions, needs_clarification→8 questions (terrain options), invalid→errors, out_of_scope→scope_note (no questions), requires-auth (401), auth-before-AI, 503 unconfigured, empty/missing body→422. Fake AI client injected — no network/key. All passing (Python 3.11; ruff + mypy clean). Full suite: **594 passed**.
- [x] **4.4 `POST /design`** — confirmed `FrameSpec` → run kernel → build PDF → store → return result. Protected route: `DesignRequest{spec, mode, sections?, cost_rate?, project_id?}` → `run_design()` (kernel `design()`/`check()`) → build PDF (`ReportBuilder`) → persist (`ReportStore`) → `DesignResponse{result, report}`. Report building + storage are **injectable interfaces** — default `WeasyPrintReportBuilder` (kernel report engine, lazy import) + `InMemoryReportStore`; **Supabase-backed store wired in Phase 5**. Input-driven kernel failures (`NoSectionFoundError`/`FrameUnstableError`/bad sections) → 422 with safe message; a *failed check* (passed=False) is a normal 200. `DesignRequest` strips computed geometry fields so a spec round-tripped from `/parse` re-validates under `extra="forbid"`. `service/src/torenone_service/{design_service,reports}.py`.
  - [x] Support **Check mode** (`mode=check` with supplied sections) → runs `check()` instead of `design()` (PRD FR-24).
  - **13 tests** (`service/tests/test_design_route.py`): design happy path (result+report, matches kernel, builder/store called, custom cost rate), check mode (valid sections, missing→422, unknown designation→422), guards (auth 401, invalid/missing spec→422, bad mode→422), plus a WeasyPrint-gated end-to-end test producing a real `%PDF` (skips in CI). Kernel runs for real (CI-safe); PDF/store are injected fakes. All passing (Python 3.11; ruff + mypy clean). Full suite: **606 passed** (CI: 597 + 9 skipped).
- [x] **4.5 Error handling** — typed errors, safe messages, no secret leakage. `service/src/torenone_service/errors.py`: a catch-all `Exception` handler logs full detail server-side (structured, with traceback) but returns a generic `{"detail":"internal server error"}` 500 — never a stack trace or internal text. Routes map known failures to typed statuses: upstream `OpenAIError` in `/parse` → **502** (safe message), report build/store failure in `/design` → **502**, `DesignError` → **422**, auth → 401/503. **8 tests** (`service/tests/test_errors.py`): OpenAIError→502, unexpected→generic 500, report failure→502, `DesignError`→422, and **no-secret-leak** assertions across 401/500/502 paths (JWT secret + API key never appear in any error body). All passing (Python 3.11; ruff + mypy clean). Full suite: **614 passed**.
- [x] **4.6 Containerise & deploy** — two-stage `Dockerfile` (repo root): **builder** installs `.[service,pdf]` into a venv (gets `torenone_kernel` + all runtime deps **including WeasyPrint**); **runtime** = `python:3.11-slim` + WeasyPrint native libs (`libpango-1.0-0`, `libpangoft2-1.0-0`, `fonts-dejavu-core`, `shared-mime-info`), copies the venv + `service/` and runs `uvicorn torenone_service.main:app` on :8000 as non-root `appuser` with a `/health` `HEALTHCHECK`. `torenone_service`/`torenone_ai` aren't pip-packaged, so they're exposed via `PYTHONPATH=/app/service/src`. `.dockerignore` keeps the build context small + secret-free; `fly.toml` (Fly.io, region `jnb`, internal_port 8000, `/health` check, 1 GB RAM); `docs/DEPLOY.md` documents build/run/Fly-deploy + env wiring (app boots for `/health` without secrets; protected routes 503 until set). **Verification:** new CI `docker` job builds the image, runs the container, and asserts `GET /health` → 200 with the expected JSON; `service/tests/test_deploy.py` (**9 tests**) locks the deploy contract (py3.11 base, `[service,pdf]` extra, Pango native lib, `service/src` on PYTHONPATH, uvicorn ASGI entrypoint binding 0.0.0.0, non-root USER, `/health` HEALTHCHECK, `.dockerignore` excludes `.git`/`web`/`standards`/`.env`, `fly.toml` internal_port 8000 + `/health`). All passing (ruff + mypy clean). Full suite: **700 passed**. *(Deploy to a live Fly app needs the co-founder's Fly account + secrets — infra/credentials step, not code.)*
- [x] **Check mode shipped** *(advisor improvement #5)* — already live as `POST /design` with `mode=check` (Task 4.4); kernel `check()` from Task 1.14. *Optional polish: add a `POST /check` alias for clarity/marketing — non-blocking.* The `/design` response already carries the new last-mile fields once 1.18 lands (additive — no route change).

**Acceptance:** authenticated end-to-end request runs parse + design and stores a report; unauthenticated rejected. **Phase 4 complete (4.1–4.6).** *(Live Fly deploy is a one-time credentials/infra step for the co-founder — the image + config + CI build-smoke are all in place.)*

---

## Phase 5 — Supabase backend (data + RLS)
*Goal: multi-tenant data model with strict isolation.*

- [x] **5.1 Project & schema** — Supabase project scaffolded (`supabase/config.toml`, `project_id = "torenone"`) + first migration `supabase/migrations/20260612120000_initial_schema.sql` creating the five Design §A.7 tables: **`firms`** (tenant root), **`profiles`** (`id` = `auth.users.id`, FK→`firms`), **`projects`** (FK→`firms`/`profiles`), **`runs`** (`frame_spec` jsonb, `mode`, `status`, `rules_version` jsonb, `passed`, `governing_utilisation`, FK→`projects`/`firms`/`profiles`), **`reports`** (`storage_path`, FK→`runs`/`firms`). **Design choice:** `firm_id` is denormalised onto `runs`+`reports` so the Task 5.4 RLS policies are simple index-backed equality checks (no recursive joins); every FK column is indexed. RLS-enable (5.4), the signup profile/firm trigger (5.2), the Storage bucket (5.3) and seed data (5.5) are their own migrations. **Test-first (no live DB in this env — no Docker/psql):** `supabase/tests/test_schema.py` (**19 tests**) parses every migration with `sqlglot` (Postgres dialect) and asserts the contract — valid Postgres, exactly the 5 tables, required columns per §A.7, uuid `id` PKs, the multi-tenant backbone (`firm_id` NOT NULL on every non-root table), and the FK tenant graph incl. `profiles.id`→`auth.users`. `sqlglot` pinned in `[dev]`; `supabase/tests` added to pytest `testpaths`. All passing (ruff + mypy clean). Full suite: **719 passed**. *(Creating the actual hosted Supabase project + `supabase link`/`db push` is a one-time credentials step for the co-founder — the migration + contract test are the code deliverable.)*
- [x] **5.2 Auth** — email auth; `profiles` row created on sign-up, linked to a `firm`. Migration `supabase/migrations/20260612120100_auth_profile_trigger.sql`: a `handle_new_user()` trigger function on `auth.users` (AFTER INSERT, per row) that bootstraps the tenant — **invited user** (sign-up metadata carries `firm_id`) joins that firm as `engineer`; **first user of a new firm** (no `firm_id`) gets a fresh `firms` row (name from `firm_name` metadata, else derived from email) and role `owner`. Always inserts the `profiles` row with `id = new.id` (so `profiles.id == auth.users.id`). **Hardened:** `SECURITY DEFINER` (the sign-up user has no profile yet, so without definer rights the Task 5.4 RLS policies would block the insert) + pinned `search_path = ''` with every object schema-qualified (no definer-hijack). **Test-first:** `supabase/tests/test_auth_trigger.py` (**5 tests**) asserts the contract on the parsed/normalised SQL — function exists (sqlglot confirms it's a `CREATE FUNCTION`), `SECURITY DEFINER` + empty `search_path`, profile keyed to `new.id`, firm linked, and the trigger fires `AFTER INSERT ON auth.users ... EXECUTE FUNCTION public.handle_new_user`. All passing (ruff + mypy clean). Full suite: **724 passed**. *(Enabling the actual email-auth provider is a Supabase dashboard/config toggle for the co-founder; the DB-side bootstrap is the code deliverable.)*
- [x] **5.3 Storage** — bucket for report PDFs, access scoped per firm. Migration `supabase/migrations/20260612120200_storage_reports_bucket.sql`: a single **private** `reports` bucket (`public = false` → no public URLs) holding the calc-package PDFs, stored under a `<firm_id>/…` path prefix. Adds the shared helper **`public.current_firm_id()`** (`SECURITY DEFINER` + `set search_path = ''`, STABLE) that resolves the caller's firm from `profiles` without recursing through that table's own RLS — **reused by the Task 5.4 table policies**. Three `storage.objects` RLS policies (`select`/`insert`/`delete`, role `authenticated`) each require `bucket_id = 'reports'` AND `(storage.foldername(name))[1] = current_firm_id()`, so a firm can only touch objects under its own folder (insert uses `WITH CHECK`). **Test-first:** `supabase/tests/test_storage.py` (**8 tests**) — private bucket created, hardened `current_firm_id()` helper, policies target `storage.objects` for `authenticated`, the per-firm folder predicate + `bucket_id` scope, read/write/delete all scoped, insert uses `WITH CHECK`. All passing (ruff + mypy clean). Full suite: **732 passed**. *(Creating the bucket in the hosted project happens when `db push` runs against it — the migration is the deliverable.)*
- [~] **5.4 Row-Level Security** — policies filtering every table by the user's `firm_id`.
  - [~] **Test:** user A cannot read/write user B's firm data (automated RLS test).
- [ ] **5.5 Seed/dev data** — a dev firm + user for local testing.

**Acceptance:** auth works; RLS proven to isolate firms; PDFs store/retrieve per firm.

---

## Phase 6 — Frontend (design system + screens)
*Goal: the user-facing app implementing the Supabase-style steel-blue design system and the six MVP screens.*

- [ ] **6.1 Design-system shell** — themed shadcn/ui primitives (Button, Input, Card, Table, Dialog, Tabs, Toast, Form) using Phase 0 tokens. **Test:** component/visual checks; contrast assertions.
- [ ] **6.2 Auth screens** — Supabase UI Library sign-in/sign-up, themed. **Test:** auth flow E2E (Phase 7).
- [ ] **6.3 Projects** — list + create, per firm. **Test.**
- [ ] **6.4 Describe screen** — text input + examples; calls `/parse`. **Test.**
- [ ] **6.5 Spec-review / confirm screen (trust gate)** — the parsed `FrameSpec` as **editable fields** the engineer can override (geometry, **wind terrain, roof pitch, loads**, optional sections, allowable bearing pressure) + geometry sketch; clarifying questions surfaced inline; "Run design" CTA calls `/design`. Cannot proceed without explicit confirm — the AI prepares, the engineer is the authoritative pilot (PRD FR-4/FR-32). **Test.**
- [ ] **6.6 Results screen** — utilisation table (icon+label+colour status) for **members + connections + baseplates + footing**, member sizes, deflections, "Download calc package (PDF)". **Test.**
  - [ ] **Interactive visual feedback** (FR-32) — 2D stick-model of the PyNite frame + interactive **BMD/SFD** (lightweight SVG/canvas), shown on the web *before* PDF export, not only buried in the PDF.
  - [ ] **Design / Check mode** toggle — Check mode lets the user enter their own sections (PRD FR-24).
  - [ ] **Audit / "show-your-working" panel** + deterministic-kernel **provenance badge** (FR-26).
  - [ ] **Steel tonnage + cost** readout with **editable cost-per-ton** input (FR-25/FR-31); **assumptions & limitations** block (FR-27).
- [ ] **6.7 Run history** — past runs + stored PDFs per project. **Test.**
- [ ] **6.8 States** — loading/empty/error states for every async view. **Test.**

**Acceptance:** all six screens implemented to the design system; component tests pass; accessible.

---

## Phase 7 — Integration & end-to-end
*Goal: the whole happy path works in the deployed app.*

- [ ] **7.1 Wire frontend ↔ FastAPI ↔ Supabase ↔ kernel** end-to-end.
- [ ] **7.2 E2E happy path (Playwright)** — sign in → create project → describe → confirm → design → PDF stored → visible in history. **Test.**
- [ ] **7.3 E2E multi-tenant** — second firm cannot see first firm's data. **Test.**
- [ ] **7.4 E2E error paths** — invalid input, out-of-scope request, auth failure handled gracefully. **Test.**
- [ ] **7.5 Performance check** — design run < 60s on the demo case (NFR-5). **Test.**

**Acceptance:** green E2E suite covering happy path, isolation, errors, performance.

---

## Phase 8 — Validation gate & hardening
*Goal: prove correctness against reality and lock quality before any customer touches it.*

- [ ] **8.1 Benchmark project** — co-founder selects the most typical past portal frame; capture its inputs + original results.
- [ ] **8.2 Validation test** — run benchmark through TorenOne; assert member sizes + utilisations match the original within agreed tolerances (PRD NFR-1). **THE gate — must pass.**
- [ ] **8.3 Worked-example regression suite** — published worked examples as permanent regression tests across loads/analysis/checks.
- [ ] **8.4 Coverage & review** — kernel ≥95%; co-founder reviews every formula + clause mapping.
- [ ] **8.5 Security pass** — secrets server-side only; RLS verified; dependency audit.
- [ ] **8.6 Honest-limitations audit** — every out-of-scope/approximation is stated in the report, never hidden.

**Acceptance:** validation gate passed; regression suite green; co-founder sign-off on correctness.

---

## Phase 9 — Pilot & YC readiness
*Goal: real usage + the evidence the application needs.*

- [ ] **9.1 Polish** — final design QA against Design §B; report PDF looks stamp-worthy.
- [ ] **9.2 Onboard 3–5 Cape Town firms** — run real projects through TorenOne.
- [ ] **9.3 Capture pilot evidence** — time saved (1–3 days → minutes); ≥1 paying firm; testimonials/logos.
- [ ] **9.4 Update [YC application](../TorenOne-YC-Application.md)** — progress, traction, demo, validation-gate proof.
- [ ] **9.5 Founder demo** — record the "describe → stamped-ready calc package in minutes, validated against a real job" demo.

**Acceptance (MVP DONE — per PRD §10):** all FRs tested & passing; validation gate passed; full happy path live; multi-tenant verified; CI green, kernel ≥95%; design system implemented; ≥1 real firm has run a live project.

---

## Backlog — explicitly OUT of MVP (do not build now)
Logged so we stay disciplined. Revisit only after MVP ships.
- Architect's-plan / PDF parsing (v2 flagship) · **general/universal** connection designer (we build *only* the single-bay portal's eaves/apex/baseplate — §1.15–1.16) · **general foundation/geotechnical** design beyond the simple pad footing (§1.17) · 3D / BIM / Revit / drawings · Eurocode / ACI / AISC · other structure types (RC frames, multi-storey, multi-bay, cranes, trusses) · Class 4 sections · team collaboration · billing/subscriptions · mobile app · cost optimisation.

> **What NOT to do right now (advisor guardrails):** no multi-storey buildings · no concrete frames (the only concrete element is the simple pad footing) · no AISC/Eurocode yet · no generic FEA node-drawing UI. Stay on the single-bay SANS steel portal-frame wedge; *complete it* before widening.
