import { expect, test } from "@playwright/test";

test("landing page renders the TorenOne heading", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /the ai structural engineer/i }),
  ).toBeVisible();
});
