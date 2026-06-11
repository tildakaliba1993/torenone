# TorenOne — Product Requirements Document (PRD)

> **This document is the bible of the MVP.** If a proposed feature is not in here, we do not build it. If a requirement here is not met, we are not done.
>
> **Status:** v1.1 · **Last updated:** 2026-06-11 (advisor-aligned: completed the single-structure workflow — connections, baseplates, footings, tonnage cost; spec-review + visual feedback) · **Owners:** [Your name] (product/build), [Co-founder name] (engineering correctness)
> **Companion docs:** [Design & Architecture](./DESIGN-ARCHITECTURE.md) · [Tasks & Implementation](./TASKS.md)

---

## 1. Vision

TorenOne is the AI structural engineer. An engineer describes a structure in plain language; TorenOne produces a code-checked, review-ready structural calculation package in minutes — work that takes a firm 1–3 days on a $7K/seat legacy software stack.

We are not "ETABS, but faster." We **collapse the fragmented legacy stack** — analysis (ETABS/STAAD) + member checks (Prokon) + connections (IdeaStatica) + the written report (Mathcad/Word) — into a **single AI-orchestrated, prompt-to-PDF pipeline**. The engineer never leaves the tool to finish the job. This is the "compound startup" wedge: own one structure's *entire* workflow end-to-end, then expand structure-by-structure (the long-term vision is the operating system for the structural firm — explicitly post-MVP).

**MVP scope of that vision:** a single, bounded, high-frequency structure type — the **steel portal frame** — designed to South African standards (**SANS 10160** loading, **SANS 10162-1** steel). We make this **one structure complete end-to-end** (members **and** connections, baseplates, footings, steel tonnage + cost) before expanding to any other structure or code. The north-star demo: a Cape Town engineer types *"15 m span, 5 m high warehouse in Woodstock with a light sheet roof,"* verifies the parsed spec on a clean screen, and downloads a finished, SANS-compliant calc package — connections, baseplates, and steel tonnage cost included — in under 3 minutes.

## 2. The problem

Structural engineers run analysis in legacy desktop tools (ETABS, STAAD, Prokon) and then spend hours **manually** assembling a calculation package: transcribing results, applying load combinations, checking every clause by hand, and formatting a report. It is expensive, error-prone, repetitive labour. The legacy tools are costly, dated, and have no AI-native workflow.

## 3. Target users

| Persona | Who | Pain | What they need from us |
|---|---|---|---|
| **Primary — the design engineer** | Pr.Eng / candidate engineer at a small/mid SA structural firm | Spends 1–3 days hand-building portal-frame calc packages | Describe frame → get a correct, clause-referenced calc package they can review and stamp in minutes |
| **Secondary — the firm principal** | Practice owner | Engineer-hours are the firm's cost base | Faster turnaround, consistent output, lower cost per job |

Launch beachhead: structural firms in Cape Town we already have relationships with (near-zero CAC).

## 4. Core principles (non-negotiable)

1. **Accuracy is absolute. Human lives are at stake.** The product must never produce a wrong or fabricated engineering number. A single wrong result destroys trust permanently.
2. **AI orchestrates; the kernel computes.** Every engineering number is produced by a deterministic, version-pinned, unit-tested Python kernel. The LLM parses language, asks questions, and writes narrative prose — it **never** performs or invents a calculation.
3. **Engineer-in-the-loop. We never stamp.** TorenOne drafts; a registered engineer reviews and stamps. This is a feature, not a limitation.
4. **Test-driven development.** No kernel logic ships without tests written first and passing. Engineering checks are validated against published worked examples and at least one real past project (the validation gate).
5. **Reproducibility & auditability.** Same input + same code-rule version → identical output. Every reported number traces to a specific SANS clause.
6. **Discipline.** We build only the MVP defined in §6. Anything else is logged and deferred.

## 5. The product — end-to-end flow

```
[1] Describe → [2] Confirm → [3] Generate → [4] Report → [5] Review & stamp
     (AI)          (AI+human)    (kernel)      (AI+kernel)     (human)
```

1. **Describe** — Engineer types a plain-language description of the portal frame.
2. **Confirm (trust gate)** — System echoes a structured interpretation + geometry sketch; engineer edits and confirms. **Nothing computes until confirmation.**
3. **Generate (deterministic kernel)** — loads → load combinations → 2D analysis (+ 2nd-order check) → SANS 10162-1 member checks → auto-size → **connection & baseplate design + pad-footing sizing** (the "last mile") → steel tonnage + cost.
4. **Report** — clause-referenced calc-package PDF with assumptions, loads, combinations, results, member + **connection/baseplate/footing** checks (pass/fail + utilisation), diagrams, and a steel-tonnage cost readout.
5. **Review & stamp** — Engineer reviews, optionally overrides, regenerates, exports, stamps.

