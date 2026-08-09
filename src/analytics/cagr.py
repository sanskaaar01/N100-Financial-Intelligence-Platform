"""
CAGR Engine
Sprint 2 - Epic 02 - Day 10

Handles CAGR calculations for:
- Revenue
- PAT / Net Profit
- EPS

Supported edge cases:
- Positive -> Positive
- Positive -> Negative
- Negative -> Positive
- Negative -> Negative
- Zero base
- Insufficient data
"""

from __future__ import annotations

from typing import Optional, Any


# ============================================================
# CONSTANTS
# ============================================================

POSITIVE = "POSITIVE"
DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
TURNAROUND = "TURNAROUND"
BOTH_NEGATIVE = "BOTH_NEGATIVE"
ZERO_BASE = "ZERO_BASE"
INSUFFICIENT = "INSUFFICIENT"


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
# CORE CAGR
# ============================================================

def calculate_cagr(
    start_value: float,
    end_value: float,
    years: int,
) -> dict:
    """
    Calculate CAGR and return the result together with its flag.

    Formula:

        ((end / start) ** (1 / years) - 1) * 100

    Edge cases:

        Positive -> Positive:
            Calculate normally.

        Positive -> Negative:
            CAGR = None
            flag = DECLINE_TO_LOSS

        Negative -> Positive:
            CAGR = None
            flag = TURNAROUND

        Negative -> Negative:
            CAGR = None
            flag = BOTH_NEGATIVE

        Zero base:
            CAGR = None
            flag = ZERO_BASE

        Invalid / insufficient years:
            CAGR = None
            flag = INSUFFICIENT

    Returns:

        {
            "cagr": float | None,
            "flag": str
        }
    """

    start_value = _to_float(start_value)
    end_value = _to_float(end_value)

    # --------------------------------------------------------
    # Insufficient / invalid period
    # --------------------------------------------------------

    if years is None:
        return {
            "cagr": None,
            "flag": INSUFFICIENT,
        }

    try:
        years = int(years)
    except (TypeError, ValueError):
        return {
            "cagr": None,
            "flag": INSUFFICIENT,
        }

    if years <= 0:
        return {
            "cagr": None,
            "flag": INSUFFICIENT,
        }

    # --------------------------------------------------------
    # Invalid values
    # --------------------------------------------------------

    if start_value is None or end_value is None:
        return {
            "cagr": None,
            "flag": INSUFFICIENT,
        }

    # --------------------------------------------------------
    # Zero base
    # --------------------------------------------------------

    if start_value == 0:
        return {
            "cagr": None,
            "flag": ZERO_BASE,
        }

    # --------------------------------------------------------
    # Positive -> Positive
    # --------------------------------------------------------

    if start_value > 0 and end_value > 0:
        cagr = (
            (end_value / start_value) ** (1 / years) - 1
        ) * 100

        return {
            "cagr": cagr,
            "flag": POSITIVE,
        }

    # --------------------------------------------------------
    # Positive -> Negative
    # --------------------------------------------------------

    if start_value > 0 and end_value < 0:
        return {
            "cagr": None,
            "flag": DECLINE_TO_LOSS,
        }

    # --------------------------------------------------------
    # Negative -> Positive
    # --------------------------------------------------------

    if start_value < 0 and end_value > 0:
        return {
            "cagr": None,
            "flag": TURNAROUND,
        }

    # --------------------------------------------------------
    # Negative -> Negative
    # --------------------------------------------------------

    if start_value < 0 and end_value < 0:
        return {
            "cagr": None,
            "flag": BOTH_NEGATIVE,
        }

    # --------------------------------------------------------
    # End value == 0
    # --------------------------------------------------------

    if end_value == 0:
        if start_value > 0:
            return {
                "cagr": None,
                "flag": DECLINE_TO_LOSS,
            }

        return {
            "cagr": None,
            "flag": BOTH_NEGATIVE,
        }

    return {
        "cagr": None,
        "flag": INSUFFICIENT,
    }


# ============================================================
# SIMPLE CAGR VALUE FUNCTION
# ============================================================

def cagr(
    start_value: float,
    end_value: float,
    years: int,
) -> Optional[float]:
    """
    Return only the CAGR value.

    Returns None for all edge cases.
    """

    result = calculate_cagr(
        start_value=start_value,
        end_value=end_value,
        years=years,
    )

    return result["cagr"]


# ============================================================
# REVENUE CAGR
# ============================================================

def revenue_cagr(
    start_revenue: float,
    end_revenue: float,
    years: int,
) -> dict:
    """
    Calculate Revenue CAGR.
    """

    return calculate_cagr(
        start_value=start_revenue,
        end_value=end_revenue,
        years=years,
    )


# ============================================================
# PAT CAGR
# ============================================================

def pat_cagr(
    start_pat: float,
    end_pat: float,
    years: int,
) -> dict:
    """
    Calculate PAT / Net Profit CAGR.
    """

    return calculate_cagr(
        start_value=start_pat,
        end_value=end_pat,
        years=years,
    )


