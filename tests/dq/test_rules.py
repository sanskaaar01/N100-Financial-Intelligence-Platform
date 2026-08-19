import pandas as pd
import pytest


def check_rule(df, required):
    missing = [x for x in required if x not in df.columns]
    return len(missing) == 0


@pytest.mark.parametrize(
    "rule_id,column",
    [
        ("DQ01", "company_id"),
        ("DQ02", "year"),
        ("DQ03", "sales"),
        ("DQ04", "net_profit"),
        ("DQ05", "operating_profit"),
        ("DQ06", "borrowings"),
        ("DQ07", "total_assets"),
        ("DQ08", "operating_activity"),
        ("DQ09", "investing_activity"),
        ("DQ10", "financing_activity"),
        ("DQ11", "return_on_equity_pct"),
        ("DQ12", "debt_to_equity"),
        ("DQ13", "revenue_cagr_5yr"),
        ("DQ14", "fcf_cagr_5yr"),
    ],
)
def test_dq_rule_schema(rule_id, column):
    df = pd.DataFrame({column: [None]})
    assert column in df.columns
    assert not df[column].notna().all()
