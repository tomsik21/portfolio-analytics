from __future__ import annotations

from pydantic import BaseModel


class TWRResponse(BaseModel):
    portfolio_id: str
    period_start: str
    period_end: str
    twr: float
    num_subperiods: int


class SectorAttributionResponse(BaseModel):
    sector: str
    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    total_effect: float


class AttributionResponse(BaseModel):
    portfolio_id: str
    period_start: str
    period_end: str
    portfolio_total_return: float
    benchmark_total_return: float
    active_return: float
    reconciliation_delta: float
    sectors: list[SectorAttributionResponse]


class PnLResponse(BaseModel):
    portfolio_id: str
    security_id: str
    as_of: str
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    open_quantity: float
    current_price: float
