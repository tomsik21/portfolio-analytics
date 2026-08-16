"""
ETL data-quality test suite.

Runs against data/sample_feeds/, which is DELIBERATELY dirty (duplicate
txn_id, negative quantity, unparseable date, invalid txn_type, missing
txn_id, negative market_value) — this is the sample a QE would actually
build to pressure-test a pipeline's guardrails before it ever sees a
real custodian feed.
"""
import os
import sqlite3

import pytest

from app.etl import load_daily_valuations_csv, load_transactions_csv

FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "sample_feeds"
)


@pytest.fixture
def sqlite_con():
    """
    A plain sqlite3 connection standing in for DuckDB here — the ETL
    functions only use portable parameterized SQL (executemany with
    '?' placeholders), so this exercises the exact same code path
    against a real database, not a mock.
    """
    con = sqlite3.connect(":memory:")
    con.execute(
        """CREATE TABLE transactions (
        txn_id INTEGER, portfolio_id TEXT, security_id TEXT, trade_date TEXT,
        txn_type TEXT, quantity REAL, price REAL)"""
    )
    con.execute(
        """CREATE TABLE daily_valuations (
        portfolio_id TEXT, valuation_date TEXT, market_value REAL, cash_flow REAL)"""
    )
    yield con
    con.close()


class TestTransactionETL:
    def test_dirty_feed_rejects_expected_rows(self, sqlite_con):
        report = load_transactions_csv(
            sqlite_con, os.path.join(FIXTURES_DIR, "transactions_raw.csv")
        )
        assert report.rows_read == 8
        assert report.rows_loaded == 3
        assert report.rows_rejected == 5

    def test_duplicate_txn_id_is_rejected_not_double_loaded(self, sqlite_con):
        report = load_transactions_csv(
            sqlite_con, os.path.join(FIXTURES_DIR, "transactions_raw.csv")
        )
        reasons = [i.reason for i in report.issues]
        assert any("duplicate txn_id" in r for r in reasons)
        loaded = sqlite_con.execute("SELECT txn_id FROM transactions").fetchall()
        txn_ids = [row[0] for row in loaded]
        assert txn_ids.count(3) == 1  # not loaded twice

    def test_negative_quantity_rejected(self, sqlite_con):
        report = load_transactions_csv(
            sqlite_con, os.path.join(FIXTURES_DIR, "transactions_raw.csv")
        )
        assert any("non-positive quantity" in i.reason for i in report.issues)

    def test_invalid_txn_type_rejected(self, sqlite_con):
        report = load_transactions_csv(
            sqlite_con, os.path.join(FIXTURES_DIR, "transactions_raw.csv")
        )
        assert any("invalid txn_type" in i.reason for i in report.issues)

    def test_unparseable_date_rejected(self, sqlite_con):
        report = load_transactions_csv(
            sqlite_con, os.path.join(FIXTURES_DIR, "transactions_raw.csv")
        )
        assert any("unparseable date" in i.reason for i in report.issues)

    def test_clean_rows_have_correct_types_in_db(self, sqlite_con):
        load_transactions_csv(
            sqlite_con, os.path.join(FIXTURES_DIR, "transactions_raw.csv")
        )
        row = sqlite_con.execute(
            "SELECT txn_id, quantity, price FROM transactions WHERE txn_id = 1"
        ).fetchone()
        assert row == (1, 200.0, 50.0)


class TestValuationETL:
    def test_dirty_feed_rejects_expected_rows(self, sqlite_con):
        report = load_daily_valuations_csv(
            sqlite_con, os.path.join(FIXTURES_DIR, "valuations_raw.csv")
        )
        assert report.rows_read == 5
        assert report.rows_loaded == 3
        assert report.rows_rejected == 2

    def test_negative_market_value_rejected(self, sqlite_con):
        report = load_daily_valuations_csv(
            sqlite_con, os.path.join(FIXTURES_DIR, "valuations_raw.csv")
        )
        assert any("negative market_value" in i.reason for i in report.issues)

    def test_zero_market_value_is_loaded_not_rejected(self, sqlite_con, tmp_path):
        """
        Zero MV is a legitimate (if rare) fully-liquidated state — the
        ETL layer should NOT reject it; true_twr() already has a defined
        error path for zero-base sub-periods downstream. Rejecting it
        here would silently hide account-closure events from reporting.
        """
        csv_path = tmp_path / "zero_mv.csv"
        csv_path.write_text(
            "portfolio_id,valuation_date,market_value,cash_flow\n"
            "PORT9,2026-01-01,0,0\n"
        )
        report = load_daily_valuations_csv(sqlite_con, csv_path)
        assert report.rows_loaded == 1
        assert report.rows_rejected == 0


class TestReportSummary:
    def test_reject_rate_computed_correctly(self, sqlite_con):
        report = load_transactions_csv(
            sqlite_con, os.path.join(FIXTURES_DIR, "transactions_raw.csv")
        )
        assert report.reject_rate == pytest.approx(5 / 8)

    def test_empty_read_has_zero_reject_rate_not_divide_by_zero(self):
        from app.etl import DataQualityReport

        report = DataQualityReport(source_file="empty.csv")
        assert report.reject_rate == 0.0
