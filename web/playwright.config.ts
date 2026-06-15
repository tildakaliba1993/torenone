import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // Serial: the E2E suite mutates shared real backend state (one Supabase test
  // user + real data), and sign-out revokes that user's tokens — parallel runs
  // would invalidate each other's sessions.
  fullyParallel: false,
  workers: 1,
  // The happy-path runs a real design and waits up to 60s for the result (NFR-5), plus
  // sign-in / project / parse / confirm overhead — so the default 30s per-test timeout is
  // too tight (it passed locally only by a hair). Allow headroom for slower CI runners.
  timeout: 90_000,
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
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
