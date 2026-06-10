# TorenOne — Source & Resource Register (LIVING DOCUMENT)

> Every external source, dataset, and key value we use is logged here — so we can trace,
> verify, and amend anything by knowing exactly where it came from. **Updated in real time**
> throughout development.
>
> **Status:** living · **Last updated:** 2026-06-10

## How to use
- **Status legend:** `VERIFIED` (authoritative/confirmed or universal fact) · `PROVISIONAL` (sourced
  from a free reference, pending registered-engineer sign-off vs the official standard) · `PLANNED`.
- The **engineering data & SANS code values** table (§1) is the safety-critical one — every value the
  kernel computes with must have a row here.
- Sign-off tracking for PROVISIONAL items lives in [REFERENCES-AND-VALIDATION.md](./REFERENCES-AND-VALIDATION.md) §5–6;
  this register is the broader provenance log.

---

## 1. Engineering data & SANS code values (life-safety — provenance critical)

| ID | Item | Value / data | Source | Accessed | Status | Used in |
|---|---|---|---|---|---|---|
| E1 | SAISC steel section properties (64: IPE-AA/IPE 100–200, UB, UC) | full section props (A, I, Sx, Zx, rx/ry, J, Cw, geom) | Official **SAISC "Database of Structural Steel Sections"** (free PDF), supplied by co-founder; parsed via `tools/build_saisc_sections.py` | 2026-06-10 | PROVISIONAL (pending Pr.Eng spot-check vs Red Book) | `kernel/.../sections/data/saisc_sections.json` |
| E2 | Imposed roof load — inaccessible roof | **0.4 kN/m²** UDL (SANS 10160-2 Table 5) | SANS 10160-2:2011 Table 5; confirmed peer-reviewed: *J. SAICE* via SciELO `S1021-20192021000100005`; corroborated across multiple refs | 2026-06-10 | PROVISIONAL (pending sign-off) | `kernel/.../loads/imposed.py` (1.5) |
| E3 | Gravitational acceleration g | 9.81 m/s² (mass→weight) | Universal physical constant | 2026-06-10 | VERIFIED | `kernel/.../loads/dead.py` (1.4) |
| E4 | SANS 10160-3 wind **method (form)** | `cr(z)=kr·ln(z/z0)`; `vp=cr·co·vb,peak`; `qp=½ρvp²` | SkyCiv SANS 10160 docs; SciELO wind papers; EN 1991-1-4 form | 2026-06-10 | VERIFIED (form) | `loads/wind.py` (1.6) |
| E5 | SA fundamental basic wind-speed zones | `vb,0 = 32, 36, 40, 44 m/s` (10 m, terrain B) | Peer-reviewed SciELO `S1021-20192017000400001` / `...400002` | 2026-06-10 | PROVISIONAL | `loads/wind.py` (1.6) |
| E6 | Wind pressure coefficients (cpe walls/roof, cpi) | per **EN 1991-1-4** (SANS adopts; "differs only on map + terrain") | EN 1991-1-4 (freely documented); SkyCiv note | 2026-06-10 | PROVISIONAL (confirm SANS = EN) | `loads/wind.py` (1.6) |
| E7 | **SANS terrain roughness table** (z0, zmin, zg per A/B/C/D) + vb,peak factor + air density ρ | SANS 10160-3 Tables 1 & 2 | ⛔ **NOT in any legitimate free source** — in the standard only; pirated copies exist but rejected | 2026-06-10 | **BLOCKED — needs co-founder to read ~12 values off SANS 10160-3** | `loads/wind.py` (1.6) |

> Cross-verification (E1) was done against independently-known standard IPE/UC values; the spot-check
> tests live in `kernel/tests/test_saisc_dataset.py`.

## 2. Standards, code lineage & authoritative references