# ============================================================
# EPS CAGR
# ============================================================

def eps_cagr(
    start_eps: float,
    end_eps: float,
    years: int,
) -> dict:
    """
    Calculate EPS CAGR.
    """

    return calculate_cagr(
        start_value=start_eps,
        end_value=end_eps,
        years=years,
    )


# ============================================================
# TIME WINDOW VALIDATION
# ============================================================

def has_sufficient_years(
    available_years: int,
    required_years: int,
) -> bool:
    """
    Check whether enough years of data are available.

    Example:
        available_years=6, required_years=5 -> True
        available_years=4, required_years=5 -> False
    """

    if available_years is None or required_years is None:
        return False

    try:
        available_years = int(available_years)
        required_years = int(required_years)
    except (TypeError, ValueError):
        return False

    return available_years > required_years


def calculate_window_cagr(
    values: list,
    years: int,
) -> dict:
    """
    Calculate CAGR using a chronological list of values.

    The list must contain at least years + 1 observations.

    Example:

        5-year CAGR requires:

            Year 0
            Year 1
            Year 2
            Year 3
            Year 4
            Year 5

        Therefore 6 observations are required.
    """

    if values is None:
        return {
            "cagr": None,
            "flag": INSUFFICIENT,
        }

    if not isinstance(values, (list, tuple)):
        return {
            "cagr": None,
            "flag": INSUFFICIENT,
        }

    if len(values) < years + 1:
        return {
            "cagr": None,
            "flag": INSUFFICIENT,
        }

    return calculate_cagr(
        start_value=values[-(years + 1)],
        end_value=values[-1],
        years=years,
    )


# ============================================================
# ALL STANDARD WINDOWS
# ============================================================

def calculate_growth_windows(
    values: list,
) -> dict:
    """
    Calculate 3-year, 5-year and 10-year CAGR.

    Returns:

        {
            "cagr_3yr": ...,
            "cagr_3yr_flag": ...,
            "cagr_5yr": ...,
            "cagr_5yr_flag": ...,
            "cagr_10yr": ...,
            "cagr_10yr_flag": ...
        }
    """

    result_3 = calculate_window_cagr(values, 3)
    result_5 = calculate_window_cagr(values, 5)
    result_10 = calculate_window_cagr(values, 10)

    return {
        "cagr_3yr": result_3["cagr"],
        "cagr_3yr_flag": result_3["flag"],

        "cagr_5yr": result_5["cagr"],
        "cagr_5yr_flag": result_5["flag"],

        "cagr_10yr": result_10["cagr"],
        "cagr_10yr_flag": result_10["flag"],
    }


# ============================================================
# COMPANY GROWTH METRICS
# ============================================================

def calculate_company_growth(
    revenue_values: list,
    pat_values: list,
    eps_values: list,
) -> dict:
    """
    Calculate 3-year, 5-year and 10-year CAGR for:

    - Revenue
    - PAT
    - EPS
    """

    revenue = calculate_growth_windows(revenue_values)
    pat = calculate_growth_windows(pat_values)
    eps = calculate_growth_windows(eps_values)

    return {
        "revenue_cagr_3yr": revenue["cagr_3yr"],
        "revenue_cagr_3yr_flag": revenue["cagr_3yr_flag"],

        "revenue_cagr_5yr": revenue["cagr_5yr"],
        "revenue_cagr_5yr_flag": revenue["cagr_5yr_flag"],

        "revenue_cagr_10yr": revenue["cagr_10yr"],
        "revenue_cagr_10yr_flag": revenue["cagr_10yr_flag"],

        "pat_cagr_3yr": pat["cagr_3yr"],
        "pat_cagr_3yr_flag": pat["cagr_3yr_flag"],

        "pat_cagr_5yr": pat["cagr_5yr"],
        "pat_cagr_5yr_flag": pat["cagr_5yr_flag"],

        "pat_cagr_10yr": pat["cagr_10yr"],
        "pat_cagr_10yr_flag": pat["cagr_10yr_flag"],

        "eps_cagr_3yr": eps["cagr_3yr"],
        "eps_cagr_3yr_flag": eps["cagr_3yr_flag"],

        "eps_cagr_5yr": eps["cagr_5yr"],
        "eps_cagr_5yr_flag": eps["cagr_5yr_flag"],

        "eps_cagr_10yr": eps["cagr_10yr"],
        "eps_cagr_10yr_flag": eps["cagr_10yr_flag"],
    }


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "POSITIVE",
    "DECLINE_TO_LOSS",
    "TURNAROUND",
    "BOTH_NEGATIVE",
    "ZERO_BASE",
    "INSUFFICIENT",

    "calculate_cagr",
    "cagr",

    "revenue_cagr",
    "pat_cagr",
    "eps_cagr",

    "has_sufficient_years",
    "calculate_window_cagr",
    "calculate_growth_windows",
    "calculate_company_growth",
]