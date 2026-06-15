import { z } from "zod";

// Shared client-side password policy for sign-up and password-reset. A baseline minimum
// length (the server-side Supabase Auth policy is the authoritative gate — set the stricter
// requirements in the Supabase dashboard). Kept simple to avoid complexity-rule UX friction.
export const MIN_PASSWORD_LENGTH = 10;

export const passwordSchema = z
  .string()
  .min(MIN_PASSWORD_LENGTH, `Password must be at least ${MIN_PASSWORD_LENGTH} characters`);
