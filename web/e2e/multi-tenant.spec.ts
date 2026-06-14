import { expect, test } from "@playwright/test";

import { createProject, e2eConfigured, signIn, signOut, signUp } from "./support";

// 7.3 — a second firm cannot see or open the first firm's data (RLS isolation).
test.describe("multi-tenant isolation", () => {
  test.skip(!e2eConfigured, "set E2E_EMAIL/E2E_PASSWORD (seeded firm-A user)");

  test("a second firm cannot see or open the first firm's project", async ({ page }) => {
    // Firm A (seeded user) creates a project, then signs out.
    await signIn(page);
    await expect(page).toHaveURL(/\/projects/);
    const projectName = `Isolation A ${Date.now()}`;
    await createProject(page, projectName);
    await page.getByRole("link", { name: projectName }).click();
    await expect(page.getByRole("heading", { name: projectName })).toBeVisible();
    const firmAProjectUrl = page.url(); // /projects/<id>
    await signOut(page);

    // Firm B — a brand-new user/firm — signs up.
    const stamp = Date.now();
    await signUp(page, {
      email: `e2e-firm-b-${stamp}@example.com`,
      password: "e2e-firm-b-pass-123",
      firmName: `Firm B ${stamp}`,
    });
    await expect(page).toHaveURL(/\/projects/);

    // B's project list must NOT contain A's project.
    await expect(page.getByRole("link", { name: projectName })).toHaveCount(0);

    // B cannot open A's project URL directly — RLS makes it not-found.
    await page.goto(firmAProjectUrl);
    await expect(page.getByText(/project not found/i)).toBeVisible();
  });
});
