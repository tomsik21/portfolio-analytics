"""
FIFO P&L test suite. Focus areas: lot-level correctness (not just
aggregate totals, since offsetting lot errors can hide behind a correct
sum), partial-lot sells that span multiple lots, and bad-data guardrails.
"""
from datetime import date

import pytest

from app.calculations.pnl import Transaction, TransactionType, compute_fifo_pnl

BUY = TransactionType.BUY
SELL = TransactionType.SELL


class TestFIFOPnL:
    def test_single_lot_full_sell(self):
        txns = [
            Transaction(date(2026, 1, 1), BUY, 100, 10.0),
            Transaction(date(2026, 1, 10), SELL, 100, 15.0),
        ]
        result = compute_fifo_pnl(txns)
        assert result.total_realized_pnl == pytest.approx(500.0)
        assert result.open_quantity() == pytest.approx(0.0)

    def test_sell_spans_multiple_lots_fifo_order(self):
        """
        100 @ 10, then 50 @ 12, then sell 120 — FIFO must consume the
        entire first lot (100 @ 10) before touching any of the second.
        Realized = 100*(15-10) + 20*(15-12) = 500 + 60 = 560.
        Remaining open lot must be 30 shares at the SECOND lot's cost basis (12),
        not a blended average — that's the classic FIFO-vs-average-cost bug.
        """
        txns = [
            Transaction(date(2026, 1, 1), BUY, 100, 10.0),
            Transaction(date(2026, 1, 5), BUY, 50, 12.0),
            Transaction(date(2026, 1, 10), SELL, 120, 15.0),
        ]
        result = compute_fifo_pnl(txns)
        assert result.total_realized_pnl == pytest.approx(560.0)
        assert result.open_quantity() == pytest.approx(30.0)
        assert len(result.remaining_lots) == 1
        assert result.remaining_lots[0].cost_basis_per_share == pytest.approx(12.0)

    def test_lot_level_gains_are_individually_correct(self):
        """Assert each realized lot separately — not just the aggregate — per the module's own warning."""
        txns = [
            Transaction(date(2026, 1, 1), BUY, 100, 10.0),
            Transaction(date(2026, 1, 5), BUY, 50, 12.0),
            Transaction(date(2026, 1, 10), SELL, 120, 15.0),
        ]
        result = compute_fifo_pnl(txns)
        assert len(result.realized_gains) == 2
        first, second = result.realized_gains
        assert first.quantity == pytest.approx(100.0)
        assert first.gain == pytest.approx(500.0)
        assert second.quantity == pytest.approx(20.0)
        assert second.gain == pytest.approx(60.0)

    def test_unrealized_pnl_uses_remaining_lot_cost_basis(self):
        txns = [
            Transaction(date(2026, 1, 1), BUY, 100, 10.0),
            Transaction(date(2026, 1, 5), BUY, 50, 12.0),
            Transaction(date(2026, 1, 10), SELL, 120, 15.0),
        ]
        result = compute_fifo_pnl(txns)
        assert result.unrealized_pnl(16.0) == pytest.approx(30.0 * (16.0 - 12.0))
        assert result.total_pnl(16.0) == pytest.approx(560.0 + 120.0)

    def test_sell_exceeding_open_position_raises(self):
        """No short-selling support — must fail loud rather than go negative-quantity silently."""
        txns = [
            Transaction(date(2026, 1, 1), BUY, 100, 10.0),
            Transaction(date(2026, 1, 10), SELL, 150, 15.0),
        ]
        with pytest.raises(ValueError, match="exceeds open position"):
            compute_fifo_pnl(txns)

    def test_zero_or_negative_quantity_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            compute_fifo_pnl([Transaction(date(2026, 1, 1), BUY, 0, 10.0)])
        with pytest.raises(ValueError, match="must be positive"):
            compute_fifo_pnl([Transaction(date(2026, 1, 1), BUY, -5, 10.0)])

    def test_no_transactions_yields_flat_zero_pnl(self):
        result = compute_fifo_pnl([])
        assert result.total_realized_pnl == pytest.approx(0.0)
        assert result.open_quantity() == pytest.approx(0.0)
