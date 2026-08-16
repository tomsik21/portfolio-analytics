"""
Brinson attribution test suite.

The single most important property of an attribution engine is that the
effects RECONCILE — allocation + selection + interaction must sum to the
total active return, exactly. Every test here either verifies that
invariant directly or verifies the guardrails that protect it (weight
validation, empty input handling).
"""
import pytest

from app.calculations.brinson import (
    SectorData,
    brinson_fachler,
    compute_benchmark_return,
    compute_portfolio_return,
)


@pytest.fixture
def three_sector_data():
    return [
        SectorData("Tech", 0.50, 0.30, 0.10, 0.08),
        SectorData("Energy", 0.20, 0.30, 0.02, 0.05),
        SectorData("Health", 0.30, 0.40, 0.06, 0.04),
    ]


class TestBrinsonFachler:
    def test_reconciliation_invariant_holds(self, three_sector_data):
        """The core regression test: sum(effects) must equal active return."""
        result = brinson_fachler(three_sector_data)
        assert result.reconciliation_delta == pytest.approx(0.0, abs=1e-9)

    def test_active_return_matches_manual_calc(self, three_sector_data):
        result = brinson_fachler(three_sector_data)
        rp = compute_portfolio_return(three_sector_data)
        rb = compute_benchmark_return(three_sector_data)
        assert result.active_return == pytest.approx(rp - rb)

    def test_pure_overweight_no_selection_skill_isolates_allocation(self):
        """
        Overweighting a sector that matches the benchmark's return exactly
        (rp_i == rb_i) should produce a NONZERO allocation effect but ZERO
        selection and interaction effects for that sector — this isolates
        whether the allocation formula is wired correctly.
        """
        sectors = [
            SectorData("Tech", portfolio_weight=0.60, benchmark_weight=0.30,
                       portfolio_return=0.08, benchmark_return=0.08),
            SectorData("Rest", portfolio_weight=0.40, benchmark_weight=0.70,
                       portfolio_return=0.05, benchmark_return=0.05),
        ]
        result = brinson_fachler(sectors)
        tech = next(s for s in result.sector_results if s.sector == "Tech")
        assert tech.selection_effect == pytest.approx(0.0, abs=1e-12)
        assert tech.interaction_effect == pytest.approx(0.0, abs=1e-12)
        assert tech.allocation_effect != pytest.approx(0.0, abs=1e-9)

    def test_matched_weights_isolates_selection(self):
        """wp_i == wb_i for every sector should zero out allocation AND interaction everywhere."""
        sectors = [
            SectorData("Tech", 0.5, 0.5, 0.12, 0.08),
            SectorData("Rest", 0.5, 0.5, 0.04, 0.05),
        ]
        result = brinson_fachler(sectors)
        for s in result.sector_results:
            assert s.allocation_effect == pytest.approx(0.0, abs=1e-12)
            assert s.interaction_effect == pytest.approx(0.0, abs=1e-12)

    def test_portfolio_weights_not_summing_to_one_raises(self):
        sectors = [
            SectorData("Tech", 0.5, 0.5, 0.1, 0.1),
            SectorData("Energy", 0.3, 0.5, 0.1, 0.1),  # portfolio sums to 0.8
        ]
        with pytest.raises(ValueError, match="Portfolio weights sum"):
            brinson_fachler(sectors)

    def test_benchmark_weights_not_summing_to_one_raises(self):
        sectors = [
            SectorData("Tech", 0.5, 0.4, 0.1, 0.1),
            SectorData("Energy", 0.5, 0.4, 0.1, 0.1),  # benchmark sums to 0.8
        ]
        with pytest.raises(ValueError, match="Benchmark weights sum"):
            brinson_fachler(sectors)

    def test_empty_sectors_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            brinson_fachler([])

    def test_zero_active_return_zero_sum_effects(self):
        """When the portfolio exactly mirrors the benchmark, every effect should net to zero."""
        sectors = [
            SectorData("Tech", 0.3, 0.3, 0.05, 0.05),
            SectorData("Energy", 0.3, 0.3, 0.02, 0.02),
            SectorData("Health", 0.4, 0.4, 0.03, 0.03),
        ]
        result = brinson_fachler(sectors)
        assert result.active_return == pytest.approx(0.0, abs=1e-12)
        assert result.total_allocation_effect == pytest.approx(0.0, abs=1e-12)
        assert result.total_selection_effect == pytest.approx(0.0, abs=1e-12)
        assert result.total_interaction_effect == pytest.approx(0.0, abs=1e-12)
