import { test, expect } from "@playwright/test";

test.describe("Attribution panel", () => {
  test("renders all three seeded sectors with correct values", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByTestId("attribution-row-Tech")).toContainText("Tech");
    await expect(page.getByTestId("attribution-row-Energy")).toContainText("Energy");
    await expect(page.getByTestId("attribution-row-Health")).toContainText("Health");

    // Energy has the worst selection effect in the seed data (underperformed
    // its benchmark slice) — this is the number a portfolio manager would
    // actually look for first, so it's worth pinning down explicitly.
    await expect(page.getByTestId("attribution-row-Energy")).toContainText("-0.90%");
  });

  test("active return equals portfolio minus benchmark return", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByTestId("attribution-active-return")).toHaveText("1.70%");
  });

  test("reconciliation delta is displayed and effectively zero", async ({ page }) => {
    await page.goto("/");

    const deltaText = await page.getByTestId("attribution-reconciliation-delta").innerText();
    // Extract the scientific-notation number, e.g. "-6.94e-18", and assert
    // its magnitude is genuinely tiny — this is the UI-level equivalent of
    // the reconciliation_delta assertion in the pytest suite, now verified
    // against what a user actually sees on screen, not just the API response.
    const match = deltaText.match(/delta:\s*(-?[\d.]+e[-+]?\d+)/i);
    expect(match).not.toBeNull();
    const delta = parseFloat(match![1]);
    expect(Math.abs(delta)).toBeLessThan(1e-6);
  });

  test("changing the attribution date range to one with no data shows a clear error", async ({
    page,
  }) => {
    await page.goto("/");

    // Reach into the attribution period inputs specifically (there are
    // multiple date inputs on the page, so scope the locator to the
    // right card first).
    const attrCard = page.locator(".card", { hasText: "Attribution period" });
    await attrCard.locator('input[type="date"]').first().fill("2020-01-01");
    await attrCard.locator('input[type="date"]').nth(1).fill("2020-01-31");

    await expect(
      page.locator(".card", { hasText: "Brinson-Fachler Attribution" })
    ).toContainText(/No sector attribution data|404/i);
  });
});
