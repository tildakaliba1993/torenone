# TorenOne — Competitive Landscape

> Who else is building AI for structural engineering, what they do, where the gaps are, and the
> advantages TorenOne builds its MVP around. Living doc — update as the field moves.
>
> **Status:** v1.0 · **Last updated:** 2026-06-10

## TL;DR
The AI-structural space is real, hot, and funding is flowing — which validates the category for YC.
But the field clusters tightly: **US codes (ACI/AISC/ASCE), horizontal "any building" scope, and a
heavy lean on existing analysis tools (ETABS/SAP2000).** Three lanes are essentially **unclaimed**,
and they're exactly ours:
1. **SANS / Southern Africa (then Eurocode + rest of Africa).**
2. **Vertical depth in one high-frequency structure — the steel portal frame.**
3. **The stampable, clause-referenced calc package as the deliverable** (vs. drawings/layouts), with a
   **deterministic kernel that can't fabricate numbers.**

## The two archetypes
- **Augment the incumbent** — an AI agent that drives ETABS/SAP2000/RISA for you. The firm still rents
  the $7K legacy tool; the AI speeds up using it. (Stru AI, ConGro AI.)
- **Generate from plans** — upload architectural drawings, AI proposes structural layouts, a rule-based
  engine validates them, export drawings + takeoff. (Genia.)

TorenOne is a **third thing: replace the stack.** Own analysis kernel (no ETABS rent), AI-native
text→calc-package, engineer-in-the-loop. That's the true "SaaS Challenger" displacement, not augmentation.

## Competitor profiles

### Genia (genia.design) — the strongest funded player
- **What:** Upload architectural DWG/BIM → AI identifies elements → generates *hundreds* of structural
  layout options → rule-based engine validates each → export drawings, PDF calc sheets, material takeoff.
- **Funding/team:** ~$3M; LA; ex-Arup structural engineer + ex-Amazon + genAI researchers. Serious.
- **Codes/geo:** unspecified publicly — presents as US/general. **No SANS signal.**
- **Focus:** generative *layout* (reads like concrete / residential & general buildings), cost/material
  optimisation, "5 design options."
- **Read:** They are ahead on the **plans-in → generative-layout** magic — which is **our v2 vision**, not
  our MVP. They are **not** doing deep steel-portal SANS calc packages. Don't fight them on layout
  generation now; win on reliability + SANS + steel depth.

### Stru AI (stru.ai)
- **What:** AI agent that works **inside** ETABS/SAP2000/RISA + Mathcad/Teams; builds the model in your
  tool window in real time, runs analysis, generates native editable Mathcad/Excel calc sheets, code-checks.
- **Codes/geo:** ACI/AISC/ASCE — **US.** No Eurocode/SANS noted.
- **Backing:** Google Cloud / AWS startup programs (no YC noted). Polished "glass-box / auditable" positioning.
- **Read:** Augmentation play — the customer **still needs the expensive legacy license.** Strong on calc-sheet
  transparency (a bar we must match). US-only.

### ConGro AI (congro.ai) — closest to our *flow*
- **What:** Text/description → code research → structural design report → auto-builds the model in ETABS.
  Self-correcting pipeline.
- **Codes/geo:** ASCE 7-22, AISC 360-22, ACI 318-19 — **US.** No Eurocode/SANS noted.
- **Pricing:** $25/mo (1,500 credits) / $100/mo (7,500). **ETABS-only today.**
- **Read:** Conceptually nearest to "describe → design report," but **US codes, ETABS-dependent, general
  buildings.** Confirms the text→report approach is viable and that **cheap, credit-based pricing** is the norm.

### Adjacent / platform players
- **VIKTOR (viktor.ai):** low-code platform for engineers to build their own design apps / explore variants.
  A *tooling platform*, not a vertical product — a different game.
- **Spacial (spacial.io):** AI + licensed professionals coordinating structural/MEP/energy — broader AEC.
- **"Structured AI" (YC):** "AI workforce for construction engineering" — note: a **different** company from
  stru.ai; worth tracking as a YC-backed entrant.

### Legacy incumbents (the displacement target — see PRD/REFERENCES)
- **CSI (ETABS/SAP2000/SAFE), Bentley (STAAD/RAM), Autodesk (Robot/Revit), Trimble (Tekla), Prokon (SA).**
  Expensive, desktop, no AI-native workflow. The thing we ultimately replace.
