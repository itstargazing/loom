import { test, expect } from "@playwright/test";

/**
 * Soft-launch smoke: public legal surfaces render without auth.
 * Run: npx playwright test (from dashboard/, after `npx playwright install`).
 */
test.describe("legal smoke", () => {
  test("privacy policy", async ({ page }) => {
    await page.goto("/legal/privacy");
    await expect(page.getByRole("heading", { name: "Privacy Policy" })).toBeVisible();
    await expect(page.getByText("not on-device-only", { exact: false })).toBeVisible();
  });

  test("terms of service", async ({ page }) => {
    await page.goto("/legal/terms");
    await expect(page.getByRole("heading", { name: "Terms of Service" })).toBeVisible();
  });
});
