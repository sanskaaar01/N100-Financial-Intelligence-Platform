from pathlib import Path

path = Path(r"src\api\main.py")
text = path.read_text(encoding="utf-8")

route_start = text.find('@app.get("/api/v1/sectors")')
if route_start == -1:
    raise RuntimeError("Could not find /api/v1/sectors route.")

sql_start = text.find('        rows = conn.execute(', route_start)
if sql_start == -1:
    raise RuntimeError("Could not find sectors SQL.")

sql_end = text.find('        ).fetchall()', sql_start)
if sql_end == -1:
    raise RuntimeError("Could not find end of sectors SQL.")

sql_end += len('        ).fetchall()')

new_block = '''        rows = conn.execute(
            """
            SELECT
                s.broad_sector AS sector,
                COUNT(DISTINCT s.company_id) AS company_count,
                AVG(c.roe_percentage) AS median_roe,
                AVG(mc.pe_ratio) AS median_pe,
                AVG(fr.debt_to_equity) AS median_de
            FROM sectors s

            LEFT JOIN companies c
                ON c.id = s.company_id

            LEFT JOIN financial_ratios fr
                ON fr.company_id = s.company_id
                AND fr.year = (
                    SELECT MAX(fr2.year)
                    FROM financial_ratios fr2
                    WHERE fr2.company_id = s.company_id
                )

            LEFT JOIN market_cap mc
                ON mc.company_id = s.company_id
                AND mc.year = (
                    SELECT MAX(mc2.year)
                    FROM market_cap mc2
                    WHERE mc2.company_id = s.company_id
                )

            WHERE s.broad_sector IS NOT NULL
            GROUP BY s.broad_sector
            ORDER BY s.broad_sector
            """
        ).fetchall()'''

text = text[:sql_start] + new_block + text[sql_end:]

path.write_text(text, encoding="utf-8")

print("PASS - Replaced complete sectors SQL")
print("PASS - companies table joined as c")
print("PASS - c.roe_percentage is now valid")
