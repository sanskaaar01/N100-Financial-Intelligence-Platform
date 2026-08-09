-- N100 Financial Intelligence Platform
-- Sprint 1 - Exploratory Queries


-- 1. Total number of companies
SELECT COUNT(*) AS total_companies
FROM companies;


-- 2. Companies by broad sector
SELECT
    broad_sector,
    COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;


-- 3. Top 10 companies by market capitalisation
SELECT
    company_id,
    year,
    market_cap_crore
FROM market_cap
ORDER BY market_cap_crore DESC
LIMIT 10;


-- 4. Top 10 companies by ROE
SELECT
    company_id,
    year,
    return_on_equity_pct
FROM financial_ratios
WHERE return_on_equity_pct IS NOT NULL
ORDER BY return_on_equity_pct DESC
LIMIT 10;


-- 5. Top 10 companies by net profit margin
SELECT
    company_id,
    year,
    net_profit_margin_pct
FROM financial_ratios
WHERE net_profit_margin_pct IS NOT NULL
ORDER BY net_profit_margin_pct DESC
LIMIT 10;


-- 6. Companies with zero debt
SELECT
    company_id,
    year,
    debt_to_equity
FROM financial_ratios
WHERE debt_to_equity = 0
ORDER BY company_id, year;


-- 7. Average ROE by sector
SELECT
    s.broad_sector,
    ROUND(AVG(fr.return_on_equity_pct), 2) AS average_roe
FROM financial_ratios fr
JOIN sectors s
    ON fr.company_id = s.company_id
WHERE fr.return_on_equity_pct IS NOT NULL
GROUP BY s.broad_sector
ORDER BY average_roe DESC;


-- 8. Companies with the highest free cash flow
SELECT
    company_id,
    year,
    free_cash_flow_cr
FROM financial_ratios
WHERE free_cash_flow_cr IS NOT NULL
ORDER BY free_cash_flow_cr DESC
LIMIT 10;


-- 9. Companies with highest interest coverage
SELECT
    company_id,
    year,
    interest_coverage
FROM financial_ratios
WHERE interest_coverage IS NOT NULL
ORDER BY interest_coverage DESC
LIMIT 10;


-- 10. Latest available financial year for each company
SELECT
    company_id,
    MAX(year) AS latest_year
FROM profitandloss
GROUP BY company_id
ORDER BY company_id;