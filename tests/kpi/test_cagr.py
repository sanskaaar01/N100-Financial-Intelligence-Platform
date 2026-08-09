import pytest

from src.analytics.cagr import (
    calculate_cagr,
    cagr,
    revenue_cagr,
    pat_cagr,
    eps_cagr,
    calculate_window_cagr,
    calculate_growth_windows,
    POSITIVE,
    DECLINE_TO_LOSS,
    TURNAROUND,
    BOTH_NEGATIVE,
    ZERO_BASE,
    INSUFFICIENT,
)


# ============================================================
# NORMAL CAGR
# ============================================================

def test_normal_cagr():
    result = calculate_cagr(
        start_value=100,
        end_value=121,
        years=2,
    )

    assert result["cagr"] == pytest.approx(10.0)
    assert result["flag"] == POSITIVE


# ============================================================
# POSITIVE -> NEGATIVE
# ============================================================

def test_decline_to_loss():
    result = calculate_cagr(
        start_value=100,
        end_value=-20,
        years=3,
    )

    assert result["cagr"] is None
    assert result["flag"] == DECLINE_TO_LOSS


# ============================================================
# NEGATIVE -> POSITIVE
# ============================================================

def test_turnaround():
    result = calculate_cagr(
        start_value=-100,
        end_value=50,
        years=3,
    )

    assert result["cagr"] is None
    assert result["flag"] == TURNAROUND


# ============================================================
# NEGATIVE -> NEGATIVE
# ============================================================

def test_both_negative():
    result = calculate_cagr(
        start_value=-100,
        end_value=-50,
        years=3,
    )

    assert result["cagr"] is None
    assert result["flag"] == BOTH_NEGATIVE


# ============================================================
# ZERO BASE
# ============================================================

def test_zero_base():
    result = calculate_cagr(
        start_value=0,
        end_value=100,
        years=5,
    )

    assert result["cagr"] is None
    assert result["flag"] == ZERO_BASE


# ============================================================
# INSUFFICIENT YEARS
# ============================================================

def test_insufficient_years():
    result = calculate_window_cagr(
        values=[100, 110, 120, 130],
        years=5,
    )

    assert result["cagr"] is None
    assert result["flag"] == INSUFFICIENT


# ============================================================
# REVENUE CAGR
# ============================================================

def test_revenue_cagr():
    result = revenue_cagr(
        start_revenue=100,
        end_revenue=146.41,
        years=4,
    )

    assert result["cagr"] == pytest.approx(10.0)
    assert result["flag"] == POSITIVE


# ============================================================
# PAT TURNAROUND
# ============================================================

def test_pat_turnaround():
    result = pat_cagr(
        start_pat=-50,
        end_pat=100,
        years=5,
    )

    assert result["cagr"] is None
    assert result["flag"] == TURNAROUND


# ============================================================
# EPS ZERO BASE
# ============================================================

def test_eps_zero_base():
    result = eps_cagr(
        start_eps=0,
        end_eps=20,
        years=5,
    )

    assert result["cagr"] is None
    assert result["flag"] == ZERO_BASE


# ============================================================
# GROWTH WINDOWS
# ============================================================

def test_growth_windows():
    values = [
        100,
        110,
        121,
        133.1,
        146.41,
        161.051,
    ]

    result = calculate_growth_windows(values)

    assert result["cagr_3yr"] == pytest.approx(10.0)
    assert result["cagr_3yr_flag"] == POSITIVE

    assert result["cagr_5yr"] == pytest.approx(10.0)
    assert result["cagr_5yr_flag"] == POSITIVE

    assert result["cagr_10yr"] is None
    assert result["cagr_10yr_flag"] == INSUFFICIENT