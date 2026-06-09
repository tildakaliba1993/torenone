# TorenOne — Y Combinator Application (Living Document)

> **Status:** Draft v2 — pre-product. First MVP scoped: a **steel portal-frame designer to SANS** (loading 10160, steel 10162-1).
> **Last updated:** 2026-06-09
> **Domain:** torenone.com
> **Name origin:** "Toren" = *tower* (Afrikaans/Dutch). TorenOne = Tower One. A structural name, rooted in Cape Town.

---

## ⚠️ How to use this doc
- Answers below are drafts built on our idea definition. **Edit freely** as you make progress — this is a living spec.
- `[BRACKETS]` mark things only you two know (names, dates, exact numbers). Fill these in.
- YC rewards **clarity, brevity, evidence, and earned conviction** — not hype. Keep answers tight. Update the "Progress" section every time you ship something or sign a pilot, because that section moves the needle most.

---

## ONE-LINE PITCH (internal north star)
Upload the architect's plans → get a code-checked, stamp-ready structural calculation package in minutes. Work that takes a firm days on a $7K/seat legacy software stack.

---

# COMPANY

### Company name
TorenOne

### Describe what your company does in 50 characters or less.
> *(Pick one — all under 50 chars)*
- **The AI structural engineer** *(26)*
- **AI that does structural engineering calcs** *(43)*
- **AI-native software for structural engineers** *(45)*

### Company URL
torenone.com

### What is your company going to make? Please describe your product and what it does or will do.
TorenOne is the AI structural engineer. An engineer describes the structure — guided, conversational input today, the architect's plans directly down the line — and TorenOne produces a code-checked, stamp-ready structural calculation package in minutes: member sizing, load combinations, capacity checks, and full code-clause references.

Today, structural engineers run analysis in legacy desktop tools (ETABS, STAAD) and then spend 6–10 hours per project *manually* transcribing the results into a calculation report, formatting it for the building authority, and citing every code clause by hand. It's expensive people doing low-value grunt work.

