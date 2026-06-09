# TorenOne — Design & Architecture Document

> System architecture + UI design system for the MVP. Governed by the [PRD](./PRD.md). Work tracked in [Tasks](./TASKS.md).
>
> **Status:** v1.0 · **Last updated:** 2026-06-09

---

## Part A — System architecture

### A.1 Guiding rule
**Supabase is the backend for everything except the core engineering kernel.** The kernel is heavy, deterministic Python (numerical analysis + SANS rules) and runs as its own service. Supabase provides auth, database, storage, and multi-tenant isolation. The two never blur: **Supabase is app plumbing; the kernel is compute.**

### A.2 The three boxes

```
┌──────────────────────────────────────┐
│  Frontend — Next.js (Vercel)         │  shadcn/ui + Supabase UI Library,
│  describe · confirm · results · PDF  │  TorenOne steel-blue dark theme
└──────────┬─────────────────┬─────────┘
           │ auth + data     │ "run this design"  (JWT)
           ▼                 ▼
┌────────────────────┐   ┌───────────────────────────────────┐
│  Supabase          │   │  Engineering service — FastAPI    │
│  • Postgres (data) │◀──│  • verifies Supabase JWT          │
│  • Auth (JWT)      │   │  • AI orchestration (Claude)      │
│  • Storage (PDFs)  │   │  • CORE KERNEL (pure Python pkg)  │
│  • Row-Level Sec.  │   │  • report engine (PDF)            │
└────────────────────┘   └───────────────────────────────────┘
                                     │ Anthropic API (server-side key)
                                     ▼
                              claude-opus-4-8
```

### A.3 Component responsibilities

| Component | Owns | Must NOT do |
|---|---|---|
| **Frontend (Next.js)** | UI, design system, auth flows (Supabase), reading/writing project data, calling the engineering service | Hold the Anthropic key; perform any engineering logic |
| **Supabase** | Postgres data, Auth/JWT, Storage for PDFs, RLS isolation | Run the kernel (no heavy Python compute) |
| **Engineering service (FastAPI)** | JWT verification, AI orchestration, running the kernel, generating PDFs, persisting results | Let the LLM compute or invent numbers |
| **Core kernel (Python package)** | All engineering math, deterministic, versioned, tested | Network calls; non-determinism; any UI/IO concern |
| **AI layer (Claude)** | text → typed spec, clarifying questions, report prose | Produce or alter any engineering number |

### A.4 Data flow — one design run
1. Frontend sends the user's text + project id to **FastAPI** (with Supabase JWT).
2. FastAPI verifies the JWT, calls **Claude** with structured outputs → typed `FrameSpec`.
3. Frontend renders the **confirm screen**; user edits/confirms; confirmed `FrameSpec` returns to FastAPI.
4. FastAPI invokes the **kernel**: loads → combinations → analysis (+2nd-order) → SANS checks → auto-size. *(LLM not involved.)*
5. FastAPI builds the **PDF** (numbers from kernel; narrative from Claude), uploads it to **Supabase Storage**, writes a `run` + `report` row to **Postgres**.
6. Frontend reads the run/report from Supabase and shows results + download.

### A.5 The kernel architecture (the moat)
A standalone, importable, pure-Python package — no framework, no IO, fully unit-tested.

```
kernel/
  models/        # Pydantic: FrameSpec, Loads, Combination, AnalysisResult, CheckResult, DesignResult
  sections/      # SAISC section property database (data + accessors)
  loads/         # dead.py, imposed.py (SANS 10160-2), wind.py (SANS 10160-3)
  combinations/  # sans10160_1.py  (ULS/SLS limit-state combinations)
  analysis/      # plane_frame.py (wraps PyNite, 2D), second_order.py
  checks/        # sans10162_1/  classification, axial, moment, interaction, ltb, deflection
  design/        # auto_size.py (lightest passing section)
  rules_version.py  # e.g. SANS_10162_1 = "2011"  → stamped into every report
```
Principles: deterministic, side-effect-free, every rule module version-pinned, validated against worked examples + the benchmark project.

