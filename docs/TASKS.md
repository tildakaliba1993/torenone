# TorenOne — Tasks & Implementation Plan

> The single source of truth for **what we are building and how far along we are.** Update in real time: when a task is done and its tests pass, mark it `[x]`. Governed by the [PRD](./PRD.md) and [Design & Architecture](./DESIGN-ARCHITECTURE.md).
>
> **Status:** v1.0 · **Last updated:** 2026-06-11 (1.14 done)

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
| 2 | Report engine | `[ ]` |
| 3 | AI orchestration layer | `[ ]` |
| 4 | Engineering service (FastAPI) + auth | `[ ]` |
| 5 | Supabase backend (data + RLS) | `[ ]` |
| 6 | Frontend (design system + screens) | `[ ]` |
| 7 | Integration & end-to-end | `[ ]` |
| 8 | Validation gate & hardening | `[ ]` |
| 9 | Pilot & YC readiness | `[ ]` |

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

**Acceptance:** full kernel runs; ≥95% coverage; all checks carry clause refs; determinism test passes.

---

## Phase 2 — Report engine
*Goal: a clause-referenced, engineer-grade calc-package PDF from a `DesignResult`.*

- [ ] **2.1 Template** — Jinja2 HTML/CSS report matching Design §B.7 (cover, assumptions, loads, combinations, results, checks, schedule, diagrams, limitations).
- [ ] **2.2 PDF rendering** — WeasyPrint HTML→PDF; brand styling, monospaced numbers.
- [ ] **2.3 Diagrams** — Matplotlib geometry + BMD/SFD.
- [ ] **2.4 Status rendering** — pass/fail/near-limit via icon + label + colour (never colour alone). **Test.**
- [ ] **2.5 Audit metadata** — rules version, input spec, timestamp embedded (PRD FR-20). **Test.**
- [ ] **2.6 Golden-file test** — render a fixture `DesignResult`; assert key values + clause refs present in output.
- [ ] **2.7 Competitive-advantage report features** *(PRD FR-25/26/27)*
  - [ ] Line-by-line **audit / "show-your-working"** layout (assumptions → loads → combinations → checks → section).
  - [ ] **Provenance label** — every number marked "computed by deterministic kernel, not AI".
  - [ ] **Assumptions & limitations** block (assumed / out-of-scope / engineer-must-verify).
  - [ ] **Steel mass + indicative cost** readout. **Test:** golden-file asserts each block is present.

**Acceptance:** a `DesignResult` produces a correct, branded PDF with every number traceable to a clause.

---

## Phase 3 — AI orchestration layer
*Goal: text → typed `FrameSpec`, clarifying questions, and report narrative — with the LLM unable to compute numbers.*

- [ ] **3.1 Anthropic client** — server-side `claude-opus-4-8`; key from env. **Test:** key never exposed client-side (config test).
- [ ] **3.2 Spec parsing** — structured outputs (`messages.parse()` against `FrameSpec`); apply documented defaults; **never silently guess** (PRD FR-2). **Test:** sample descriptions → expected specs; missing-field cases flagged.
- [ ] **3.3 Clarifying questions** — when input is ambiguous, return a question, not a guess. **Test.**
- [ ] **3.4 Narrative generation** — prose only; **numbers injected from kernel**, not generated. **Test:** assert no engineering numbers originate from the model output path (architectural guard).
- [ ] **3.5 Guardrail test** — adversarial inputs (nonsense, out-of-scope, contradictory) handled gracefully (PRD FR-3, §9).

**Acceptance:** parsing reliable on a sample set; LLM provably cannot emit engineering numbers; out-of-scope handled.

---

## Phase 4 — Engineering service (FastAPI) + auth
*Goal: the HTTP service that ties AI + kernel + report together, secured by Supabase JWT.*

- [ ] **4.1 App skeleton** — FastAPI app, health check, structured logging.
- [ ] **4.2 JWT verification** — verify Supabase JWT on every protected route; reject invalid. **Test:** valid passes, invalid/expired rejected.
- [ ] **4.3 `POST /parse`** — text → `FrameSpec` (+ clarifying questions). **Test.**
- [ ] **4.4 `POST /design`** — confirmed `FrameSpec` → run kernel → build PDF → upload to Supabase Storage → persist `run` + `report` → return result. **Test (mocked kernel/storage).**
  - [ ] Support **Check mode** (`mode=check` with supplied sections) → runs `check()` instead of `design()` (PRD FR-24). **Test.**
- [ ] **4.5 Error handling** — typed errors, safe messages, no secret leakage. **Test.**
- [ ] **4.6 Containerise & deploy** — Dockerfile; deploy to Fly.io/Render/Railway; env wired.

**Acceptance:** authenticated end-to-end request runs parse + design and stores a report; unauthenticated rejected.

---

## Phase 5 — Supabase backend (data + RLS)
*Goal: multi-tenant data model with strict isolation.*

- [ ] **5.1 Project & schema** — create Supabase project; tables `firms`, `profiles`, `projects`, `runs`, `reports` (Design §A.7) via migrations.
- [ ] **5.2 Auth** — email auth; `profiles` row created on sign-up, linked to a `firm`.
- [ ] **5.3 Storage** — bucket for report PDFs, access scoped per firm.
- [ ] **5.4 Row-Level Security** — policies filtering every table by the user's `firm_id`.
  - [ ] **Test:** user A cannot read/write user B's firm data (automated RLS test).
- [ ] **5.5 Seed/dev data** — a dev firm + user for local testing.

**Acceptance:** auth works; RLS proven to isolate firms; PDFs store/retrieve per firm.

---

## Phase 6 — Frontend (design system + screens)
*Goal: the user-facing app implementing the Supabase-style steel-blue design system and the six MVP screens.*

- [ ] **6.1 Design-system shell** — themed shadcn/ui primitives (Button, Input, Card, Table, Dialog, Tabs, Toast, Form) using Phase 0 tokens. **Test:** component/visual checks; contrast assertions.
- [ ] **6.2 Auth screens** — Supabase UI Library sign-in/sign-up, themed. **Test:** auth flow E2E (Phase 7).
- [ ] **6.3 Projects** — list + create, per firm. **Test.**
- [ ] **6.4 Describe screen** — text input + examples; calls `/parse`. **Test.**
- [ ] **6.5 Confirm screen (trust gate)** — editable structured `FrameSpec` form + geometry sketch; "Run design" CTA calls `/design`. Cannot proceed without explicit confirm (PRD FR-4). **Test.**
- [ ] **6.6 Results screen** — utilisation table (icon+label+colour status), member sizes, deflections, diagrams, "Download calc package (PDF)". **Test.**
  - [ ] **Design / Check mode** toggle — Check mode lets the user enter their own sections (PRD FR-24).
  - [ ] **Audit / "show-your-working" panel** + deterministic-kernel **provenance badge** (FR-26).
  - [ ] **Steel mass + indicative cost** readout (FR-25); **assumptions & limitations** block (FR-27).
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
- Architect's-plan / PDF parsing (v2 flagship) · connection & base-plate design · 3D / BIM / Revit / drawings · Eurocode / ACI / AISC · other structure types (RC, multi-bay, cranes, trusses, foundations) · Class 4 sections · team collaboration · billing/subscriptions · mobile app · cost optimisation.
