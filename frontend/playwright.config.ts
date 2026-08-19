import { defineConfig, devices } from "@playwright/test";

// webServer starts BOTH the backend and frontend automatically before
// tests run, and tears them down after — so `npm run test:e2e` is fully
// self-contained: no manual multi-terminal setup required, locally or
// in CI. Playwright polls each `url` until it responds, then proceeds.
//
// `reuseExistingServer: !process.env.CI` means: locally, if you already
// have servers running (e.g. mid-development, iterating quickly), those
// existing servers are reused instead of starting duplicates. In CI,
// this is always false, so it always starts fresh — the exact isolation
// a CI run needs.
//
// The backend command assumes `uvicorn` is on PATH — run this from a
// terminal with your Python virtual environment activated (the same one
// requirements.txt was installed into).
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
  webServer: [
    {
      command: "cd .. && uvicorn app.main:app --host 0.0.0.0 --port 8000",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: "npm run dev -- --host 0.0.0.0",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