### A.6 AI integration
- Model: **`claude-opus-4-8`** via the `anthropic` Python SDK (server-side only).
- **Parsing:** structured outputs (`messages.parse()` against the Pydantic `FrameSpec`) → guaranteed-valid spec.
- **Orchestration:** the model may call the kernel as **tools**; it never computes itself.
- **Narrative:** the model drafts report prose; all numbers are injected from kernel results.
- Cost note: model is a minor cost line; do not prematurely downgrade. `claude-sonnet-4-6` is the fallback if parsing volume grows.

### A.7 Data model (Supabase / Postgres) — high level
| Table | Key fields | Notes |
|---|---|---|
| `firms` | id, name | tenant root |
| `profiles` | id (=auth uid), firm_id, name, role | links auth user → firm |
| `projects` | id, firm_id, name, created_by | owned by a firm |
| `runs` | id, project_id, frame_spec (jsonb), status, rules_version, created_by, created_at | one design run |
| `reports` | id, run_id, storage_path, created_at | PDF in Supabase Storage |

**RLS:** every table filtered by `firm_id` via the user's `profiles.firm_id`. A user can only read/write rows for their firm. Verified by test.

### A.8 Security
- Anthropic key + service secrets live only in the FastAPI service env.
- FastAPI verifies the Supabase JWT on every request; rejects otherwise.
- RLS enforced at the database layer (defence in depth, not just app logic).
- No engineering secret sauce or keys ever reach the browser.

### A.9 Tech stack summary
| Layer | Choice |
|---|---|
| Frontend | Next.js + TypeScript + Tailwind + shadcn/ui + Supabase UI Library, on Vercel |
| Backend (app) | Supabase: Postgres, Auth, Storage, RLS |
| Engineering service | Python + FastAPI |
| Kernel | Pure Python: Pydantic, NumPy, **PyNite** (2D now, 3D-ready) |
| Report engine | Jinja2 + WeasyPrint (HTML/CSS→PDF) + Matplotlib (diagrams) |
| AI | Anthropic API, `claude-opus-4-8`, structured outputs + tool use |
| Hosting (service) | Fly.io / Render / Railway (container) |
| CI | GitHub Actions (tests gate every merge) |

---

## Part B — UI design system

### B.1 Foundation
TorenOne adopts **Supabase's design system wholesale**: it is open-source **shadcn/ui + Tailwind CSS**, distributed via the shadcn registry, with pre-built **Auth / Storage / Realtime** components. We use that foundation directly and re-theme it with the **TorenOne steel-blue** identity. We keep Supabase's *system* (layout, spacing, component style, dark-first feel); we use our *own brand colour*.

- Base: **Next.js + Tailwind + shadcn/ui** (components copied into our repo — we own the code).
- Pull Supabase UI Library auth/storage components from the registry to get sign-in/sign-up and upload flows nearly free.
- Dark-first. Clean, minimal, generous spacing, subtle low-contrast borders, monospace for numbers/clauses.

### B.2 Brand & colour tokens (dark theme)
Steel-blue for a **trustworthy, authoritative** feel. All foreground/interactive tokens verified against the dark base for **WCAG AA** (≥ 4.5:1 normal text, ≥ 3:1 large/UI). *(Run final values through a contrast checker before lock; ratios below are computed targets.)*

**Neutrals (cool-tinted to complement steel):**
| Token | Hex | Use | Contrast vs `--bg` |
|---|---|---|---|
| `--bg` | `#0E1116` | app background | — |
| `--surface` | `#14181F` | panels, sidebar | — |
| `--surface-raised` | `#1B212B` | cards, modals, popovers | — |
| `--border` | `#29313C` | dividers, input borders | — |
| `--border-strong` | `#3A4452` | emphasis borders, focus outline base | — |
| `--text` | `#E8ECF1` | primary text | ~14:1 ✓ |
| `--text-muted` | `#9AA4B2` | secondary text | ~6:1 ✓ |
| `--text-subtle` | `#6A7585` | tertiary — **large/decorative only** | ~3.8:1 (not for small body) |

