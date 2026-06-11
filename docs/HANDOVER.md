# TorenOne — Session Handover

**Date:** 2026-06-12
**Branch:** `claude/serene-bhabha-853ff0` → pushed to `origin/main`
**Latest commit:** `bd5f92a` — Task 2.8 (report sections for connections/baseplate/footing + tonnage)
**Test status:** **691 passed** locally (Python 3.11); **CI green** (682 passed + 9 skipped — the 9 are WeasyPrint PDF tests that skip without pango/cairo). ruff + mypy clean.
**Working tree:** clean, everything committed + pushed.

> ## ⚠️ READ FIRST — Task 4.5 is ALREADY DONE
> The previous user instruction was "implement 4.5 (error handling) in the new session." **4.5 was actually completed earlier this same session** (commit `ff8bae6`): `service/src/torenone_service/errors.py` + `install_exception_handlers` wired into `app.py`, `service/tests/test_errors.py` (8 tests, all passing), TASKS.md 4.5 = `[x]`. **Do NOT re-implement it.**
> **The real next task is 4.6 (Dockerfile + deploy)** — or, since 4.6 is infra-only, **jump to Phase 5 (Supabase backend + RLS)**, which unblocks the real `/design` persistence and the frontend. Recommend confirming with the user which they want first.

---

## CRITICAL RULES (non-negotiable — human lives at stake)

1. **Accuracy is absolute.** Every engineering number must trace to a verified SANS clause. Never guess or use training-data values for code coefficients.
2. **Kernel computes; AI never does arithmetic.** All numbers come from deterministic, version-pinned, unit-tested kernel functions. The LLM only parses language, asks clarifying questions, and writes narrative prose — architecturally **unable** to emit a number (see the narrative guard, below).
3. **Never fabricate code values** — transcribe from the SANS PDFs in `standards/`. If a PDF isn't present, mark the value **PROVISIONAL** and flag it in the clause string + `SOURCES.md`.
4. **Test-driven.** Write tests first; a task is `[x]` only when tests pass green in CI.
5. **Small commits per task.** Commit + push to `origin/main` after each green task; update `TASKS.md` and `SOURCES.md`. Then watch CI and confirm green.
6. **Engineer-in-the-loop, honest limitations.** TorenOne drafts; a registered engineer reviews and stamps. Every assumption/PROVISIONAL/out-of-scope item is stated in the report, never hidden.

---

## Environment & workflow

- **Repo:** `/Users/cash/TorenOne/` ; **worktree** (where all work happens): `/Users/cash/TorenOne/.claude/worktrees/serene-bhabha-853ff0/`
- **Python 3.11 is the only supported interpreter** (`requires-python>=3.11`; CI runs 3.11). Path: `/opt/homebrew/opt/python@3.11/bin/python3.11`.
  - ⚠️ **Python 3.9 is retired.** The Pydantic models use `X | None` / `list[X]` syntax (PEP 604/585) evaluated at runtime → needs 3.10+. Do not use `python3` (system 3.9).
  - WeasyPrint (PDF) needs Python 3.11 + Homebrew pango/cairo (present on this machine).
- **Run the full suite:**
  ```bash
  cd /Users/cash/TorenOne/.claude/worktrees/serene-bhabha-853ff0
  PYTHONPATH="kernel/src:tools:service/src" /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest -q
  # Expected: 691 passed
  ```
- **Lint + types (CI gates on these — keep clean):**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -m ruff check .
  PYTHONPATH="kernel/src:tools:service/src" /opt/homebrew/opt/python@3.11/bin/python3.11 -m mypy kernel/src tools service/src
  ```
  - ruff and mypy are **version-pinned** in pyproject (`ruff==0.15.16`, `mypy==2.1.0`) for reproducible CI. ruff config: line-length 120, `ignore=["UP042"]`, per-file E402 ignores for `plane_frame.py`/`sway_check.py`/`test_report.py`, and `flake8-bugbear.extend-immutable-calls` for FastAPI `Depends`.
- **Commit + push:** `git push origin HEAD:main`. **Commit footer:** `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Watch CI after push:**
  ```bash
  RUN=$(gh run list --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
  gh run watch "$RUN" --exit-status
  ```
- **CI** (`.github/workflows/ci.yml`): installs `.[dev,service]`; runs `ruff check .`, `mypy kernel/src tools service/src`, `pytest`. Web job runs Next.js lint/typecheck/test/build. Both must be green.

---

