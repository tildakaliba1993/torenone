import { LogoMark } from "@/components/brand/logo";

/**
 * Animated hero graphic: a stylised TorenOne "design" window showing the product flow —
 * a plain-English brief → the deterministic SANS kernel → a stamp-ready calc package
 * (checks pass, member sections, a bending-moment sketch, PDF + tonnage/cost). It conveys
 * exactly what a user gets out of the product. Pure CSS animation (staggered fade-up +
 * gentle float), no JS — respects prefers-reduced-motion.
 */
function Row({ children, delay }: { children: React.ReactNode; delay: number }) {
  return (
    <div className="animate-fade-up" style={{ animationDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

export function ProductPreview() {
  return (
    <div className="relative w-full">
      {/* Ambient glow behind the card */}
      <div
        aria-hidden
        className="bg-accent/20 pointer-events-none absolute -inset-6 -z-10 rounded-[2rem] blur-3xl"
      />

      <div className="animate-float border-border bg-surface w-full rounded-2xl border shadow-2xl">
        {/* Window chrome */}
        <div className="border-border/70 flex items-center gap-2 border-b px-4 py-3">
          <span className="bg-danger/70 size-3 rounded-full" />
          <span className="bg-warning/70 size-3 rounded-full" />
          <span className="bg-success/70 size-3 rounded-full" />
          <span className="text-subtle ml-2 flex items-center gap-1.5 font-mono text-xs">
            <LogoMark className="h-3.5 w-auto" aria-hidden />
            TorenOne · new design
          </span>
        </div>

        <div className="flex flex-col gap-4 p-5">
          {/* The brief (what the engineer types) */}
          <Row delay={80}>
            <div className="border-border bg-surface-raised rounded-xl border p-3">
              <p className="text-subtle mb-1 text-[11px] tracking-wide uppercase">Describe</p>
              <p className="text-foreground text-sm leading-relaxed">
                15&nbsp;m span warehouse, 5&nbsp;m eaves, 8° pitch, 6&nbsp;m bays, wind 36&nbsp;m/s,
                terrain B
                <span className="bg-accent animate-blink ml-0.5 inline-block h-4 w-[2px] translate-y-0.5" />
              </p>
            </div>
          </Row>

          {/* Kernel status */}
          <Row delay={420}>
            <div className="text-muted flex items-center gap-2 px-1 text-xs">
              <span className="bg-accent size-2 animate-pulse rounded-full" />
              Computed by the deterministic SANS kernel — every value cited to a clause
            </div>
          </Row>

          {/* The result */}
          <Row delay={620}>
            <div className="border-border bg-surface-raised flex flex-col gap-3 rounded-xl border p-4">
              <div className="flex items-center justify-between">
                <span className="bg-success/15 text-success inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium">
                  ✓ All checks pass
                </span>
                <span className="text-muted font-mono text-xs">Governing 0.88</span>
              </div>

              <FrameSketch />

              <div className="flex flex-wrap gap-2">
                <Chip label="Rafter" value="IPE-AA 140" />
                <Chip label="Column" value="203×133×30" />
              </div>

              <div className="border-border/60 flex items-center justify-between border-t pt-3">
                <span className="text-foreground flex items-center gap-2 text-sm font-medium">
                  <PdfGlyph />
                  Calc package PDF
                </span>
                <span className="text-muted font-mono text-xs">3.8 t · R 6,080</span>
              </div>
            </div>
          </Row>
        </div>
      </div>
    </div>
  );
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span className="border-border bg-surface inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs">
      <span className="text-subtle">{label}</span>
      <span className="text-foreground font-mono">{value}</span>
    </span>
  );
}

/** A small portal-frame elevation with a light bending-moment curve under the roof. */
function FrameSketch() {
  return (
    <svg viewBox="0 0 320 130" role="img" aria-label="Portal frame with bending-moment diagram" className="w-full">
      {/* bending-moment fill under the rafters (sagging) */}
      <path
        d="M40 38 Q160 96 280 38 L280 44 Q160 104 40 44 Z"
        fill="var(--accent)"
        opacity="0.18"
      />
      <path d="M40 38 Q160 96 280 38" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.5" />
      {/* frame outline: columns + duopitch roof */}
      <polyline
        points="40,110 40,38 160,18 280,38 280,110"
        fill="none"
        stroke="var(--accent)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* pinned bases */}
      <polygon points="33,118 47,118 40,110" fill="var(--text-muted)" />
      <polygon points="273,118 287,118 280,110" fill="var(--text-muted)" />
      <line x1="30" y1="118" x2="290" y2="118" stroke="var(--border-strong)" strokeDasharray="3 3" />
    </svg>
  );
}

function PdfGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="text-accent size-4" fill="none" aria-hidden>
      <path
        d="M7 3h7l4 4v14H7zM14 3v4h4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M12 11v6m0 0 2.2-2.2M12 17l-2.2-2.2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
