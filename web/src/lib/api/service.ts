import { createClient } from "@/lib/supabase/client";

/**
 * Typed client for the FastAPI engineering service (Task 6.4). Mirrors the
 * Pydantic schemas in service/src/torenone_service/schemas.py. Requests are
 * authenticated with the caller's Supabase access token (the service verifies
 * the JWT). No engineering numbers originate here — the kernel/AI own those.
 */
export type ParseStatus = "complete" | "needs_clarification" | "invalid" | "out_of_scope";

export interface ParseAssumption {
  field: string;
  value: boolean | number | string | null;
  note: string;
}

export interface ParseQuestion {
  field: string;
  question: string;
  kind: "missing" | "invalid";
  unit?: string | null;
  options?: string[] | null;
  /** The FrameSpecExtraction field this answer fills — the key sent to /build-spec. */
  input_field?: string | null;
}

/** A flat set of FrameSpecExtraction inputs (read values + clarified answers). */
export type FrameSpecInputs = Record<string, boolean | number | string | null>;

export type RoofType = "duopitch" | "monopitch";

export interface FrameGeometry {
  span_m: number;
  eaves_height_m: number;
  roof_pitch_deg: number;
  bay_spacing_m: number;
  number_of_bays: number;
  roof_type?: RoofType;
  apex_height_m?: number;
  high_eaves_height_m?: number;
  building_length_m?: number;
}

export type TerrainCategory = "A" | "B" | "C" | "D";
export type SteelGrade = "S275JR" | "S355JR";

export interface FrameSpec {
  geometry: FrameGeometry;
  materials?: { steel_grade: SteelGrade };
  base_fixity?: "pinned" | "fixed";
  restraints?: {
    rafter_restraint_spacing_m: number | null;
    column_restraint_spacing_m: number | null;
  };
  dead: { roof_kpa: number; services_kpa: number; wall_cladding_kpa: number };
  imposed?: { roof_access: boolean };
  wind: {
    basic_wind_speed_ms: number;
    terrain_category: TerrainCategory;
    site_altitude_m: number;
    has_dominant_opening: boolean;
  };
  foundation?: { allowable_bearing_kpa: number | null; concrete_fcu_mpa: number };
}

export interface ParseResponse {
  status: ParseStatus;
  spec: FrameSpec | null;
  assumptions: ParseAssumption[];
  questions: ParseQuestion[];
  missing: string[];
  errors: string[];
  scope_note: string | null;
  /** The values already read (keyed by FrameSpecExtraction field) — pre-fills the clarify form. */
  partial?: FrameSpecInputs;
}

/** Raised for any failure talking to the engineering service (network or HTTP). */
export class ServiceError extends Error {}

function serviceBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_ENGINEERING_SERVICE_URL;
  if (!base) throw new ServiceError("The engineering service URL is not configured.");
  return base.replace(/\/$/, "");
}

const SERVICE_MAX_ATTEMPTS = 3;
const SERVICE_RETRY_BASE_MS = 700;

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/**
 * Fetch a service endpoint, transparently retrying ONLY connection-level failures.
 *
 * The engineering service runs scale-to-zero on Fly (`min_machines_running = 0`), so the
 * first call after an idle period must boot the machine (~5–8s) and can briefly reset the
 * connection — surfacing as a thrown `fetch`. A thrown `fetch` means the request never
 * completed server-side, so retrying is safe and cannot double-run a design. Genuine HTTP
 * error statuses are returned unchanged for the caller to interpret (never retried, to
 * avoid duplicating a request the server already processed).
 */
async function serviceFetch(url: string, init: RequestInit): Promise<Response> {
  for (let attempt = 1; attempt <= SERVICE_MAX_ATTEMPTS; attempt++) {
    try {
      return await fetch(url, init);
    } catch {
      if (attempt < SERVICE_MAX_ATTEMPTS) {
        await sleep(SERVICE_RETRY_BASE_MS * attempt);
        continue;
      }
    }
  }
  throw new ServiceError(
    "Couldn’t reach the engineering service — please try again in a moment.",
  );
}

