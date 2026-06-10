# TorenOne

The AI structural engineer. Describe a steel portal frame in plain language; get a code-checked,
review-ready SANS calculation package in minutes.

> **Accuracy is absolute — human lives are at stake.** Every engineering number is produced by a
> deterministic, version-pinned, unit-tested kernel. The AI never computes. We build test-first.

## Documents (read these first)
- [docs/PRD.md](docs/PRD.md) — product requirements (the bible of the MVP)
- [docs/DESIGN-ARCHITECTURE.md](docs/DESIGN-ARCHITECTURE.md) — architecture + UI design system
- [docs/TASKS.md](docs/TASKS.md) — phased implementation plan (live progress)
- [docs/REFERENCES-AND-VALIDATION.md](docs/REFERENCES-AND-VALIDATION.md) — code basis, benchmark, tolerances
- [docs/SOURCES.md](docs/SOURCES.md) — **living** source & resource register (provenance for every value)
- [docs/COMPETITIVE-LANDSCAPE.md](docs/COMPETITIVE-LANDSCAPE.md) — competitors & our differentiation
- [docs/PROJECT-SETUP.md](docs/PROJECT-SETUP.md) — Supabase/Vercel/GitHub isolation

## Repository layout (monorepo)
```
kernel/    Pure-Python engineering kernel (the moat) + its tests   [Phase 1]
service/   FastAPI service: AI orchestration + report engine        [Phase 4]
web/       Next.js frontend + design system                         [Phase 6]
tools/     Shared tooling — design tokens + WCAG contrast test       [Phase 0]
docs/      PRD, architecture, tasks, references
```
**Decision (Task 0.1):** single monorepo — simplest for a two-person team; one CI pipeline, atomic changes.

## Quick start (dev)
Requires **Python 3.11+** (system Python may be older — use pyenv/uv) and **Node 20+**.

```bash
# Python: kernel + tools tests
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                       # runs kernel + contrast tests

# Verify design tokens pass WCAG AA (no deps needed)
python tools/torenone_tokens/contrast.py
```

## Principles
1. Accuracy is absolute. 2. AI orchestrates; the kernel computes. 3. Engineer-in-the-loop — we never stamp.
4. Test-driven development. 5. Reproducible & auditable. 6. Build only the MVP.
