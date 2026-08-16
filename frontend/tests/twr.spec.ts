import { test, expect } from "@playwright/test";

test.describe("TWR panel", () => {
  test("shows the correct default TWR for the seeded portfolio", async ({ page }) => {
    await page.goto("/");
    // Default range (Jan 1 - Jan 3) should show 32.00%, matching the
    // hand-verified reference value from the calc engine.
    await expect(page.getByTestId("twr-value")).toHaveText("32.00%");
    await expect(page.getByTestId("twr-subperiods")).toHaveText("2");
  });

  test("recalculates live when the date range changes", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("twr-value")).toHaveText("32.00%");

    // Narrow the range to just the first sub-period (Jan 1 -> Jan 2).
    // This should drop to 20.00% — the exact scenario walked through
    // manually earlier in the project.
    await page.getByTestId("input-twr-end").fill("2026-01-02");

    await expect(page.getByTestId("twr-value")).toHaveText("20.00%");
    await expect(page.getByTestId("twr-subperiods")).toHaveText("1");
  });

  test("shows a clear error for an unknown portfolio rather than a blank panel", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByTestId("input-portfolio-id").fill("DOES_NOT_EXIST");

    // The API returns 422 for a portfolio with insufficient valuations,
    // which the frontend surfaces as an error banner inside the TWR card.
    await expect(page.locator(".card", { hasText: "Time-Weighted Return" })).toContainText(
      /found 0|422|Need at least/i
    );
  });
});