/**
 * Best-effort wake of the scale-to-zero service so the engineer's first real call
 * (parse/design) doesn't pay the cold start. Safe to call on mount — it never throws and
 * ignores the response; any genuine outage still surfaces on the real call.
 */
export async function warmService(): Promise<void> {
  try {
    await fetch(`${serviceBaseUrl()}/health`, { method: "GET", cache: "no-store" });
  } catch {
    // best-effort only
  }
}

export async function parseDescription(description: string): Promise<ParseResponse> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    throw new ServiceError("Your session has expired — please sign in again.");
  }

  const res = await serviceFetch(`${serviceBaseUrl()}/parse`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ description }),
  });

  if (!res.ok) {
    let detail = `Parsing failed (${res.status}).`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail) detail = String(body.detail);
    } catch {
      // non-JSON error body — keep the status-based message
    }
    throw new ServiceError(detail);
  }

  return (await res.json()) as ParseResponse;
}

/**
 * Drawings-in: parse an uploaded drawing/sketch of a portal frame into a draft FrameSpec.
 *
 * Mirrors {@link parseDescription} exactly — same auth, same retry, same `ParseResponse` — so the
 * confirm/clarification UI is shared. The image is sent as a `data:` URL. The vision model only
 * transcribes labelled dimensions; the kernel does all engineering and the user confirms downstream.
 */
export async function parseDrawing(
  imageDataUrl: string,
  note?: string,
): Promise<ParseResponse> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    throw new ServiceError("Your session has expired — please sign in again.");
  }

  const res = await serviceFetch(`${serviceBaseUrl()}/parse-drawing`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ image_data_url: imageDataUrl, note: note?.trim() || null }),
  });

  if (!res.ok) {
    let detail = `Reading the drawing failed (${res.status}).`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail) detail = String(body.detail);
    } catch {
      // non-JSON error body — keep the status-based message
    }
    throw new ServiceError(detail);
  }

  return (await res.json()) as ParseResponse;
}

/**
 * Clarify-loop commit: build a FrameSpec from the merged read + clarified inputs.
 *
 * Deterministic on the server (NO LLM) — `build_frame_spec` flags any still-missing required field,
 * applies documented defaults, and validates. So the engineer's answers and whatever was read
 * combine into a spec without a second model pass. Same auth/retry/ParseResponse as parsing.
 */
export async function buildSpec(values: FrameSpecInputs): Promise<ParseResponse> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    throw new ServiceError("Your session has expired — please sign in again.");
  }

  const res = await serviceFetch(`${serviceBaseUrl()}/build-spec`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify(values),
  });

  if (!res.ok) {
    let detail = `Couldn’t build the specification (${res.status}).`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail) detail = String(body.detail);
    } catch {
      // non-JSON error body — keep the status-based message
    }
    throw new ServiceError(detail);
  }

  return (await res.json()) as ParseResponse;
}

// ---------------------------------------------------------------------------
// /design
// ---------------------------------------------------------------------------

export interface SectionChoice {
  member: string;
  designation: string;
}

/** Optional document/admin metadata for the calc-package cover (not engineering data). */
export interface ReportMetadata {
  project_name?: string | null;
  client?: string | null;
  project_number?: string | null;
  site_address?: string | null;
  engineer_name?: string | null;
  engineer_reg_no?: string | null;
  revision?: string | null;
}

export interface DesignRequest {
  spec: FrameSpec;
  mode: "design" | "check";
  sections?: SectionChoice[] | null;
  cost_rate_zar_per_kg?: number | null;
  project_id?: string | null;
  report_metadata?: ReportMetadata | null;
}

export interface StoredReport {
  run_id: string;
  report_id: string;
  storage_path: string;
  content_type: string;
  size_bytes: number;
}

