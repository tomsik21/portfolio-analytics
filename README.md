# portfolio-analytics

A full-stack investment performance & analytics platform: calculates
**Time-Weighted Return (TWR)**, **Brinson-Fachler attribution**, and
**FIFO P&L**, serves them over a REST API backed by a columnar/OLAP-style
database, and renders them in a React dashboard. Every layer —
calculation engine, API, ETL pipeline, and UI — is covered by an
automated test suite (pytest for backend/logic, Playwright for
end-to-end browser tests).

Built as a hands-on learning project to understand the domain and tools
behind investment performance analytics: how time-weighted return works,
why performance attribution needs to reconcile exactly, how FIFO lot
accounting works, and how to test all of that rigorously at every layer
of a real application.

## What it does

- **Time-Weighted Return (TWR)** — the standard method for measuring
  investment performance independent of investor cash flows (deposits/
  withdrawals shouldn't make a manager look better or worse than they
  actually performed). Includes both the true daily-valued method and
  the Modified Dietz approximation, since knowing when and why they
  diverge is itself an important part of this domain.
- **Brinson-Fachler attribution** — breaks down *why* a portfolio beat
  or lagged its benchmark, sector by sector, into allocation, selection,
  and interaction effects.
- **FIFO P&L** — realized and unrealized profit/loss on a security,
  using first-in-first-out lot matching.
- **ETL pipeline** — ingests raw CSV transaction/valuation feeds into
  the database, rejecting malformed rows (duplicates, bad dates, invalid
  values) with a clear data-quality report instead of crashing.
- **A React dashboard** that displays all of the above with live,
  editable filters (portfolio, security, date ranges).

## Architecture

```text
┌─────────────────┐        ┌──────────────────────┐        ┌─────────────────┐
│  React frontend   │ ─── │  FastAPI backend       │ ─── │  DuckDB (OLAP)     │
│  (Vite + TS)       │  HTTP │  TWR / Attribution /   │  SQL  │  columnar store      │
│  localhost:5173    │       │  P&L / ETL              │       │  portfolio_analytics │
└─────────────────┘        └──────────────────────┘        └─────────────────┘
```

Two independent test suites cover this: **pytest** exercises the
calculation engine, database queries, ETL, and API directly (no browser
involved); **Playwright** drives a real Chromium browser against the
actual running frontend + backend together, the way a real user would.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite |
| Backend | Python, FastAPI, Pydantic |
| Database | DuckDB (columnar/OLAP) |
| Testing (unit/API) | pytest, FastAPI TestClient |
| Testing (E2E) | Playwright |
| AI-assisted development | Repo includes a `CLAUDE.md` for use with Claude Code / Cursor |

## Quick start

You'll want **three terminal tabs** open at once: backend, frontend, and
one free for running commands (tests, git, etc).

### 1. Backend

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python -m app.seed_data         # creates portfolio_analytics.duckdb with sample data
uvicorn app.main:app --reload   # starts the API on http://localhost:8000
```

Visit `http://localhost:8000/docs` for interactive API documentation
(Swagger UI) — you can try every endpoint directly from the browser.

### 2. Frontend

In a second terminal, from the project root:

```bash
cd frontend
npm install
npm run dev                     # starts the dashboard on http://localhost:5173
```

Open `http://localhost:5173`. With both servers running, you should see
live TWR, attribution, and P&L numbers for the seeded sample portfolio.

## Running the tests

**Backend / calculation engine (pytest):**
```bash
pytest tests/ -v
```
Covers: TWR and Modified Dietz edge cases, the Brinson attribution
reconciliation invariant, FIFO lot-matching correctness, ETL data-quality
rejection against deliberately dirty sample CSVs, and API-level contract
tests (correct HTTP status codes for good vs. bad input).

**End-to-end (Playwright):** starts the backend and frontend
automatically — no need to have them running first.
```bash
cd frontend
npx playwright install chromium   # one-time browser download
npm run test:e2e                  # headless run
npm run test:e2e:ui               # interactive mode, useful for debugging
```
The backend command in `playwright.config.ts` assumes `uvicorn` is on
your `PATH`, so run this from a terminal with your Python virtual
environment activated. If you already have both servers running
manually (e.g. mid-development), Playwright reuses them instead of
starting duplicates — see the `webServer` config for details.

Drives a real browser against the real dashboard: page loads, live data
recalculation when filters change, the attribution reconciliation
invariant re-verified from rendered page text (not just the API
response), and error states for missing/invalid data.

## Test dashboard and monitoring

Every CI run uploads Playwright results to a [Currents.dev](https://currents.dev)
dashboard — pass/fail history over time (not just the latest run),
flaky-test detection, and recorded traces/videos/screenshots for every
test, not just failures. This is what turns "the tests are green right
now" into something with actual history and trends behind it.

`frontend/currents.config.ts` holds the (non-secret) project ID;
`CURRENTS_RECORD_KEY` is a GitHub Actions secret, never committed. To
also upload local runs, export it yourself before running tests:
```bash
export CURRENTS_RECORD_KEY=...   # from your Currents.dev org settings
```


## Project structure

```text
app/
  calculations/
    twr.py        # True TWR (daily-valued) + Modified Dietz
    brinson.py     # Brinson-Fachler sector attribution
    pnl.py           # FIFO realized/unrealized P&L
  db.py            # DuckDB schema + query layer
  etl.py            # CSV -> OLAP store, with data-quality rejection reporting
  seed_data.py      # Populates the database with a small, hand-checkable dataset
  models.py         # Pydantic response schemas
  main.py           # FastAPI app and route definitions
data/
  sample_feeds/     # Deliberately dirty CSVs for exercising the ETL guardrails
tests/
  test_twr.py        # unit tests: TWR / Modified Dietz calc engine
  test_brinson.py     # unit tests: attribution calc engine
  test_pnl.py          # unit tests: FIFO P&L calc engine
  test_etl.py           # data-quality tests against dirty sample feeds
  test_api.py            # integration tests against the real DB-backed API
  conftest.py             # seeds a temp DuckDB file per pytest session
frontend/
  src/
    api/client.ts          # typed API client
    components/             # TwrCard, AttributionCard, PnlCard
    App.tsx                  # dashboard shell + filter controls
  tests/                      # Playwright end-to-end specs
  playwright.config.ts
requirements.txt    # backend Python dependencies
CLAUDE.md            # repo context for AI pair-programming tools (Claude Code, Cursor)
```

## Why the domain math is the point

The calculation engine is the part that actually matters here, not the
API wrapper around it. `true_twr()` and `modified_dietz()` will
legitimately disagree whenever a cash flow is large and well-timed
relative to a market move — that's not a bug, it's the nature of the
approximation, and confusing the two is exactly the kind of subtle gap
that matters in performance analytics. Similarly, the Brinson attribution
engine's real safety net isn't any individual sector's number — it's the
**reconciliation invariant** (`allocation + selection + interaction`
must always sum exactly to the active return), verified at three
separate layers of this project: the pytest unit test, the API response,
and the rendered UI text via Playwright.

## What's next

1. **Property-based tests** (`hypothesis`) for the Brinson reconciliation
   invariant, generating random weight/return combinations rather than
   relying on hand-picked cases.
2. **Dockerize and deploy** behind a serverless API (e.g. AWS Lambda +
   API Gateway).
3. **Terraform** for the infrastructure, even minimally.
4. **A GIPS composite rollup** aggregating multiple portfolios.
5. **Multi-currency attribution**, extending the calc engine and its test
   suite together (a good task to hand to Claude Code, using `CLAUDE.md`
   as context).
