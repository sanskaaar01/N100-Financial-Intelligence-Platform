import sqlite3
from pathlib import Path

import pytest

DB = Path("db/nifty100.db")


@pytest.fixture
def conn():
    assert DB.exists()
    c = sqlite3.connect(DB)
    yield c
    c.close()


@pytest.mark.parametrize(
    "table, minimum",
    [
        ("companies", 92),
        ("financial_ratios", 1100),
        ("profitandloss", 1000),
        ("balancesheet", 1000),
        ("cashflow", 1000),
        ("market_cap", 1),
        ("sectors", 92),
        ("documents", 1),
        ("peer_groups", 1),
        ("prosandcons", 1),
    ],
)
def test_table_row_count(conn, table, minimum):
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    assert count >= minimum


@pytest.mark.parametrize(
    "table, required",
    [
        ("companies", ["id", "company_name"]),
        ("financial_ratios", ["company_id", "year"]),
        ("profitandloss", ["company_id", "year"]),
        ("balancesheet", ["company_id", "year"]),
        ("cashflow", ["company_id", "year"]),
        ("market_cap", ["company_id", "year"]),
        ("sectors", ["company_id", "broad_sector"]),
        ("documents", ["company_id"]),
        ("peer_groups", ["company_id"]),
        ("prosandcons", ["company_id"]),
    ],
)
def test_required_columns(conn, table, required):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    for column in required:
        assert column in columns
