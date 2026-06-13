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

export interface FrameSpec {
  geometry: FrameGeometry;
  [key: string]: unknown;
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
