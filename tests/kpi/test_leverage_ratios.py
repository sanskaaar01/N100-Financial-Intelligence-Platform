import pytest

from src.analytics.ratios import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_label,
    interest_coverage_ratio,
)

# ============================================================
# TEST 1 - Normal Debt-to-Equity
# ============================================================


def test_debt_to_equity_normal():
    result = debt_to_equity(
        borrowings=200,
        equity_capital=300,
        reserves=700,
    )

    assert result == pytest.approx(0.2)


# ============================================================
# TEST 2 - Debt-Free Company
# ============================================================


def test_debt_to_equity_debt_free():
    result = debt_to_equity(
        borrowings=0,
        equity_capital=300,
        reserves=700,
    )

    assert result == 0.0


# ============================================================
# TEST 3 - Negative Equity
# ============================================================


def test_debt_to_equity_negative_equity():
    result = debt_to_equity(
        borrowings=200,
        equity_capital=-500,
        reserves=100,
    )

    assert result is None


# ============================================================
# TEST 4 - Normal Interest Coverage
# ============================================================


def test_interest_coverage_normal():
    result = interest_coverage_ratio(
        operating_profit=200,
        other_income=50,
        interest=50,
    )

    assert result == pytest.approx(5.0)


# ============================================================
# TEST 5 - Zero Interest
# ============================================================


def test_interest_coverage_zero_interest():
    result = interest_coverage_ratio(
        operating_profit=200,
        other_income=50,
        interest=0,
    )

    assert result is None


# ============================================================
# TEST 6 - Debt-Free Label
# ============================================================


def test_interest_coverage_debt_free_label():
    icr = interest_coverage_ratio(
        operating_profit=200,
        other_income=50,
        interest=0,
    )

    label = interest_coverage_label(icr)

    assert label == "Debt Free"


# ============================================================
# TEST 7 - High Leverage Flag
# ============================================================


def test_high_leverage_flag():
    result = high_leverage_flag(
        debt_equity=6.0,
        broad_sector="Industrials",
    )

    assert result is True


# ============================================================
# TEST 8 - Financials High Leverage Suppressed
# ============================================================


def test_financials_high_leverage_suppressed():
    result = high_leverage_flag(
        debt_equity=10.0,
        broad_sector="Financials",
    )

    assert result is False
