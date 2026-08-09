import pytest
import pandas as pd

from src.etl.normaliser import normalize_year, normalize_ticker


# ============================================================
# normalize_ticker() - 15 tests
# ============================================================

def test_ticker_uppercase():
    assert normalize_ticker("tcs") == "TCS"


def test_ticker_lowercase():
    assert normalize_ticker("hdfcbank") == "HDFCBANK"


def test_ticker_spaces():
    assert normalize_ticker(" tcs ") == "TCS"


def test_ticker_multiple_spaces():
    assert normalize_ticker("HDFC BANK") == "HDFCBANK"


def test_ticker_mixed_case():
    assert normalize_ticker("TaTaMoToRs") == "TATAMOTORS"


def test_ticker_empty_string():
    assert normalize_ticker("") == ""


def test_ticker_whitespace_only():
    assert normalize_ticker("   ") == ""


def test_ticker_none():
    assert normalize_ticker(None) is None


def test_ticker_nan():
    assert normalize_ticker(float("nan")) is None


def test_ticker_numeric():
    assert normalize_ticker(123) == "123"


def test_ticker_leading_spaces():
    assert normalize_ticker("   INFY") == "INFY"


def test_ticker_trailing_spaces():
    assert normalize_ticker("INFY   ") == "INFY"


def test_ticker_newline():
    assert normalize_ticker("TCS\n") == "TCS"


def test_ticker_tab():
    assert normalize_ticker("\tRELIANCE\t") == "RELIANCE"


def test_ticker_multiple_internal_spaces():
    assert normalize_ticker("RE LI AN CE") == "RELIANCE"


# ============================================================
# normalize_year() - 20 tests
# ============================================================

def test_year_mar_24():
    assert normalize_year("Mar-24") == "2024-03"


def test_year_mar_23():
    assert normalize_year("Mar-23") == "2023-03"


def test_year_dec_24():
    assert normalize_year("Dec-24") == "2024-12"


def test_year_jun_24():
    assert normalize_year("Jun-24") == "2024-06"


def test_year_sep_24():
    assert normalize_year("Sep-24") == "2024-09"


def test_year_jan_24():
    assert normalize_year("Jan-24") == "2024-01"


def test_year_feb_24():
    assert normalize_year("Feb-24") == "2024-02"


def test_year_apr_24():
    assert normalize_year("Apr-24") == "2024-04"


def test_year_may_24():
    assert normalize_year("May-24") == "2024-05"


def test_year_jul_24():
    assert normalize_year("Jul-24") == "2024-07"


def test_year_aug_24():
    assert normalize_year("Aug-24") == "2024-08"


def test_year_oct_24():
    assert normalize_year("Oct-24") == "2024-10"


def test_year_nov_24():
    assert normalize_year("Nov-24") == "2024-11"


def test_year_with_spaces():
    assert normalize_year(" Mar-24 ") == "2024-03"


def test_year_none():
    assert normalize_year(None) is None


def test_year_nan():
    assert normalize_year(float("nan")) is None


def test_year_integer():
    assert normalize_year(2024) == "2024"


def test_year_string_integer():
    assert normalize_year("2024") == "2024"


def test_year_invalid_string():
    assert normalize_year("invalid") == "invalid"


def test_year_empty_string():
    assert normalize_year("") == ""


# ============================================================
# Total tests:
# normalize_ticker = 15
# normalize_year   = 20
# TOTAL            = 35
# ============================================================