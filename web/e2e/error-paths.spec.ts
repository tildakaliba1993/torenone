import { expect, test } from "@playwright/test";

import { OUT_OF_SCOPE_PARSE, createProject, e2eConfigured, mockParse, signIn } from "./support";

// 7.4 — invalid input, out-of-scope requests, and auth failures are handled gracefully.
test.describe("error paths", () => {
  test("an unauthenticated visit to a protected route redirects to login", async ({ page }) => {
    await page.goto("/projects/00000000-0000-0000-0000-000000000000/design/new");
    await expect(page).toHaveURL(/\/login(\?|$)/);
  });

  test.describe("signed in", () => {
    test.skip(!e2eConfigured, "set E2E_EMAIL/E2E_PASSWORD");

    test("empty / invalid design input is blocked by validation", async ({ page }) => {
      await signIn(page);
      await expect(page).toHaveURL(/\/projects/);
      const name = `Errors ${Date.now()}`;
      await createProject(page, name);
      await page.getByRole("link", { name }).click();
      await page.getByRole("link", { name: /new design/i }).click();
      // Parse is disabled until there's text; clarity beats a silent no-op.
      await expect(page.getByRole("button", { name: /parse description/i })).toBeDisabled();
    });

    test("an out-of-scope description shows a scope note, not a crash", async ({ page }) => {
      await mockParse(page, OUT_OF_SCOPE_PARSE);
      await signIn(page);
      await expect(page).toHaveURL(/\/projects/);
      const name = `Scope ${Date.now()}`;
      await createProject(page, name);
      await page.getByRole("link", { name }).click();
      await page.getByRole("link", { name: /new design/i }).click();
      await page
        .getByLabel(/describe your portal frame/i)
        .fill("Design a 12-storey reinforced-concrete office tower with a basement.");
      await page.getByRole("button", { name: /parse description/i }).click();
      await expect(page.getByText(/outside the current scope/i)).toBeVisible();
      await expect(page.getByText(/single-bay steel portal frames/i)).toBeVisible();
    });
  });
});
