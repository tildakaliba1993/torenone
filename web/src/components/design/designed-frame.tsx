"use client";

import { useState } from "react";

import type { CheckResult, FrameSpec, SectionChoice } from "@/lib/api/service";
import { cn } from "@/lib/utils";

/**
 * The "hero" visual of a completed design: the actual portal frame drawn to scale, with each member
 * coloured by how hard it's working (its governing utilisation) and labelled with the chosen section.
 * One glance answers "what did we design, and where is it tight?".
 *
 * Pure presentation of kernel outputs — geometry from the spec, per-member utilisation read off the
 * kernel's checks (names are prefixed "column:"/"rafter:"). No engineering number is computed here.
 */

type Band = "ok" | "tight" | "over" | "unknown";

function band(util: number | null): Band {
  if (util == null) return "unknown";
  if (util > 1.0) return "over";
  if (util >= 0.85) return "tight";
  return "ok";
}

const BAND_COLOR: Record<Band, string> = {
  ok: "var(--success)",
  tight: "var(--warning)",
  over: "var(--danger)",
  unknown: "var(--border-strong)",
};

type MemberKind = "column" | "rafter";

/** The governing (max-utilisation) gating check for a member, read off the kernel's check names. */
function governingCheck(checks: CheckResult[], member: MemberKind): CheckResult | null {
  const own = checks.filter(
    (c) => !c.informational && c.name.toLowerCase().startsWith(`${member}:`),
  );
  return own.length ? own.reduce((m, c) => (c.utilisation > m.utilisation ? c : m)) : null;
}

function designationFor(sections: SectionChoice[], member: string): string | null {
  return sections.find((s) => s.member === member)?.designation ?? null;
}

interface DrawMember {
  a: [number, number]; // world metres
  b: [number, number];
  kind: MemberKind;
  util: number | null;
  designation: string | null;
}

export function DesignedFrame({
  spec,
  sections,
  checks,
}: {
  spec: FrameSpec;
  sections: SectionChoice[];
  checks: CheckResult[];
}) {
  const [hovered, setHovered] = useState<MemberKind | null>(null);

  const g = spec.geometry;
  const span = g.span_m;
  const eaves = g.eaves_height_m;
  const pitch = g.roof_pitch_deg;
  const monopitch = g.roof_type === "monopitch";

  const valid =
    Number.isFinite(span) && Number.isFinite(eaves) && Number.isFinite(pitch) && span > 0 && eaves > 0;
  if (!valid) return null;

  const rise = (span / 2) * Math.tan((pitch * Math.PI) / 180);
  const apex = eaves + rise; // duopitch ridge height
  const highEaves = eaves + span * Math.tan((pitch * Math.PI) / 180); // monopitch high side
  const topH = monopitch ? highEaves : apex;

  const colCheck = governingCheck(checks, "column");
  const rafCheck = governingCheck(checks, "rafter");
  const colUtil = colCheck?.utilisation ?? null;
  const rafUtil = rafCheck?.utilisation ?? null;
  const colSec = designationFor(sections, "column");
  const rafSec = designationFor(sections, "rafter");

  const members: DrawMember[] = monopitch
    ? [
        { a: [0, 0], b: [0, eaves], kind: "column", util: colUtil, designation: colSec },
        { a: [span, 0], b: [span, highEaves], kind: "column", util: colUtil, designation: colSec },
        { a: [0, eaves], b: [span, highEaves], kind: "rafter", util: rafUtil, designation: rafSec },
      ]
    : [
        { a: [0, 0], b: [0, eaves], kind: "column", util: colUtil, designation: colSec },
        { a: [span, 0], b: [span, eaves], kind: "column", util: colUtil, designation: colSec },
        { a: [0, eaves], b: [span / 2, apex], kind: "rafter", util: rafUtil, designation: rafSec },
        { a: [span / 2, apex], b: [span, eaves], kind: "rafter", util: rafUtil, designation: rafSec },
      ];

  const W = 560;
  const H = 320;
  const margin = 52;
  const scale = Math.min((W - 2 * margin) / span, (H - 2 * margin) / topH);
  const ox = margin + (W - 2 * margin - span * scale) / 2;
  const oy = H - margin;
  const px = (x: number) => ox + x * scale;
  const py = (y: number) => oy - y * scale;

  function baseTri(x: number) {
    const bx = px(x);
    const by = py(0);
    return `${bx - 8},${by + 10} ${bx + 8},${by + 10} ${bx},${by}`;
  }

  // Roof surface height (metres) at plan position x — for placing the gravity load arrows.
  function roofY(x: number): number {
    if (monopitch) return eaves + x * Math.tan((pitch * Math.PI) / 180);
    return x <= span / 2
      ? eaves + x * Math.tan((pitch * Math.PI) / 180)
      : eaves + (span - x) * Math.tan((pitch * Math.PI) / 180);
  }
  const arrowXs = [0.1, 0.3, 0.5, 0.7, 0.9].map((f) => f * span);

  return (
    <div className="flex flex-col gap-3">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Designed portal frame, members coloured by utilisation"
        className="animate-fade-in w-full"
      >
        {/* ground line */}
        <line
          x1={px(0)}
          y1={py(0)}
          x2={px(span)}
          y2={py(0)}
          stroke="var(--border-strong)"
          strokeDasharray="3 3"
        />
        {/* gravity load arrows above the roof (dead + imposed act downward) */}
        <g stroke="var(--text-subtle)" strokeWidth={1.25} opacity={0.7}>
          {arrowXs.map((x, i) => {
            const sx = px(x);
            const top = py(roofY(x)) - 24;
            const tip = py(roofY(x)) - 7;
            return (
              <g key={i}>
                <line x1={sx} y1={top} x2={sx} y2={tip} />
                <polyline
                  points={`${sx - 3},${tip - 4} ${sx},${tip} ${sx + 3},${tip - 4}`}
                  fill="none"
                />
              </g>
            );
          })}
        </g>
        {/* members, coloured by utilisation, drawn in on mount; hover to inspect */}
        {members.map((m, i) => (
          <line
            key={i}
            pathLength={1}
            className="animate-draw cursor-pointer"
            style={{ animationDelay: `${i * 90}ms` }}
            x1={px(m.a[0])}
            y1={py(m.a[1])}
            x2={px(m.b[0])}
            y2={py(m.b[1])}
            stroke={BAND_COLOR[band(m.util)]}
            strokeWidth={hovered === m.kind ? 10 : 7}
            strokeOpacity={hovered && hovered !== m.kind ? 0.45 : 1}
            strokeLinecap="round"
            onPointerEnter={() => setHovered(m.kind)}
            onPointerLeave={() => setHovered(null)}
          />
        ))}
        {/* pinned bases */}
        <polygon points={baseTri(0)} fill="var(--text-muted)" />
        <polygon points={baseTri(span)} fill="var(--text-muted)" />
        {/* member designation labels */}
        {colSec ? (
          <text
            x={px(0) - 12}
            y={py(eaves / 2)}
            textAnchor="middle"
            fontSize="11"
            fill="var(--text-muted)"
            transform={`rotate(-90 ${px(0) - 12} ${py(eaves / 2)})`}
          >
            {colSec}
          </text>
        ) : null}
        {rafSec ? (
          <text
            x={px(span / 2)}
            y={py(monopitch ? (eaves + highEaves) / 2 : apex) - 12}
            textAnchor="middle"
            fontSize="11"
            fill="var(--text-muted)"
          >
            {rafSec}
          </text>
        ) : null}
        {/* span dimension */}
        <text x={px(span / 2)} y={py(0) + 30} textAnchor="middle" fontSize="11" fill="var(--text-subtle)">
          {span} m span
        </text>
      </svg>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <MemberRow
          kind="column"
          designation={colSec}
          check={colCheck}
          hovered={hovered}
          onHover={setHovered}
        />
        <MemberRow
          kind="rafter"
          designation={rafSec}
          check={rafCheck}
          hovered={hovered}
          onHover={setHovered}
        />
      </div>
      <Legend />
    </div>
  );
}

