import { test, expect } from "@playwright/test";

test.describe("P&L panel", () => {
  test("shows correct FIFO-matched realized and unrealized P&L", async ({ page }) => {
    await page.goto("/");

    // These exact figures were verified three separate ways earlier in
    // this project: by hand, via pytest, and via curl against the raw
    // API. This test is the fourth and final check — the same numbers,
    // now confirmed in the actual rendered UI a user would see.
    await expect(page.getByTestId("pnl-realized")).toHaveText("$560.00");
    await expect(page.getByTestId("pnl-unrealized")).toHaveText("$120.00");
    await expect(page.getByTestId("pnl-open-quantity")).toHaveText("30");
  });

  test("shows a clear error for a security with no transactions", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("input-security-id").fill("NOT_A_REAL_SECURITY");

    await expect(
      page.locator(".card", { hasText: "P&L —" })
    ).toContainText(/No transactions|404/i);
  });
});
