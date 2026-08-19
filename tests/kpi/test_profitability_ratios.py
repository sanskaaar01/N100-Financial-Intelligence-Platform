import pytest

from src.analytics.ratios import (
    check_opm_crosscheck,
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)

# ============================================================
# TEST 1 - Normal Net Profit Margin
# ============================================================


def test_net_profit_margin_normal():
    result = net_profit_margin(200, 1000)

    assert result == pytest.approx(20.0)


# ============================================================
# TEST 2 - Zero Sales
# ============================================================


def test_net_profit_margin_zero_sales():
    result = net_profit_margin(200, 0)

    assert result is None


# ============================================================
# TEST 3 - Normal ROE
# ============================================================


def test_return_on_equity_normal():
    result = return_on_equity(
        net_profit=200,
        equity_capital=300,
        reserves=700,
    )

    assert result == pytest.approx(20.0)


# ============================================================
# TEST 4 - Negative Equity
# ============================================================


def test_return_on_equity_negative_equity():
    result = return_on_equity(
        net_profit=200,
        equity_capital=-500,
        reserves=100,
    )

    assert result is None


# ============================================================
# TEST 5 - Normal OPM
# ============================================================


def test_operating_profit_margin_normal():
    result = operating_profit_margin(
        operating_profit=250,
        sales=1000,
    )

    assert result == pytest.approx(25.0)


# ============================================================
# TEST 6 - OPM Cross-check Mismatch
# ============================================================


def test_opm_crosscheck_mismatch():
    calculated = operating_profit_margin(
        operating_profit=250,
        sales=1000,
    )

    result = check_opm_crosscheck(
        calculated_opm=calculated,
        source_opm=22.0,
    )

    assert result["difference"] == pytest.approx(3.0)
    assert result["mismatch"] is True


# ============================================================
# TEST 7 - Normal ROCE
# ============================================================


def test_return_on_capital_employed_normal():
    result = return_on_capital_employed(
        operating_profit=200,
        other_income=50,
        equity_capital=500,
        reserves=500,
        borrowings=500,
    )

    assert result == pytest.approx(16.6666667)


# ============================================================
# TEST 8 - ROA Zero Assets
# ============================================================


def test_return_on_assets_zero_assets():
    result = return_on_assets(
        net_profit=200,
        total_assets=0,
    )

    assert result is None
