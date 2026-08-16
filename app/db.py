"""
DuckDB-backed data layer.

DuckDB stands in here for the "modern OLAP and Columnar technologies"
the JD references (production equivalents: ClickHouse, Druid, Snowflake).
It's the right learning tool for this because it's columnar, vectorized,
speaks full SQL, and needs zero infrastructure — you get the same
analytical-query mental model (scan-heavy aggregations over time series)
that a real perf/attribution platform runs on, without standing up a
cluster.

Schema is deliberately close to how a real front-office performance
system models this: positions/transactions feed P&L, daily valuations
feed TWR, and sector-level portfolio-vs-benchmark rows feed attribution.
"""
from __future__ import annotations

import duckdb


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id VARCHAR PRIMARY KEY,
    portfolio_name VARCHAR NOT NULL,
    benchmark_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_valuations (
    portfolio_id VARCHAR NOT NULL,
    valuation_date DATE NOT NULL,
    market_value DOUBLE NOT NULL,
    cash_flow DOUBLE NOT NULL DEFAULT 0.0,
    PRIMARY KEY (portfolio_id, valuation_date)
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id INTEGER,
    portfolio_id VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    txn_type VARCHAR NOT NULL,   -- 'BUY' | 'SELL'
    quantity DOUBLE NOT NULL,
    price DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS sector_returns (
    portfolio_id VARCHAR NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    sector VARCHAR NOT NULL,
    portfolio_weight DOUBLE NOT NULL,
    benchmark_weight DOUBLE NOT NULL,
    portfolio_return DOUBLE NOT NULL,
    benchmark_return DOUBLE NOT NULL,
    PRIMARY KEY (portfolio_id, period_start, period_end, sector)
);

CREATE TABLE IF NOT EXISTS current_prices (
    security_id VARCHAR PRIMARY KEY,
    price DOUBLE NOT NULL
);
"""


def get_connection(db_path: str = "portfolio_analytics.duckdb") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(db_path)
    con.execute(SCHEMA_SQL)
    return con


def fetch_daily_valuations(con: duckdb.DuckDBPyConnection, portfolio_id: str,
                            start, end) -> list[tuple]:
    return con.execute(
        """
        SELECT valuation_date, market_value, cash_flow
        FROM daily_valuations
        WHERE portfolio_id = ? AND valuation_date BETWEEN ? AND ?
        ORDER BY valuation_date ASC
        """,
        [portfolio_id, start, end],
    ).fetchall()


def fetch_sector_returns(con: duckdb.DuckDBPyConnection, portfolio_id: str,
                          start, end) -> list[tuple]:
    return con.execute(
        """
        SELECT sector, portfolio_weight, benchmark_weight,
               portfolio_return, benchmark_return
        FROM sector_returns
        WHERE portfolio_id = ? AND period_start = ? AND period_end = ?
        """,
        [portfolio_id, start, end],
    ).fetchall()


def fetch_transactions(con: duckdb.DuckDBPyConnection, portfolio_id: str,
                        security_id: str, as_of) -> list[tuple]:
    return con.execute(
        """
        SELECT trade_date, txn_type, quantity, price
        FROM transactions
        WHERE portfolio_id = ? AND security_id = ? AND trade_date <= ?
        ORDER BY trade_date ASC, txn_id ASC
        """,
        [portfolio_id, security_id, as_of],
    ).fetchall()


def fetch_current_price(con: duckdb.DuckDBPyConnection, security_id: str) -> float:
    row = con.execute(
        "SELECT price FROM current_prices WHERE security_id = ?", [security_id]
    ).fetchone()
    if row is None:
        raise ValueError(f"No current price found for security {security_id}")
    return row[0]
