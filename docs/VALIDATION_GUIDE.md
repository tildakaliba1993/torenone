# Validating the kernel with your co-founder

This is the **Phase 8 validation gate** — the most important checkpoint before any
customer touches TorenOne. The goal is simple:

> Prove that TorenOne's engine produces the **same answers a trusted structural
> engineer would**, on a real portal frame your firm has already designed.

Your co-founder is a structural engineer, not a programmer. **You never show him
code.** You show him what he already knows how to judge: **inputs and a calc
package**. He reviews TorenOne exactly like he'd peer-review a graduate engineer's
calculations.

---

## Part 1 — How to approach him

- **Frame it as a peer review, not a software demo.** "I've built a tool that
  designs a single-bay steel portal frame end-to-end. I want you to check its work
  against a job you've already done — like marking a junior's calcs."
- **He stays the authority.** TorenOne *assists*; the engineer is the pilot and
  signs off. Nothing computes until he confirms the inputs, and every number cites
  a SANS clause. He's the one who's professionally liable — make him feel in
  control, because he is.
- **Lead with the honesty.** TorenOne **never hides an assumption**. Every
  approximation and out-of-scope item is printed in the report ("effective length
  K = 1.0 assumed — engineer to verify", "ULS wind combinations not checked", etc.).
  Engineers trust a tool that states its limits far more than one that hand-waves.
- **Pick the *typical* job, not the hardest.** The most ordinary shed your firm
  does every month — one he can judge in his sleep and has the original calcs for.

---

## Part 2 — The session, step by step

You drive the laptop; he reads and judges.

### Step 1 — Pick one real frame
He chooses a past single-bay portal frame and brings its **drawing + original
calculations** (his own, or from the software your firm used).

### Step 2 — Read the inputs off the drawing
Fill in this worksheet together (these are the only numbers TorenOne needs):

| Input | Value | Notes |
|---|---|---|
| Clear span (m) | | eaves to eaves |
| Eaves height (m) | | |
| Roof pitch (°) | | |
| Bay spacing (m) | | spacing between frames |
| Number of bays | | |
| Roof dead load (kPa) | | sheeting + purlins + insulation |
| Basic wind speed (m/s) | | from the SANS 10160-3 map |
| Terrain category | | A / B / C / D |
| Allowable bearing (kPa) | | geotech value (leave blank if none → no footing) |
| Steel grade | | S275JR / S355JR (default S355JR) |

### Step 3 — Run it through TorenOne
You type those inputs into the app and run the design. Out comes a **calc package
PDF** with member sizes, every code check, and clause references.

### Step 4 — He compares against his original
The four things he checks:

1. **Member sizes** — are the rafter and column sections what he'd choose (or
   within one size)?
2. **Utilisations** — is the governing utilisation in the same ballpark as his?
   (Tip: also run **"Check my sections"** mode with *his exact* sections — then the
   utilisations should line up directly with his hand-calcs.)
3. **Loads** — are the dead/imposed/wind values right per SANS 10160?
4. **Clause references** — are the SANS 10162-1 (steel) and SANS 10160 (loads)
   citations correct?

### Step 5 — He reviews the honesty
Have him read the report's **"Notes / limitations"** section and confirm:
- the **PROVISIONAL** items (e.g. imposed-load category, cost rate) are acceptable, and
- **nothing is approximated that isn't flagged.** If he spots an assumption we
  make silently, that's a finding to fix.

### Step 6 — Agree tolerances and record the outcome
Together decide what "close enough" means (e.g. governing utilisation within
±0.10, steel mass within ±15%, sections within one size). Write down the result
and any discrepancies.

---

## Part 3 — Lock it in as a permanent test (your job, not his)

Once he's picked the frame and you have the inputs + his original results, you
(the technical co-founder) drop the numbers into the test harness — **no code, just
values**:

1. Open `kernel/tests/validation/benchmarks.py`.
2. Copy the commented `TEMPLATE` block at the bottom into the `BENCHMARKS` list.
3. Replace each value with the worksheet numbers + his original member sizes (and,
   if he recorded them, the governing utilisation / steel mass).
4. Save. The validation test (`kernel/tests/validation/test_validation.py`) now
   runs that frame through the kernel on every commit and **fails the build** if the
   answers ever drift from his.

While `BENCHMARKS` is empty the gate **skips** (the build stays green); the moment
you add a real case it becomes a hard, must-pass gate (PRD NFR-1). A built-in
`test_harness_self_check` already proves the machinery works, so you can trust the
scaffold before the first real number goes in.

---

## Part 4 — What the result means

- **Numbers match within tolerance** → the kernel is validated for that case. Add
  2–3 more typical frames and you have a real regression safety net (Task 8.3).
- **Numbers don't match** → that's a **finding**, not a failure of the exercise.
  Either:
  - a genuine kernel issue to fix (great — caught before a customer), or
  - a difference in assumptions to clarify (e.g. he used a different wind case).

  Log it, resolve it, re-run. This back-and-forth *is* the validation.

The goal of the whole session is his **sign-off on correctness** — the green light
the plan requires before a pilot. He's not approving software; he's confirming the
engineering. That's a checkpoint only he can give.

---

## Part 5 — Sign-off checklist (the co-founder's deliverables)

These map 1:1 to `PRODUCTION_READINESS.md` §1. The pilot **cannot** open until **1.1 + 1.2**
are done; the rest should follow before scaling. Record his initials + date against each.

- [ ] **1.1 Validate the PROVISIONAL methods/values** (`docs/SOURCES.md`). The code↔standard
  *transcription* is already verified; this is his **professional sign-off** of: the SAISC
  section data (E1) vs the Red Book; the connection/baseplate **methods** (end-plate T-stub,
  baseplate bearing model); and the **wind-on-frame method** (sign conventions + governing case).
  *Done-when:* each `SOURCES.md` row he's responsible for is `VERIFIED` with his initials + date.
- [ ] **1.2 Fill the benchmark gate** — one real past frame + its original results into
  `kernel/tests/validation/` (you do the typing; see Part 3). *Done-when:* the kernel matches his
  real design within agreed tolerance, **in CI**. **← the launch blocker.**
- [ ] **1.3 Worked-example regressions** — ≥2 published worked examples as permanent
  `BenchmarkCase`s. *Done-when:* green in CI.
- [ ] **1.4 Formula/clause review** — he reads every check's clause mapping in the report and
  confirms it. *Done-when:* signed off.
- [ ] **1.5 Limitations completeness** — he confirms the report's "out of scope / engineer must
  verify" block omits nothing dangerous. *Done-when:* signed off.
- [ ] **1.6 Wind decision** — after 1.1, decide whether to flip the wind checks from **advisory**
  back to **gating** + turn `design(autosize_for_wind=True)` on (and whether SLS-2 sway should
  gate). See `SESSION_HANDOFF.md` → Wind section. *(This is a code change the technical co-founder
  makes once the engineer decides — it's the only remaining code item, and it's blocked on his
  judgement.)*

> When **1.1 + 1.2** are signed off, the engineering green light is given. Combine that with the
> founder's go-live phases (`GO_LIVE.md`) and you have a production-ready MVP.