We invert that workflow. Instead of software that *helps an engineer do the work manually*, TorenOne *does the work and the engineer supervises and stamps it*. Under the hood, a deterministic, verified calculation kernel does all the engineering math (so it can't hallucinate a number), while AI parses the inputs, selects load cases, writes the report, and cites the clauses. Every output is auditable and traceable to a specific code clause.

We start narrow — **steel portal-frame design to South African standards (SANS 10160 loading, SANS 10162-1 steel)**, the bread-and-butter structure behind every SA warehouse, factory, and shed. A single, bounded, high-frequency structure type means we stay correct on the 100th project, not just the demo. From there we expand structure by structure and code by code (Eurocode next, then ACI/AISC) until we cover the full pipeline: architect's plans → structural design → analysis → calculations → drawings. The legacy stack a firm rents for ~$7K/seat/year, replaced by AI-native software that costs a fraction and does the work.

### Where do you live now, and where would the company be based after YC?
We live in Cape Town, South Africa. We'd relocate for the batch and are open to basing the company wherever is best for the company post-YC. South Africa is our ideal launch market: we know the SANS codes, we have direct relationships with structural firms here, and our customer acquisition cost is effectively zero at the start.

---

# FOUNDERS

> *YC's founder section is mostly a video + short background prompts. Drafting talking points — record the video, don't over-script it.*

### Founder backgrounds (talking points)
- **[Co-founder name]** — BTech/Bachelor's in **Structural Engineering**, CPUT. ~4 years post-grad structural engineering experience. Owns the engineering correctness, the code knowledge, and the trust layer. *This is the person who makes the product something engineers will actually stamp their name to.*
- **[Your name]** — National Diploma in **Civil Engineering**, CPUT. ~3 years in construction, then moved into tech and learned to **build software 10x faster with AI**. Owns product and shipping; knows detailing, drawings, takeoffs, and site reality firsthand.
- We've known each other since university (CPUT). Both based in Cape Town.

### Why you're the team to win (the killer line)
A normal software engineer can't build this — they don't understand structures. A normal structural engineer can't ship software fast. **We're the rare team that does both.** One of us encodes the engineering; the other ships it.

### Founder achievement prompts (fill in)
- [A hard thing you built or shipped — the AI-built software project that proves you can ship]
- [A structural project your co-founder led/owned that shows depth + judgment]

---

# PROGRESS

### How far along are you?
Early and moving fast. We've validated the problem from the inside — we've both done this manual calc-package work ourselves and felt the pain. We've defined a sharp first wedge — a **steel portal-frame designer to SANS** (one bounded, high-frequency structure type we can make bulletproof) — and we have warm access to several Cape Town structural firms ready to pilot.
> **UPDATE AS YOU GO:** [demo built? pilots signed? hours-saved measured? first rand of revenue?]

### How long have each of you been working on this? Full-time?
[Fill in — be honest. e.g. "Started [date]. [Your name] full-time on the build, [co-founder] transitioning from his structural role."]

### Are people using your product?
[Not yet / In pilot with X firms — update.] Our immediate goal before the interview: a working v0 demo and 3–5 firms testing it on real projects.

### Do you have revenue?
[Not yet / R___ MRR from ___ — update. Even one paying firm changes this answer's weight enormously.]

---

# THE IDEA

### Why did you pick this idea? Do you have domain expertise? How do you know people need it?
We picked it because we *live* the pain. Between us we cover the entire structural design-to-documentation pipeline — [co-founder] does the analysis, design, and calcs; [your name] does drawings, detailing, and knows how it's built on site. We've personally spent the 6–10 hours per project hand-assembling calc packages and citing clauses, and we've personally paid the ~$7K/seat/year ransom to Autodesk and CSI for ancient desktop software with no AI.

We know firms need this because we are those firms' people. We're starting by talking to structural practices in Cape Town and timing exactly where their hours go — and the answer is always the same: too many expensive hours on work that should be automated.

### Who are your competitors? What do you understand that they don't?
The incumbents are **Autodesk** (Revit, AutoCAD, Civil 3D — ~$3.7K/seat/yr), **CSI** (ETABS/SAP2000/SAFE), and **Bentley** (STAAD.Pro). They sell 30-year-old desktop software, recently forcing customers onto pure rental (CSI went cloud-sign-in-only in July 2025). They're slow and trapped in decades-old codebases — exactly the kind of incumbent YC says is now vulnerable.

What we understand that they don't (or can't act on): the calculation package — the most painful, time-consuming workflow — sits *outside* their analysis tools, in Word and Mathcad, hand-assembled. We attack that soft underbelly first and earn the customer before we ever fight ETABS head-on. And we understand the work as engineers, so we can build something trustworthy enough to stamp — which a generic "AI for X" startup can't.

### How will you make money? How much could you make?
Subscription, priced 5–10x below the incumbent stack — land at ~$100–300/seat/month, expanding as we replace more of the workflow. Pitch: *replace your $7K/yr software rent with software that costs a fraction and does the work for you.*

Market: AEC software is a $10–15B+ global market. Bottom-up: there are hundreds of thousands of structural engineers worldwide. Even 100k seats at ~$2K/yr is ~$200M ARR — and our ACV rises as we expand from calcs into full design, analysis, and drawings, eventually replacing the entire stack per seat.

### Which category best applies?
B2B Software / SaaS (vertical AI for AEC).

### Other ideas you considered
[Optional — list briefly if asked. e.g. AI-native EDA, AI-native ERP. Keep it short; shows you chose deliberately.]

---

# WHY NOW
- AI has collapsed the cost of building software 10–100x — the moat that protected legacy AEC software (millions of lines of code) is gone.
- Vision models can now read engineering drawings; LLMs can interpret code text.
- Incumbents just forced customers onto rental — industry frustration is peaking.
- **No AI-native player exists in structural engineering yet.** The lane is open.
- YC literally requested this ("SaaS Challengers" RFS).

---

# RISKS & ANSWERS (be ready for these in the interview)
- **Liability / life-safety:** Engineer-in-the-loop. We never auto-stamp. Verified kernel + full audit trail; every number traces to a code clause. We're a power tool; the engineer remains accountable.
- **Will engineers trust it?** Kernel validated against published worked examples; we show the clause for every result. And it's built *by* structural engineers — that's the trust.
- **Conservative industry / slow adoption:** We start as augmentation on real projects with design partners we know, not a rip-and-replace.
- **Can you actually build a verified calc kernel?** Yes — that's precisely [co-founder]'s expertise, and it's the moat a generalist team can't cross.

---

# PRE-INTERVIEW CHECKLIST (what moves us from "maybe" to "yes")
- [ ] Working **v0 demo**: steel portal-frame inputs → SANS-clause-referenced calc PDF
- [ ] **Validation gate passed**: tool's member sizes & utilisations match a real past frame designed by hand / in ETABS-STAAD-Prokon
- [ ] **3–5 Cape Town firms** piloting on real projects
- [ ] **Timed-pain evidence**: "engineers spend X hrs/project; we cut it to Y minutes"
- [ ] **First revenue** (even R500/mo — a paying customer outweighs any deck)
- [ ] Tight **founder video** (authentic, not scripted)

---

# HOW WE MAP TO THE "SaaS CHALLENGERS" RUBRIC
| YC requirement | TorenOne |
|---|---|
| Expensive incumbent | ✅ ~$7K/seat/yr stack |
| Hated incumbent | ✅ "Autodesk tax" + forced CSI rental |
| Ancient, "invulnerable" codebase | ✅ Revit/ETABS/STAAD — decades old |
| Workflow rethought, not reskinned | ✅ Software does the work, engineer supervises |
| 10x cheaper *and* better | ✅ 5–10x cost + hours→minutes |
| Avoids the graveyard (PM/CRM/notes) | ✅ Hard, regulated, untouched vertical |
| Strong founder-market fit | ✅ Structural + civil + AI-native builder |
| Fast wedge + early customers | ✅ 2-week demo, network for pilots |
