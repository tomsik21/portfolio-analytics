# CLAUDE.md

Context for Claude Code (or Cursor) when working in this repo. This
file exists because Ridgeline's Performance & Analytics team explicitly
builds with Claude Code / Cursor day-to-day — keeping a repo well
primed for an AI pair-programmer is itself a relevant skill for this
role, not just a nice-to-have.

## What this is

A small performance & analytics platform: TWR, Brinson-Fachler
attribution, and FIFO P&L, backed by DuckDB (OLAP/columnar stand-in),
exposed via FastAPI, validated by a pytest QE suite.

## Domain ground truth (don't re-derive, just use these)

- **TWR**: `true_twr()` in `app/calculations/twr.py` geometrically links
  daily sub-period returns. Cash flows must NOT distort the return —
  that's the entire point of TWR vs a naive return calc.
- **Modified Dietz** is an APPROXIMATION of true TWR, not an
  alternative implementation of the same number. They are expected to
  diverge when cash flows are large and well-timed. Never "fix" a test
  that asserts they differ.
- **Brinson-Fachler attribution**: the non-negotiable invariant is
  `allocation + selection + interaction == active_return` (see
  `AttributionResult.reconciliation_delta`, which should always be ~0).
  Any change to `brinson.py` that breaks this invariant is a bug, full
  stop — don't adjust the test tolerance to make it pass.
- **FIFO P&L**: oldest lots are consumed first. Test at the lot level,
  not just aggregate totals — offsetting lot-level errors can hide
  behind a correct sum.

## Conventions

- Every calculation function raises `ValueError` with a specific,
  actionable message on bad input (zero-base returns, weights that
  don't sum to 1, oversold positions) — never silently returns 0/NaN/inf.
- API endpoints map calc-engine `ValueError`s to HTTP 422, and "no data
  found" to HTTP 404. Keep that distinction — a QE test suite relies on
  telling "bad input" apart from "no data."
- New calculation logic needs a matching pytest file in `tests/` with:
  a golden-path test, at least one guardrail/edge-case test, and (for
  attribution-style code) an explicit reconciliation/invariant test —
  not just happy-path coverage.

## Running things here

```bash
pip install -r requirements.txt
python -m app.seed_data
pytest tests/ -v
uvicorn app.main:app --reload
```

## When extending this project

Good next tasks to hand to Claude Code directly (each should come with
its own pytest file, not just implementation):
- Multi-currency attribution (Ridgeline's actual accounting engine is
  multi-currency, multi-asset, double-entry — this repo's isn't yet)
- A GIPS composite rollup on top of `brinson.py` / `twr.py`
- Property-based tests (`hypothesis`) for the reconciliation invariant
  across randomized weight/return combinations
- Extending `app/etl.py` to a second source format and reconciling
  row counts between source and loaded — data lineage, not just
  data-quality rejection
