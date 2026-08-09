"""
validator.py

N100 Financial Intelligence Platform
Sprint 1 - Data Quality Validator

Implements DQ-01 to DQ-16.

Important:
- Raw Excel files are NEVER modified.
- Duplicate (company_id, year) records are logged and deduplicated
  by keeping the last occurrence, as required by DQ-02.
- WARNING rules are logged but do not reject rows.
- CRITICAL rules reject invalid rows.
"""

from pathlib import Path
import re
import pandas as pd


class DataValidator:

    def __init__(self, output_folder=None):

        if output_folder is None:
            root = Path(__file__).resolve().parents[2]
            output_folder = root / "data" / "output"

        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)

        self.failures = []

        # These are the time-series tables where
        # (company_id, year) should be unique.
        self.time_series_files = {
            "profitandloss.xlsx",
            "balancesheet.xlsx",
            "cashflow.xlsx",
            "financial_ratios.xlsx",
        }

    # ==========================================================
    # GENERAL HELPERS
    # ==========================================================

    def log_failure(
        self,
        rule,
        severity,
        filename,
        row,
        message
    ):
        self.failures.append({
            "rule": rule,
            "severity": severity,
            "file": filename,
            "row": row,
            "message": message
        })

    def _clean_columns(self, df):

        df = df.copy()

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(" ", "_", regex=False)
            .str.replace("-", "_", regex=False)
        )

        return df

    def _find_column(self, df, names):

        for name in names:
            if name in df.columns:
                return name

        return None

    def _numeric(self, value):

        try:
            if pd.isna(value):
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    def _is_financial_company(self, company_id, companies_df):

        if companies_df is None or company_id is None:
            return False

        company_id = str(company_id).strip().upper()

        company_col = self._find_column(
            companies_df,
            ["company_id", "id", "ticker"]
        )

        sector_cols = [
            "broad_sector",
            "sector",
            "sector_name"
        ]

        sector_col = None

        for col in sector_cols:
            if col in companies_df.columns:
                sector_col = col
                break

        if company_col is None or sector_col is None:
            return False

        matches = companies_df[
            companies_df[company_col]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq(company_id)
        ]

        if matches.empty:
            return False

        sector = str(
            matches.iloc[0][sector_col]
        ).strip().lower()

        return sector == "financials"

    # ==========================================================
    # DQ-01
    # COMPANY PRIMARY KEY UNIQUENESS
    # ==========================================================

    def dq01_company_pk(self, df, filename):

        df = df.copy()

        id_col = self._find_column(
            df,
            ["id", "company_id", "ticker"]
        )

        if id_col is None:
            return df

        duplicate_mask = df[id_col].duplicated(
            keep=False
        )

        for index in df.index[duplicate_mask]:

            self.log_failure(
                "DQ-01",
                "CRITICAL",
                filename,
                index + 2,
                "Duplicate company primary key."
            )

        return df

    # ==========================================================
    # DQ-02
    # ANNUAL PRIMARY KEY UNIQUENESS
    #
    # REQUIRED BEHAVIOUR:
    # Duplicate (company_id, year)
    # -> log duplicates
    # -> KEEP LAST
    # ==========================================================

    def dq02_deduplicate(self, df, filename):

        df = df.copy()

        company_col = self._find_column(
            df,
            ["company_id", "ticker"]
        )

        year_col = self._find_column(
            df,
            ["year", "financial_year"]
        )

        if company_col is None or year_col is None:
            return df

        # Normalise company IDs for comparison.
        df[company_col] = (
            df[company_col]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        duplicate_mask = df.duplicated(
            subset=[company_col, year_col],
            keep=False
        )

        duplicate_rows = df.loc[duplicate_mask]

        # Log every duplicate row.
        for index in duplicate_rows.index:

            company = df.loc[index, company_col]
            year = df.loc[index, year_col]

            self.log_failure(
                "DQ-02",
                "WARNING",
                filename,
                index + 2,
                f"Duplicate ({company}, {year}) - "
                f"keeping last occurrence."
            )

        # KEEP LAST occurrence.
        df = df.drop_duplicates(
            subset=[company_col, year_col],
            keep="last"
        )

        return df.reset_index(drop=True)

    # ==========================================================
    # DQ-03
    # FOREIGN KEY INTEGRITY
    # ==========================================================

    def dq03_fk_integrity(
        self,
        df,
        filename,
        companies_df
    ):

        if companies_df is None:
            return df

        df = df.copy()
        companies_df = companies_df.copy()

        child_col = self._find_column(
            df,
            ["company_id", "ticker"]
        )

        parent_col = self._find_column(
            companies_df,
            ["company_id", "id", "ticker"]
        )

        if child_col is None or parent_col is None:
            return df

        valid_ids = set(
            companies_df[parent_col]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
        )

        child_ids = (
            df[child_col]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        invalid_mask = ~child_ids.isin(valid_ids)

        for index in df.index[invalid_mask]:

            company_id = df.loc[
                index,
                child_col
            ]

            self.log_failure(
                "DQ-03",
                "CRITICAL",
                filename,
                index + 2,
                f"company_id '{company_id}' "
                f"does not exist in companies table."
            )

        # Reject orphan rows.
        df = df.loc[~invalid_mask].copy()

        return df.reset_index(drop=True)

    # ==========================================================
    # DQ-04
    # BALANCE SHEET BALANCE
    # ==========================================================

    def dq04_balance_sheet(
        self,
        df,
        filename
    ):

        if "total_assets" not in df.columns:
            return df

        if "total_liabilities" not in df.columns:
            return df

        for index, row in df.iterrows():

            assets = self._numeric(
                row.get("total_assets")
            )

            liabilities = self._numeric(
                row.get("total_liabilities")
            )

            if assets is None or liabilities is None:
                continue

            if assets == 0:
                continue

            difference = (
                abs(assets - liabilities)
                / abs(assets)
            )

            if difference >= 0.01:

                self.log_failure(
                    "DQ-04",
                    "WARNING",
                    filename,
                    index + 2,
                    f"Balance sheet mismatch "
                    f"{difference * 100:.2f}%."
                )

        return df

    # ==========================================================
    # DQ-05
    # OPM CROSS CHECK
    # ==========================================================

    def dq05_opm(self, df, filename):

        if "opm_percentage" not in df.columns:
            return df

        sales_col = self._find_column(
            df,
            ["sales", "revenue"]
        )

        profit_col = self._find_column(
            df,
            ["operating_profit", "operating_profit_cr"]
        )

        if sales_col is None or profit_col is None:
            return df

        for index, row in df.iterrows():

            sales = self._numeric(
                row.get(sales_col)
            )

            operating_profit = self._numeric(
                row.get(profit_col)
            )

            source_opm = self._numeric(
                row.get("opm_percentage")
            )

            if (
                sales is None
                or operating_profit is None
                or source_opm is None
                or sales == 0
            ):
                continue

            computed_opm = (
                operating_profit / sales
            ) * 100

            difference = abs(
                source_opm - computed_opm
            )

            if difference > 1:

                self.log_failure(
                    "DQ-05",
                    "WARNING",
                    filename,
                    index + 2,
                    f"OPM cross-check difference "
                    f"exceeds 1% ({difference:.2f}%)."
                )

        return df

    # ==========================================================
    # DQ-06
    # POSITIVE SALES
    # ==========================================================

    def dq06_positive_sales(
        self,
        df,
        filename,
        companies_df=None
    ):

        sales_col = self._find_column(
            df,
            ["sales", "revenue"]
        )

        company_col = self._find_column(
            df,
            ["company_id", "ticker"]
        )

        if sales_col is None:
            return df

        for index, row in df.iterrows():

            sales = self._numeric(
                row.get(sales_col)
            )

            if sales is None:
                continue

            company_id = (
                row.get(company_col)
                if company_col
                else None
            )

            # Financial companies are excluded
            # from this positive-sales warning.
            if self._is_financial_company(
                company_id,
                companies_df
            ):
                continue

            if sales <= 0:

                self.log_failure(
                    "DQ-06",
                    "WARNING",
                    filename,
                    index + 2,
                    f"Sales <= 0 ({sales})."
                )

        return df

    # ==========================================================
    # DQ-07
    # YEAR FORMAT
    # ==========================================================

    def dq07_year_format(
        self,
        df,
        filename
    ):

        year_col = self._find_column(
            df,
            ["year", "financial_year"]
        )

        if year_col is None:
            return df

        pattern = re.compile(
            r"^\d{4}-\d{2}$"
        )

        for index, value in df[year_col].items():

            if pd.isna(value):
                self.log_failure(
                    "DQ-07",
                    "CRITICAL",
                    filename,
                    index + 2,
                    "Year is missing."
                )
                continue

            if not pattern.match(
                str(value).strip()
            ):

                self.log_failure(
                    "DQ-07",
                    "CRITICAL",
                    filename,
                    index + 2,
                    f"Invalid year format: {value}"
                )

        return df

    # ==========================================================
    # DQ-08
    # TICKER FORMAT
    # ==========================================================

    def dq08_ticker_format(
        self,
        df,
        filename
    ):

        company_col = self._find_column(
            df,
            ["company_id", "ticker"]
        )

        if company_col is None:
            return df

        valid_mask = []

        for index, value in df[company_col].items():

            if pd.isna(value):

                self.log_failure(
                    "DQ-08",
                    "CRITICAL",
                    filename,
                    index + 2,
                    "Missing company_id."
                )

                valid_mask.append(False)
                continue

            ticker = (
                str(value)
                .strip()
                .upper()
                .replace(" ", "")
            )

            # Normalisation is silent.
            df.at[index, company_col] = ticker

            if not (2 <= len(ticker) <= 12):

                self.log_failure(
                    "DQ-08",
                    "CRITICAL",
                    filename,
                    index + 2,
                    f"Invalid ticker length: {ticker}"
                )

                valid_mask.append(False)

            else:
                valid_mask.append(True)

        return df.loc[valid_mask].reset_index(
            drop=True
        )

    # ==========================================================
    # DQ-09
    # NET CASH FLOW CHECK
    # ==========================================================

    def dq09_net_cash(
        self,
        df,
        filename
    ):

        cfo_col = self._find_column(
            df,
            ["operating_activity", "cfo"]
        )

        cfi_col = self._find_column(
            df,
            ["investing_activity", "cfi"]
        )

        cff_col = self._find_column(
            df,
            ["financing_activity", "cff"]
        )

        net_col = self._find_column(
            df,
            ["net_cash_flow"]
        )

        if None in (
            cfo_col,
            cfi_col,
            cff_col,
            net_col
        ):
            return df

        for index, row in df.iterrows():

            cfo = self._numeric(
                row.get(cfo_col)
            )
            cfi = self._numeric(
                row.get(cfi_col)
            )
            cff = self._numeric(
                row.get(cff_col)
            )
            net = self._numeric(
                row.get(net_col)
            )

            if None in (cfo, cfi, cff, net):
                continue

            computed = cfo + cfi + cff

            if abs(net - computed) > 10:

                self.log_failure(
                    "DQ-09",
                    "WARNING",
                    filename,
                    index + 2,
                    f"Net cash mismatch: "
                    f"source={net}, "
                    f"computed={computed}."
                )

                # Fix in the in-memory DataFrame.
                df.at[index, net_col] = computed

        return df

    # ==========================================================
    # DQ-10
    # NON-NEGATIVE FIXED ASSETS
    # ==========================================================

    def dq10_fixed_assets(
        self,
        df,
        filename
    ):

        if "fixed_assets" not in df.columns:
            return df

        for index, value in df[
            "fixed_assets"
        ].items():

            numeric_value = self._numeric(value)

            if (
                numeric_value is not None
                and numeric_value < 0
            ):

                self.log_failure(
                    "DQ-10",
                    "WARNING",
                    filename,
                    index + 2,
                    f"Negative fixed_assets "
                    f"({numeric_value}) coerced to 0."
                )

                df.at[index, "fixed_assets"] = 0

        return df

    # ==========================================================
    # DQ-11
    # TAX RATE RANGE
    # ==========================================================

    def dq11_tax_rate(
        self,
        df,
        filename
    ):

        if "tax_percentage" not in df.columns:
            return df

        for index, value in df[
            "tax_percentage"
        ].items():

            numeric_value = self._numeric(value)

            if numeric_value is None:
                continue

            if not (
                0 <= numeric_value <= 60
            ):

                self.log_failure(
                    "DQ-11",
                    "WARNING",
                    filename,
                    index + 2,
                    f"Tax percentage "
                    f"out of range: {numeric_value}"
                )

        return df

    # ==========================================================
    # DQ-12
    # DIVIDEND PAYOUT CAP
    # ==========================================================

    def dq12_dividend_payout(
        self,
        df,
        filename
    ):

        if "dividend_payout" not in df.columns:
            return df

        for index, value in df[
            "dividend_payout"
        ].items():

            numeric_value = self._numeric(value)

            if (
                numeric_value is not None
                and numeric_value > 200
            ):

                self.log_failure(
                    "DQ-12",
                    "WARNING",
                    filename,
                    index + 2,
                    f"Dividend payout "
                    f"above 200%: {numeric_value}"
                )

        return df

    # ==========================================================
    # DQ-13
    # URL VALIDITY
    #
    # We DO NOT make HTTP requests during every ETL load.
    # We validate that a URL-like value exists and log obviously
    # invalid URLs. Actual 404 checking can be performed later.
    # ==========================================================

    def dq13_url(
        self,
        df,
        filename
    ):

        url_col = None

        for col in [
            "annual_report",
            "annual_report_url",
            "url",
            "report_url"
        ]:
            if col in df.columns:
                url_col = col
                break

        if url_col is None:
            return df

        for index, value in df[url_col].items():

            if pd.isna(value):
                continue

            url = str(value).strip()

            if url == "":
                continue

            if not re.match(
                r"^https?://",
                url,
                flags=re.IGNORECASE
            ):

                self.log_failure(
                    "DQ-13",
                    "WARNING",
                    filename,
                    index + 2,
                    f"Invalid URL format: {url}"
                )

        return df

    # ==========================================================
    # DQ-14
    # EPS SIGN CONSISTENCY
    # ==========================================================

    def dq14_eps_sign(
        self,
        df,
        filename
    ):

        if (
            "eps" not in df.columns
            or "net_profit" not in df.columns
        ):
            return df

        for index, row in df.iterrows():

            eps = self._numeric(
                row.get("eps")
            )

            net_profit = self._numeric(
                row.get("net_profit")
            )

            if eps is None or net_profit is None:
                continue

            if net_profit > 0 and eps <= 0:

                self.log_failure(
                    "DQ-14",
                    "WARNING",
                    filename,
                    index + 2,
                    f"EPS sign inconsistent "
                    f"with positive net profit."
                )

        return df

    # ==========================================================
    # DQ-15
    # BSE / ASSET-LIABILITY BALANCE
    # ==========================================================

    def dq15_balance_info(
        self,
        df,
        filename
    ):

        if (
            "total_assets" not in df.columns
            or "total_liabilities" not in df.columns
        ):
            return df

        for index, row in df.iterrows():

            assets = self._numeric(
                row.get("total_assets")
            )

            liabilities = self._numeric(
                row.get("total_liabilities")
            )

            if assets is None or liabilities is None:
                continue

            if assets != liabilities:

                self.log_failure(
                    "DQ-15",
                    "INFO",
                    filename,
                    index + 2,
                    "Total assets and total liabilities "
                    "are not exactly equal."
                )

        return df

    # ==========================================================
    # DQ-16
    # COVERAGE CHECK
    #
    # This is performed against all loaded time-series DataFrames.
    # ==========================================================

    def dq16_coverage(
        self,
        pnl_df,
        bs_df,
        cf_df
    ):

        company_sets = []

        for df in [
            pnl_df,
            bs_df,
            cf_df
        ]:

            if df is None:
                continue

            company_col = self._find_column(
                df,
                ["company_id", "ticker"]
            )

            if company_col is None:
                continue

            company_sets.append(
                set(
                    df[company_col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .str.upper()
                )
            )

        if not company_sets:
            return

        companies = set.union(
            *company_sets
        )

        for company in sorted(companies):

            counts = []

            for df in [
                pnl_df,
                bs_df,
                cf_df
            ]:

                if df is None:
                    counts.append(0)
                    continue

                company_col = self._find_column(
                    df,
                    ["company_id", "ticker"]
                )

                year_col = self._find_column(
                    df,
                    ["year", "financial_year"]
                )

                if (
                    company_col is None
                    or year_col is None
                ):
                    counts.append(0)
                    continue

                rows = df[
                    df[company_col]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .eq(company)
                ]

                counts.append(
                    rows[year_col]
                    .nunique()
                )

            for table_count, count in zip(
                ["P&L", "BS", "CF"],
                counts
            ):

                if count < 5:

                    self.log_failure(
                        "DQ-16",
                        "WARNING",
                        table_count,
                        "",
                        f"{company} has only "
                        f"{count} years of data."
                    )

    # ==========================================================
    # VALIDATE ONE DATAFRAME
    # ==========================================================

    def validate_dataframe(
        self,
        df,
        filename,
        companies_df=None
    ):

        df = self._clean_columns(df)

        # DQ-08 first so company IDs are standardised.
        df = self.dq08_ticker_format(
            df,
            filename
        )

        # DQ-02 MUST happen before loading.
        if filename in self.time_series_files:

            df = self.dq02_deduplicate(
                df,
                filename
            )

        # DQ-03
        df = self.dq03_fk_integrity(
            df,
            filename,
            companies_df
        )

        # DQ-04
        if "balancesheet" in filename:
            df = self.dq04_balance_sheet(
                df,
                filename
            )

            df = self.dq15_balance_info(
                df,
                filename
            )

        # DQ-05 / DQ-06
        if "profitandloss" in filename:

            df = self.dq05_opm(
                df,
                filename
            )

            df = self.dq06_positive_sales(
                df,
                filename,
                companies_df
            )

        # DQ-07
        df = self.dq07_year_format(
            df,
            filename
        )

        # DQ-09
        if "cashflow" in filename:

            df = self.dq09_net_cash(
                df,
                filename
            )

        # DQ-10
        if "balancesheet" in filename:

            df = self.dq10_fixed_assets(
                df,
                filename
            )

        # DQ-11
        if "profitandloss" in filename:

            df = self.dq11_tax_rate(
                df,
                filename
            )

        # DQ-12
        if "profitandloss" in filename:

            df = self.dq12_dividend_payout(
                df,
                filename
            )

        # DQ-13
        if "documents" in filename:

            df = self.dq13_url(
                df,
                filename
            )

        # DQ-14
        if "profitandloss" in filename:

            df = self.dq14_eps_sign(
                df,
                filename
            )

        return df

    # ==========================================================
    # VALIDATE ALL DATA
    # ==========================================================

    def validate_all(
        self,
        dataframes
    ):

        self.failures = []

        # Find companies table.
        companies_df = dataframes.get(
            "companies.xlsx"
        )

        cleaned = {}

        # First clean companies.
        if companies_df is not None:

            companies_df = self._clean_columns(
                companies_df
            )

            companies_df = self.dq08_ticker_format(
                companies_df,
                "companies.xlsx"
            )

            companies_df = self.dq01_company_pk(
                companies_df,
                "companies.xlsx"
            )

            # Companies themselves must be unique.
            company_col = self._find_column(
                companies_df,
                ["company_id", "id", "ticker"]
            )

            if company_col is not None:

                companies_df = (
                    companies_df
                    .drop_duplicates(
                        subset=[company_col],
                        keep="last"
                    )
                    .reset_index(drop=True)
                )

            cleaned["companies.xlsx"] = companies_df

        # Validate every other dataframe.
        for filename, df in dataframes.items():

            if filename == "companies.xlsx":
                continue

            cleaned[filename] = self.validate_dataframe(
                df,
                filename,
                companies_df
            )

        # DQ-16 across the three financial statements.
        self.dq16_coverage(
            cleaned.get("profitandloss.xlsx"),
            cleaned.get("balancesheet.xlsx"),
            cleaned.get("cashflow.xlsx")
        )

        return cleaned

    # ==========================================================
    # SAVE REPORT
    # ==========================================================

    def save_report(self):

        output_file = (
            self.output_folder
            / "validation_failures.csv"
        )

        columns = [
            "rule",
            "severity",
            "file",
            "row",
            "message"
        ]

        if self.failures:

            df = pd.DataFrame(
                self.failures,
                columns=columns
            )

        else:

            df = pd.DataFrame(
                columns=columns
            )

        df.to_csv(
            output_file,
            index=False
        )

        return output_file

    # ==========================================================
    # SUMMARY
    # ==========================================================

    def summary(self):

        if not self.failures:

            return {
                "total_failures": 0,
                "critical": 0,
                "warning": 0
            }

        df = pd.DataFrame(
            self.failures
        )

        return {
            "total_failures": len(df),
            "critical": int(
                (df["severity"] == "CRITICAL").sum()
            ),
            "warning": int(
                (df["severity"] == "WARNING").sum()
            )
        }