## Progress dashboard (true state)

| Phase | Title | Status |
|---|---|---|
| 0 | Foundations & project setup | ✅ done |
| 1 | Core engineering kernel (TDD) | ✅ done — incl. **last-mile extension 1.15–1.18** |
| 2 | Report engine | ✅ done — incl. **2.8 last-mile sections** |
| 3 | AI orchestration layer | ✅ done (3.1–3.5) |
| 4 | Engineering service (FastAPI) + auth | 🔶 in progress — **4.1–4.5 done; only 4.6 (deploy) remains** |
| 5 | Supabase backend (data + RLS) | ⬜ not started ← **likely next substantive work** |
| 6 | Frontend (Next.js screens) | ⬜ not started |
| 7 | Integration & E2E | ⬜ |
| 8 | Validation gate & hardening | ⬜ (the accuracy gate) |
| 9 | Pilot & YC readiness | ⬜ |

`docs/TASKS.md` is the authoritative, detailed task log — read it for the exact per-task notes.

---

## What this product is (1-paragraph context)

TorenOne = "AI structural engineer." An engineer describes a **single-bay steel portal frame** in plain English; the system parses it (OpenAI), the engineer confirms an editable spec (trust gate), and a deterministic kernel produces a **complete, stamp-ready SANS calc-package PDF** — members **+ connections + baseplates + pad footing + steel tonnage cost** — in minutes. SANS 10160 (loads) + SANS 10162-1 (steel) + SANS 10100-1 (concrete footing). Positioning (advisor-aligned, in PRD): a "SaaS Challenger / compound startup" that **collapses the fragmented legacy stack** (ETABS + Prokon + IdeaStatica + Mathcad) into one prompt-to-PDF pipeline. Scope is deliberately the **one structure, end-to-end** — NOT multi-storey/concrete frames/other codes (those are Year 2+).

---

## Architecture (three layers)

```
kernel/src/torenone_kernel/   PURE deterministic Python — the moat. No IO/network.
  models/        FrameSpec (+ FoundationInputs), DesignResult, CheckResult, results
  sections/      SAISC section library (64 sections; PROVISIONAL data)
  loads/         dead.py, imposed.py (SANS 10160-2), wind*.py (SANS 10160-3)
  loads/combinations.py  ULS/SLS (DRAFT SANS 10160-1 — PROVISIONAL factors)
  analysis/      plane_frame.py (PyNite wrapper), sway_check.py (U2, cl. 8.7)
  checks/        classification, axial, shear, bending(LTB), interaction, deflection,
                 material(fy), autosize  (all SANS 10162-1)
  connections/   bolts.py + moment_endplate.py — eaves/apex joints (Task 1.15, PROVISIONAL)
  foundations/   baseplate.py (1.16, PROVISIONAL) + pad_footing.py (1.17, VERIFIED SANS 10100-1)
  design.py      design() + check() — the orchestrator (incl. _design_last_mile)
  report/        renderer.py (render_html/render_pdf) + template.html.jinja2 + diagrams.py
  rules_version.py

service/src/torenone_ai/       AI orchestration (Phase 3) — server-side, OpenAI gpt-5.5
  config.py      AIConfig (key from OPENAI_API_KEY; redacted in repr/str)
  client.py      build_client() (lazy openai import)
  parsing.py     FrameSpecExtraction (all-nullable) + build_frame_spec() + parse_description()
  clarify.py     clarifying_questions() / clarification_prompt() (deterministic, no LLM)
  narrative.py   slot-substitution narrative — NUMBERS GUARD: model output with any digit is
                 rejected (assert_prose_has_no_literal_numbers); all numbers injected from kernel

service/src/torenone_service/  FastAPI app (Phase 4)
  app.py         create_app() factory; routes; per-request JSON logging middleware
  auth.py        Supabase JWT verify (HS256) — require_user dependency
  ai_runtime.py  server-side OpenAI client+model on app.state.ai_runtime
  design_service.py  run_design() (kernel design/check dispatch) + DesignError
  reports.py     ReportBuilder (WeasyPrint) + ReportStore (InMemory; Supabase in Phase 5)
  schemas.py     ParseRequest/Response, DesignRequest/Response, StoredReport
  errors.py      install_exception_handlers — catch-all 500 (safe), no secret leak  (TASK 4.5 — DONE)
  logging_config.py, main.py (uvicorn torenone_service.main:app)

web/   Next.js 16 + Tailwind v4 + shadcn (Phase 0 scaffold only; screens are Phase 6)
```

