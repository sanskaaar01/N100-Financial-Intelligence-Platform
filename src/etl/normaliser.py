"""
normaliser.py

Utility functions for cleaning and standardising data.
"""

import re

import pandas as pd


def normalize_ticker(ticker):
    """
    Standardize company ticker.

    Examples:
    ---------
    ' tcs ' -> 'TCS'
    'hdfcbank' -> 'HDFCBANK'
    """

    if pd.isna(ticker):
        return None

    ticker = str(ticker).strip().upper()

    ticker = re.sub(r"\s+", "", ticker)

    return ticker


def normalize_year(year):
    """
    Convert financial year labels.

    Examples:
    ---------
    Mar-24 -> 2024-03
    Mar-23 -> 2023-03
    """

    if pd.isna(year):
        return None

    year = str(year).strip()

    try:
        dt = pd.to_datetime(year, format="%b-%y")
        return dt.strftime("%Y-%m")
    except Exception:
        return year