- **Cloud challengers — SkyCiv, ClearCalcs:** cloud-native structural tools (SkyCiv even documents SANS
  10160 wind). Proof firms will switch off desktop — but they are **cloud versions, not AI-native**, and not
  steel-portal-SANS calc-package focused.

## The gaps nobody owns (our wedge)
| Gap | Why it's open | TorenOne |
|---|---|---|
| **SANS / Southern Africa** | Everyone is US-code-first; SANS is small + niche to outsiders | Native SANS 10160/10162-1; founder-market fit; ~zero CAC via local firms |
| **Steel portal frames, deep** | Competitors are horizontal ("any building") or concrete-layout | One bounded, high-frequency structure made bulletproof — correct on the 100th job, not just a demo |
| **Replace the stack** | Stru/ConGro build models *inside* ETABS (still pay the rent) | Own deterministic analysis kernel — no legacy license required |
| **Stampable calc package** | Genia outputs layouts+takeoff; others output drawings | The clause-referenced calc package an engineer reviews and stamps — the painful, high-trust artifact |
| **Provable correctness** | Generative players validate-after-generate | Architecture where the **LLM never computes a number**; deterministic kernel, validation gate, audit trail |

## TorenOne's competitive advantages (ranked)
1. **Geographic + code moat:** SANS first (then Eurocode + Africa) — a market the funded US players ignore,
   where we have unfair domain + network advantage.
2. **Vertical depth over breadth:** steel portal frames, end-to-end and reliable. Depth in a niche beats a
   shallow "any building" demo — and it's how you earn an engineer's trust to stamp.
3. **Stack replacement, not augmentation:** our own kernel means we're not a feature on top of ETABS — we
   remove the $7K rent. The real challenger economics.
4. **Trust by construction:** deterministic, clause-referenced, "AI-never-fabricates" kernel + validation gate.
   In a life-safety field, *provable correctness* is a marketing weapon, not just engineering hygiene.
5. **Founder-market fit:** two Cape Town structural/civil engineers who live the pain — credible where a
   generalist US team is not, in a code/market they can't easily enter.

## What this means for the MVP (decisions)
- **Stay narrow.** Do NOT drift toward "any building / generative layout" — that's the crowded, funded lane
  (Genia/ConGro). Steel portal + SANS is ours.
- **Lead with the calc package** (stampable, clause-referenced) as the hero deliverable — differentiates from
  drawings/layout players and targets the most painful, trust-sensitive artifact.
- **Market the architecture:** "the AI never computes a number — a deterministic, tested kernel does, and an
  engineer stamps it." That's our answer to generative tools in a life-safety domain.
- **Plan-parsing is v2, not a race.** Genia is ahead there; we win first on reliability + SANS + steel depth,
  then add "architect's plans in" as the expansion.
- **Pricing posture:** undercut the legacy stack; credit/subscription norms are ~$25–100/mo (ConGro). Our value
  story is "replace your ETABS rent + days of manual calcs," not "another ETABS add-on."

## Threats & counters
- **Genia/others add SANS or steel-portal depth.** Counter: get there first with real local pilots + correctness
  the generative crowd can't match quickly; depth + trust + local relationships are slow to copy.
- **A funded player out-executes on speed.** Counter: narrow scope = faster to "correct and trusted"; founder-market
  fit + zero-CAC beachhead = traction they can't buy.
- **Incumbents (CSI/Autodesk) bolt on AI.** Counter: they protect legacy seat revenue and move slowly; SANS +
  steel-portal + stampable-calc is below their radar and against their economics.

## Sources
- Stru AI — https://stru.ai/ · https://stru.ai/vision
- Genia — https://www.genia.design/ · https://genia.design/product · VentureBeat (funding):
  https://venturebeat.com/business/genia-structural-copilot-lands-3-million-in-funding-for-construction-industry-ai-that-instantly-generates-physics-validated-structural-plans
- ConGro AI — https://congro.ai/
- VIKTOR — https://www.viktor.ai/why-viktor/structural-engineering-design
- Spacial — https://spacial.io/blueprint/how-ai-is-redefining-structural-engineering
- Structured AI (YC, distinct from Stru AI) — https://www.ycombinator.com/companies/structured-ai