### HTTP endpoints (all live, tested)
- `GET /health` — public liveness.
- `GET /me` — protected (Supabase JWT) → authenticated user.
- `POST /parse` — protected. Body `{description}` → `ParseResponse{status, spec, assumptions, questions, missing, errors, scope_note}` where status ∈ complete / needs_clarification / invalid / out_of_scope. OpenAI client injected (fake in tests; **502** on OpenAIError).
- `POST /design` — protected. Body `{spec, mode(design|check), sections?, cost_rate?, project_id?}` → `DesignResponse{result, report}`. Runs kernel, builds PDF (`ReportBuilder`), persists (`ReportStore`). `DesignError`→422, build/store failure→502. `DesignRequest` strips computed geometry fields so a spec round-tripped from `/parse` re-validates.

### Auth + AI config wiring
- `create_app(*, auth_config=None, ai_runtime=None, report_builder=None, report_store=None)` — all injectable for tests. Without them, loads from env; if a secret/key is missing, the relevant routes return **503** (app still boots for health checks).
- Env (server-side only; `.env.example` documents all): `OPENAI_API_KEY`, `OPENAI_MODEL` (gpt-5.5), `OPENAI_FALLBACK_MODEL` (gpt-5.4-mini), `SUPABASE_JWT_SECRET`, `SUPABASE_JWT_AUD` (default "authenticated"), Supabase URL/keys. **Keys live only in `service/.env` — never in chat/commits.**

---

## Kernel public API (what callers use)

```python
from torenone_kernel.design import design, check, DEFAULT_COST_RATE_ZAR_PER_KG
design(spec: FrameSpec, cost_rate_zar_per_kg=20.0) -> DesignResult
check(spec: FrameSpec, sections: list[SectionChoice], cost_rate_zar_per_kg=20.0) -> DesignResult
```

**`DesignResult`** (frozen Pydantic) now includes the **last mile**:
`frame_spec, sections, checks, rules_version, warnings, total_steel_mass_kg, indicative_cost_zar,`
`connections: tuple[ConnectionDesignResult,…]` (eaves+apex), `baseplate: BaseplateDesignResult|None`, `footing: PadFootingDesignResult|None`.
Computed: `passed`, `governing_utilisation`, `total_steel_tonnes`.
**Key design choice:** every connection/baseplate/footing CheckResult is **also appended to `checks`**, so `passed`/`governing_utilisation` span the whole frame with the existing formulas. The structured fields drive the report's dedicated sections. The report's main "Member Code Checks" table filters them out (renderer `_DETAIL_CHECK_PREFIXES`) to avoid duplication.

**`FrameSpec.foundation`** (`FoundationInputs`): `allowable_bearing_kpa: float|None` (**None by default — NEVER assumed**; if absent, the pad footing is skipped with a warning), `concrete_fcu_mpa=25.0`.

Standard 15 m demo frame result: rafter `305x165x54`, governing util **0.986** (apex connection), footing `600×300 Y12@200`, baseplate `404×265×12 + 4×M20`. All pass.

---

## The advisor improvements (already integrated this session)

A YC advisor recommended "completing the wedge" — finishing the single-structure workflow so the engineer never leaves the tool. Mapped + delivered:
1. **Connections & foundations (kernel)** — DONE: tasks 1.15 (eaves/apex connections), 1.16 (baseplates), 1.17 (pad footing), 1.18 (integration + tonnage), 2.8 (report sections).
2. **Spec-review / editable confirm UI** — planned Phase 6.5 (FR-32). Not yet built (no frontend yet).
3. **Visual feedback (2D model + interactive BMD/SFD on web)** — planned Phase 6.6. BMD/SFD PNGs already in the PDF.
4. **Tonnage + cost-per-ton** — DONE in kernel/report (`total_steel_tonnes`, engineer cost rate). Cost-per-ton UI input is Phase 6.
5. **Check mode endpoint** — DONE (`POST /design?mode=check`).
PRD/DESIGN/TASKS were updated to fold these in (commit `ac45dcd`); guardrails reaffirmed (no multi-storey/concrete frames/other codes/generic FEA UI).

---

## Standards status (honest)

`standards/` is git-ignored (copyright). **In THIS worktree, only `SANS 10100-1.pdf` is physically present** (+ README). The README manifest lists others (SANS 10162-1, 10160-1/2/3, steelwork guide) but they are NOT in this checkout — that's why earlier steel transcriptions relied on values verified in prior sessions, and why the new connection/baseplate work is PROVISIONAL.

