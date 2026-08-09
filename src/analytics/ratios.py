"""
Financial Ratio Engine
Sprint 2 - Epic 02

Profitability, leverage and efficiency ratio calculations.
"""

from __future__ import annotations

from typing import Optional, Any
import logging


logger = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================

def _to_float(value: Any) -> Optional[float]:
    """Safely convert a value to float."""

    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if result != result:  # NaN
        return None

    return result


# ============================================================
# PROFITABILITY RATIOS
# ============================================================

def net_profit_margin(
    net_profit: float,
    sales: float,
) -> Optional[float]:
    """
    Net Profit Margin (%)

    Formula:
        net_profit / sales * 100

    Returns None if sales == 0.
    """

    net_profit = _to_float(net_profit)
    sales = _to_float(sales)

    if net_profit is None or sales is None:
        return None

    if sales == 0:
        return None

    return (net_profit / sales) * 100


def operating_profit_margin(
    operating_profit: float,
    sales: float,
) -> Optional[float]:
    """
    Operating Profit Margin (%)

    Formula:
        operating_profit / sales * 100
    """

    operating_profit = _to_float(operating_profit)
    sales = _to_float(sales)

    if operating_profit is None or sales is None:
        return None

    if sales == 0:
        return None

    return (operating_profit / sales) * 100


def check_opm_crosscheck(
    calculated_opm: float,
    source_opm: float,
    tolerance: float = 1.0,
) -> dict:
    """
    Cross-check calculated OPM against source OPM.

    A mismatch occurs when the difference is greater than
    1 percentage point by default.
    """

    calculated_opm = _to_float(calculated_opm)
    source_opm = _to_float(source_opm)

    if calculated_opm is None or source_opm is None:
        return {
            "calculated": calculated_opm,
            "source": source_opm,
            "difference": None,
            "mismatch": False,
        }

    difference = abs(calculated_opm - source_opm)

    mismatch = difference > tolerance

    if mismatch:
        logger.warning(
            "OPM mismatch: calculated=%.4f, source=%.4f, difference=%.4f",
            calculated_opm,
            source_opm,
            difference,
        )

    return {
        "calculated": calculated_opm,
        "source": source_opm,
        "difference": difference,
        "mismatch": mismatch,
    }


def return_on_equity(
    net_profit: float,
    equity_capital: float,
    reserves: float,
) -> Optional[float]:
    """
    Return on Equity (ROE) (%)

    Formula:
        net_profit / (equity_capital + reserves) * 100

    Returns None when equity + reserves <= 0.
    """

    net_profit = _to_float(net_profit)
    equity_capital = _to_float(equity_capital)
    reserves = _to_float(reserves)

    if (
        net_profit is None
        or equity_capital is None
        or reserves is None
    ):
        return None

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return (net_profit / equity) * 100


def return_on_capital_employed(
    operating_profit: float,
    other_income: float,
    equity_capital: float,
    reserves: float,
    borrowings: float,
) -> Optional[float]:
    """
    Return on Capital Employed (ROCE) (%)

    EBIT:
        operating_profit + other_income

    Capital Employed:
        equity_capital + reserves + borrowings

    Formula:
        EBIT / Capital Employed * 100
    """

    operating_profit = _to_float(operating_profit)
    other_income = _to_float(other_income)
    equity_capital = _to_float(equity_capital)
    reserves = _to_float(reserves)
    borrowings = _to_float(borrowings)

    if any(
        value is None
        for value in [
            operating_profit,
            other_income,
            equity_capital,
            reserves,
            borrowings,
        ]
    ):
        return None

    capital_employed = (
        equity_capital
        + reserves
        + borrowings
    )

    if capital_employed <= 0:
        return None

    ebit = operating_profit + other_income

    return (ebit / capital_employed) * 100


def return_on_assets(
    net_profit: float,
    total_assets: float,
) -> Optional[float]:
    """
    Return on Assets (ROA) (%)

    Formula:
        net_profit / total_assets * 100
    """

    net_profit = _to_float(net_profit)
    total_assets = _to_float(total_assets)

    if net_profit is None or total_assets is None:
        return None

    if total_assets == 0:
        return None

    return (net_profit / total_assets) * 100


# ============================================================
# LEVERAGE RATIOS
# ============================================================

