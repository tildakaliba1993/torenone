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
| E4 | SANS 10160-3 wind method | `vp=cr·co·vb,peak`; `cr=1.36((z'−zo)/(zg−zo))^α`; `qp=½ρvp²` | **SANS 10160-3:2019 cl. 7.3–7.4 (eq. 3–6)** — official standard | 2026-06-10 | VERIFIED vs standard (final sign-off pending) | `loads/wind.py` |
| E5 | SA basic wind-speed zones vb,0 | 32 / 36 / 40 / 44 m/s (3 s gust) | **SANS 10160-3:2019 Figure 1** | 2026-06-10 | VERIFIED vs standard | `loads/wind.py` |
| E6 | Wind ext. pressure — **walls** | cpe,10 zones D/E vs h/d + correlation factor | **SANS 10160-3:2019 Table 6 + cl. 8.3.2.4** — validated vs Table 6 | 2026-06-10 | VERIFIED vs standard | `loads/wind_pressure.py` |
| E6b | Wind ext. pressure — **duopitch roof** | zones H/I cpe,10, pitch 5–45°, uplift+downforce | **SANS 10160-3:2019 Table 10** (pdfplumber) — validated vs Table 10 + cross-checked vs EN 1991-1-4 Table 7.4a | 2026-06-10 | VERIFIED vs standard | `loads/wind_pressure.py` |
| E8 | Wind **internal** pressure cpi | enclosed +0.2/−0.3; dominant opening 0.75/0.90·cpe; favourable cpi=0 | **SANS 10160-3:2019 cl. 8.3.9.6 NOTE 2, eq. 14/15, cl. 8.3.9.1** | 2026-06-10 | VERIFIED vs standard | `loads/wind_pressure.py` |
| E9 | Load combination factors | γG 1.2/0.9, STR-P 1.35, imposed 1.6, wind 1.3; SLS γG 1.1, γQ 1.0; inaccessible-roof ψ0=0 | **SANS 10160-1:2009 (DRAFT) Table 3, Table 2, eq. 6/7/10** | 2026-06-10 | ⚠️ **PROVISIONAL — DRAFT standard; confirm vs final** | `loads/combinations.py` |
| E7 | Terrain params (zg, zo, zc, α per A/B/C/D) + air density ρ(altitude) + vb,peak = 1.0·vb | Table 1; Table 4; eq. 4 | **SANS 10160-3:2019 Table 1/3/4** — implementation **validated against the standard's own Table 3** | 2026-06-10 | VERIFIED vs standard (sign-off pending) | `loads/wind.py` |

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
| PyNite (PyNiteFEA 1.6.2) | first-order linear-elastic plane-frame solver (Tasks 1.8–1.9); E=200 000 N/mm² G=77 000 N/mm² (PROVISIONAL pending SANS 10162-1 cl. 5.2 confirm at 1.10) | PyPI (`pip install PyNiteFEA`) | VERIFIED |
| SANS 10162-1:2011 cl. 8.7 | U2 sway amplification formula + notional load 0.005×gravity; sway-sensitive threshold U2>1.4 is CSA S16 basis (SANS text does not state explicit cutoff — PROVISIONAL) | standards/SANS 10162-1.pdf p.21 | PROVISIONAL |
| SANS 10162-1:2011 cl. 3.2 | E = 200 000 MPa, G = 77 000 MPa (confirmed in Symbols section) | standards/SANS 10162-1.pdf p.12 | VERIFIED |
| SANS 10162-1:2011 cl. 13.1a | φ = 0.90 (structural steel resistance factor) | standards/SANS 10162-1.pdf p.33 | VERIFIED |
| SANS 10162-1:2011 cl. 13.3.1 | Cr formula, n=1.34 hot-rolled; λ formula; KL/r≤200 limit | standards/SANS 10162-1.pdf p.34 | VERIFIED |
| SANS 10162-1:2011 cl. 11.2 Table 4 | Flange b/t limits 145/170/200·√fy (class 1/2/3); web h/t limits 1100/1700/1900·(1-reduction)·√fy | standards/SANS 10162-1.pdf p.29–31 | VERIFIED |
| SANS 10162-1:2011 cl. 13.4.1.1 | Vr=φ·Av·0.66·fy (pure shear, kv=5.34 no stiffeners); inelastic shear buckling limits | standards/SANS 10162-1.pdf p.36–37 | VERIFIED |
| SANS 10162-1:2011 cl. 13.5 | Mr=φ·Zpl·fy (class 1/2), Mr=φ·Ze·fy (class 3) | standards/SANS 10162-1.pdf p.38 | VERIFIED |
| SANS 10162-1:2011 cl. 13.6 | Mcr formula; Mr=1.15φMp(1-0.28Mp/Mcr)≤φMp (case 1) or Mr=φMcr (case 2); ω2 formula | standards/SANS 10162-1.pdf p.38–39 | VERIFIED |
| SANS 10162-1:2011 cl. 13.8.2+13.8.4 | Interaction Cu/Cr+0.85·U1·Mu/Mr≤1; U1=ω1/(1-Cu/Ce); ω1 values | standards/SANS 10162-1.pdf p.40–43 | VERIFIED |
| SANS 10162-1:2011 Annex D Table D.1 | Deflection limits: L/240 inelastic roof covering (vertical), H/400 building sway wind (informative — non-normative) | standards/SANS 10162-1.pdf p.98 | VERIFIED (informative) |
| fy for S355JR/S275JR | fy from EN 10025-2 (referenced cl. 5.1.3): 355/345/335 MPa for t≤16/40/63mm | EN 10025-2:2004 Table 7 (not in standards/ folder — PROVISIONAL pending engineer sign-off) | PROVISIONAL |
| SANS 10162-1 cl. 10.4.2.1 | KL/r ≤ 200 maximum slenderness limit for compression members | standards/SANS 10162-1.pdf p.28 | VERIFIED |
| SA fabricated steel cost rate | R20 000/tonne = R20/kg default (indicative_cost_zar). Market range R18 000–R25 000/tonne (2025). PROVISIONAL — confirm with fabricator before using for project cost estimates. | Industry knowledge; verify with SAISC or local fabricator | PROVISIONAL |
| PyNite node.DX/DY[combo] | Node displacement API — FEA apex deflection (DY, mm); eaves sway (DX, mm) | Inspected PyNite 1.6.2 source (verified in prior tasks) | VERIFIED |
| Task 1.11 auto-sizer | No new code values introduced — re-uses cl. 11.2 (classification), 13.3.1 (Cr), 13.4.1.1 (Vr), 13.5/13.6 (Mr/LTB), 13.8.2 (interaction) sourced in 1.10 | — | VERIFIED (all constituent values verified above) |
| Pydantic / pytest / vitest / Playwright | kernel + web testing | PyPI / npm | VERIFIED |
| OpenAI model | `gpt-5.5` primary / `gpt-5.4-mini` fallback (AI orchestration layer; Structured Outputs + function calling) | OpenAI API docs (developers.openai.com, verified 2026-06-11) | VERIFIED |
| Task 3.2 spec parsing | No new engineering values introduced — the LLM only transcribes/classifies user-stated inputs; all applied defaults (services 0.0 kPa, wall 0.0 kPa, roof inaccessible, altitude 0 m, no dominant opening, S355JR, pinned base, unrestrained) are the already-sourced `FrameSpec` model defaults | `models/frame_spec.py` (defaults documented in Phase 1) | VERIFIED (no new values) |
| Task 1.15 connections (bolts) | φb=0.80, φbr=0.80 (cl. 13.1); Tr=0.75·φb·As·Fu, Vr=0.60·φb·As·Fu, Br=3·φbr·t·d·Fu (cl. 13.12). Bolt 8.8 Fu=800, 10.9 Fu=1000 MPa; ISO stress areas M16/20/24/30 = 157/245/353/561 mm² | SANS 10162-1 / CSA S16 practice — **standard PDF absent from `standards/`** | **PROVISIONAL — engineer sign-off required** |
| Task 1.15 connections (welds/plate) | φw=0.67, fillet Vr=0.67·φw·(0.707·leg)·Xu (cl. 13.13.2.2); electrode Xu=480 MPa (E48xx); end-plate plastic bending (T-stub, simplified, no prying/modes 2-3); flange-force-couple moment method; plate Fy/Fu by grade | SANS 10162-1 / CSA S16 practice — not transcribed from PDF | **PROVISIONAL — engineer sign-off required** |
| Task 1.16 baseplates | φc=0.65, bearing = φc·0.85·f'c (elastic N+M pressure block, no A2/A1 confinement); plate cantilever bending φ·fy·t²/4 with AISC 0.95d/0.80b overhang; anchor tension (moment couple + uplift, axial relief ignored = conservative) + shear via cl. 13.12 bolt resistances; default f'c=25 MPa | SANS 10162-1 / CSA S16 / SANS 10100-1 practice — standard PDFs absent from `standards/` | **PROVISIONAL — engineer sign-off required** |
| Task 1.17 pad footings (concrete) | Flexure: stress block 0.67·fcu/γc (γc=1.5) + fy/γs (γs=1.15), lever arm z=d{0.5+√(0.25−K/0.9)}≤0.95d, K'=0.156 (cl. 4.3.3.1 + Fig. 4 + 4.3.3.4, p.22–24); design concrete shear vc=(0.75/γm)(fcu/25)^⅓(100As/bd)^⅓(400/d)^¼, γm=1.4 (cl. 4.3.4 **eq. 2**, p.27); max shear v_max=min(0.75√fcu, 4.75) (cl. 4.3.4.1); bending critical section at column face + uniform pressure (cl. 4.10.2.1/4.10.2.2, p.87); punching at column perimeter ≤ v_max & 1.5d perimeter (cl. 4.10.4.4, p.90); min reinforcement 0.13 % (cl. 4.11.4) | **SANS 10100-1 (SABS 0100-1 Ed. 2.2)** — PDF now in `standards/`, clauses read & transcribed 2026-06-11 | **VERIFIED vs standard** (defaults fcu=25/fy=450/cover=50 mm typical; durability-cover & full detailing remain engineer's check; allowable bearing is a geotechnical input) |
| WCAG 2.1 contrast (AA) | design-token accessibility gate | W3C WCAG 2.1 | VERIFIED |

## 6. Resources to source (hand-off checklist for the co-founder)
> ✅ **All standards OBTAINED 2026-06-10**, stored locally in **`standards/`** (git-ignored — copyright +
> size; see `standards/README.md` manifest). We transcribe specific values with clause citations, not the
> documents. Values are extracted module by module, each cited and (where possible) validated against the
> standard's own tables. **Final engineer sign-off** of transcribed values is still required (REFERENCES §5).
>
> **Document-quality caveats (from page-1 inspection):**
> - ✅ **SANS 10160-3:2019** & **SANS 10162-1:2011** — official (ISBN). Wind + steel are on solid footing.
> - ⚠️ **SANS 10160-1** is a **DRAFT (DSS, public-enquiry)** — combination partial factors **must be confirmed vs the final standard** before relied upon (1.7).
> - ⚠️ **SANS 10160-2** page-1 looks like a course re-host — verify genuine (imposed 0.4 kN/m² already corroborated).
> - ⚠️ **Steelwork guide** likely scanned (no text layer) — needs OCR; not the 4th ed.
>
> Remaining genuinely-outstanding items: **R5** (validation data the engineer *produces*) + confirm the SANS 10160-1 final-version combination factors.

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
