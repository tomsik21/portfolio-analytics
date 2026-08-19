// Reads Playwright's JSON reporter output (test-results.json) and writes
// a small, clean summary (../docs/dashboard-data.json) for the static
// dashboard page to render. Kept as a plain Node script with zero
// dependencies so it needs no separate npm install step in CI.
//
// Playwright's raw JSON report nests tests inside recursively-nested
// "suites" (one level per describe block / file). This script walks
// that tree and flattens it into one array of {specFile, title, status,
// durationMs} — much simpler for the dashboard page to consume.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const inputPath = join(__dirname, "..", "test-results.json");
const outputDir = join(__dirname, "..", "..", "docs");
const outputPath = join(outputDir, "dashboard-data.json");

const raw = JSON.parse(readFileSync(inputPath, "utf-8"));

function flattenTests(suites, specFile = null) {
  const out = [];
  for (const suite of suites ?? []) {
    // The top level of suites is one per spec file; suite.file carries
    // the filename there. Nested suites (describe blocks) don't repeat
    // it, so we thread the file name down through recursion.
    const currentFile = suite.file ?? specFile;
    for (const spec of suite.specs ?? []) {
      for (const test of spec.tests ?? []) {
        const lastResult = test.results?.[test.results.length - 1];
        out.push({
          specFile: currentFile,
          title: spec.title,
          status: test.status, // "expected" | "unexpected" | "flaky" | "skipped"
          durationMs: lastResult?.duration ?? 0,
          retries: (test.results?.length ?? 1) - 1,
        });
      }
    }
    out.push(...flattenTests(suite.suites, currentFile));
  }
  return out;
}

const tests = flattenTests(raw.suites);

const bySpec = {};
for (const t of tests) {
  const key = t.specFile ?? "unknown";
  bySpec[key] ??= { specFile: key, tests: [] };
  bySpec[key].tests.push(t);
}

const summary = {
  generatedAt: new Date().toISOString(),
  stats: {
    total: tests.length,
    passed: raw.stats?.expected ?? 0,
    failed: raw.stats?.unexpected ?? 0,
    flaky: raw.stats?.flaky ?? 0,
    skipped: raw.stats?.skipped ?? 0,
    durationMs: raw.stats?.duration ?? 0,
  },
  specs: Object.values(bySpec),
};

mkdirSync(outputDir, { recursive: true });
writeFileSync(outputPath, JSON.stringify(summary, null, 2));
console.log(`Dashboard data written to ${outputPath}`);
console.log(
  `  ${summary.stats.passed}/${summary.stats.total} passed, ${summary.stats.flaky} flaky, ${summary.stats.failed} failed`
);