export interface CheckResult {
  name: string;
  clause: string;
  utilisation: number;
  passed: boolean;
  detail?: string | null;
  /**
   * Advisory-only check (e.g. SLS-2 wind sway). Reported with its utilisation but does NOT
   * gate the design's `passed` / `governing_utilisation`. Optional for backward-compat with
   * older service responses (treated as false when absent).
   */
  informational?: boolean;
}

export interface ConnectionDesignResult {
  location: string;
  description: string;
  design_moment_knm: number;
  design_shear_kn: number;
  design_axial_kn: number;
  checks: CheckResult[];
}

export interface BaseplateDesignResult {
  base_fixity: string;
  description: string;
  design_axial_kn: number;
  design_shear_kn: number;
  design_moment_knm: number;
  checks: CheckResult[];
}

export interface PadFootingDesignResult {
  description: string;
  plan_size_mm: number;
  thickness_mm: number;
  allowable_bearing_kpa: number;
  design_service_axial_kn: number;
  design_factored_axial_kn: number;
  checks: CheckResult[];
}

export interface WindLoadCase {
  name: string;
  cpi: number;
  net_cp_windward_wall: number;
  net_cp_leeward_wall: number;
  net_cp_windward_roof: number;
  net_cp_leeward_roof: number;
  windward_column_udl_kn_per_m: number;
  leeward_column_udl_kn_per_m: number;
  windward_rafter_udl_kn_per_m: number;
  leeward_rafter_udl_kn_per_m: number;
}

export interface WindLoadResult {
  peak_velocity_pressure_kpa: number;
  reference_height_m: number;
  scenario: string;
  cases: WindLoadCase[];
  clause: string;
}

/** One sampled point along a member: global position (m) + internal forces. */
export interface DiagramStation {
  pos_m: number;
  x_m: number;
  y_m: number;
  axial_kn: number;
  shear_kn: number;
  moment_knm: number;
}

export interface MemberDiagram {
  name: string;
  label: string;
  member: string; // "column" | "rafter"
  start: [number, number];
  end: [number, number];
  length_m: number;
  stations: DiagramStation[];
}

/** BMD/SFD + stick-model data for the governing ULS-1 combination (FR-32). */
export interface FrameDiagram {
  combination: string;
  nodes: Record<string, [number, number]>;
  members: MemberDiagram[];
  max_abs_moment_knm: number;
  max_abs_shear_kn: number;
}

export interface DesignResult {
  frame_spec: FrameSpec;
  sections: SectionChoice[];
  checks: CheckResult[];
  wind?: WindLoadResult | null;
  diagram?: FrameDiagram | null;
  rules_version: Record<string, string>;
  warnings: string[];
  total_steel_mass_kg: number | null;
  indicative_cost_zar: number | null;
  total_steel_tonnes: number | null;
  connections: ConnectionDesignResult[];
  baseplate: BaseplateDesignResult | null;
  footing: PadFootingDesignResult | null;
  passed: boolean;
  governing_utilisation: number;
}

export interface DesignResponse {
  result: DesignResult;
  report: StoredReport;
}

/**
 * Mint a short-lived signed URL for a stored calc-package PDF (Task 6.6). The
 * report bucket is private; Storage RLS (Task 5.3) only lets the caller sign
 * objects under their own firm's folder.
 */
