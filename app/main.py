"""
FastAPI service exposing the performance & analytics platform.

Endpoints map directly to the JD's domain: TWR, Brinson attribution,
and P&L. This is the surface a QE would actually write API-level tests
against (contract tests, edge-case tests, data-integrity tests).
"""
from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent import summarize_attribution
from app.calculations.brinson import SectorData, brinson_fachler
from app.calculations.pnl import Transaction, TransactionType, compute_fifo_pnl
from app.calculations.twr import DailyValuation, true_twr
from app.db import (
    fetch_current_price,
    fetch_daily_valuations,
    fetch_sector_returns,
    fetch_transactions,
    get_connection,
)
from app.models import (
    AttributionResponse,
    PnLResponse,
    SectorAttributionResponse,
    TWRResponse,
)

app = FastAPI(
    title="Performance & Analytics Platform",
    description="TWR, Brinson attribution, and P&L over a columnar (DuckDB) store.",
    version="0.1.0",
)

# Dev-only CORS: allows the Vite dev server (localhost:5173) to call this
# API directly if you ever bypass the vite.config.ts proxy. In a real
# deployment this would be scoped to the actual frontend origin, never "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_con():
    return get_connection()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/portfolios/{portfolio_id}/performance/twr", response_model=TWRResponse)
def get_twr(portfolio_id: str, start: date, end: date):
    con = _get_con()
    rows = fetch_daily_valuations(con, portfolio_id, start, end)
    con.close()

    if len(rows) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Need at least 2 daily valuations in range to compute TWR, "
                f"found {len(rows)}."
            ),
        )

    valuations = [DailyValuation(r[0], r[1], r[2]) for r in rows]
    try:
        twr = true_twr(valuations)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return TWRResponse(
        portfolio_id=portfolio_id,
        period_start=str(start),
        period_end=str(end),
        twr=twr,
        num_subperiods=len(valuations) - 1,
    )


@app.get(
    "/portfolios/{portfolio_id}/attribution/brinson", response_model=AttributionResponse
)
def get_attribution(portfolio_id: str, start: date, end: date):
    con = _get_con()
    rows = fetch_sector_returns(con, portfolio_id, start, end)
    con.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No sector attribution data for {portfolio_id} in {start}..{end}.",
        )

    sectors = [
        SectorData(sector=r[0], portfolio_weight=r[1], benchmark_weight=r[2],
                   portfolio_return=r[3], benchmark_return=r[4])
        for r in rows
    ]
    try:
        result = brinson_fachler(sectors)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return AttributionResponse(
        portfolio_id=portfolio_id,
        period_start=str(start),
        period_end=str(end),
        portfolio_total_return=result.portfolio_total_return,
        benchmark_total_return=result.benchmark_total_return,
        active_return=result.active_return,
        reconciliation_delta=result.reconciliation_delta,
        sectors=[
            SectorAttributionResponse(
                sector=s.sector,
                allocation_effect=s.allocation_effect,
                selection_effect=s.selection_effect,
                interaction_effect=s.interaction_effect,
                total_effect=s.total_effect,
            )
            for s in result.sector_results
        ],
    )


@app.get(
    "/portfolios/{portfolio_id}/attribution/brinson/insight"
)
def get_attribution_insight(portfolio_id: str, start: date, end: date):
    """
    Same underlying computation as /attribution/brinson, but returns an
    AI-generated plain-English narration instead of raw numbers. Recomputes
    rather than caching the prior result — this is intentionally a thin
    wrapper so the deterministic calc engine stays the single source of
    truth for the numbers themselves.
    """
    con = _get_con()
    rows = fetch_sector_returns(con, portfolio_id, start, end)
    con.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No sector attribution data for {portfolio_id} in {start}..{end}.",
        )

    sectors = [
        SectorData(sector=r[0], portfolio_weight=r[1], benchmark_weight=r[2],
                   portfolio_return=r[3], benchmark_return=r[4])
        for r in rows
    ]
    try:
        result = brinson_fachler(sectors)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        summary = summarize_attribution(result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {"portfolio_id": portfolio_id, "summary": summary}


@app.get("/portfolios/{portfolio_id}/pnl", response_model=PnLResponse)
def get_pnl(portfolio_id: str, security_id: str, as_of: date):
    con = _get_con()
    rows = fetch_transactions(con, portfolio_id, security_id, as_of)
    if not rows:
        con.close()
        raise HTTPException(
            status_code=404,
            detail=f"No transactions for {security_id} in {portfolio_id} as of {as_of}.",
        )
    try:
        current_price = fetch_current_price(con, security_id)
    except ValueError as e:
        con.close()
        raise HTTPException(status_code=404, detail=str(e))
    con.close()

    transactions = [
        Transaction(
            trade_date=r[0],
            txn_type=TransactionType(r[1]),
            quantity=r[2],
            price=r[3],
        )
        for r in rows
    ]
    try:
        pnl = compute_fifo_pnl(transactions)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return PnLResponse(
        portfolio_id=portfolio_id,
        security_id=security_id,
        as_of=str(as_of),
        realized_pnl=pnl.total_realized_pnl,
        unrealized_pnl=pnl.unrealized_pnl(current_price),
        total_pnl=pnl.total_pnl(current_price),
        open_quantity=pnl.open_quantity(),
        current_price=current_price,
    )
