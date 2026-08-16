"""
Brinson-Fachler performance attribution.

Decomposes a portfolio's active return (portfolio return - benchmark return)
into three effects at each sector/segment level:

  Allocation effect_i = (wp_i - wb_i) * (rb_i - rb_total)
      Reward/penalty for over/underweighting sector i relative to the
      benchmark, regardless of stock selection skill within the sector.

  Selection effect_i  = wb_i * (rp_i - rb_i)
      Reward/penalty for security selection within sector i, holding the
      benchmark's sector weight constant.

  Interaction effect_i = (wp_i - wb_i) * (rp_i - rb_i)
      Captures the cross-term between allocation and selection decisions.
      Some shops fold this into selection; we report it separately (the
      Brinson-Fachler standard) since collapsing it silently is a common
      source of reconciliation breaks between vendor platforms.

Where:
  wp_i, wb_i = portfolio / benchmark weight of sector i
  rp_i, rb_i = portfolio / benchmark return of sector i
  rb_total   = total benchmark return = sum(wb_i * rb_i)

Invariant that MUST hold (this is the key regression test for any
attribution engine): sum of all three effects across all sectors equals
the total active return (rp_total - rb_total), to within floating point
tolerance.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectorData:
    sector: str
    portfolio_weight: float   # wp_i, e.g. 0.25 for 25%
    benchmark_weight: float   # wb_i
    portfolio_return: float   # rp_i, e.g. 0.05 for 5%
    benchmark_return: float   # rb_i


@dataclass(frozen=True)
class SectorAttribution:
    sector: str
    allocation_effect: float
    selection_effect: float
    interaction_effect: float

    @property
    def total_effect(self) -> float:
        return self.allocation_effect + self.selection_effect + self.interaction_effect


@dataclass(frozen=True)
class AttributionResult:
    sector_results: list[SectorAttribution]
    portfolio_total_return: float
    benchmark_total_return: float

    @property
    def active_return(self) -> float:
        return self.portfolio_total_return - self.benchmark_total_return

    @property
    def total_allocation_effect(self) -> float:
        return sum(s.allocation_effect for s in self.sector_results)

    @property
    def total_selection_effect(self) -> float:
        return sum(s.selection_effect for s in self.sector_results)

    @property
    def total_interaction_effect(self) -> float:
        return sum(s.interaction_effect for s in self.sector_results)

    @property
    def reconciliation_delta(self) -> float:
        """
        Should be ~0. This is the number a QE should assert against in
        every attribution test: sum(effects) - active_return.
        """
        summed = (
            self.total_allocation_effect
            + self.total_selection_effect
            + self.total_interaction_effect
        )
        return summed - self.active_return


def compute_portfolio_return(sectors: list[SectorData]) -> float:
    return sum(s.portfolio_weight * s.portfolio_return for s in sectors)


def compute_benchmark_return(sectors: list[SectorData]) -> float:
    return sum(s.benchmark_weight * s.benchmark_return for s in sectors)


def brinson_fachler(sectors: list[SectorData]) -> AttributionResult:
    """
    Compute Brinson-Fachler sector-level attribution.

    Validates that portfolio and benchmark weights each sum to ~1.0
    (within tolerance) before computing — a common data-integrity bug
    in real pipelines is silently dropping a sector's benchmark weight,
    which this catches immediately rather than producing a subtly wrong
    attribution number downstream.
    """
    if not sectors:
        raise ValueError("sectors must not be empty.")

    wp_sum = sum(s.portfolio_weight for s in sectors)
    wb_sum = sum(s.benchmark_weight for s in sectors)
    tol = 1e-6
    if abs(wp_sum - 1.0) > tol:
        raise ValueError(f"Portfolio weights sum to {wp_sum:.6f}, expected 1.0 (+-{tol}).")
    if abs(wb_sum - 1.0) > tol:
        raise ValueError(f"Benchmark weights sum to {wb_sum:.6f}, expected 1.0 (+-{tol}).")

    rb_total = compute_benchmark_return(sectors)
    rp_total = compute_portfolio_return(sectors)

    sector_results = []
    for s in sectors:
        allocation = (s.portfolio_weight - s.benchmark_weight) * (s.benchmark_return - rb_total)
        selection = s.benchmark_weight * (s.portfolio_return - s.benchmark_return)
        interaction = (s.portfolio_weight - s.benchmark_weight) * (
            s.portfolio_return - s.benchmark_return
        )
        sector_results.append(
            SectorAttribution(
                sector=s.sector,
                allocation_effect=allocation,
                selection_effect=selection,
                interaction_effect=interaction,
            )
        )

    return AttributionResult(
        sector_results=sector_results,
        portfolio_total_return=rp_total,
        benchmark_total_return=rb_total,
    )