**Brand steel-blue:**
| Token | Hex | Use | Contrast |
|---|---|---|---|
| `--primary` | `#2F6FB0` | primary button fill (white text) | white-on-fill ~5.2:1 ✓ |
| `--primary-hover` | `#3A7EC2` | primary hover | — |
| `--primary-active` | `#275E97` | primary pressed | — |
| `--accent` | `#5AA2E8` | links, interactive text, data highlights, focus ring | on `--bg` ~6.9:1 ✓ |
| `--accent-muted` | `rgba(90,162,232,0.15)` | subtle tint backgrounds, hover surfaces | — |
| `--ring` | `#5AA2E8` | keyboard focus ring | meets 3:1 UI ✓ |

**Semantic status (calc pass/fail — never colour-only; pair with icon + label):**
| Token | Hex | Meaning |
|---|---|---|
| `--success` | `#3FB950` | check passes / utilisation OK |
| `--danger` | `#F85149` | **FAILS** / over-capacity |
| `--warning` | `#D6A02A` | near limit / review |
| `--info` | `#5AA2E8` | informational (= accent) |

White text token for use on `--primary`/semantic fills: `#FFFFFF`.

### B.3 Typography
- **UI / headings / body:** **Geist Sans** (clean, technical, free, pairs with Next.js — deliberately not a generic default).
- **Numbers, clause references, calc values, code:** **Geist Mono** (alignment + an engineering feel; numeric results always monospaced for scannability).
- Fallback: Inter (UI) / JetBrains Mono (mono) if Geist unavailable.
- Scale (Tailwind): display 30/36, h1 24, h2 20, h3 16, body 14, small 12. Line-height generous (1.5 body).

### B.4 Spacing, radius, elevation
- **Spacing:** Tailwind 4px scale; sections breathe (Supabase-like density — not cramped).
- **Radius:** `--radius-sm` 4px, `--radius-md` 6px (default: buttons, inputs, cards), `--radius-lg` 8px (modals).
- **Elevation:** dark UI relies on **borders + slight surface lift**, minimal shadows. Raised surfaces use `--surface-raised` + `--border`, not heavy drop shadows.

### B.5 Component conventions
- Use shadcn/ui primitives (Button, Input, Dialog, Card, Table, Tabs, Toast, Form) themed with the tokens above.
- **Primary action** = filled `--primary` + white text. **Secondary** = `--surface-raised` + `--border` + `--text`. **Tertiary/ghost** = transparent + `--accent` text.
- **Focus:** always a visible `--ring`; never remove outlines.
- **Forms:** inline validation messages; the confirm screen is a structured, editable form (PRD FR-4).
- **Tables (results/utilisation):** monospaced numeric columns; status cell = colour chip + icon + text (e.g. ✓ PASS / ✕ FAIL / ⚠ REVIEW).
- **Empty/loading/error states** designed for every async view (don't ship bare spinners).

### B.6 Key screens (MVP)
1. **Auth** — Supabase UI Library sign-in/sign-up, themed.
2. **Projects** — list + create; per-firm.
3. **Describe** — text input + examples; submit to parse.
4. **Confirm** — editable structured `FrameSpec` form + geometry sketch; explicit "Run design" CTA (the trust gate).
5. **Results** — utilisation table (pass/fail), member sizes, key deflections, BMD/SFD + geometry diagrams, "Download calc package (PDF)".
6. **Run history** — past runs per project, with stored PDFs.

### B.7 Report (PDF) design
- Matches the brand: clean, engineer-grade, monospaced numbers, clause references in the margin/inline.
- Sections: cover (project, date, rules version) · assumptions · load takedown · combinations · analysis results · checks (clause + pass/fail + utilisation) · member schedule · diagrams · limitations/notes.
- Status never colour-only; every number traceable to a clause (PRD FR-18/19/20).

### B.8 Accessibility checklist (enforced)
- [ ] All text/interactive tokens meet WCAG AA against their background.
- [ ] Status conveyed by icon + label, not colour alone.
- [ ] Visible focus rings everywhere; full keyboard navigation.
- [ ] Respect `prefers-reduced-motion`.