> **Confirm (trust gate) is the spec-review screen:** the parsed `FrameSpec` is shown as **editable fields** (wind terrain, pitch, loads, sections…). The AI prepares the data; the engineer is the authoritative pilot and nothing computes until they confirm (FR-4).

## 6. MVP scope

### 6.1 IN scope
- Single-bay symmetric steel portal frame, pinned bases.
- Conversational/guided text input → typed frame spec, with a mandatory confirm/edit step.
- Loads (SANS 10160): dead (self-weight, sheeting, purlins, services), imposed roof (10160-2), **wind (10160-3)**.
- Load combinations (SANS 10160-1): ULS + SLS limit states.
- 2D elastic plane-frame analysis + second-order / sway check.
- Member checks (SANS 10162-1): section classification, axial resistance, moment resistance, combined axial+bending interaction, lateral-torsional buckling (with restraint positions), SLS deflection (apex + eaves sway).
- Auto-sizing from a curated SAISC section list (lightest passing section + utilisation ratios).
- **Two run modes:** *Design* (auto-size to lightest passing section) and *Check* (verify engineer-supplied sections to SANS — same checks, no auto-size). *(Competitive differentiator — §11.)*
- **The "last mile" — completing the single-bay portal frame** *(so the engineer never leaves TorenOne to finish this structure):*
  - **Connections (SANS 10162-1):** the *specific* joints of a single-bay portal frame only — **eaves (knee) connection**, **apex haunch/splice**. Bolt group + end-plate/weld checks for the design forces. **Not** a universal connection designer.
  - **Column baseplates (SANS 10162-1):** pinned and fixed baseplate sizing (plate area/thickness, anchor bolts) for the base reactions.
  - **Pad footings:** simple concrete pad-footing sizing from the PyNite base reactions (plan area vs an engineer-supplied allowable bearing pressure; thickness/reinforcement to SANS 10100-1). Single-bay portal frame only.
- **Instant steel tonnage + cost estimate:** the kernel knows the exact SAISC sections, so it reports total steel **tonnage** and a project cost from an engineer-supplied **cost-per-ton** (or per-kg) rate.
- **Spec-review trust gate:** the parsed `FrameSpec` is presented as **editable fields** the engineer overrides before any computation (FR-4).
- **Interactive visual feedback:** the web app renders a 2D stick-model of the frame and interactive BMD/SFD before the PDF is generated.
- Clause-referenced calc-package PDF with: a line-by-line **audit / "show-your-working"** view, a **deterministic-kernel provenance** label (numbers are computed, not AI-generated), an explicit **assumptions & limitations** block, and a **steel tonnage + indicative cost** readout.
- Accounts, projects, saved runs, stored report PDFs (multi-tenant, isolated per firm).

### 6.2 OUT of scope (explicitly deferred — do not build)
- Architect's-plan / PDF / drawing parsing (the v2 flagship).
- **A general/universal connection designer.** We build *only* the eaves, apex, and baseplate connections of a single-bay portal frame (§6.1) — no arbitrary joint library, no moment-connection wizard.
- **General foundation / geotechnical design.** Only a simple pad footing from base reactions + an engineer-supplied bearing pressure (§6.1). No piles, rafts, retaining structures, or soil modelling.
- Steel detailing / shop drawings / BIM / Revit export / drawing generation; 3D analysis.
- Eurocode / ACI / AISC or any code other than SANS.
- Any other structure type (RC frames, multi-storey, multi-bay, mezzanines, cranes, trusses).
- Class 4 (slender) sections — **refuse with a clear message** rather than approximate.
- Team collaboration, billing/subscriptions, mobile app.

> **Discipline note (advisor-aligned):** the above keeps us on the wedge. We are *completing one structure*, not broadening to many. Multi-storey, concrete frames, and other codes are the Year 2+ "vertical monopoly" — deliberately not now.

## 7. Functional requirements

> IDs are stable references for tasks and tests. Each must have automated tests.

### Input & interpretation
- **FR-1** The system shall accept a free-text description and produce a typed `FrameSpec` (geometry, materials, loads context, restraints, base fixity).
- **FR-2** Where required inputs are missing, the system shall apply documented SANS-appropriate defaults **and surface them on the confirm screen**, or ask a clarifying question — never guess silently.
- **FR-3** The system shall reject contradictory/invalid input (e.g. negative span, pitch >45°, eaves > span) with a clear, specific message.
- **FR-4** The system shall require explicit user confirmation of the structured interpretation before any computation runs.

### Loads & combinations
- **FR-5** The kernel shall compute dead loads from self-weight + user/standard component loads.
- **FR-6** The kernel shall compute imposed roof loads per SANS 10160-2.
- **FR-7** The kernel shall compute wind loads per SANS 10160-3 (peak wind speed, terrain category, external + internal pressure coefficients, zone pressures → frame line loads), including uplift cases.
- **FR-8** The kernel shall generate ULS and SLS load combinations per SANS 10160-1.

