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
}

export interface FrameGeometry {
  span_m: number;
  eaves_height_m: number;
  roof_pitch_deg: number;
  bay_spacing_m: number;
  number_of_bays: number;
  apex_height_m?: number;
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
}

/** Raised for any failure talking to the engineering service (network or HTTP). */
export class ServiceError extends Error {}

function serviceBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_ENGINEERING_SERVICE_URL;
  if (!base) throw new ServiceError("The engineering service URL is not configured.");
  return base.replace(/\/$/, "");
}

export async function parseDescription(description: string): Promise<ParseResponse> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    throw new ServiceError("Your session has expired — please sign in again.");
  }

  let res: Response;
  try {
    res = await fetch(`${serviceBaseUrl()}/parse`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ description }),
    });
  } catch {
    throw new ServiceError("Couldn’t reach the engineering service. Is it running?");
  }

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

// ---------------------------------------------------------------------------
// /design
// ---------------------------------------------------------------------------

export interface SectionChoice {
  member: string;
  designation: string;
}

export interface DesignRequest {
  spec: FrameSpec;
  mode: "design" | "check";
  sections?: SectionChoice[] | null;
  cost_rate_zar_per_kg?: number | null;
  project_id?: string | null;
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

export interface DesignResult {
  frame_spec: FrameSpec;
  sections: SectionChoice[];
  checks: CheckResult[];
  wind?: WindLoadResult | null;
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

export async function runDesign(request: DesignRequest): Promise<DesignResponse> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    throw new ServiceError("Your session has expired — please sign in again.");
  }

  let res: Response;
  try {
    res = await fetch(`${serviceBaseUrl()}/design`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify(request),
    });
  } catch {
    throw new ServiceError("Couldn’t reach the engineering service. Is it running?");
  }

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
