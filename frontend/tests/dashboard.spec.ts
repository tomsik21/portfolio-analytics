import { test, expect } from "@playwright/test";

// Smoke test: confirms the whole app loads, the backend connection
// succeeds, and every dashboard panel actually renders data (not just
// its loading state forever, which is the most common "looks fine,
// is actually broken" bug in a data-fetching UI).
test.describe("Dashboard smoke test", () => {
  test("loads and connects to the backend", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Performance & Analytics Platform")).toBeVisible();

    // If the backend isn't running, this error banner appears instead —
    // failing fast and clearly here beats every downstream test timing
    // out individually with a less obvious root cause.
    await expect(page.getByText(/Can't reach the backend API/)).not.toBeVisible();
  });

  test("all three data panels render real values, not stuck loading", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByTestId("twr-value")).toBeVisible();
    await expect(page.getByTestId("attribution-active-return")).toBeVisible();
    await expect(page.getByTestId("pnl-realized")).toBeVisible();

    // None of the panels should be showing an error banner on default load.
    await expect(page.locator(".status-banner.error")).toHaveCount(0);
  });
});
