# standards/ — Source standards (LOCAL ONLY — git-ignored)

The official SANS standards + design guide we transcribe the kernel's code values from. Kept here
so they're always accessible to the project's tooling and don't get lost.

## ⚠️ The PDFs are intentionally NOT committed
- **Copyright:** these are © SABS licensed copies ("…no copy may be reproduced…"). Committing or
  pushing them is unauthorised redistribution.
- **Size:** the steelwork guide (~162 MB) exceeds GitHub's 100 MB hard limit — the push would fail.

They are git-ignored via `.gitignore` (`standards/*.pdf`). **Keep your own backup** of the originals
(e.g. a private cloud drive) — git will not back these up. This README (the manifest) *is* committed,
so the project always documents what belongs here.

We **transcribe specific values** into the kernel with clause/table citations (see `docs/SOURCES.md`)
and validate against the standards' own tables where possible — we never redistribute the documents.

## Manifest (received 2026-06-10)
| File | Pages | What it is | Status / caveat |
|---|---|---|---|
| `SANS 10160-3.pdf` | 95 | **SANS 10160-3:2019 Ed 2.1** — Wind actions | ✅ Official (ISBN). Used in 1.6a; validated vs its Table 3. |
| `SANS 10162-1.pdf` | 109 | **SANS 10162-1:2011 Ed 2.1** — Steel design | ✅ Official (ISBN). For 1.10 member checks. |
| `SANS 10160-1.pdf` | 85 | **SANS 10160-1:2011 Ed 1.1 (+ Amdt 1)** — Basis of design / load combinations | ✅ Official (ISBN 978-0-626-26428-4), obtained 2026-06-15 — replaced the earlier draft. Combination factors (Table 3 / Table 2 / eq. 6/7/10) verified — see SOURCES E9. |
| `SANS 10160-2.pdf` | 38 | **SANS 10160-2:2011 Ed 1.1** — Self-weight & imposed loads | Genuine SABS content (ISBN 978-0-626-26429-1) wrapped in a **Studocu re-host** — licensing copy is a separate procurement item. Imposed roof 0.4 kN/m² (E2) independently corroborated; clause read pending. |
| `Design of Structural Steelwork to SANS 10162.pdf` | 575 | Design guide / worked examples | ⚠️ Likely **scanned** (no text layer on p.1); needs OCR to use. Not the 4th edition. |
| `SANS 10100-1.pdf` | 214 | **SANS 10100-1 (SABS 0100-1 Ed. 2.2)** — Structural use of concrete, Part 1: Design (BS 8110 basis) | ✅ Official (ISBN 0-626-12497-2). Received 2026-06-11. Used in **1.17 pad footings** — flexure 4.3.3, shear 4.3.4 (vc eq. 2, v_max 4.3.4.1), bases 4.10, min steel 4.11.4. Clauses read & transcribed. |
| `EN 10025-2.pdf` | 45 | **BS EN 10025-2:2019** — Hot rolled structural steels, Part 2 (non-alloy) | Genuine BSI/CEN content (ISBN 978 0 580 73966 8), obtained 2026-06-15 via a **re-host** (Studocu wrapper) — licensing copy is a separate procurement item. Used for **fy** (Table 6): S355JR/S275JR yield by thickness **verified** — see SOURCES fy row. |

## How the kernel uses these
Values are extracted **programmatically** (exact text, never eyeballed), each **cited by clause/table**
in `docs/SOURCES.md`, and validated against the standard's own tables where one exists. **Final
registered-engineer sign-off** of every transcribed value is required before the Phase 8 validation gate.
