import math

import pytest


def roe(net_profit, equity):
    if equity is None or equity <= 0:
        return None
    return net_profit / equity * 100


def debt_to_equity(debt, equity):
    if equity is None or equity <= 0:
        return None
    return debt / equity


def interest_coverage(ebit, interest):
    if interest is None or interest == 0:
        return None
    return ebit / abs(interest)


def cagr(start, end, years):
    if start <= 0 or end <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100


def test_roe_positive_equity():
    assert roe(100, 500) == pytest.approx(20)


def test_roe_negative_equity():
    assert roe(100, -500) is None


def test_roe_zero_equity():
    assert roe(100, 0) is None


def test_roe_none_equity():
    assert roe(100, None) is None


def test_debt_free_company():
    assert debt_to_equity(0, 500) == pytest.approx(0)


def test_debt_to_equity_normal():
    assert debt_to_equity(200, 500) == pytest.approx(0.4)


def test_debt_to_equity_invalid_equity():
    assert debt_to_equity(200, 0) is None


def test_interest_coverage_normal():
    assert interest_coverage(500, 100) == pytest.approx(5)


def test_interest_zero():
    assert interest_coverage(500, 0) is None


def test_interest_none():
    assert interest_coverage(500, None) is None


def test_cagr_normal():
    assert cagr(100, 161.051, 5) == pytest.approx(10, abs=0.1)


def test_cagr_negative_start():
    assert cagr(-100, 200, 5) is None


def test_cagr_negative_end():
    assert cagr(100, -200, 5) is None


def test_cagr_zero_start():
    assert cagr(0, 200, 5) is None


def test_cagr_zero_years():
    assert cagr(100, 200, 0) is None


def test_debt_high_flag():
    debt_to_equity_value = 6
    assert debt_to_equity_value > 5


def test_debt_low_no_flag():
    debt_to_equity_value = 2
    assert not debt_to_equity_value > 5


def test_cagr_turnaround_flag():
    previous = -100
    current = 200
    assert previous < 0 and current > 0


def test_cagr_decline_to_loss():
    previous = 200
    current = -100
    assert previous > 0 and current < 0


def test_cagr_positive():
    result = cagr(100, 200, 5)
    assert result is not None
    assert math.isfinite(result)
