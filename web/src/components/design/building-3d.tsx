"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";
import type { CheckResult, FrameSpec, SectionChoice } from "@/lib/api/service";

/**
 * Code-split entry point for the WebGL building model. `ssr: false` + dynamic import keeps three.js
 * out of every other page's bundle and off the server, so it never blocks first paint — a skeleton
 * shows while the (heavy) 3D chunk streams in, honouring the "must feel fast" bar.
 */
const Model = dynamic(() => import("./building-model-3d"), {
  ssr: false,
  loading: () => <Skeleton className="h-[360px] w-full rounded-lg sm:h-[440px]" />,
});

export function Building3D(props: {
  spec: FrameSpec;
  sections: SectionChoice[];
  checks: CheckResult[];
  uniformUtil?: number | null;
  onSelect?: (kind: "column" | "internal column" | "rafter") => void;
  className?: string;
}) {
  return <Model {...props} />;
}
