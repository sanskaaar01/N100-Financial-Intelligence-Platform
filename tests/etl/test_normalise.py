
import pytest


def normalize_year(value):
    """Normalize supported year formats to YYYY-MM."""
    value = str(value).strip()

    if value.lower() in {"nan", "none", ""}:
        return None

    months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }

    parts = value.replace("-", " ").replace("/", " ").split()

    if len(parts) == 2:
        a, b = parts

        if a.lower()[:3] in months and b.isdigit():
            return f"{int(b):04d}-{months[a.lower()[:3]]}"

        if b.lower()[:3] in months and a.isdigit():
            return f"{int(a):04d}-{months[b.lower()[:3]]}"

    if len(value) == 4 and value.isdigit():
        return f"{value}-12"

    return None


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Mar 2024", "2024-03"),
        ("Dec 2023", "2023-12"),
        ("Jan 2020", "2020-01"),
        ("Jun 2022", "2022-06"),
        ("Sep 2021", "2021-09"),
        ("2024-Mar", "2024-03"),
        ("2023-Dec", "2023-12"),
        ("2020-Jan", "2020-01"),
        ("2022-Jun", "2022-06"),
        ("2021-Sep", "2021-09"),
        ("Mar/2024", "2024-03"),
        ("Dec/2023", "2023-12"),
        ("2024", "2024-12"),
        ("  Mar 2024  ", "2024-03"),
        ("JAN 2024", "2024-01"),
        ("FEB 2024", "2024-02"),
        ("invalid", None),
        ("", None),
        ("None", None),
        ("nan", None),
    ],
)
def test_normalize_year(value, expected):
    assert normalize_year(value) == expected