### Analysis
- **FR-9** The kernel shall perform 2D elastic plane-frame analysis per load combination and return M, V, N envelopes.
- **FR-10** The kernel shall perform a second-order / sway-amplification check and flag sway-sensitive frames. (If first-order only ships in v0, the report must state this limitation explicitly.)

### Member design (SANS 10162-1)
- **FR-11** Section classification (Class 1–3 supported; Class 4 refused per §6.2).
- **FR-12** Axial resistance check.
- **FR-13** Moment resistance check.
- **FR-14** Combined axial + bending interaction check.
- **FR-15** Lateral-torsional buckling check using restraint positions.
- **FR-16** SLS deflection checks (apex vertical, eaves horizontal sway) against limits.
- **FR-17** Auto-sizing (*Design mode*): iterate the SAISC list to the lightest section passing all checks; report utilisation ratios for each check.
- **FR-24** Check mode: the system shall accept engineer-supplied member sections and run the full SANS 10162-1 checks on them (no auto-sizing), producing the same clause-referenced result. *(Lower-liability adoption wedge; no competitor equivalent — §11.)*

### Connections, baseplates & foundations (the "last mile")
- **FR-28** The kernel shall design the **eaves (knee)** and **apex** connections of the single-bay portal frame for their governing design forces (bolt group + end-plate/weld), per SANS 10162-1, each with clause references and utilisation. *Scope-limited to these two joints — not a general connection designer.*
- **FR-29** The kernel shall size the **column baseplate** (plate dimensions/thickness + anchor bolts) for the base reactions, for both pinned and fixed bases, per SANS 10162-1.
- **FR-30** The kernel shall size a **pad footing** from the PyNite base reactions: plan area against an engineer-supplied allowable bearing pressure, with thickness/reinforcement to SANS 10100-1. *(Concrete values flagged PROVISIONAL pending the standard + engineer sign-off; bearing pressure is an explicit user input, never assumed.)*

### Costing & verification UX
- **FR-31** The kernel shall report total structural-steel **tonnage**, and the system shall accept an engineer-supplied **cost rate** (per ton or per kg) to produce an indicative project cost. *(Default rate is PROVISIONAL — §6.)*
- **FR-32** The confirm/spec-review screen shall present the parsed `FrameSpec` as **editable fields** (incl. wind terrain, roof pitch, loads, sections) that the engineer can override before computation, and the results UI shall render an interactive 2D frame model + BMD/SFD before PDF export. *(Human-in-the-loop; reinforces FR-4.)*

