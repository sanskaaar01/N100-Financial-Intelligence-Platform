"""
Sprint 2 - Day 11
Cash Flow KPIs and Capital Allocation
"""


def free_cash_flow(operating_activity, investing_activity):
    if operating_activity is None or investing_activity is None:
        return None
    return operating_activity + investing_activity


def cfo_quality_ratio(cfo, pat):
    if cfo is None or pat is None or pat == 0:
        return None
    return cfo / pat


def cfo_quality_label(ratio):
    if ratio is None:
        return None
    if ratio > 1.0:
        return "High Quality"
    if ratio >= 0.5:
        return "Moderate"
    return "Accrual Risk"


def cfo_quality_score(cfo, pat):
    ratio = cfo_quality_ratio(cfo, pat)
    return {
        "ratio": ratio,
        "label": cfo_quality_label(ratio),
    }


def average_cfo_quality(cfo_values, pat_values):
    if not cfo_values or not pat_values:
        return None

    ratios = []

    for cfo, pat in zip(cfo_values, pat_values):
        ratio = cfo_quality_ratio(cfo, pat)
        if ratio is not None:
            ratios.append(ratio)

    if not ratios:
        return None

    return sum(ratios) / len(ratios)


def capex_intensity(investing_activity, sales):
    if investing_activity is None or sales is None:
        return None

    if sales == 0:
        return None

    return abs(investing_activity) / sales * 100


def capex_intensity_label(intensity):
    if intensity is None:
        return None

    if intensity < 3:
        return "Asset Light"

    if intensity <= 8:
        return "Moderate"

    return "Capital Intensive"


def fcf_conversion_rate(fcf, operating_profit):
    if fcf is None or operating_profit is None:
        return None

    if operating_profit == 0:
        return None

    return fcf / operating_profit * 100


def _sign(value):
    if value is None:
        return "0"

    if value > 0:
        return "+"

    if value < 0:
        return "-"

    return "0"


def capital_allocation_pattern(
    cfo,
    cfi,
    cff,
    cfo_pat_ratio=None,
):
    cfo_sign = _sign(cfo)
    cfi_sign = _sign(cfi)
    cff_sign = _sign(cff)

    pattern = (cfo_sign, cfi_sign, cff_sign)

    if pattern == ("+", "-", "-"):
        if cfo_pat_ratio is not None and cfo_pat_ratio > 1.0:
            label = "Shareholder Returns"
        else:
            label = "Reinvestor"

    elif pattern == ("+", "+", "-"):
        label = "Liquidating Assets"

    elif pattern == ("-", "+", "+"):
        label = "Distress Signal"

    elif pattern == ("-", "-", "+"):
        label = "Growth Funded by Debt"

    elif pattern == ("+", "+", "+"):
        label = "Cash Accumulator"

    elif pattern == ("-", "-", "-"):
        label = "Pre-Revenue"

    elif pattern == ("+", "-", "+"):
        label = "Mixed"

    else:
        label = "Mixed"

    return {
        "cfo_sign": cfo_sign,
        "cfi_sign": cfi_sign,
        "cff_sign": cff_sign,
        "pattern_label": label,
    }


def calculate_cashflow_kpis(
    operating_activity,
    investing_activity,
    financing_activity,
    pat=None,
    sales=None,
    operating_profit=None,
):
    fcf = free_cash_flow(
        operating_activity,
        investing_activity,
    )

    quality_ratio = None
    quality_label = None

    if pat is not None:
        quality_ratio = cfo_quality_ratio(
            operating_activity,
            pat,
        )
        quality_label = cfo_quality_label(
            quality_ratio,
        )

    capex_pct = None
    capex_label = None

    if sales is not None:
        capex_pct = capex_intensity(
            investing_activity,
            sales,
        )
        capex_label = capex_intensity_label(
            capex_pct,
        )

    conversion_pct = None

    if operating_profit is not None:
        conversion_pct = fcf_conversion_rate(
            fcf,
            operating_profit,
        )

    allocation = capital_allocation_pattern(
        operating_activity,
        investing_activity,
        financing_activity,
        quality_ratio,
    )

    return {
        "free_cash_flow": fcf,
        "cfo_quality_ratio": quality_ratio,
        "cfo_quality_label": quality_label,
        "capex_intensity_pct": capex_pct,
        "capex_intensity_label": capex_label,
        "fcf_conversion_rate_pct": conversion_pct,
        "cfo_sign": allocation["cfo_sign"],
        "cfi_sign": allocation["cfi_sign"],
        "cff_sign": allocation["cff_sign"],
        "pattern_label": allocation["pattern_label"],
    }


__all__ = [
    "free_cash_flow",
    "cfo_quality_ratio",
    "cfo_quality_label",
    "cfo_quality_score",
    "average_cfo_quality",
    "capex_intensity",
    "capex_intensity_label",
    "fcf_conversion_rate",
    "capital_allocation_pattern",
    "calculate_cashflow_kpis",
]
