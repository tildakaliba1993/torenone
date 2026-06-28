/**
 * Public Red Book benchmark data shown on /validation.
 *
 * These are our deterministic kernel's COMPUTED values placed beside the published values in the
 * SAISC *Southern African Steel Construction Handbook* ("Red Book", 8th ed. 2013). Every row is
 * backed by an automated, must-pass test in `kernel/tests/validation/redbook/` (43 checks) — this
 * table is a curated, human-readable selection of those results. Only numeric facts are reproduced
 * (no Red Book text/tables). Scope is the member-level gravity design path; see REDBOOK_SCOPE.
 */

export interface BenchmarkRow {
  /** What was checked + the Red Book example/table reference. */
  check: string;
  /** Published Red Book value. */
  redbook: string;
  /** TorenOne kernel's computed value. */
  kernel: string;
  /** Difference (rounded) or "match". */
  delta: string;
}

export interface BenchmarkGroup {
  title: string;
  basis: string;
  rows: BenchmarkRow[];
}

export const REDBOOK_GROUPS: BenchmarkGroup[] = [
  {
    title: "Section properties",
    basis: "Red Book Tables 2.9 / 2.10 — 11 sections checked (≤ 1%)",
    rows: [
      { check: "IPE 200 — area A", redbook: "2 850 mm²", kernel: "2 850 mm²", delta: "match" },
      { check: "IPE 200 — second moment Iₓ", redbook: "19.4 ×10⁶ mm⁴", kernel: "19.4 ×10⁶ mm⁴", delta: "match" },
      { check: "203×203×46 UC — area A", redbook: "5 880 mm²", kernel: "5 880 mm²", delta: "match" },
      { check: "254×254×73 UC — plastic modulus Zₓ", redbook: "990 ×10³ mm³", kernel: "990 ×10³ mm³", delta: "match" },
    ],
  },
  {
    title: "Axial compression resistance, Cr",
    basis: "SANS 10162-1 cl. 13.3.1 · Red Book Ch 4 (Ex 4.1, 4.3)",
    rows: [
      { check: "203×133×30, KL = 2 000 mm (Ex 4.1)", redbook: "834 kN", kernel: "842 kN", delta: "+1.0%" },
      { check: "305×305×118, Crx, KL = 3 700 mm (Ex 4.3)", redbook: "4 510 kN", kernel: "4 506 kN", delta: "−0.1%" },
      { check: "305×305×118, Cry, KL = 3 700 mm (Ex 4.3)", redbook: "3 890 kN", kernel: "3 894 kN", delta: "+0.1%" },
    ],
  },
  {
    title: "Bending & lateral-torsional buckling, Mr",
    basis: "SANS 10162-1 cl. 13.5 / 13.6 · Red Book Ch 4–5 (Ex 4.3, 5.1, 5.2)",
    rows: [
      { check: "305×305×118 — laterally supported Mrx (Ex 4.3)", redbook: "614 kN·m", kernel: "614 kN·m", delta: "match" },
      { check: "305×305×118 — laterally supported Mry (Ex 4.3)", redbook: "281 kN·m", kernel: "281 kN·m", delta: "match" },
      { check: "533×210×122 — critical LTB moment Mcr, KL = 5 m (Ex 5.2)", redbook: "1 625 kN·m", kernel: "1 626 kN·m", delta: "+0.1%" },
      { check: "533×210×122 — LTB resistance Mr, KL = 5 m (Ex 5.2)", redbook: "929 kN·m", kernel: "936 kN·m", delta: "+0.8%" },
      { check: "533×210×122 — LTB resistance Mr, KL = 10 m (Ex 5.1)", redbook: "317 kN·m", kernel: "317 kN·m", delta: "match" },
    ],
  },
  {
    title: "Section classification",
    basis: "SANS 10162-1 cl. 11 · Red Book §5.1.3 / Table 5.3 — 15 sections, all exact",
    rows: [
      { check: "152×152×23 H — in flexure", redbook: "Class 4", kernel: "Class 4 (rejected)", delta: "match" },
      { check: "203×203×46 H — in flexure", redbook: "Class 3", kernel: "Class 3", delta: "match" },
      { check: "305×305×97 H — in flexure", redbook: "Class 3", kernel: "Class 3", delta: "match" },
      { check: "305×305×118 H — in flexure", redbook: "Class 2", kernel: "Class 2", delta: "match" },
    ],
  },
  {
    title: "Shear resistance, Vr",
    basis: "SANS 10162-1 cl. 13.4.1.1 · Red Book Ch 5 (Ex 5.3)",
    rows: [
      { check: "533×210×82 — web shear (Ex 5.3)", redbook: "1 050 kN", kernel: "1 040 kN", delta: "−1.0%" },
    ],
  },
  {
    title: "Bolt resistances",
    basis: "SANS 10162-1 cl. 13.10 / 13.12 · Red Book Table 7.2 — M16–M30, Class 8.8 & 10.9",
    rows: [
      { check: "M20 8.8 — tension", redbook: "156 kN", kernel: "156 kN", delta: "match" },
      { check: "M20 8.8 — shear (1 plane, threads incl.)", redbook: "87.6 kN", kernel: "87.6 kN", delta: "match" },
      { check: "M24 8.8 — tension", redbook: "225 kN", kernel: "225 kN", delta: "match" },
      { check: "M30 8.8 — tension", redbook: "352 kN", kernel: "352 kN", delta: "match" },
      { check: "M20 10.9 — tension", redbook: "196 kN", kernel: "196 kN", delta: "match" },
    ],
  },
];

export const REDBOOK_SUMMARY = {
  checks: 43,
  reference: "SAISC Southern African Steel Construction Handbook (Red Book), 8th ed. 2013",
} as const;

/** Honest scope — what the benchmark does and does not cover. */
export const REDBOOK_SCOPE = {
  covered:
    "Member-level gravity design: section properties, axial compression, bending & lateral-torsional buckling, section classification, shear, and bolt resistances.",
  ongoing:
    "Connection detailing (baseplates, moment end-plates), beam-column interaction at frame level, and wind effects are under continued validation and registered-engineer sign-off.",
} as const;
