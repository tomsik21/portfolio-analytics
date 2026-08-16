import { defineConfig, devices } from "@playwright/test";

// This test suite assumes BOTH servers are already running:
//   backend:  uvicorn app.main:app --reload   (port 8000)
//   frontend: npm run dev                      (port 5173)
// It does NOT start them automatically — a real E2E suite in CI would,
// but for local development it's clearer (and faster to iterate on)
// to keep servers running yourself and just re-run tests against them.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  retries: 0,
  reporter: "html",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
