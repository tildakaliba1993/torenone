import { type Page } from "@playwright/test";

/**
 * E2E support (Phase 7). The full stack is exercised — real Supabase auth + RLS,
 * real /design (kernel + PDF + Storage). Only the non-deterministic OpenAI /parse
 * call is mocked, so the suite is stable and free.
 *
 * Gated on E2E_EMAIL / E2E_PASSWORD (a seeded Supabase user) so CI stays green
 * until those secrets — and a running engineering service — are provided.
 */
export const E2E_EMAIL = process.env.E2E_EMAIL;
export const E2E_PASSWORD = process.env.E2E_PASSWORD;
export const e2eConfigured = Boolean(E2E_EMAIL && E2E_PASSWORD);

/** A deterministic, complete /parse response (stands in for the OpenAI call). */
export const COMPLETE_PARSE = {
  status: "complete",
  spec: {
    geometry: {
      span_m: 20,
      eaves_height_m: 6,
      roof_pitch_deg: 10,
      bay_spacing_m: 6,
      number_of_bays: 5,
    },
    materials: { steel_grade: "S355JR" },
    base_fixity: "pinned",
    restraints: { rafter_restraint_spacing_m: null, column_restraint_spacing_m: null },
    dead: { roof_kpa: 0.15, services_kpa: 0, wall_cladding_kpa: 0 },
    imposed: { roof_access: false },
    wind: {
      basic_wind_speed_ms: 36,
      terrain_category: "B",
      site_altitude_m: 0,
      has_dominant_opening: false,
    },
    foundation: { allowable_bearing_kpa: 150, concrete_fcu_mpa: 25 },
  },
  assumptions: [],
  questions: [],
  missing: [],
  errors: [],
  scope_note: null,
};

/** Intercept the engineering service's /parse and return a fixed result. */
export async function mockParse(page: Page, body: unknown = COMPLETE_PARSE): Promise<void> {
  await page.route(/\/parse(\?|$)/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

/** An out-of-scope /parse result (e.g. the user described a non-portal-frame structure). */
export const OUT_OF_SCOPE_PARSE = {
  status: "out_of_scope",
  spec: null,
  assumptions: [],
  questions: [],
  missing: [],
  errors: [],
  scope_note: "TorenOne designs single-bay steel portal frames, not multi-storey concrete buildings.",
};

/** Sign in through the real login form (real Supabase auth). */
export async function signIn(
  page: Page,
  email: string = E2E_EMAIL!,
  password: string = E2E_PASSWORD!,
): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /^sign in$/i }).click();
}

/** Sign up a brand-new firm/user (email confirmation must be off for the flow to land). */
export async function signUp(
  page: Page,
  { email, password, firmName }: { email: string; password: string; firmName: string },
): Promise<void> {
  await page.goto("/signup");
  await page.getByLabel("Firm name").fill(firmName);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /create account/i }).click();
}

/** Sign out via the nav (server action) and wait for the login screen. */
export async function signOut(page: Page): Promise<void> {
  await page.getByRole("button", { name: /sign out/i }).click();
  await page.waitForURL(/\/login/);
}

/** Create a project from the projects list (assumes already signed in + on /projects). */
export async function createProject(page: Page, name: string): Promise<void> {
  await page
    .getByRole("button", { name: /new project|create your first project/i })
    .first()
    .click();
  await page.getByLabel("Project name").fill(name);
  await page.getByRole("button", { name: /^create project$/i }).click();
}