| ID | Reference | Use | Link / note | Status |
|---|---|---|---|---|
| S1 | SANS 10162-1:2011 ≈ **CSA S16** (Canada) | Steel design method/equations for the member checks (1.10) | Lineage exploited for public worked examples; comparison: SciELO `S1021-20192016000100002` | reference |
| S2 | SANS 10160-3 ≈ **EN 1991-1-4** (Eurocode wind) | Wind method/coefficients (1.6); SA differs on wind-speed map + terrain categories | per SkyCiv docs + Eurocode | reference |
| S3 | SANS 10160-1/-2 ≈ ISO 2394 / EN 1990–1991 | Limit-state combinations + imposed-load format | — | reference |
| S4 | **SAISC "Design of Structural Steelwork to SANS 10162" (4th ed.)** | Authoritative worked examples + validated spreadsheets (validation-gate cross-check) | saisc.co.za (to acquire) | PLANNED |
| S5 | **"Background to SANS 10160"** (Retief & Dunaiski) | Code committee's explanatory text (imposed/wind background) | CORE `188220688` — *download blocked in our env; co-founder can access* | reference |

## 3. Competitive research sources
Logged in [COMPETITIVE-LANDSCAPE.md](./COMPETITIVE-LANDSCAPE.md) §Sources. Key: YC RFS (ycombinator.com/rfs),
Genia (genia.design; funding via VentureBeat), Stru AI (stru.ai), ConGro AI (congro.ai), SkyCiv, VIKTOR, Spacial.

## 4. Tooling, frameworks & process references

| Item | Version / value | Source | Status |
|---|---|---|---|
| Next.js | 16.2.7 (stable; rejected the preview create-next-app pulled) | npm | VERIFIED |
| React / React-DOM | 19.2.7 | npm | VERIFIED |
| Tailwind CSS | v4 (`@theme`-based) | npm | VERIFIED |
| shadcn/ui + Supabase UI Library | design-system foundation (Phase 6) | supabase.com/ui (blog), ui.shadcn.com | VERIFIED |
| Geist Sans / Mono | UI + monospace fonts | `next/font` | VERIFIED |
| PyNite | planned (Task 1.8 analysis solver) | PyPI | PLANNED |
| Pydantic / pytest / vitest / Playwright | kernel + web testing | PyPI / npm | VERIFIED |
| Claude model | `claude-opus-4-8` (AI orchestration layer) | Anthropic (per claude-api skill) | VERIFIED |
| WCAG 2.1 contrast (AA) | design-token accessibility gate | W3C WCAG 2.1 | VERIFIED |

## 6. Resources to source (hand-off checklist for the co-founder)
> All are SANS standards SA firms keep on hand — **not new purchases**, just specific tables/values
> to transcribe. We need the *values*, not the documents.

| # | Document | Exactly what we need | Unblocks | Priority |
|---|---|---|---|---|
| R1 | **SANS 10160-3** (Wind actions) | Table 1/2: z₀, zmin, zg for terrain **A/B/C/D**; the `vb,peak` factor vs `vb,0`; air density ρ; cpe/cpi tables **or** confirm = EN 1991-1-4 | 1.6c/1.6d wind (in progress) | 🔴 first |
| R2 | **SANS 10160-1** (Basis of design) | ULS + SLS load-combination equations, partial factors (γ), ψ factors; SLS deflection limits | 1.7 load combinations | 🔴 |
| R3 | **SANS 10162-1** (Steel design) | φ, fy (S355 incl. thickness); Class 1/2/3 b-t/h-w limits; Cr (n, K); Mr; LTB (Mu, ω₂); beam-column interaction (U₁, ω₁) | 1.10 member checks → 1.11/1.12 | 🔴 |
| R4 | **SANS 10160-2** (Imposed) | Table 5 — confirm inaccessible-roof **0.4 kN/m²** (provisional E2) | 1.5 sign-off | 🟡 |
| R5 | Validation data (he *produces*) | Reference Frame v1: Vb zone + terrain + grade; golden outputs from Prokon/SAISC spreadsheet; spot-check the 64 sections | Phase 8 validation gate | 🟡 |
| R6 | *(optional)* SAISC "Design of Structural Steelwork to SANS 10162" (4th ed.) | Worked examples + validated spreadsheets | 1.10 + validation | ⚪ optional |

> We will source EN 1991-1-4 (wind coefficients) and CSA S16 (steel method) **free** ourselves — not on this list.

---
*Add a row the moment a new source, dataset, or key value enters the project.*
