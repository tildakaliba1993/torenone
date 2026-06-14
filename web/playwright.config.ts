import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // Serial: the E2E suite mutates shared real backend state (one Supabase test
  // user + real data), and sign-out revokes that user's tokens — parallel runs
  // would invalidate each other's sessions.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
