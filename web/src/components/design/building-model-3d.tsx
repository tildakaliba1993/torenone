"use client";

import { useMemo, useState } from "react";

import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import * as THREE from "three";

import type { CheckResult, FrameSpec, SectionChoice } from "@/lib/api/service";

/**
 * Interactive WebGL 3D model of the whole portal-framed building — drag to orbit, hover a member to
 * inspect it. Members are coloured by their governing utilisation. Every value shown traces to the
 * validated kernel (geometry from the spec; utilisation + governing check read off the kernel's
 * checks): a code-true, explorable audit of the design, not decorative 3D. Pure presentation (🟢).
 *
 * Heavy (three.js) — imported only via a dynamic() wrapper (BuildingModel3DLazy) so it never loads
 * on other pages and never blocks first paint.
 */

type MemberKind = "column" | "rafter";
type Band = "ok" | "tight" | "over" | "unknown";

const BAND_COLOR: Record<Band, string> = {
  ok: "#3fb950",
  tight: "#d6a02a",
  over: "#f85149",
  unknown: "#3a4452",
};

function band(util: number | null): Band {
  if (util == null) return "unknown";
  if (util > 1.0) return "over";
  if (util >= 0.85) return "tight";
  return "ok";
}

interface Segment {
  a: THREE.Vector3;
  b: THREE.Vector3;
  kind: MemberKind;
}

interface MemberMeta {
  kind: MemberKind;
  designation: string | null;
  util: number | null;
  check: CheckResult | null;
}

function governingCheck(checks: CheckResult[], kind: MemberKind): CheckResult | null {
  const own = checks.filter((c) => !c.informational && c.name.toLowerCase().startsWith(`${kind}:`));
  if (own.length === 0) return null;
  return own.reduce((max, c) => (c.utilisation > max.utilisation ? c : max));
}

function buildGeometry(spec: FrameSpec) {
  const g = spec.geometry;
  const span = g.span_m;
  const eaves = g.eaves_height_m;
  const pitch = g.roof_pitch_deg;
  const mono = g.roof_type === "monopitch";
  const bays = g.number_of_bays;
  const spacing = g.bay_spacing_m;
  const nFrames = Math.min(bays + 1, 41); // safety cap on mesh count
  const length = spacing * bays;

  const apex = eaves + (span / 2) * Math.tan((pitch * Math.PI) / 180);
  const highEaves = eaves + span * Math.tan((pitch * Math.PI) / 180);
  const topH = mono ? highEaves : apex;

  const hx = span / 2;
  const v = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

  const segments: Segment[] = [];
  const zAt = (i: number) => -length / 2 + i * spacing;

  for (let i = 0; i < nFrames; i++) {
    const z = zAt(i);
    // columns
    segments.push({ a: v(-hx, 0, z), b: v(-hx, eaves, z), kind: "column" });
    segments.push({ a: v(hx, 0, z), b: v(hx, mono ? highEaves : eaves, z), kind: "column" });
    // rafters
    if (mono) {
      segments.push({ a: v(-hx, eaves, z), b: v(hx, highEaves, z), kind: "rafter" });
    } else {
      segments.push({ a: v(-hx, eaves, z), b: v(0, apex, z), kind: "rafter" });
      segments.push({ a: v(0, apex, z), b: v(hx, eaves, z), kind: "rafter" });
    }
  }

  // Longitudinal ties (ridge + eaves lines) so the frames read as a building.
  const nodes: [number, number][] = mono
    ? [
        [-hx, eaves],
        [hx, highEaves],
      ]
    : [
        [-hx, eaves],
        [0, apex],
        [hx, eaves],
      ];
  const ties = nodes.map(
    ([x, y]) => [v(x, y, zAt(0)), v(x, y, zAt(nFrames - 1))] as [THREE.Vector3, THREE.Vector3],
  );

  const maxDim = Math.max(span, length, topH);
  return {
    segments,
    ties,
    center: new THREE.Vector3(0, topH / 2, 0),
    maxDim,
    length,
    nFrames,
  };
}

function Beam({
  seg,
  color,
  thickness,
  highlighted,
  onOver,
  onOut,
}: {
  seg: Segment;
  color: string;
  thickness: number;
  highlighted: boolean;
  onOver: () => void;
  onOut: () => void;
}) {
  const { position, quaternion, length } = useMemo(() => {
    const dir = new THREE.Vector3().subVectors(seg.b, seg.a);
    const len = dir.length();
    const mid = new THREE.Vector3().addVectors(seg.a, seg.b).multiplyScalar(0.5);
    const quat = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(0, 1, 0),
      dir.clone().normalize(),
    );
    return { position: mid, quaternion: quat, length: len };
  }, [seg]);

  return (
    <mesh
      position={position}
      quaternion={quaternion}
      onPointerOver={(e) => {
        e.stopPropagation();
        onOver();
      }}
      onPointerOut={onOut}
    >
      {/* slightly rectangular section to read as steel */}
      <boxGeometry args={[thickness, length, thickness * 1.4]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={highlighted ? 0.55 : 0.06}
        metalness={0.35}
        roughness={0.5}
      />
    </mesh>
  );
}

