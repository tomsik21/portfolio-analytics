"""
Time-Weighted Return (TWR) calculations.

TWR isolates portfolio manager performance from the distorting effect of
investor-driven cash flows (deposits/withdrawals). This is the standard
GIPS-compliant methodology for reporting investment performance.

Two methods are implemented:
  1. True (daily-valued) TWR — geometrically links daily sub-period returns.
     This is the gold-standard method and what production systems use when
     daily valuations are available.
  2. Modified Dietz — a money-weighted approximation used when only
     beginning/ending values and cash flow dates/amounts are available
     (no daily valuations). Included because QE engineers validating a
     performance platform need to know WHEN these two methods should and
     should not agree — that divergence is a classic source of production
     bugs and a great source of test cases.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True)
class CashFlow:
    flow_date: date
    amount: float  # positive = contribution (money in), negative = withdrawal


@dataclass(frozen=True)
class DailyValuation:
    valuation_date: date
    market_value: float
    # Cash flows that occurred ON this date, assumed to land at start of day
    # (i.e. included in market_value already per most custodial conventions).
    cash_flow: float = 0.0


def daily_subperiod_return(begin_mv: float, end_mv: float, cash_flow: float) -> float:
    """
    Single sub-period return, isolating the cash flow's effect.

    r = (EMV - CF - BMV) / BMV

    Convention: cash_flow is assumed to occur at the START of the period
    (already reflected in end_mv, not in begin_mv). This matches most
    custodial "beginning of day" cash flow conventions.

    Raises ValueError on a zero/negative beginning base — a fully
    liquidated-then-reseeded account is a genuine edge case that callers
    must handle explicitly (don't silently return 0 or inf).
    """
    if begin_mv == 0:
        raise ValueError(
            "begin_mv is 0 — cannot compute a sub-period return from a zero base. "
            "This typically happens on account inception or full liquidation; "
            "the caller should treat this as a new performance-start boundary."
        )
    return (end_mv - cash_flow - begin_mv) / begin_mv


def true_twr(valuations: Sequence[DailyValuation]) -> float:
    """
    True time-weighted return via geometric linking of daily sub-periods.

    valuations must be sorted ascending by date and include a valuation
    for every day a cash flow occurs (this is what "daily valued" means).
    """
    if len(valuations) < 2:
        raise ValueError("Need at least 2 valuations (begin + end) to compute TWR.")

    linked = 1.0
    for prev, curr in zip(valuations, valuations[1:]):
        r = daily_subperiod_return(prev.market_value, curr.market_value, curr.cash_flow)
        linked *= (1.0 + r)
    return linked - 1.0


def modified_dietz(
    begin_mv: float,
    end_mv: float,
    cash_flows: Sequence[CashFlow],
    period_start: date,
    period_end: date,
) -> float:
    """
    Modified Dietz return — a money-weighted approximation of TWR.

    R = (EMV - BMV - CF) / (BMV + sum(CF_i * W_i))

    where W_i is the fraction of the period each cash flow was invested:
    W_i = (period_end - flow_date) / (period_end - period_start)

    This APPROXIMATES true TWR and will diverge from it when cash flows
    are large relative to the portfolio and/or poorly timed relative to
    market moves within the period — exactly the scenario a QE should
    write regression tests around, since the two methods are often (and
    incorrectly) treated as interchangeable in naive implementations.
    """
    total_days = (period_end - period_start).days
    if total_days <= 0:
        raise ValueError("period_end must be after period_start.")

    net_cf = sum(cf.amount for cf in cash_flows)
    weighted_cf = 0.0
    for cf in cash_flows:
        if not (period_start <= cf.flow_date <= period_end):
            raise ValueError(f"cash flow on {cf.flow_date} is outside the period.")
        weight = (period_end - cf.flow_date).days / total_days
        weighted_cf += cf.amount * weight

    denominator = begin_mv + weighted_cf
    if denominator == 0:
        raise ValueError(
            "Modified Dietz denominator is 0 (begin_mv + weighted cash flows). "
            "Cannot compute a return; check for a fully-funded-mid-period account."
        )
    return (end_mv - begin_mv - net_cf) / denominator


def annualize(period_return: float, num_days: int) -> float:
    """
    Annualize a return over num_days using a 365-day compounding convention.
    Sub-annual periods (<365 days) are NOT annualized per GIPS guidance —
    callers should gate this themselves; it's exposed here as a pure
    utility function so that rule can be tested independently.
    """
    if num_days <= 0:
        raise ValueError("num_days must be positive.")
    return (1.0 + period_return) ** (365.0 / num_days) - 1.0


def link_returns(returns: Sequence[float]) -> float:
    """Geometrically link a sequence of periodic returns into one cumulative return."""
    linked = 1.0
    for r in returns:
        linked *= (1.0 + r)
    return linked - 1.0
