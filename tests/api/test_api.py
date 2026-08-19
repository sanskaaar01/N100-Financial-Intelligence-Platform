from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "db_row_counts" in data


def test_companies_returns_92():
    response = client.get("/api/v1/companies")
    assert response.status_code == 200

    data = response.json()

    if isinstance(data, dict):
        rows = data.get("data", [])
    else:
        rows = data

    assert len(rows) == 92


def test_tcs_profile():
    response = client.get("/api/v1/companies/TCS")
    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert "company_name" in data


def test_invalid_company():
    response = client.get("/api/v1/companies/INVALID")
    assert response.status_code == 404


def test_screener_min_roe():
    response = client.get(
        "/api/v1/screener",
        params={"min_roe": 15},
    )

    assert response.status_code == 200

    data = response.json()

    if isinstance(data, dict):
        rows = data.get("data", [])
    else:
        rows = data

    for row in rows:
        assert float(row["roe_pct"]) >= 15


def test_screener_invalid_parameter():
    response = client.get(
        "/api/v1/screener",
        params={"min_roe": "invalid"},
    )

    assert response.status_code == 400


def test_sectors():
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200

    data = response.json()

    if isinstance(data, dict):
        rows = data.get("data", [])
    else:
        rows = data

    assert len(rows) == 10


def test_information_technology_sector():
    response = client.get("/api/v1/sectors/Information%20Technology/companies")

    assert response.status_code == 200

    data = response.json()

    if isinstance(data, dict):
        rows = data.get("data", [])
    else:
        rows = data

    for row in rows:
        assert row.get("broad_sector") == "Information Technology"