function MemberRow({
  kind,
  designation,
  check,
  hovered,
  onHover,
}: {
  kind: MemberKind;
  designation: string | null;
  check: CheckResult | null;
  hovered: MemberKind | null;
  onHover: (k: MemberKind | null) => void;
}) {
  const util = check?.utilisation ?? null;
  const active = hovered === kind;
  return (
    <div
      onPointerEnter={() => onHover(kind)}
      onPointerLeave={() => onHover(null)}
      className={cn(
        "border-border flex cursor-pointer flex-col gap-0.5 rounded-md border p-3 text-sm transition-colors",
        active ? "border-accent bg-surface-raised" : "bg-surface",
      )}
    >
      <div className="flex items-center gap-2">
        <span
          className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
          style={{ backgroundColor: BAND_COLOR[band(util)] }}
        />
        <span className="text-muted w-16 shrink-0 capitalize">{kind}</span>
        <span className="text-foreground font-mono">{designation ?? "—"}</span>
        <span className="text-muted ml-auto tabular-nums">
          {util != null ? `${Math.round(util * 100)}%` : "—"}
        </span>
      </div>
      {check ? (
        <p className="text-subtle pl-4 text-xs">
          Governed by {check.name.replace(/^[^:]+:\s*/, "")} ({check.clause})
        </p>
      ) : null}
    </div>
  );
}

function Legend() {
  const items: { band: Band; label: string }[] = [
    { band: "ok", label: "Comfortable (< 85%)" },
    { band: "tight", label: "Working hard (85–100%)" },
    { band: "over", label: "Over capacity (> 100%)" },
  ];
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted">
      <span className="text-subtle">Member utilisation:</span>
      {items.map((it) => (
        <span key={it.band} className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: BAND_COLOR[it.band] }}
          />
          {it.label}
        </span>
      ))}
    </div>
  );
}
