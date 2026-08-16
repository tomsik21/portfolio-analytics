"""
Populates the DuckDB store with a small, hand-checkable dataset:
  - Portfolio "PORT1" (benchmark "SPX-LIKE")
  - Daily valuations across Jan 2026 including one mid-month cash flow
  - Three sectors of Brinson attribution data for Jan 2026
  - A FIFO-testable transaction history for security "AAPL_DEMO"

Run directly: `python -m app.seed_data`
"""
from __future__ import annotations

from datetime import date

from app.db import get_connection


def seed(db_path: str = "portfolio_analytics.duckdb") -> None:
    con = get_connection(db_path)

    con.execute("DELETE FROM portfolios")
    con.execute("DELETE FROM daily_valuations")
    con.execute("DELETE FROM transactions")
    con.execute("DELETE FROM sector_returns")
    con.execute("DELETE FROM current_prices")

    con.execute(
        "INSERT INTO portfolios VALUES (?, ?, ?)",
        ["PORT1", "Demo Growth Portfolio", "SPX-LIKE"],
    )

    # Daily valuations: matches the TWR example verified in the calc engine —
    # a mid-period deposit of 100 on Jan 2 that should NOT distort TWR.
    valuations = [
        (date(2026, 1, 1), 100_000.0, 0.0),
        (date(2026, 1, 2), 220_000.0, 100_000.0),
        (date(2026, 1, 3), 242_000.0, 0.0),
    ]
    for vdate, mv, cf in valuations:
        con.execute(
            "INSERT INTO daily_valuations VALUES (?, ?, ?, ?)",
            ["PORT1", vdate, mv, cf],
        )

    # Brinson attribution sectors for the full-month period.
    sectors = [
        ("Tech", 0.50, 0.30, 0.10, 0.08),
        ("Energy", 0.20, 0.30, 0.02, 0.05),
        ("Health", 0.30, 0.40, 0.06, 0.04),
    ]
    for sector, wp, wb, rp, rb in sectors:
        con.execute(
            "INSERT INTO sector_returns VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ["PORT1", date(2026, 1, 1), date(2026, 1, 31), sector, wp, wb, rp, rb],
        )

    # FIFO-testable transaction history.
    transactions = [
        (1, "PORT1", "AAPL_DEMO", date(2026, 1, 1), "BUY", 100, 10.0),
        (2, "PORT1", "AAPL_DEMO", date(2026, 1, 5), "BUY", 50, 12.0),
        (3, "PORT1", "AAPL_DEMO", date(2026, 1, 10), "SELL", 120, 15.0),
    ]
    for txn_id, pid, sec, tdate, ttype, qty, price in transactions:
        con.execute(
            "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?)",
            [txn_id, pid, sec, tdate, ttype, qty, price],
        )

    con.execute("INSERT INTO current_prices VALUES (?, ?)", ["AAPL_DEMO", 16.0])

    con.close()
    print(f"Seeded {db_path}")


if __name__ == "__main__":
    seed()
