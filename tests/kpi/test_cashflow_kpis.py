import pytest

from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_ratio,
    cfo_quality_label,
    average_cfo_quality,
    capex_intensity,
    capex_intensity_label,
    fcf_conversion_rate,
    capital_allocation_pattern,
    calculate_cashflow_kpis,
)


def test_free_cash_flow_normal():
    assert free_cash_flow(100, -40) == pytest.approx(60)


def test_free_cash_flow_negative_allowed():
    assert free_cash_flow(50, -100) == pytest.approx(-50)


def test_cfo_quality_zero_pat():
    assert cfo_quality_ratio(100, 0) is None


def test_cfo_quality_high():
    ratio = cfo_quality_ratio(120, 100)
    assert ratio == pytest.approx(1.2)
    assert cfo_quality_label(ratio) == "High Quality"


def test_cfo_quality_moderate():
    ratio = cfo_quality_ratio(75, 100)
    assert ratio == pytest.approx(0.75)
    assert cfo_quality_label(ratio) == "Moderate"


def test_cfo_quality_accrual_risk():
    ratio = cfo_quality_ratio(30, 100)
    assert ratio == pytest.approx(0.3)
    assert cfo_quality_label(ratio) == "Accrual Risk"


def test_average_cfo_quality():
    result = average_cfo_quality(
        [100, 120, 80],
        [100, 100, 100],
    )
    assert result == pytest.approx(1.0)


def test_capex_intensity_normal():
    assert capex_intensity(-40, 1000) == pytest.approx(4.0)


def test_capex_intensity_zero_sales():
    assert capex_intensity(-40, 0) is None


def test_capex_intensity_asset_light():
    assert capex_intensity_label(2.5) == "Asset Light"


def test_capex_intensity_moderate():
    assert capex_intensity_label(5.0) == "Moderate"


def test_capex_intensity_capital_intensive():
    assert capex_intensity_label(10.0) == "Capital Intensive"


def test_fcf_conversion_normal():
    assert fcf_conversion_rate(60, 150) == pytest.approx(40.0)


def test_fcf_conversion_zero_operating_profit():
    assert fcf_conversion_rate(60, 0) is None


def test_reinvestor_pattern():
    result = capital_allocation_pattern(
        100,
        -50,
        -20,
        cfo_pat_ratio=0.8,
    )
    assert result["pattern_label"] == "Reinvestor"


def test_shareholder_returns_pattern():
    result = capital_allocation_pattern(
        150,
        -50,
        -20,
        cfo_pat_ratio=1.5,
    )
    assert result["pattern_label"] == "Shareholder Returns"


def test_liquidating_assets_pattern():
    result = capital_allocation_pattern(100, 50, -20)
    assert result["pattern_label"] == "Liquidating Assets"


def test_distress_signal_pattern():
    result = capital_allocation_pattern(-100, 50, 20)
    assert result["pattern_label"] == "Distress Signal"


def test_growth_funded_by_debt_pattern():
    result = capital_allocation_pattern(-100, -50, 75)
    assert result["pattern_label"] == "Growth Funded by Debt"


def test_cash_accumulator_pattern():
    result = capital_allocation_pattern(100, 50, 20)
    assert result["pattern_label"] == "Cash Accumulator"


def test_pre_revenue_pattern():
    result = capital_allocation_pattern(-100, -50, -20)
    assert result["pattern_label"] == "Pre-Revenue"


def test_mixed_pattern():
    result = capital_allocation_pattern(100, -50, 50)
    assert result["pattern_label"] == "Mixed"


def test_calculate_cashflow_kpis():
    result = calculate_cashflow_kpis(
        operating_activity=100,
        investing_activity=-40,
        financing_activity=-20,
        pat=80,
        sales=1000,
        operating_profit=150,
    )

    assert result["free_cash_flow"] == pytest.approx(60)
    assert result["cfo_quality_ratio"] == pytest.approx(1.25)
    assert result["cfo_quality_label"] == "High Quality"
    assert result["capex_intensity_pct"] == pytest.approx(4.0)
    assert result["capex_intensity_label"] == "Moderate"
    assert result["fcf_conversion_rate_pct"] == pytest.approx(40.0)
    assert result["pattern_label"] == "Shareholder Returns"