export async function getReportSignedUrl(storagePath: string): Promise<string> {
  const supabase = createClient();
  const objectPath = storagePath.replace(/^reports\//, "");
  const { data, error } = await supabase.storage
    .from("reports")
    .createSignedUrl(objectPath, 60);
  if (error || !data?.signedUrl) {
    throw new ServiceError(error?.message ?? "Could not generate a download link.");
  }
  return data.signedUrl;
}

// ---------------------------------------------------------------------------
// Agentic design exploration (POST /design-agent)
// ---------------------------------------------------------------------------

/** Engineer-stated limits the agentic search must honour (inputs, never results). */
export interface AgentConstraints {
  /** If set, members may only use these section designations (e.g. stock on hand). */
  allowed_sections?: string[] | null;
  /** If set, no member may be deeper than this (mm) — e.g. headroom/clearance. */
  max_depth_mm?: number | null;
}

/** One kernel-verified design option the agent found. `result` is the source of truth. */
export interface AgentAlternative {
  label: string;
  rationale: string;
  mode: "design" | "check";
  rafter_restraint_spacing_m?: number | null;
  column_restraint_spacing_m?: number | null;
  sections?: SectionChoice[] | null;
  result: DesignResult;
  /** Frame steel mass vs the baseline (kg); negative = lighter. Kernel-derived. */
  mass_delta_kg?: number | null;
  trade_off_note: string;
}

/** The full exploration outcome — no PDF; the chosen option is replayed via {@link runDesign}. */
export interface AgentDesignOutcome {
  baseline: DesignResult | null;
  baseline_note?: string | null;
  alternatives: AgentAlternative[];
  /** Index into `alternatives` of the recommended option, or null to keep the baseline. */
  recommended_index: number | null;
  narrative: string;
  notes: string[];
  /** False if the exploration degraded to the baseline only (AI unavailable). */
  used_llm: boolean;
}

/**
 * Run the agentic design loop over a confirmed spec. The AI only orchestrates the kernel and
 * proposes input levers — it never computes an engineering number; every value comes back from
 * the deterministic kernel, and the plain design is always the baseline (never worse than
 * {@link runDesign}). Exploration only: no PDF is produced. Replay the chosen option through
 * {@link runDesign} to get the stamped calc package.
 */
export async function runDesignAgent(
  spec: FrameSpec,
  constraints?: AgentConstraints | null,
): Promise<AgentDesignOutcome> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    throw new ServiceError("Your session has expired — please sign in again.");
  }

  const res = await serviceFetch(`${serviceBaseUrl()}/design-agent`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ spec, constraints: constraints ?? null }),
  });

  if (!res.ok) {
    let detail = `The design exploration failed (${res.status}).`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail) detail = String(body.detail);
    } catch {
      // non-JSON error body — keep the status-based message
    }
    throw new ServiceError(detail);
  }

  return (await res.json()) as AgentDesignOutcome;
}

/** A registered engineer's e-stamp recorded on a run (mirrors the kernel Stamp + audit). */
export interface RunStamp {
  engineer_name: string;
  ecsa_reg_no: string;
  stamped_at: string;
  fingerprint: string;
  stamped_by?: string;
}

/**
 * Apply the calling registered engineer's e-stamp to a stored run. The service re-renders the
 * calc package with the stamp and re-stores it; only a user the firm owner marked a registered
 * engineer (with an ECSA reg no) may stamp. Records professional responsibility — not validation.
 */
export async function stampRun(runId: string): Promise<RunStamp> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    throw new ServiceError("Your session has expired — please sign in again.");
  }

  const res = await serviceFetch(`${serviceBaseUrl()}/stamp`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ run_id: runId }),
  });

  if (!res.ok) {
    let detail = `Stamping failed (${res.status}).`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail) detail = String(body.detail);
    } catch {
      // keep status-based message
    }
    throw new ServiceError(detail);
  }
  return (await res.json()) as RunStamp;
}

export async function runDesign(request: DesignRequest): Promise<DesignResponse> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    throw new ServiceError("Your session has expired — please sign in again.");
  }

  const res = await serviceFetch(`${serviceBaseUrl()}/design`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    let detail = `The design run failed (${res.status}).`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail) detail = String(body.detail);
    } catch {
      // non-JSON error body — keep the status-based message
    }
    throw new ServiceError(detail);
  }

  return (await res.json()) as DesignResponse;
}
