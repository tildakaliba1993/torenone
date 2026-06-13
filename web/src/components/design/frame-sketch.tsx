/**
 * Live elevation sketch of the single-bay portal frame (Task 6.5) drawn from
 * the editable geometry, so the engineer sees what they're confirming. Pure
 * geometry — apex height = eaves + (span/2)·tan(pitch). No engineering numbers.
 */
export function FrameSketch({
  span,
  eaves,
  pitch,
}: {
  span: number;
  eaves: number;
  pitch: number;
}) {
  const valid =
    Number.isFinite(span) &&
    Number.isFinite(eaves) &&
    Number.isFinite(pitch) &&
    span > 0 &&
    eaves > 0 &&
    pitch > 0 &&
    pitch <= 45;

  if (!valid) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-md border border-dashed border-border text-sm text-subtle">
        Enter span, eaves height and pitch to preview the frame.
      </div>
    );
  }

  const W = 340;
  const H = 200;
  const margin = 34;
  const apex = eaves + (span / 2) * Math.tan((pitch * Math.PI) / 180);

  const scale = Math.min((W - 2 * margin) / span, (H - 2 * margin) / apex);
  const ox = margin + ((W - 2 * margin) - span * scale) / 2;
  const oy = H - margin;
  const px = (x: number) => ox + x * scale;
  const py = (y: number) => oy - y * scale;

  const frame = [
    [px(0), py(0)],
    [px(0), py(eaves)],
    [px(span / 2), py(apex)],
    [px(span), py(eaves)],
    [px(span), py(0)],
  ]
    .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");

  function base(x: number) {
    const bx = px(x);
    const by = py(0);
    return `${bx - 6},${by + 8} ${bx + 6},${by + 8} ${bx},${by}`;
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`Portal frame elevation: ${span} m span, ${eaves} m eaves, ${pitch}° pitch`}
      className="w-full"
    >
      <line
        x1={px(0)}
        y1={py(0)}
        x2={px(span)}
        y2={py(0)}
        stroke="var(--border-strong)"
        strokeDasharray="3 3"
      />
      <polyline
        points={frame}
        fill="none"
        stroke="var(--accent)"
        strokeWidth={2.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <polygon points={base(0)} fill="var(--text-muted)" />
      <polygon points={base(span)} fill="var(--text-muted)" />
      <text x={px(span / 2)} y={py(0) + 24} textAnchor="middle" fontSize="11" fill="var(--text-muted)">
        {span} m
      </text>
      <text
        x={px(0) - 10}
        y={py(eaves / 2)}
        textAnchor="end"
        dominantBaseline="middle"
        fontSize="11"
        fill="var(--text-muted)"
      >
        {eaves} m
      </text>
      <text
        x={px(span / 2)}
        y={py(apex) - 8}
        textAnchor="middle"
        fontSize="11"
        fill="var(--text-subtle)"
      >
        {pitch}°
      </text>
    </svg>
  );
}
