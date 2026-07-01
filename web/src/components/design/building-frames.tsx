import type { RoofType } from "@/lib/api/service";

/**
 * A light pseudo-3D picture of the whole building: its row of identical portal frames marching back
 * along the length, tied by ridge + eaves lines. Turns "5 frames @ 6 m" into something you can see.
 *
 * Pure geometry from confirmed inputs — no engineering number. Used on the results page and in the
 * layout comparison so a framing choice reads as a building, not a row of numbers.
 */
export function BuildingFrames({
  numberOfFrames,
  span,
  eaves,
  pitch,
  roofType = "duopitch",
  baySpacingM,
  className,
}: {
  numberOfFrames: number;
  span: number;
  eaves: number;
  pitch: number;
  roofType?: RoofType;
  baySpacingM?: number;
  className?: string;
}) {
  const valid =
    Number.isFinite(span) && Number.isFinite(eaves) && Number.isFinite(pitch) &&
    span > 0 && eaves > 0 && numberOfFrames >= 1;
  if (!valid) return null;

  const mono = roofType === "monopitch";
  const apex = eaves + (span / 2) * Math.tan((pitch * Math.PI) / 180);
  const highEaves = eaves + span * Math.tan((pitch * Math.PI) / 180);
  const topH = mono ? highEaves : apex;

  // Frame outline in local metres (base→eaves→ridge→eaves→base). Mono-pitch: single slope.
  const outline: [number, number][] = mono
    ? [
        [0, 0], [0, eaves], [span, highEaves], [span, 0],
      ]
    : [
        [0, 0], [0, eaves], [span / 2, apex], [span, eaves], [span, 0],
      ];

  // Cap how many frames we actually draw (readability + perf); the caption carries the true count.
  const drawn = Math.min(numberOfFrames, 10);

  // Screen scale: fit the front frame into a comfortable box, leave room for the receding depth.
  const boxW = 360;
  const frameScale = boxW / span;
  const depthPerFrame = Math.min(34, 240 / Math.max(1, drawn - 1)); // total depth bounded
  const dx = depthPerFrame * 0.9;
  const dy = depthPerFrame * 0.5;

  const totalW = span * frameScale + (drawn - 1) * dx + 40;
  const totalH = topH * frameScale + (drawn - 1) * dy + 40;
  const ox = 20;
  const oy = totalH - 20;

  // Project a local (metre) point on frame index i (0 = front) to screen.
  const proj = (x: number, y: number, i: number): [number, number] => [
    ox + x * frameScale + i * dx,
    oy - y * frameScale - i * dy,
  ];

  const outlinePoints = (i: number): string =>
    outline.map(([x, y]) => proj(x, y, i).map((v) => v.toFixed(1)).join(",")).join(" ");

  // Key points to tie front→back (ridge + both eaves) so the roof reads as planes.
  const tiePoints: [number, number][] = mono
    ? [[0, eaves], [span, highEaves]]
    : [[0, eaves], [span / 2, apex], [span, eaves]];

  return (
    <div className={className}>
      <svg
        viewBox={`0 0 ${totalW.toFixed(0)} ${totalH.toFixed(0)}`}
        role="img"
        aria-label={`Building of ${numberOfFrames} portal frames`}
        className="animate-fade-in w-full"
      >
        {/* depth ties (drawn first, behind the frames) */}
        {tiePoints.map((p, k) => {
          const [fx, fy] = proj(p[0], p[1], 0);
          const [bx, by] = proj(p[0], p[1], drawn - 1);
          return (
            <line
              key={`tie-${k}`}
              x1={fx}
              y1={fy}
              x2={bx}
              y2={by}
              stroke="var(--border-strong)"
              strokeWidth={1}
            />
          );
        })}
        {/* frames: back → front, so nearer frames overlap and read as closer */}
        {Array.from({ length: drawn }).map((_, idx) => {
          const i = drawn - 1 - idx; // draw back first
          const isFront = i === 0;
          const opacity = 0.35 + 0.65 * (1 - i / Math.max(1, drawn - 1));
          return (
            <polyline
              key={i}
              points={outlinePoints(i)}
              pathLength={1}
              className="animate-draw"
              style={{ animationDelay: `${(drawn - 1 - i) * 80}ms` }}
              fill="none"
              stroke={isFront ? "var(--accent)" : "var(--primary)"}
              strokeWidth={isFront ? 2.6 : 1.6}
              strokeOpacity={opacity}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          );
        })}
      </svg>
      <p className="text-subtle mt-1 text-center text-xs">
        {numberOfFrames} portal frames{baySpacingM ? ` @ ${baySpacingM.toFixed(2)} m` : ""}
        {numberOfFrames > drawn ? " (showing 10)" : ""}
      </p>
    </div>
  );
}
