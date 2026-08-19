import { defineConfig, devices, ReporterDescription } from "@playwright/test";
import { currentsReporter } from "@currents/playwright";

// The Currents reporter (v2) fails hard at startup if CURRENTS_RECORD_KEY
// isn't set — it doesn't just skip recording the way v1 used to. Since
// the key is only meant to be set in CI (via GitHub secrets), building
// the reporter list conditionally lets local runs work fine without it
// (falls back to just the local HTML report), while CI — which always
// has the key — still uploads to the Currents.dev dashboard.
const reporters: ReporterDescription[] = [["html"]];
if (process.env.CURRENTS_RECORD_KEY) {
  reporters.push(currentsReporter());
}

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
  // Currents.dev does not currently support parallelizing multiple
  // tests within the same spec file — only across files. Turning this
  // off keeps Currents recording reliable; Playwright still runs
  // different spec files in parallel across workers, so this is a
  // small, not a large, slowdown.
  fullyParallel: false,
  retries: 0,
  // "html" always runs so local reports keep working. The Currents
  // reporter is appended above only when CURRENTS_RECORD_KEY is set —
  // see the comment near the top of this file for why.
  reporter: reporters,
  use: {
    baseURL: "http://localhost:5173",
    // Currents' dashboard is only genuinely useful once there's
    // something to look at for every run, not just failures — "on"
    // records a trace/video/screenshot for every test, pass or fail.
    trace: "on",
    video: "on",
    screenshot: "on",
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
