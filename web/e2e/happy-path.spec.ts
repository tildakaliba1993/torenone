import { expect, test } from "@playwright/test";

import { e2eConfigured, mockParse, signIn } from "./support";

// 7.2 — sign in → create project → describe → confirm → design → PDF stored → in history.
test.describe("happy path", () => {
  test.skip(
    !e2eConfigured,
    "set E2E_EMAIL/E2E_PASSWORD (seeded Supabase user) and run the engineering service",
  );

  test("design a frame end-to-end and see it in run history", async ({ page }) => {
    await mockParse(page); // deterministic parse; /design stays real (kernel + PDF + Storage)
    await signIn(page);
    await expect(page).toHaveURL(/\/projects/);

    // Create a uniquely-named project.
    const projectName = `E2E happy ${Date.now()}`;
    await page
      .getByRole("button", { name: /new project|create your first project/i })
      .first()
      .click();
    await page.getByLabel("Project name").fill(projectName);
    await page.getByRole("button", { name: /^create project$/i }).click();

    // Open it and start a design.
    await page.getByRole("link", { name: projectName }).click();
    await expect(page.getByRole("heading", { name: projectName })).toBeVisible();
    await page.getByRole("link", { name: /new design/i }).click();

    // Describe → (mocked) parse → review screen, prefilled from the parsed spec.
    await page
      .getByLabel(/describe your portal frame/i)
      .fill("20 m warehouse, 6 m eaves, 10 deg pitch, 6 m bays, 5 bays, terrain B, wind 36, dead 0.15, bearing 150");
    await page.getByRole("button", { name: /parse description/i }).click();
    await expect(page.getByLabel(/^span/i)).toHaveValue("20");

    // Confirm (the trust gate) and run the real design.
    await page.getByLabel(/reviewed these inputs/i).check();
    const startedAt = Date.now();
    await page.getByRole("button", { name: /^run design$/i }).click();

    // Results render within the 60s NFR (7.5), with the PDF download available.
    await expect(page.getByText("Design result")).toBeVisible({ timeout: 60_000 });
    expect(Date.now() - startedAt).toBeLessThan(60_000);
    await expect(page.getByRole("button", { name: /download calc package/i })).toBeVisible();

    // The run is persisted and shows in the project's history with a downloadable PDF.
    await page.getByRole("link", { name: /back to project/i }).click();
    // Wait for the project page to actually load before asserting — the results page (which
    // has its own tables) stays mounted until the project's server data resolves, which can
    // be slow in CI. The project heading appears only once we've navigated.
    await expect(page.getByRole("heading", { name: projectName })).toBeVisible();
    await expect(page.getByRole("table").first()).toBeVisible();
    await expect(page.getByRole("button", { name: /^pdf$/i }).first()).toBeVisible();
  });
});
