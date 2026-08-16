"""
Realized / Unrealized Profit & Loss calculations using FIFO lot matching.

This is the piece of a performance platform most prone to silent
correctness bugs: lot matching convention (FIFO vs LIFO vs average cost),
corporate actions, and partial fills all change the "right" answer. This
module implements FIFO explicitly and exposes lot-level detail so a QE
can assert against individual lot P&L, not just the aggregate — aggregate
totals can look correct while offsetting lot-level errors cancel out.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Transaction:
    trade_date: date
    txn_type: TransactionType
    quantity: float  # always positive; direction comes from txn_type
    price: float


@dataclass
class Lot:
    open_date: date
    quantity: float  # remaining open quantity in this lot
    cost_basis_per_share: float


@dataclass(frozen=True)
class RealizedGain:
    close_date: date
    open_date: date
    quantity: float
    cost_basis_per_share: float
    proceeds_per_share: float

    @property
    def gain(self) -> float:
        return (self.proceeds_per_share - self.cost_basis_per_share) * self.quantity

    @property
    def holding_period_days(self) -> int:
        return (self.close_date - self.open_date).days


@dataclass
class PnLResult:
    realized_gains: list[RealizedGain] = field(default_factory=list)
    remaining_lots: list[Lot] = field(default_factory=list)

    @property
    def total_realized_pnl(self) -> float:
        return sum(g.gain for g in self.realized_gains)

    def unrealized_pnl(self, current_price: float) -> float:
        return sum(
            (current_price - lot.cost_basis_per_share) * lot.quantity
            for lot in self.remaining_lots
        )

    def total_pnl(self, current_price: float) -> float:
        return self.total_realized_pnl + self.unrealized_pnl(current_price)

    def open_quantity(self) -> float:
        return sum(lot.quantity for lot in self.remaining_lots)


def compute_fifo_pnl(transactions: list[Transaction]) -> PnLResult:
    """
    Process a chronological transaction list with FIFO lot matching.

    Transactions must be sorted ascending by trade_date; ties are
    processed in list order (caller's responsibility — this is a common
    source of off-by-one bugs when two trades clear same-day).
    """
    open_lots: list[Lot] = []
    realized: list[RealizedGain] = []

    for txn in transactions:
        if txn.quantity <= 0:
            raise ValueError(f"Transaction quantity must be positive, got {txn.quantity}.")

        if txn.txn_type == TransactionType.BUY:
            open_lots.append(
                Lot(
                    open_date=txn.trade_date,
                    quantity=txn.quantity,
                    cost_basis_per_share=txn.price,
                )
            )
        else:  # SELL
            remaining_to_sell = txn.quantity
            while remaining_to_sell > 1e-9:
                if not open_lots:
                    raise ValueError(
                        f"SELL of {txn.quantity} on {txn.trade_date} exceeds open "
                        f"position — short-selling is out of scope for this engine "
                        f"and likely indicates bad upstream data."
                    )
                oldest = open_lots[0]
                matched_qty = min(oldest.quantity, remaining_to_sell)

                realized.append(
                    RealizedGain(
                        close_date=txn.trade_date,
                        open_date=oldest.open_date,
                        quantity=matched_qty,
                        cost_basis_per_share=oldest.cost_basis_per_share,
                        proceeds_per_share=txn.price,
                    )
                )

                oldest.quantity -= matched_qty
                remaining_to_sell -= matched_qty
                if oldest.quantity <= 1e-9:
                    open_lots.pop(0)

    return PnLResult(realized_gains=realized, remaining_lots=open_lots)
