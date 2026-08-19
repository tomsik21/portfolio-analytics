import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app
from app.seed_data import seed


@pytest.fixture(scope="session", autouse=True)
def seeded_db(tmp_path_factory):
    """
    Seed a fresh DuckDB file once per test session. Using a real (temp)
    file rather than mocking the DB layer is intentional: this suite is
    meant to catch SQL/schema regressions too, not just calc-engine bugs.
    """
    db_path = str(tmp_path_factory.mktemp("db") / "test_portfolio_analytics.duckdb")
    seed(db_path)
    # app.db.get_connection() defaults to a relative path; point it at ours
    os.environ["PERF_ANALYTICS_DB_PATH"] = db_path
    import app.db as db_module

    original_get_connection = db_module.get_connection

    def _patched_get_connection(path: str = db_path, read_only: bool = False):
        return original_get_connection(path, read_only=read_only)

    db_module.get_connection = _patched_get_connection
    yield db_path
    db_module.get_connection = original_get_connection


@pytest.fixture
def client():
    return TestClient(app)
