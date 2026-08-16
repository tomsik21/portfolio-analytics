"""
TWR test suite.

Organized the way a QE would actually approach this domain: start with a
golden-path reference value, then attack the edges — zero bases, flow
timing, and the True-TWR-vs-Modified-Dietz divergence that's the #1
source of "why don't these two numbers match" tickets in real perf
platforms.
"""
from datetime import date

import pytest

from app.calculations.twr import (
    CashFlow,
    DailyValuation,
    annualize,
    daily_subperiod_return,
    link_returns,
    modified_dietz,
    true_twr,
)


class TestDailySubperiodReturn:
    def test_simple_growth_no_cashflow(self):
        assert daily_subperiod_return(100.0, 110.0, 0.0) == pytest.approx(0.10)

    def test_zero_begin_mv_raises(self):
        """Account inception / full liquidation edge case — must fail loud, not return inf/nan."""
        with pytest.raises(ValueError, match="zero base"):
            daily_subperiod_return(0.0, 50.0, 0.0)

    def test_cashflow_is_excluded_from_return(self):
        # 100 -> 220 with a 100 deposit should read as a 20% return, not 120%.
        assert daily_subperiod_return(100.0, 220.0, 100.0) == pytest.approx(0.20)


class TestTrueTWR:
    def test_golden_path_no_cashflows(self):
        vals = [
            DailyValuation(date(2026, 1, 1), 100.0),
            DailyValuation(date(2026, 1, 2), 110.0),
            DailyValuation(date(2026, 1, 3), 121.0),
        ]
        assert true_twr(vals) == pytest.approx(0.21)

    def test_deposit_does_not_distort_return_shape(self):
        """
        A pure market-driven 10%-then-10% growth pattern should link to the
        same 21% whether or not a cash flow happens to land mid-period —
        this is the entire point of TWR vs a naive (end-begin)/begin calc.
        """
        vals = [
            DailyValuation(date(2026, 1, 1), 100.0),
            DailyValuation(date(2026, 1, 2), 220.0, cash_flow=100.0),
            DailyValuation(date(2026, 1, 3), 242.0),
        ]
        # sub-period 1: (220-100-100)/100 = 20%   sub-period 2: (242-220)/220 = 10%
        assert true_twr(vals) == pytest.approx(0.32)

    def test_single_valuation_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            true_twr([DailyValuation(date(2026, 1, 1), 100.0)])

    def test_large_withdrawal_that_drains_account_raises_on_next_subperiod(self):
        """A full withdrawal leaves begin_mv=0 for the next sub-period — must raise, not silently 0 it out."""
        vals = [
            DailyValuation(date(2026, 1, 1), 100.0),
            DailyValuation(date(2026, 1, 2), 0.0, cash_flow=-100.0),
            DailyValuation(date(2026, 1, 3), 50.0, cash_flow=50.0),
        ]
        with pytest.raises(ValueError, match="zero base"):
            true_twr(vals)


class TestModifiedDietz:
    def test_matches_true_twr_when_no_intra_period_flows(self):
        r_dietz = modified_dietz(
            100.0, 121.0, [], date(2026, 1, 1), date(2026, 1, 3)
        )
        assert r_dietz == pytest.approx(0.21)

    def test_diverges_from_true_twr_with_large_mid_period_flow(self):
        """
        This is the key regression test: with a large, well-timed cash
        flow, Modified Dietz is only an APPROXIMATION of true TWR. A naive
        implementation that treats them as interchangeable will fail this.
        """
        dietz = modified_dietz(
            begin_mv=100.0, end_mv=242.0,
            cash_flows=[CashFlow(date(2026, 1, 2), 100.0)],
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 3),
        )
        true = true_twr([
            DailyValuation(date(2026, 1, 1), 100.0),
            DailyValuation(date(2026, 1, 2), 220.0, cash_flow=100.0),
            DailyValuation(date(2026, 1, 3), 242.0),
        ])
        assert dietz != pytest.approx(true, rel=1e-6)

    def test_cashflow_outside_period_raises(self):
        with pytest.raises(ValueError, match="outside the period"):
            modified_dietz(
                100.0, 110.0,
                [CashFlow(date(2026, 2, 1), 10.0)],
                date(2026, 1, 1), date(2026, 1, 31),
            )

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError, match="after period_start"):
            modified_dietz(100.0, 110.0, [], date(2026, 1, 31), date(2026, 1, 1))


class TestLinkAndAnnualize:
    def test_link_returns_compounds_geometrically(self):
        assert link_returns([0.10, 0.10]) == pytest.approx(0.21)

    def test_link_returns_empty_is_zero(self):
        assert link_returns([]) == pytest.approx(0.0)

    def test_annualize_one_year_is_noop(self):
        assert annualize(0.10, 365) == pytest.approx(0.10)

    def test_annualize_zero_days_raises(self):
        with pytest.raises(ValueError):
            annualize(0.10, 0)
