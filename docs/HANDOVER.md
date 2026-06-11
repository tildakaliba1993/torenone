# TorenOne — Session Handover (Phase 2 start)

**Date:** 2026-06-11
**Previous session:** Completed Phase 1 in full (Tasks 1.1–1.14)
**Next session scope:** Phase 2, Tasks 2.1 + 2.2 (template + PDF rendering)
**Test status at handover:** 263 passing, 0 failing
**Branch:** `claude/serene-bhabha-853ff0` tracking `origin/main`
**Latest commit:** `876aa4c` — Task 1.14 check mode + material readout

---

## CRITICAL RULES (non-negotiable — human lives at stake)

1. **Accuracy absolute** — every number the kernel outputs must be traceable to a verified SANS
   clause; never guess or use training-data values
2. **Kernel computes, AI never does arithmetic** — no in-line calculations; all numbers from
   verified modules
3. **Never fabricate code values** — transcribe from SANS PDFs in `standards/`
4. **Test-driven** — write tests first, implement until green; task is `[x]` only when tests pass
5. **Small commits per task** — commit + push to `origin main` after each green task; update
   TASKS.md and SOURCES.md
6. **SANS PDFs** are at `/Users/cash/TorenOne/standards/`; read via `pypdf.PdfReader(path)` with
   empty password (they decrypt automatically)

---

## Environment

- **Repo:** `/Users/cash/TorenOne/` (main); worktree at
  `/Users/cash/TorenOne/.claude/worktrees/serene-bhabha-853ff0/`
- **Python 3.11 — the project target** (`requires-python>=3.11`; CI runs 3.11).
  `/opt/homebrew/opt/python@3.11/bin/python3.11` (has WeasyPrint 69.0 + openai + pydantic + jinja2).
  - Full suite: `PYTHONPATH="kernel/src:tools:service/src" /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest -q`
  - ⚠️ **Python 3.9 is no longer supported for the kernel.** The models use `X | None` /
    `list[X]` syntax (PEP 604/585) which Pydantic evaluates at runtime — that requires 3.10+.
    The earlier 3.9 local workflow is retired; use 3.11 for everything.
  - WeasyPrint requires Python 3.11 + Homebrew pango/cairo on this machine.
- **Push command:** `git push origin HEAD:main`
- **Commit footer:** `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`

---

## Phase 1 — COMPLETE (263 tests passing)

All tasks 1.1–1.14 are done. Key public API:

### `from torenone_kernel.design import design, check, DEFAULT_COST_RATE_ZAR_PER_KG`

```python
design(spec: FrameSpec, cost_rate_zar_per_kg: float = 20.0) → DesignResult
check(spec: FrameSpec, sections: list[SectionChoice], cost_rate_zar_per_kg: float = 20.0) → DesignResult
```

### `DesignResult` (frozen Pydantic model)
Fields: `frame_spec`, `sections` (list[SectionChoice]), `checks` (list[CheckResult]),
`rules_version` (dict), `warnings` (tuple), `total_steel_mass_kg` (Optional[float]),
`indicative_cost_zar` (Optional[float]).
Computed: `passed` (bool), `governing_utilisation` (float).

### `CheckResult`
Fields: `name`, `clause` (SANS clause ref), `utilisation`, `passed`, `detail` (Optional).

---

## Phase 2 — Tasks 2.1 + 2.2

### Task 2.1 — Jinja2 HTML/CSS template (prerequisite for 2.2)
Template file: `kernel/src/torenone_kernel/report/template.html.jinja2`
Render function: `kernel/src/torenone_kernel/report/renderer.py` → `render_html(result: DesignResult) → str`

Sections required (Design §B.7):
1. Cover (project title, date, rules_version, PROVISIONAL warnings)
2. Assumptions & limitations block
3. Results (sections chosen, governing utilisation, pass/fail)
4. Checks table (name, clause, utilisation, pass/fail — icon + label + colour, PRD FR-19)
5. Steel schedule (designation, mass/m, total mass, indicative cost)
6. Provenance label: "All engineering values computed by TorenOne deterministic kernel"

### Task 2.2 — WeasyPrint PDF rendering
`render_pdf(result: DesignResult) → bytes` in `renderer.py`
Brand: steel-blue (#1B3A57) header, white body, monospace numbers.
PDF must start with `%PDF-`.

Test file: `kernel/tests/test_report.py` (run with python3.11 — see command above)

---

## PROVISIONAL items requiring engineer sign-off

1. fy values: S355JR from EN 10025-2 — PROVISIONAL
2. U2 > 1.4 sway-sensitive threshold: CSA S16 basis — PROVISIONAL
3. Load combination factors: from DRAFT SANS 10160-1 — PROVISIONAL
4. SAISC section data: 64 sections — PROVISIONAL (Phase 8 spot-check)
5. Indicative cost rate: R20/kg — PROVISIONAL
6. K=1.0 effective length — PROVISIONAL

---

## Key file locations

```
kernel/
  src/torenone_kernel/
    design.py                    ← design(), check(), DEFAULT_COST_RATE_ZAR_PER_KG
    rules_version.py             ← pinned standard editions
    report/                      ← TO BE CREATED (Tasks 2.1 + 2.2)
      __init__.py
      renderer.py                ← render_html(), render_pdf()
      template.html.jinja2       ← Jinja2 HTML template
    models/results.py            ← DesignResult, CheckResult, SectionChoice, etc.
  tests/
    test_report.py               ← TO BE CREATED (run with python3.11)
docs/
  TASKS.md                       ← Phase 1 all [x]; Phase 2.1/2.2 pending
  SOURCES.md                     ← sourced values with clause citations
  HANDOVER.md                    ← this document
```

## How to verify before starting

```bash
cd /Users/cash/TorenOne/.claude/worktrees/serene-bhabha-853ff0
PYTHONPATH="kernel/src:tools:service/src" /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest -q
# Expected: 447 passed
# Lint + types (must be clean — CI gates on these):
/opt/homebrew/opt/python@3.11/bin/python3.11 -m ruff check .
PYTHONPATH="kernel/src:tools" /opt/homebrew/opt/python@3.11/bin/python3.11 -m mypy kernel/src tools
```
