"""Pytest fixtures for orchestrator tests."""
import pytest
import psycopg
from psycopg.rows import dict_row
import os


@pytest.fixture(scope="session")
def db_url():
    """Database URL for tests. Uses test database."""
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://agency:test@localhost:5432/agency_test"
    )


@pytest.fixture(scope="function")
def test_db(db_url):
    """Fresh database connection with transaction rollback after each test."""
    conn = psycopg.connect(db_url, row_factory=dict_row)

    # Start transaction
    conn.execute("BEGIN")

    # Clean tables
    conn.execute("DELETE FROM pipeline_metrics")
    conn.execute("DELETE FROM agency_events")
    conn.execute("DELETE FROM agency_tasks")
    conn.execute("DELETE FROM agency_metrics_hourly")
    conn.execute("DELETE FROM agency_live_snapshot")

    yield conn

    # Rollback after test
    conn.execute("ROLLBACK")
    conn.close()