### Report
- **FR-18** Generate a calc-package PDF containing: assumptions, load takedown, load combinations, analysis results, every member, **connection, baseplate and footing** check with its **SANS clause reference** and pass/fail, member sizes, utilisation ratios, and geometry + BMD/SFD diagrams.
- **FR-19** Status (pass/fail/near-limit) shall never be conveyed by colour alone — always with text/icon as well.
- **FR-20** Reports shall record the code-rule version used, the input spec, and a timestamp for audit/reproducibility.
- **FR-25** The calc package shall report total steel mass (kg) and **tonnage**, and an indicative cost (from an engineer-supplied per-ton/per-kg rate — FR-31). *(Counters competitors' "material savings" pitch — §11.)*
- **FR-26** The calc package shall present a line-by-line audit (assumptions → loads → combinations → checks → section) and label every result as **computed by the deterministic kernel, not the AI**. *(Trust/provenance differentiator — §11.)*
- **FR-27** Every calc package shall include an explicit **assumptions, out-of-scope, and "engineer must verify"** block — honest limitations as a feature.

### Accounts & projects
- **FR-21** Users can sign up / sign in (Supabase Auth).
- **FR-22** Users can create projects, save runs, and retrieve stored report PDFs.
- **FR-23** A firm's data is strictly isolated from other firms (row-level security).

## 8. Non-functional requirements

- **NFR-1 Accuracy (paramount):** Kernel outputs validated against published worked examples **and** at least one real past project (the validation gate). Tolerances defined per check and asserted in tests.
- **NFR-2 No fabricated numbers:** Architecturally enforced — the LLM cannot emit engineering numbers; it only calls kernel tools. Verified by tests.
- **NFR-3 Reproducibility:** Identical input + code-rule version → byte-identical numerical results. Code-rule modules are versioned (e.g. `SANS 10162-1:2011`).
- **NFR-4 Reliability:** Kernel is deterministic and side-effect-free; no network calls inside computation.
- **NFR-5 Performance:** A single design run (parse excluded) completes in < 60 s for the demo case.
- **NFR-6 Security:** OpenAI API key and all secrets stay server-side; FastAPI verifies Supabase JWTs; RLS enforced.
- **NFR-7 Test coverage:** Kernel ≥ 95% line coverage with meaningful assertions; every FR has at least one test; CI blocks merge on failing tests.
- **NFR-8 Auditability:** Every numerical result in a report is traceable to a clause and a kernel function.

## 9. The trust & safety model

- **Confirm gate (FR-4):** misread input is caught by a human before any computation.
- **Deterministic kernel (NFR-2/3):** no hallucinated numbers; reproducible.
- **Validation gate (NFR-1):** tool output must match known-good designs within tolerance before any customer sees it.
- **Engineer-in-the-loop (principle 3):** the registered engineer remains accountable and stamps.
- **Honest limitations:** anything out of scope or approximated is stated explicitly in the report, never hidden.

## 10. Acceptance criteria — Definition of Done for the MVP

The MVP is "done" when **all** hold:
1. Every functional requirement (FR-1…FR-32) is implemented and covered by passing tests.
2. **Validation gate passed:** for a real past portal frame [benchmark project — TBD by co-founder], TorenOne's member sizes and utilisation ratios match the original design within agreed tolerances.
3. The full happy path runs end-to-end in the deployed app: describe → **review/edit spec** → generate → clause-referenced PDF (members **+ connections + baseplates + footing + steel tonnage cost**) → stored under the user's project — the engineer never leaves TorenOne to finish the frame.
4. Multi-tenant isolation verified (a user cannot access another firm's data).
5. CI is green; kernel coverage ≥ 95%.
6. The UI implements the design system in [Design & Architecture](./DESIGN-ARCHITECTURE.md) (dark theme, steel-blue, accessible contrast).
7. At least one real Cape Town firm has run a live project through it (pilot evidence for YC).

## 11. Competitive positioning & differentiation
> Full analysis: [Competitive Landscape](./COMPETITIVE-LANDSCAPE.md).

The AI-structural category is active and funded — which validates the market. Competitors cluster tightly, and TorenOne is deliberately positioned away from the crowd.

**The field**
- **Genia** (~$3M funded — the most serious AI-native competitor): architect's plans → AI-generated structural *layouts* → rule-based validation → drawings + material takeoff. Concrete/layout, general buildings, US/general codes. *(Plans-in generative layout is our v2 — not our MVP.)*
- **Stru AI**: AI agent *inside* ETABS/SAP2000/RISA; native Mathcad calc sheets; ACI/AISC/ASCE (US). Augments the legacy tool — the firm still rents it.
- **ConGro AI**: text → design report → builds the model in ETABS; US codes; ETABS-only; general buildings ($25–100/mo).
- **Legacy incumbents** (the displacement target): CSI/Bentley/Autodesk/Trimble/Prokon — expensive desktop, no AI-native workflow. Cloud challengers (SkyCiv, ClearCalcs) prove firms will switch, but aren't AI-native.

**What we do that they don't (our moats)**
1. **SANS + Southern Africa first** — every funded player is US-code-first; none target SANS. Founder-market fit + local network = near-zero CAC in a market they can't easily enter. (Expansion: Eurocode, rest of Africa.)
2. **Vertical depth, not breadth** — steel portal frames made bulletproof, vs horizontal "any building." Depth earns the trust to stamp.
3. **Replace the stack, not augment it** — our own deterministic kernel removes the ETABS rent (Stru/ConGro still require it). True challenger economics.
4. **The stampable, clause-referenced calc package is the deliverable** — vs layouts/drawings/takeoff. The most painful, trust-sensitive artifact.
5. **Provable correctness by construction** — the LLM never computes a number; deterministic kernel + validation gate + audit trail. In a life-safety field, generative tools cannot match this quickly.

**Discipline this implies (reinforces §6):** do **not** drift toward generative layout / plan-parsing / any-building (the crowded, funded lane). Win first on reliability + SANS + steel-portal depth; plan-parsing is a deliberate v2.

## 12. Success metrics

- **Product:** time-to-calc-package (target: < 10 min vs. 1–3 days); validation-gate accuracy (target: 100% within tolerance on benchmark); design runs completed on real projects.
- **Pilot:** ≥ 3 firms testing on real work before the YC interview; ≥ 1 paying (even nominal).
- **YC narrative:** "A Cape Town firm produced a portal-frame calc package with us last week that would have taken their engineer two days."

## 13. Open questions
- [ ] Which past project is the validation benchmark? (Co-founder to select the most *typical* warehouse frame.)
- [ ] Exact SLS deflection limits and load-factor set to adopt as defaults (confirm against current SANS editions).
- [ ] Curated SAISC section list for v1 (which series: IPE/HEA, UB/UC, or both).
- [ ] Agreed numerical tolerances per check for the validation gate.