def debt_to_equity(
    borrowings: float,
    equity_capital: float,
    reserves: float,
) -> Optional[float]:
    """
    Debt-to-Equity ratio.

    Formula:
        borrowings / (equity_capital + reserves)

    Rules:
        - borrowings == 0 -> 0
        - equity <= 0 -> None
    """

    borrowings = _to_float(borrowings)
    equity_capital = _to_float(equity_capital)
    reserves = _to_float(reserves)

    if (
        borrowings is None
        or equity_capital is None
        or reserves is None
    ):
        return None

    if borrowings == 0:
        return 0.0

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return borrowings / equity


def interest_coverage_ratio(
    operating_profit: float,
    other_income: float,
    interest: float,
) -> Optional[float]:
    """
    Interest Coverage Ratio.

    Formula:
        (operating_profit + other_income) / interest

    Returns None when interest == 0.
    """

    operating_profit = _to_float(operating_profit)
    other_income = _to_float(other_income)
    interest = _to_float(interest)

    if (
        operating_profit is None
        or other_income is None
        or interest is None
    ):
        return None

    if interest == 0:
        return None

    return (operating_profit + other_income) / interest


def interest_coverage_label(
    icr: Optional[float],
) -> Optional[str]:
    """
    Return Debt Free label when ICR is None.

    None ICR represents zero interest expense.
    """

    if icr is None:
        return "Debt Free"

    return None


def interest_coverage_warning(
    icr: Optional[float],
) -> bool:
    """
    Returns True when ICR < 1.5.
    """

    if icr is None:
        return False

    return icr < 1.5


# ============================================================
# FINANCIALS SECTOR
# ============================================================

def is_financials_sector(
    broad_sector: Optional[str],
) -> bool:
    """
    Check whether a company belongs to Financials sector.

    Financials include banks, NBFCs and insurance companies
    for the Sprint 2 leverage carve-out.
    """

    if broad_sector is None:
        return False

    return str(broad_sector).strip().lower() == "financials"


def high_leverage_flag(
    debt_equity: Optional[float] = None,
    broad_sector: Optional[str] = None,
) -> bool:
    """
    High leverage flag.

    Rule:
        D/E > 5
        AND company is NOT in Financials sector.

    Important:
    The parameter is intentionally named `debt_equity`
    because this is the interface expected by the KPI tests.
    """

    if debt_equity is None:
        return False

    if is_financials_sector(broad_sector):
        return False

    return debt_equity > 5


# ============================================================
# EFFICIENCY RATIOS
# ============================================================

def net_debt(
    borrowings: float,
    investments: float,
) -> Optional[float]:
    """
    Net Debt.

    Formula:
        borrowings - investments

    Investments are used as the liquid asset proxy.
    """

    borrowings = _to_float(borrowings)
    investments = _to_float(investments)

    if borrowings is None or investments is None:
        return None

    return borrowings - investments


def asset_turnover(
    sales: float,
    total_assets: float,
) -> Optional[float]:
    """
    Asset Turnover.

    Formula:
        sales / total_assets

    Returns None if total_assets == 0.
    """

    sales = _to_float(sales)
    total_assets = _to_float(total_assets)

    if sales is None or total_assets is None:
        return None

    if total_assets == 0:
        return None

    return sales / total_assets


# ============================================================
# LEVERAGE + EFFICIENCY ENGINE
# ============================================================

def calculate_leverage_efficiency_ratios(
    borrowings: float,
    equity_capital: float,
    reserves: float,
    operating_profit: float,
    other_income: float,
    interest: float,
    investments: float,
    sales: float,
    total_assets: float,
    broad_sector: Optional[str] = None,
) -> dict:
    """
    Calculate leverage and efficiency KPIs.
    """

    de = debt_to_equity(
        borrowings=borrowings,
        equity_capital=equity_capital,
        reserves=reserves,
    )

    icr = interest_coverage_ratio(
        operating_profit=operating_profit,
        other_income=other_income,
        interest=interest,
    )

    nd = net_debt(
        borrowings=borrowings,
        investments=investments,
    )

    turnover = asset_turnover(
        sales=sales,
        total_assets=total_assets,
    )

    return {
        "debt_to_equity": de,
        "high_leverage_flag": high_leverage_flag(
            debt_equity=de,
            broad_sector=broad_sector,
        ),
        "interest_coverage": icr,
        "icr_label": interest_coverage_label(icr),
        "icr_warning_flag": interest_coverage_warning(icr),
        "net_debt": nd,
        "asset_turnover": turnover,
    }


# ============================================================
# PROFITABILITY ENGINE
# ============================================================

