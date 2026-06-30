# TorenOne — Competitive positioning & prioritisation reference

> The single reference for "how do we compete, and what do we build next?" Created
> 2026-06-30. Pairs with `docs/SIGN-OFF-PACK.md` (validation), `docs/PRICING.md` (model),
> and the `strategy-and-roadmap` / `competitive-positioning` memory notes.

## TL;DR
The closest real peer is **Genia** (genia.design) — a $3M-funded US "structural AI agent."
Their core architecture is the **same as ours** (generative AI proposes, a deterministic
rule-based engine validates and is the source of truth) — strong validation that our bet is
right. They lead on **scope, output, team, capital**. We lead on **jurisdiction (SANS / SA),
depth of auditable trust, accredited-stamp liability, and pricing.**

**Strategy: do NOT match their breadth. Win a defensible jurisdiction + trust niche.**
> Be the deepest, most trusted, code-true AI structural design agent for South African /
> African **steel** — narrow and deep, backed by an accredited SANS stamp Genia structurally
> cannot issue.

At MVP stage the real risk is **not the product** — it's **(1) the validation gate and
(2) pilots.** Features come after those, and only ones that deepen the wedge.

## The competitor — Genia (facts, June 2026)
- LA-based; **$3M** raised. Co-founders: ex-Amazon ML engineer + **ex-Arup structural engineer**
  (their own accredited engineer in-house).
- Flow: upload architectural **CAD / BIM / PDF** → AI identifies walls/openings/columns/stairs →
  generates **hundreds of structural layout options** → **rule-based engine validates each** →
  returns **3–5 cost/material-optimal recommendations** → "permit-ready drawings in minutes."
- Headline claims: **10× faster, 20% less material**, multi-material (steel/concrete/timber), US codes.
- Sources: genia.design, VentureBeat (2026 $3M), Under the Hard Hat, ProptechConnect.

Other landscape (not direct peers): **ClearCalcs** (cloud calc tool, not agentic), **Autodesk
Forma** (early-stage architectural/site AI, not structural member design), academic "structural
copilots." None are SANS/SA.

## Scorecard — honest

**Where Genia leads us today**
1. **Scope** — whole buildings, multi-material. We do single-bay **SANS steel portal frames** only.
2. **Topology generation** — they decide *where* structure goes from an architect's drawing; we
   *size* a frame whose shape you give us. (Topology is the harder, flashier AI.)
3. **Output is drawings**, not just a calc package.
4. **Team + capital** — $3M, full-time in-house engineer. We have a part-time co-founder Pr.Eng.

**Where we lead / are differentiated**
1. **Jurisdiction (the strongest moat).** They're US-coded; we're **SANS / South Africa**. They will
   almost certainly never build SANS or carry SA professional liability — different codes, small TAM
   for them, large for us locally.
2. **Depth of auditable trust.** Clause-by-clause citations; **two independent accredited authorities
   validate the kernel** (Red Book + Mahachi); sign-off pack; honest PROVISIONAL flagging; engineer
   stamps everything. "Physics-validated" is their line; *provable, auditable, stamped* is our substance.
3. **Outcome-based pricing** ("free to calculate, pay to print") vs the per-seat incumbent model.

## The four moats (defensible, compounding)
1. **Jurisdiction** — SANS + SA registered-engineer liability. Structural; Genia won't contest it.
2. **Accredited stamp + dual-validated, auditable compliance** — regulatory-grade trust that gets
   designs *actually used* (permits, liability).
3. **Outcome-based pricing** — adoption-friction killer; turns Check mode into lead-gen.
4. **Local data** — SA designs, fabricator costs, section availability; compounds with every pilot.

## Roadmap (tiers)

**Tier 0 — the actual moat (do before features):**
- Close the **validation gate** (co-founder works the sign-off pack → stamps the methods).
- Land **1–3 SA pilot firms** running their past projects. Traction > features.
- *(Both depend on the co-founder; in progress / waiting.)*

**Tier 1 — highest-leverage, in-wedge, mostly co-founder-independent (build NOW):** see tickets below.

**Tier 2 — agent differentiators, still in-wedge:**
- Ingest a real architect's shed GA (not just a labelled portal sketch) → propose the frame.
- Cost/material optimisation with **real SA fabricator rates + section availability** (data moat).

**Tier 3 — only post-traction:** AISC (US) *to follow SA firms doing international work*, not to fight
Genia head-on; reinforced concrete as a Year-2 TAM expansion.