- ✅ **Pad footing (1.17): VERIFIED against SANS 10100-1** (user supplied the PDF). Transcribed: flexure K/z/As + 0.95d + K'=0.156 (cl. 4.3.3), vc=(0.75/γm)(fcu/25)^⅓(100As/bd)^⅓(400/d)^¼ γm=1.4 (cl. 4.3.4 eq. 2), v_max=min(0.75√fcu,4.75) (cl. 4.3.4.1), bases cl. 4.10, min steel 0.13% (cl. 4.11.4).
- ⚠️ **Connections (1.15) + baseplates (1.16): PROVISIONAL** — they need **SANS 10162-1** (connection/bolt/weld clauses), whose PDF is NOT in this worktree. Coefficients follow SANS 10162-1 / CSA S16 practice, flagged PROVISIONAL in every clause string + `SOURCES.md`. **If the user uploads SANS 10162-1, verify these the same way 1.17 was verified** (place in `standards/`, read the clauses, transcribe, flip to VERIFIED, re-pin tests, update SOURCES).

### All PROVISIONAL items (pending registered-engineer sign-off — Phase 8 gate)
1. `fy` (S355JR/S275JR) from EN 10025-2 — `checks/material.py`
2. Sway threshold U2 > 1.4 (CSA S16 basis) — `analysis/sway_check.py`
3. Load-combination factors from **DRAFT** SANS 10160-1 — `loads/combinations.py`
4. SAISC 64-section dataset — `sections/` (Phase 8 spot-check vs Red Book)
5. Indicative cost rate R20/kg — `design.py`
6. K=1.0 effective length — `design.py`
7. **Connections** (bolts/welds/end-plate, flange-couple method) — `connections/` (SANS 10162-1 not in worktree)
8. **Baseplates** (bearing/plate/anchors) — `foundations/baseplate.py`

---

## Reading the SANS PDFs (for verification work)

The PDFs are vector/figure-heavy; **equation and table pages often do not extract as text**. Use the `Read` tool with the `pages` parameter (max 20 pages/request). Page offset: front matter is roman, body arabic restarts at 1 — for SANS 10100-1, content page P ≈ PDF page P+13 (e.g., cl. 4.10 "Bases" content p.87 ≈ PDF p.100). When a clause page won't extract, read the surrounding prose pages and rely on the BS 8110 lineage + cross-checks, transcribing only what you can confirm; flag the rest.

---

## Recommended next steps (in order)

1. **Confirm with the user** that 4.5 is done and ask whether to do **4.6 (deploy infra)** now or **jump to Phase 5 (Supabase)**. Phase 5 is the higher-value unblock (real persistence + RLS + enables the frontend).
2. **Phase 5 — Supabase backend (data + RLS):** create project; tables `firms/profiles/projects/runs/reports`; Auth; Storage bucket for PDFs; **RLS policies filtering every table by firm_id** (the multi-tenant isolation — must be test-proven: firm A cannot read firm B). Then implement a **Supabase-backed `ReportStore`** (replacing `InMemoryReportStore`) and wire `/design` persistence. The `ReportStore` Protocol in `reports.py` is the seam — designed for exactly this swap.
3. If uploaded: **verify SANS 10162-1** and flip connections/baseplates to VERIFIED.
4. Then Phase 6 (frontend screens, incl. the spec-review + visual-canvas advisor items), Phase 7 (E2E), Phase 8 (validation gate — THE accuracy gate vs a real past project).

---

## Pre-flight checklist for the new session

```bash
cd /Users/cash/TorenOne/.claude/worktrees/serene-bhabha-853ff0
git log --oneline -3            # latest should be bd5f92a (Task 2.8)
git status --short              # should be clean
PYTHONPATH="kernel/src:tools:service/src" /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest -q   # 691 passed
/opt/homebrew/opt/python@3.11/bin/python3.11 -m ruff check .                                          # clean
PYTHONPATH="kernel/src:tools:service/src" /opt/homebrew/opt/python@3.11/bin/python3.11 -m mypy kernel/src tools service/src  # clean
```
Then read `docs/TASKS.md` (authoritative task log), `docs/PRD.md` (v1.1 — scope), `docs/SOURCES.md` (every value's provenance), and this file. **Do not start 4.5 — it's done. Start with 4.6 or Phase 5 per the user.**