def calculate_profitability_ratios(
    net_profit: float,
    sales: float,
    operating_profit: float,
    other_income: float,
    equity_capital: float,
    reserves: float,
    borrowings: float,
    total_assets: float,
    source_opm: Optional[float] = None,
) -> dict:
    """
    Calculate profitability KPIs.
    """

    npm = net_profit_margin(
        net_profit=net_profit,
        sales=sales,
    )

    opm = operating_profit_margin(
        operating_profit=operating_profit,
        sales=sales,
    )

    roe = return_on_equity(
        net_profit=net_profit,
        equity_capital=equity_capital,
        reserves=reserves,
    )

    roce = return_on_capital_employed(
        operating_profit=operating_profit,
        other_income=other_income,
        equity_capital=equity_capital,
        reserves=reserves,
        borrowings=borrowings,
    )

    roa = return_on_assets(
        net_profit=net_profit,
        total_assets=total_assets,
    )

    opm_crosscheck = None

    if source_opm is not None:
        opm_crosscheck = check_opm_crosscheck(
            calculated_opm=opm,
            source_opm=source_opm,
        )

    return {
        "net_profit_margin_pct": npm,
        "operating_profit_margin_pct": opm,
        "return_on_equity_pct": roe,
        "return_on_capital_employed_pct": roce,
        "return_on_assets_pct": roa,
        "opm_crosscheck": opm_crosscheck,
    }


# ============================================================
# ROCE CROSS-CHECK
# ============================================================

def check_roce_crosscheck(
    calculated_roce: Optional[float],
    source_roce: Optional[float],
    tolerance: float = 5.0,
) -> dict:
    """
    Compare calculated ROCE with source ROCE.

    Anomaly threshold:
        difference > 5 percentage points
    """

    calculated_roce = _to_float(calculated_roce)
    source_roce = _to_float(source_roce)

    if calculated_roce is None or source_roce is None:
        return {
            "calculated": calculated_roce,
            "source": source_roce,
            "difference": None,
            "anomaly": False,
        }

    difference = abs(calculated_roce - source_roce)

    return {
        "calculated": calculated_roce,
        "source": source_roce,
        "difference": difference,
        "anomaly": difference > tolerance,
    }


# ============================================================
# ROE CROSS-CHECK
# ============================================================

def check_roe_crosscheck(
    calculated_roe: Optional[float],
    source_roe: Optional[float],
    tolerance: float = 5.0,
) -> dict:
    """
    Compare calculated ROE with source ROE.
    """

    calculated_roe = _to_float(calculated_roe)
    source_roe = _to_float(source_roe)

    if calculated_roe is None or source_roe is None:
        return {
            "calculated": calculated_roe,
            "source": source_roe,
            "difference": None,
            "anomaly": False,
        }

    difference = abs(calculated_roe - source_roe)

    return {
        "calculated": calculated_roe,
        "source": source_roe,
        "difference": difference,
        "anomaly": difference > tolerance,
    }


# ============================================================
# COMBINED RATIO ENGINE
# ============================================================

def calculate_all_ratios(row: dict) -> dict:
    """
    Convenience function for calculating all currently
    implemented ratios from a company-year dictionary.
    """

    profitability = calculate_profitability_ratios(
        net_profit=row.get("net_profit"),
        sales=row.get("sales"),
        operating_profit=row.get("operating_profit"),
        other_income=row.get("other_income", 0),
        equity_capital=row.get("equity_capital"),
        reserves=row.get("reserves"),
        borrowings=row.get("borrowings"),
        total_assets=row.get("total_assets"),
        source_opm=row.get("opm_percentage"),
    )

    leverage = calculate_leverage_efficiency_ratios(
        borrowings=row.get("borrowings"),
        equity_capital=row.get("equity_capital"),
        reserves=row.get("reserves"),
        operating_profit=row.get("operating_profit"),
        other_income=row.get("other_income", 0),
        interest=row.get("interest"),
        investments=row.get("investments"),
        sales=row.get("sales"),
        total_assets=row.get("total_assets"),
        broad_sector=row.get("broad_sector"),
    )

    return {
        **profitability,
        **leverage,
    }


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "net_profit_margin",
    "operating_profit_margin",
    "check_opm_crosscheck",
    "return_on_equity",
    "return_on_capital_employed",
    "return_on_assets",
    "calculate_profitability_ratios",
    "debt_to_equity",
    "interest_coverage_ratio",
    "interest_coverage_label",
    "interest_coverage_warning",
    "is_financials_sector",
    "high_leverage_flag",
    "calculate_leverage_efficiency_ratios",
    "net_debt",
    "asset_turnover",
    "check_roce_crosscheck",
    "check_roe_crosscheck",
    "calculate_all_ratios",
]