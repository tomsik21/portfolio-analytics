# portfolio-analytics (learning project)

A small, honest simulation of what Ridgeline's *Senior Quality Engineer,
Performance and Analytics* job is actually testing: a service that
calculates **Time-Weighted Return (TWR)**, **Brinson-Fachler attribution**,
and **FIFO P&L**, backed by a columnar/OLAP-style store, with a QE-style
pytest suite validating it.

## How this maps to the JD — and to Ridgeline's actual stack

This isn't guesswork: Ridgeline's own DevOps blog and several sibling
job postings on the same Performance & Analytics team confirm the real
stack. Where this project matches, it's deliberate; where it diverges,
it's noted.

| JD / Ridgeline signal | Confirmed from | This project |
|---|---|---|
| "modern OLAP and Columnar technologies" | JD + sibling postings | DuckDB (`app/db.py`) — vectorized/columnar SQL, same mental model as their likely AWS-native choice (Redshift is the most probable fit given their all-in-AWS serverless stack, though they don't name the product publicly) |
| **FastAPI + Pydantic** | Ridgeline's own DevOps blog names these exact libraries | `app/main.py`, `app/models.py` — direct match, not an approximation |
| Python as a core language | Ridgeline DevOps blog ("Languages: Python, golang, TypeScript") | This whole project |
| **"ETL Pipelines that move data into OLAP systems"** (named bonus) | Sibling SWE postings, same team | `app/etl.py` + `tests/test_etl.py` — CSV ingestion with data-quality rejection, tested against a deliberately dirty fixture file |
| "TWR, Brinson Attribution, benchmark analysis, P&L" | JD | `app/calculations/twr.py`, `brinson.py`, `pnl.py` |
| "APIs, databases, and automated testing frameworks" | JD | FastAPI + DuckDB + pytest (`tests/`) |
| Cloud native on AWS, serverless microservices, Lambda | Ridgeline DevOps blog + architecture posts | Not yet built here — see "Next steps" |
| Terraform / IaC | Ridgeline DevOps blog | Not yet built here — see "Next steps" |
| GIPS Composites (named product feature) | ridgeline.ai reporting page | Attribution/TWR math here is GIPS-aligned methodology; a composite rollup isn't built yet |
| "validate business-critical workflows where accuracy... is essential" | JD | `tests/` is written the way a QE would: golden-path + edge cases + a **reconciliation invariant** test for attribution |
| Kotlin | Named on the Staff Analytics Engineer posting (same team, more senior) | Not covered — this project is Python-only by design |

## Why the domain math is the point

Anyone can wire up a CRUD API. What a QE at a firm like this actually
needs to understand is *why* two numbers that "should" match sometimes
don't — e.g. `true_twr()` vs `modified_dietz()` will diverge whenever a
cash flow is large and well-timed relative to a market move. That's not
a bug; it's the nature of the approximation. Confusing the two (or not
knowing they should sometimes differ) is exactly the kind of gap this
role exists to catch before a client sees a wrong number.

Similarly, the Brinson attribution engine's real safety net isn't any
individual sector's number — it's the **reconciliation invariant**:
`allocation + selection + interaction` must sum to the total active
return, always. That single assertion (`test_reconciliation_invariant_holds`)
would catch the vast majority of real-world attribution bugs.

## Project layout

```
app/
  calculations/
    twr.py       # True TWR (daily-valued) + Modified Dietz
    brinson.py   # Brinson-Fachler sector attribution
    pnl.py       # FIFO realized/unrealized P&L
  db.py          # DuckDB schema + query layer
  etl.py         # CSV -> OLAP store, with data-quality rejection reporting
  seed_data.py   # Small, hand-checkable dataset
  models.py      # Pydantic response schemas
  main.py        # FastAPI app
data/
  sample_feeds/  # Deliberately dirty CSVs for exercising the ETL guardrails
tests/
  test_twr.py        # unit tests, calc engine
  test_brinson.py    # unit tests, calc engine
  test_pnl.py         # unit tests, calc engine
  test_etl.py          # data-quality tests against dirty sample feeds
  test_api.py           # integration tests against the real DB-backed API
  conftest.py            # seeds a temp DuckDB file per test session
CLAUDE.md            # repo context for Claude Code / Cursor — Ridgeline's team uses these daily
```

## Running it

This was built and had its logic verified in a sandboxed environment with
**no network access**, so `duckdb`/`fastapi`/`pytest` couldn't actually be
`pip install`ed here. The calculation engine (the domain-critical part)
was verified with hand-checked reference values directly, and the DB/API
query logic was simulated with `sqlite3` standing in for DuckDB to catch
schema/query bugs. Both passed. Run it for real locally:

```bash
pip install -r requirements.txt

# seed the database
python -m app.seed_data

# run the test suite
pytest tests/ -v

# run the API
uvicorn app.main:app --reload
# then: http://localhost:8000/docs for interactive Swagger UI
```

Try it:
```bash
curl "http://localhost:8000/portfolios/PORT1/performance/twr?start=2026-01-01&end=2026-01-03"
curl "http://localhost:8000/portfolios/PORT1/attribution/brinson?start=2026-01-01&end=2026-01-31"
curl "http://localhost:8000/portfolios/PORT1/pnl?security_id=AAPL_DEMO&as_of=2026-01-31"
```

## What to build next (in rough order of relevance to the JD)

1. **Property-based tests** (`hypothesis`) for the Brinson reconciliation
   invariant — generate random weight/return combinations and assert the
   invariant holds for *all* of them, not just your hand-picked cases.
2. **Contract/schema tests** — use `pydantic` models to validate API
   responses against a fixed schema so a field-rename becomes an
   immediately-caught test failure, not a silent client break.
3. **Dockerize it and deploy behind AWS Lambda + API Gateway** — Ridgeline's
   own DevOps blog confirms their services deploy as Lambda functions
   behind serverless infra managed with Terraform/CDK. Getting this
   FastAPI app running on Lambda (via Mangum) is the single highest-value
   next step to mirror their actual deployment model, and directly
   addresses "experience validating applications built on cloud native
   platforms."
4. **Terraform for the DB + API infra** — even a minimal `main.tf`
   provisioning the equivalent of what you're running locally shows
   IaC familiarity, which their DevOps blog treats as core to the role.
5. **A GIPS composite rollup** on top of `twr.py` — aggregate several
   portfolios into a composite return, since GIPS Composites are a
   named feature on Ridgeline's own reporting product page.
6. **Use Claude Code or Cursor** to extend this — the repo now has a
   `CLAUDE.md` primed for exactly that. Try asking it to add
   multi-currency attribution and write the QE test suite alongside it —
   the JD explicitly wants people comfortable pairing with these tools.
7. **Deliberately break something** (e.g. flip FIFO to LIFO silently) and
   confirm your test suite catches it. That exercise — "would my tests
   have caught this?" — is the actual day-to-day instinct this role wants.