**What NOT to do (discipline):** don't chase whole-building multi-material generative design now;
don't go to US/AISC to fight Genia on their turf; don't build full CAD/BIM drawing generation yet.
All three burn scarce resources attacking our own moat.

---

## Tier 1 — concrete build tickets

Correctness boundary (company law) applies: 🟢 build freely (no engineering number changes);
🟡 new engineering logic is PROVISIONAL + queued for co-founder sign-off; 🔴 never flip
PROVISIONAL→VERIFIED or let the LLM compute an engineering number.

### T1-2 — Submission-ready calc package  ·  🟢  ·  co-founder-independent  ·  **recommended first**
**Why (moat 2):** the rational-design calc report *is* the SA steel deliverable. Making it
submission-grade closes Genia's "permit-ready" gap on the dimension that matters here, and makes the
paid artifact more valuable — all from existing kernel output (presentation only).

**Scope**
- Capture **project metadata**: client, project name/number, site address, the responsible engineer's
  name + ECSA reg no. (project- and/or run-level).
- Upgrade the PDF to a rational-design report: **cover sheet** (metadata + scope/declaration),
  methodology + pinned standards (already have), full clause-by-clause working (already have),
  an **assumptions & limitations register**, a **revision/version** line, and a **stamp/signature
  block placeholder** (filled by T1-1).
- "Computational aid / engineer must verify" wording retained.

**Dependency:** none. **Correctness:** 🟢 (presentation of existing numbers).
**Acceptance:** a generated PDF shows the cover with captured metadata, declaration, assumptions/
limitations register, standards, working, and an (empty) stamp block; metadata is editable in the UI;
golden report tests updated.
**Build areas:** kernel report template + `_compute_working` context; project/run metadata
(Supabase migration + web forms); no kernel engineering changes.

### T1-1 — Engineer review & e-stamp workflow  ·  🟢 to build (use needs an accredited engineer)
**Why (moat 1 — the strongest):** operationalises the accredited SANS stamp — turns "an engineer
stamps it" from a disclaimer into a product feature Genia cannot replicate locally.

**Scope**
- Per-run **review state**: `draft → under_review → stamped` (or `changes_requested`).
- An **engineer role** (with ECSA reg no) can open a run, add review notes, and apply an **e-stamp**
  (name, reg no, date, + the existing report **fingerprint/hash** for tamper-evidence). The stamp
  renders on the calc-package cover (ties to T1-2's stamp block). Audit trail (who/when).
- UI: "stamped" badge; non-engineers see "pending engineer review"; only the engineer role can stamp.
- Honest wording: the stamp records the engineer taking professional responsibility per *their own*
  review — it does not imply TorenOne validated anything.

**Dependency:** BUILD is independent; real USE needs an accredited-engineer user (the co-founder) and,
for live billable work, the validation gate. **Correctness:** 🟢 (no engineering numbers change; the
stamp is a recorded human action).
**Acceptance:** engineer role stamps a run → stamped PDF shows stamp block (name/reg no/date/
fingerprint) + audit recorded + RLS-scoped; non-engineers cannot stamp.
**Build areas:** Supabase migration (`runs.review_status`, `runs.stamp` jsonb, audit), role gating,
web server actions + UI, kernel report cover (render stamp when present).

### T1-3 — Broaden the steel wedge (mono-pitch / multi-bay / lean-to / mezzanine)  ·  🟡 PROVISIONAL  ·  go-live needs co-founder
**Why:** more of the real SA shed market without leaving the steel-portal wedge.
**Scope:** extend geometry + frame analysis (PyNite) + design + report to the next configuration —
recommend starting with **mono-pitch** or **multi-bay**. Each is new topology/analysis/design logic.
**Dependency:** new engineering logic → **PROVISIONAL**; the co-founder must validate (ideally vs a
worked example) before it is enabled for live/billable use. Biggest lift of the three.
**Correctness:** 🟡 — write the logic, mark PROVISIONAL, gate behind a scope note/flag, add validation
tests; do NOT bill on it until signed off. **Acceptance:** the new config designs end-to-end, clearly
labelled PROVISIONAL, with a validation test and an entry in the sign-off pack.

---

### Recommended sequence (given Tier 0 is co-founder-blocked)
1. **T1-2** (submission-ready package) — fully independent, immediately valuable, sets up T1-1's stamp block.
2. **T1-1** (review & e-stamp) — build now so it's ready the moment the co-founder engages.
3. **T1-3** (scope broadening) — build as PROVISIONAL; go-live waits on validation.
