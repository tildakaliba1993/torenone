# TorenOne — Session Handover (read this FIRST)

> A new session should read this top-to-bottom, then skim the living docs it points to. It tells you
> what TorenOne is, the rules you must follow, exactly where we are, and **precisely what to do next (Task 1.8)**.
>
> **Last updated:** 2026-06-10 · **HEAD commit:** `f4a1bf6` · **Tests:** 110 passing · **Repo:** github.com/tildakaliba1993/torenone (`main`)

---

## 1. What TorenOne is
The AI structural engineer. An engineer describes a **steel portal frame**; TorenOne produces a
**code-checked, review-ready SANS calculation package** in minutes. MVP wedge: **steel portal frames to
South African standards (SANS)**, for Cape Town firms (the two founders are SA structural/civil
engineers). Competitors are all US-code-first and horizontal — we win on **SANS + steel-portal depth +
a stampable, clause-referenced calc package + provable correctness**.

## 2. NON-NEGOTIABLE PRINCIPLES (do not violate)
1. **Accuracy is absolute — human lives are at stake.** Never produce a wrong/fabricated engineering number.
2. **AI orchestrates; the kernel computes.** All numbers come from the deterministic, tested kernel. The LLM never does engineering arithmetic.
3. **Never fabricate or guess a code value.** Transcribe from the official standard (in `standards/`), **cite the clause/table**, and **validate against the standard's own tables** where one exists. If a value isn't available, gate it (raise) — don't invent it.
4. **Engineer-in-the-loop.** We never auto-stamp; a Pr.Eng reviews & stamps. All transcribed values await **final engineer sign-off** (tracked in REFERENCES §5–6 / SOURCES).
5. **Test-driven.** Write the test first (with the expected value from the standard's table or a hand calc). A task is done only when its tests pass.
6. **Discipline.** Build only the MVP scope. Out-of-scope items raise a clear error and are logged.
7. **Read the source exactly.** PDFs extract via text or, for tricky tables, **pdfplumber** (structure-aware). Never transcribe a life-safety table by eyeballing a rendered image.

## 3. The living docs (single sources of truth — keep them updated in real time)
- `docs/PRD.md` — product requirements (the MVP "bible"); FR-1…FR-27.
- `docs/TASKS.md` — phased plan + **live progress checkboxes** (update as you go).
- `docs/DESIGN-ARCHITECTURE.md` — architecture + UI design system (steel-blue, dark, shadcn/Supabase UI).
- `docs/SOURCES.md` — **living source register**: every value → its origin + status (VERIFIED/PROVISIONAL/PENDING). Add a row whenever a new value enters.
- `docs/REFERENCES-AND-VALIDATION.md` — code basis, benchmark, tolerances, provisional values, engineer sign-off list.
- `docs/COMPETITIVE-LANDSCAPE.md` — competitors (Genia is the serious one) + our differentiation.
- `docs/PROJECT-SETUP.md` — Supabase/Vercel/GitHub isolation.
- `standards/README.md` — manifest of the source PDFs + their quality caveats.

## 4. Where we are — Phase 1 (the kernel) progress
**Done & green (110 tests):**
- **1.1** domain models — `FrameSpec` (frozen, validated) + result contracts (`LoadCombination`, `AnalysisResult`, `MemberForces`, `CheckResult`, `DesignResult`, `DeadLoadResult`, `ImposedLoadResult`, …).
- **1.2** SAISC section database — **64 real sections** (IPE-AA/IPE 100–200, UB, UC) parsed from the official free SAISC PDF; cross-checked vs known values. (`sections/`)
- **1.3** rules versioning — `rules_version.py` (editions pinned; SANS 10160-3 = 2019, 10162-1 = 2011, 10160-1 = 2009 DRAFT).
- **1.4** dead loads — self-weight + area loads × tributary. (`loads/dead.py`)
- **1.5** imposed roof load — 0.4 kN/m² inaccessible (SANS 10160-2 Table 5). (`loads/imposed.py`)
- **1.6** wind (SANS 10160-3:2019) — **fully done**, validated vs the standard's tables:
  - `loads/wind.py` — terrain Table 1, power-law `cr(z)` (validated vs Table 3), air density Table 4, qp.
  - `loads/wind_pressure.py` — walls (Table 6), duopitch roof (Table 10, zones H/I, uplift+downforce), internal pressure (cl. 8.3.9).
  - `loads/wind_loads.py` — `wind_loads(spec)` → `WindLoadResult` (member UDLs per case; explicit uplift case).
- **1.7** load combinations — `loads/combinations.py`, ULS/SLS per SANS 10160-1. ⚠️ **PROVISIONAL (draft standard)**.

**Remaining Phase 1:** **1.8 analysis** ← NEXT · 1.9 second-order · 1.10 member checks (SANS 10162-1) · 1.11 auto-size · 1.12 orchestrator · 1.13 determinism · 1.14 check-mode + material readout.

## 5. How to work in this repo
- **Run tests:** `PYTHONPATH="kernel/src:tools" python3 -m pytest -q` (local Python is **3.9**; project targets **3.11** — avoid `X | None` runtime in pydantic models; use `Optional[...]` and `from __future__ import annotations`. Builtin generics `list[...]`/`dict[...]` are fine on 3.9.)
- **Kernel layout:** pure package under `kernel/src/torenone_kernel/` (`models/`, `sections/`, `loads/`). Deterministic, no IO/network.
- **Commit style:** small, per-task; message ends with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Commit + push to `origin main` after each green task (user is fine with this cadence). Then update `docs/TASKS.md` + `docs/SOURCES.md`.
- **gh accounts:** the active gh account is `tildakaliba1993` (the repo owner). `git push` works.
- **Standards PDFs:** in `standards/` (**git-ignored** — copyright + size). They're **AES-encrypted**; read with:
  ```python
  from pypdf import PdfReader
  r = PdfReader("standards/SANS 10162-1.pdf")  # decrypts with empty password automatically (cryptography installed)
  print(r.pages[i].extract_text())
  # For tricky tables use pdfplumber:
  import pdfplumber; pdfplumber.open("standards/...pdf", password="").pages[i].extract_tables()
  ```
  `pypdf`, `pdfplumber`, `cryptography`, `pytest`, `pydantic` are pip-installed (`--user`). Disk was tight earlier (cleared npm cache); fine now.
- **Standards we have (in `standards/`):** SANS 10160-1 (⚠️ DRAFT), 10160-2, 10160-3:2019 (official), 10162-1:2011 (official), "Design of Structural Steelwork to SANS 10162" (575pp, **likely scanned/no text layer** — needs OCR if used).

## 6. Open / provisional items (do NOT lose these)
- **SANS 10160-1 is a DRAFT** → load-combination factors (1.7) are PROVISIONAL; confirm vs the final standard.
- Imposed 0.4 kN/m², section data, all transcribed values → **engineer sign-off pending** (REFERENCES §5–6).
- **R5 (cofounder produces):** Reference Frame v1 wind inputs + steel grade + **golden outputs** (Prokon/SAISC spreadsheet) for the Phase-8 validation gate; spot-check the 64 sections.
- Wind scope deferreds (documented): gable-edge zones F/G, ridge zone J, near-flat (<5°) roofs, accessible roofs.

---

## 7. ⭐ NEXT TASK — 1.8: Plane-frame analysis engine

**Character:** This is **code-agnostic statics** (no SANS values). So validate against **first-principles exact solutions**, not a standard's table. This is the computational heart of the kernel.

### What to build
1. **Add PyNite** (`PyNiteFEA` on PyPI) to `pyproject.toml` deps; `pip install --user PyNiteFEA`. **Verify its actual API** against the installed version (it drifts from training data — read the installed package / its examples; recent PyNite uses `from Pynite import FEModel3D`, `add_node`, `add_material`, `add_section`, `add_member`, `add_member_dist_load`, `analyze`, then read member forces / node reactions). Confirm before coding.
2. **New module** `kernel/src/torenone_kernel/analysis/plane_frame.py`:
   - A thin wrapper to define a 2D plane frame (nodes in the X–Y plane, members with section `A` and `Iz`, supports, member UDLs / point loads), solve a **first-order linear elastic** analysis, and extract **member forces (N, V, M)** at salient points + reactions.
   - Constrain out-of-plane DOFs so it behaves as 2D.
   - Steel **E = 200 000 MPa (N/mm²)** — a physical constant; confirm against SANS 10162-1 when you reach 1.10. Shear modulus G ≈ 77 000 MPa.
3. **Portal model-builder** from `FrameSpec` + `SectionProperties` (rafter + column): build nodes (base, eaves, apex) and members (columns + rafters), **pinned bases** (MVP). Use `geometry.apex_height_m`, `span_m`, etc. (units: the kernel uses mm for section props; keep a consistent unit system — decide N, mm or kN, m and document it).
4. **Map to the existing result contract:** return `AnalysisResult(combination=..., forces=[MemberForces(location, axial_kn, shear_kn, moment_knm), ...])` (already defined in `models/results.py`). Provide force **envelopes** (max/min M, V, N at column base, eaves, apex).

### How to validate (test-first — this is the trust anchor)
Validate the solver wiring against **analytically exact** cases first (these are EI-independent for forces):
- **Simply-supported beam, UDL w, span L:** mid-span `M = wL²/8`, reactions `wL/2`, max shear `wL/2`.
- **Cantilever, point load P at tip, length L:** fixed-end `M = PL`, shear `P`.
- **Propped cantilever / fixed beam** (optional) for indeterminate-solver confidence.
Then a **pinned-base portal** check: a pinned-base portal is **statically indeterminate (1°)** — validate it against a **worked example with known answers** (hand calc via stiffness/虚功, or a textbook portal example; the "Design of Structural Steelwork to SANS 10162" guide may have one if OCR'd, else a standard structural-analysis text). Assert member moments/reactions within ~1–2% (see tolerances in REFERENCES §4).

### Scope guards / notes
- MVP: single-bay symmetric **pinned-base** duopitch portal, **first-order** elastic. (Second-order/sway is **1.9**, next.)
- Don't over-couple to loads/combinations here — 1.8 takes geometry + sections + applied loads and returns forces. The **orchestrator (1.12)** will: compute loads (1.4–1.6) → factor by combinations (1.7) → run analysis per combination → envelopes → checks (1.10) → auto-size (1.11).
- Commit when green; update `docs/TASKS.md` (1.8 checkboxes) and `docs/SOURCES.md` (add PyNite as VERIFIED tooling; note E/G constants).

### Definition of done for 1.8
PyNite wrapper + portal builder + `AnalysisResult` output; **solver validated against the exact determinate cases AND a known portal result**; tests green; committed/pushed; TASKS/SOURCES updated.

---

## 8. After 1.8 (rough order)
**1.9** second-order/sway amplification · **1.10** member checks (SANS 10162-1:2011 — in `standards/`; classification, axial Cr, moment Mr, combined interaction, LTB, deflection limits) · **1.11** auto-size (lightest passing section via `SectionLibrary.by_increasing_mass()`) · **1.12** orchestrator (`design()` + `check()` for Check mode) · **1.13** determinism · **1.14** material mass + cost readout. Then Phase 2 (report), 3 (AI), 4 (FastAPI), 5 (Supabase), 6 (Next.js UI), 7 (E2E), 8 (validation gate), 9 (pilot/YC).
