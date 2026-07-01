/**
 * On-screen Bending-Moment + Shear-Force diagrams and stick model (FR-32, §9.1).
 *
 * Renders the kernel's `FrameDiagram` (governing ULS-1 combination) as SVG — the same
 * sampled M/V the PDF draws, brought on-screen before export. Pure presentation: every
 * number originates in the deterministic kernel (DesignResult.diagram); this component
 * only maps world metres → screen and plots the values perpendicular to each member.
 */
import type { FrameDiagram, MemberDiagram } from "@/lib/api/service";

const NODE_ORDER = ["BL", "EL", "AP", "ER", "BR"] as const;

type ValueKey = "moment_knm" | "shear_kn";

interface Panel {
  W: number;
  H: number;
  sx: (x: number) => number;
  sy: (y: number) => number;
}

function unitNormal(m: MemberDiagram): [number, number] {
  const [x0, y0] = m.start;
  const [x1, y1] = m.end;
  const dx = x1 - x0;
  const dy = y1 - y0;
  const len = Math.hypot(dx, dy) || 1;
  // Rotate the member direction +90°: n = (-dy, dx)/|d|.
  return [-dy / len, dx / len];
}

/** Build a screen transform whose world bbox includes the frame AND the offset curves. */
function makePanel(
  diagram: FrameDiagram,
  key: ValueKey,
  maxAbs: number,
  W: number,
  H: number,
): { panel: Panel; offScale: number } {
  const pad = 30;
  const xs: number[] = [];
  const ys: number[] = [];
  for (const n of Object.values(diagram.nodes)) {
    xs.push(n[0]);
    ys.push(n[1]);
  }
  const frameSize = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)) || 1;
  const offScale = maxAbs > 0 ? (0.32 * frameSize) / maxAbs : 0;

  for (const m of diagram.members) {
    const [nx, ny] = unitNormal(m);
    for (const s of m.stations) {
      xs.push(s.x_m + nx * s[key] * offScale);
      ys.push(s.y_m + ny * s[key] * offScale);
    }
  }
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const bw = maxX - minX || 1;
  const bh = maxY - minY || 1;
  const scale = Math.min((W - 2 * pad) / bw, (H - 2 * pad) / bh);
  // Centre the drawing in the panel.
  const ox = pad + ((W - 2 * pad) - bw * scale) / 2;
  const oy = pad + ((H - 2 * pad) - bh * scale) / 2;
  const sx = (x: number) => ox + (x - minX) * scale;
  const sy = (y: number) => H - oy - (y - minY) * scale; // flip Y
  return { panel: { W, H, sx, sy }, offScale };
}

function framePolyline(diagram: FrameDiagram, panel: Panel): string {
  return NODE_ORDER.map((name) => {
    const [x, y] = diagram.nodes[name];
    return `${panel.sx(x).toFixed(1)},${panel.sy(y).toFixed(1)}`;
  }).join(" ");
}

function memberDiagramPath(
  m: MemberDiagram,
  key: ValueKey,
  offScale: number,
  panel: Panel,
): string {
  const [nx, ny] = unitNormal(m);
  const baseline = m.stations.map(
    (s) => `${panel.sx(s.x_m).toFixed(1)},${panel.sy(s.y_m).toFixed(1)}`,
  );
  const curve = m.stations.map((s) => {
    const ox = s.x_m + nx * s[key] * offScale;
    const oy = s.y_m + ny * s[key] * offScale;
    return `${panel.sx(ox).toFixed(1)},${panel.sy(oy).toFixed(1)}`;
  });
  // Closed polygon: baseline forward, curve back.
  return `${baseline[0]} ${curve.join(" ")} ${baseline[baseline.length - 1]}`;
}

function peakLabel(
  diagram: FrameDiagram,
  key: ValueKey,
  offScale: number,
  panel: Panel,
): { x: number; y: number; text: string } | null {
  let best: { v: number; x: number; y: number } | null = null;
  for (const m of diagram.members) {
    const [nx, ny] = unitNormal(m);
    for (const s of m.stations) {
      if (best === null || Math.abs(s[key]) > Math.abs(best.v)) {
        best = {
          v: s[key],
          x: s.x_m + nx * s[key] * offScale * 1.1,
          y: s.y_m + ny * s[key] * offScale * 1.1,
        };
      }
    }
  }
  if (best === null) return null;
  return { x: panel.sx(best.x), y: panel.sy(best.y), text: best.v.toFixed(1) };
}

function DiagramPanel({
  diagram,
  valueKey,
  maxAbs,
  color,
  fill,
  title,
  unit,
}: {
  diagram: FrameDiagram;
  valueKey: ValueKey;
  maxAbs: number;
  color: string;
  fill: string;
  title: string;
  unit: string;
}) {
  const W = 360;
  const H = 240;
  const { panel, offScale } = makePanel(diagram, valueKey, maxAbs, W, H);
  const peak = peakLabel(diagram, valueKey, offScale, panel);
  return (
    <figure className="flex flex-col gap-1">
      <figcaption className="text-xs font-medium text-muted">
        {title} <span className="text-subtle">({unit})</span>
      </figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${title}: peak ${peak ? peak.text : "0"} ${unit}`}
        className="animate-fade-in w-full rounded-md border border-border bg-surface"
      >
        {diagram.members.map((m) => (
          <polygon
            key={m.name}
            points={memberDiagramPath(m, valueKey, offScale, panel)}
            fill={fill}
            stroke={color}
            strokeWidth={1}
            strokeLinejoin="round"
            opacity={0.85}
          />
        ))}
        <polyline
          points={framePolyline(diagram, panel)}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={2}
          strokeLinejoin="round"
        />
        {peak ? (
          <text
            x={peak.x}
            y={peak.y}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="10"
            className="font-mono"
            fill="var(--text)"
          >
            {peak.text}
          </text>
        ) : null}
      </svg>
    </figure>
  );
}

export function FrameDiagrams({ diagram }: { diagram: FrameDiagram }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <DiagramPanel
          diagram={diagram}
          valueKey="moment_knm"
          maxAbs={diagram.max_abs_moment_knm}
          color="var(--accent)"
          fill="color-mix(in srgb, var(--accent) 22%, transparent)"
          title="Bending moment"
          unit="kN·m"
        />
        <DiagramPanel
          diagram={diagram}
          valueKey="shear_kn"
          maxAbs={diagram.max_abs_shear_kn}
          color="var(--warning)"
          fill="color-mix(in srgb, var(--warning) 22%, transparent)"
          title="Shear force"
          unit="kN"
        />
      </div>
      <p className="text-xs text-subtle">
        Governing {diagram.combination}. Diagrams are plotted from the deterministic kernel
        analysis (the same data as the PDF), not AI. The blue outline is the frame stick model.
      </p>
    </div>
  );
}
