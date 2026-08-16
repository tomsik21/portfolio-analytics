"""
API-level tests. These hit the real FastAPI app wired to a real (seeded,
temp-file) DuckDB instance — this is the layer that catches integration
bugs the pure calc-engine unit tests can't see: wrong SQL, bad param
binding, response-model mismatches, and HTTP status/contract regressions.
"""
import pytest


class TestHealthCheck:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestTWREndpoint:
    def test_twr_golden_path(self, client):
        resp = client.get(
            "/portfolios/PORT1/performance/twr",
            params={"start": "2026-01-01", "end": "2026-01-03"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["twr"] == pytest.approx(0.32, abs=1e-6)
        assert body["num_subperiods"] == 2

    def test_twr_unknown_portfolio_returns_422_not_500(self, client):
        """
        A missing portfolio should surface as a client-correctable error
        (not enough valuations found), not an unhandled server exception.
        """
        resp = client.get(
            "/portfolios/DOES_NOT_EXIST/performance/twr",
            params={"start": "2026-01-01", "end": "2026-01-03"},
        )
        assert resp.status_code == 422

    def test_twr_malformed_date_returns_422(self, client):
        resp = client.get(
            "/portfolios/PORT1/performance/twr",
            params={"start": "not-a-date", "end": "2026-01-03"},
        )
        assert resp.status_code == 422

    def test_twr_single_day_range_returns_422(self, client):
        """Range with fewer than 2 valuations must be rejected explicitly."""
        resp = client.get(
            "/portfolios/PORT1/performance/twr",
            params={"start": "2026-01-01", "end": "2026-01-01"},
        )
        assert resp.status_code == 422


class TestAttributionEndpoint:
    def test_attribution_golden_path_reconciles(self, client):
        resp = client.get(
            "/portfolios/PORT1/attribution/brinson",
            params={"start": "2026-01-01", "end": "2026-01-31"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["reconciliation_delta"] == pytest.approx(0.0, abs=1e-6)
        assert len(body["sectors"]) == 3
        assert body["active_return"] == pytest.approx(
            body["portfolio_total_return"] - body["benchmark_total_return"]
        )

    def test_attribution_missing_period_returns_404(self, client):
        resp = client.get(
            "/portfolios/PORT1/attribution/brinson",
            params={"start": "2020-01-01", "end": "2020-01-31"},
        )
        assert resp.status_code == 404


class TestPnLEndpoint:
    def test_pnl_golden_path(self, client):
        resp = client.get(
            "/portfolios/PORT1/pnl",
            params={"security_id": "AAPL_DEMO", "as_of": "2026-01-31"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["realized_pnl"] == pytest.approx(560.0)
        assert body["open_quantity"] == pytest.approx(30.0)
        assert body["unrealized_pnl"] == pytest.approx(30.0 * (16.0 - 12.0))

    def test_pnl_as_of_date_before_any_trades_returns_404(self, client):
        """as_of filtering must actually be applied server-side, not ignored."""
        resp = client.get(
            "/portfolios/PORT1/pnl",
            params={"security_id": "AAPL_DEMO", "as_of": "2025-01-01"},
        )
        assert resp.status_code == 404

    def test_pnl_unknown_security_returns_404(self, client):
        resp = client.get(
            "/portfolios/PORT1/pnl",
            params={"security_id": "NOT_A_SECURITY", "as_of": "2026-01-31"},
        )
        assert resp.status_code == 404