function Scene({
  spec,
  sections,
  checks,
  onHover,
}: {
  spec: FrameSpec;
  sections: SectionChoice[];
  checks: CheckResult[];
  onHover: (m: MemberMeta | null) => void;
}) {
  const geo = useMemo(() => buildGeometry(spec), [spec]);
  const [hoveredKind, setHoveredKind] = useState<MemberKind | null>(null);

  const meta: Record<MemberKind, MemberMeta> = useMemo(() => {
    const make = (kind: MemberKind): MemberMeta => ({
      kind,
      designation: sections.find((s) => s.member === kind)?.designation ?? null,
      util: governingCheck(checks, kind)?.utilisation ?? null,
      check: governingCheck(checks, kind),
    });
    return { column: make("column"), rafter: make("rafter") };
  }, [sections, checks]);

  const thickness = Math.max(0.14, geo.maxDim * 0.014);
  const camPos: [number, number, number] = [geo.maxDim * 0.95, geo.maxDim * 0.75, geo.maxDim * 1.25];

  function hover(kind: MemberKind | null) {
    setHoveredKind(kind);
    onHover(kind ? meta[kind] : null);
  }

  return (
    <>
      <PerspectiveCamera makeDefault position={camPos} fov={42} />
      <OrbitControls
        target={geo.center.toArray()}
        enablePan={false}
        autoRotate
        autoRotateSpeed={0.6}
        minDistance={geo.maxDim * 0.6}
        maxDistance={geo.maxDim * 3}
        makeDefault
      />
      <ambientLight intensity={0.65} />
      <directionalLight position={[1, 2, 1.5]} intensity={1.1} />
      <directionalLight position={[-1.5, 1, -1]} intensity={0.35} />

      {/* members */}
      {geo.segments.map((seg, i) => (
        <Beam
          key={i}
          seg={seg}
          color={BAND_COLOR[band(meta[seg.kind].util)]}
          thickness={thickness}
          highlighted={hoveredKind === seg.kind}
          onOver={() => hover(seg.kind)}
          onOut={() => hover(null)}
        />
      ))}

      {/* longitudinal ties */}
      {geo.ties.map((pts, i) => (
        <line key={`tie-${i}`}>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              args={[new Float32Array(pts.flatMap((p) => [p.x, p.y, p.z])), 3]}
            />
          </bufferGeometry>
          <lineBasicMaterial color="#6a7585" />
        </line>
      ))}

      {/* ground grid for context */}
      <gridHelper
        args={[geo.maxDim * 4, 24, "#29313c", "#20272f"]}
        position={[0, 0, 0]}
      />
    </>
  );
}

export default function BuildingModel3D({
  spec,
  sections,
  checks,
  className,
}: {
  spec: FrameSpec;
  sections: SectionChoice[];
  checks: CheckResult[];
  className?: string;
}) {
  const [hovered, setHovered] = useState<MemberMeta | null>(null);
  const g = spec.geometry;
  const valid =
    Number.isFinite(g?.span_m) && Number.isFinite(g?.eaves_height_m) && g?.span_m > 0;
  if (!valid) return null;

  return (
    <div className={className}>
      <div className="border-border bg-surface-raised relative h-[360px] w-full overflow-hidden rounded-lg border sm:h-[440px]">
        <Canvas dpr={[1, 2]} gl={{ antialias: true }}>
          <color attach="background" args={["#0e1116"]} />
          <Scene spec={spec} sections={sections} checks={checks} onHover={setHovered} />
        </Canvas>

        {/* hover inspector overlay */}
        <div className="pointer-events-none absolute left-3 top-3 rounded-md border border-border bg-surface/90 px-3 py-2 text-xs backdrop-blur">
          {hovered ? (
            <div className="flex flex-col gap-0.5">
              <span className="text-foreground font-medium capitalize">
                {hovered.kind} · {hovered.designation ?? "—"}
              </span>
              {hovered.check ? (
                <span className="text-muted">
                  {hovered.check.name} ({hovered.check.clause}) —{" "}
                  <span className="text-foreground tabular-nums">
                    {Math.round(hovered.check.utilisation * 100)}%
                  </span>
                </span>
              ) : (
                <span className="text-subtle">No governing check</span>
              )}
            </div>
          ) : (
            <span className="text-subtle">Drag to orbit · hover a member to inspect</span>
          )}
        </div>
      </div>
    </div>
  );
}
