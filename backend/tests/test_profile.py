from pathlib import Path

from fastapi.testclient import TestClient


def _upload(client: TestClient, fixtures_dir: Path, filename: str) -> str:
    content = (fixtures_dir / filename).read_bytes()
    response = client.post("/api/datasets/upload", files={"file": (filename, content, "text/csv")})
    assert response.status_code == 200
    return str(response.json()["dataset_id"])


def test_customer_segments_profile_matches_known_fixture_facts(
    client: TestClient, fixtures_dir: Path
) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")

    response = client.get(f"/api/datasets/{dataset_id}/profile")
    assert response.status_code == 200
    body = response.json()

    assert body["row_count"] == 222
    assert body["column_count"] == 8
    assert body["duplicate_row_count"] == 2

    missing_by_column = {c["name"]: c["missing_count"] for c in body["columns"]}
    assert missing_by_column["annual_income"] == 2
    assert missing_by_column["spending_score"] == 2
    assert missing_by_column["region"] == 2
    assert missing_by_column["customer_id"] == 0
    assert missing_by_column["churned"] == 0

    percentage_by_column = {c["name"]: c["missing_percentage"] for c in body["columns"]}
    assert percentage_by_column["annual_income"] == round(2 / 222 * 100, 2)

    dtype_by_column = {c["name"]: c["dtype"] for c in body["columns"]}
    assert dtype_by_column["age"] == "numeric"
    assert dtype_by_column["annual_income"] == "numeric"
    assert dtype_by_column["visits_per_month"] == "numeric"
    assert dtype_by_column["churned"] == "numeric"
    assert dtype_by_column["customer_id"] == "categorical"
    assert dtype_by_column["membership_type"] == "categorical"
    assert dtype_by_column["region"] == "categorical"

    unique_by_column = {c["name"]: c["unique_count"] for c in body["columns"]}
    assert unique_by_column["customer_id"] == 220
    assert unique_by_column["membership_type"] == 3
    assert unique_by_column["region"] == 4
    assert unique_by_column["churned"] == 2

    numeric_summary_columns = {s["column"] for s in body["numeric_summary"]}
    assert numeric_summary_columns == {
        "age",
        "annual_income",
        "spending_score",
        "visits_per_month",
        "churned",
    }
    summary_by_column = {s["column"]: s for s in body["numeric_summary"]}
    assert summary_by_column["age"]["count"] == 222
    assert summary_by_column["annual_income"]["count"] == 220
    for stats in body["numeric_summary"]:
        assert stats["min"] <= stats["median"] <= stats["max"]

    assert len(body["numeric_distributions"]) == len(numeric_summary_columns)
    distribution_by_column = {d["column"]: d for d in body["numeric_distributions"]}
    for column in ("age", "annual_income", "spending_score", "visits_per_month"):
        assert len(distribution_by_column[column]["bins"]) == 10
    # churned has only 2 distinct values, so it gets one bar per value
    # instead of being forced into 10 mostly-empty equal-width buckets.
    churned_bins = distribution_by_column["churned"]["bins"]
    assert len(churned_bins) == 2
    assert {b["bin_start"] for b in churned_bins} == {0.0, 1.0}
    for distribution in body["numeric_distributions"]:
        assert sum(b["count"] for b in distribution["bins"]) > 0

    frequency_columns = {f["column"] for f in body["categorical_frequencies"]}
    # customer_id is high-cardinality (near-unique) and must be excluded.
    assert "customer_id" not in frequency_columns
    assert frequency_columns == {"membership_type", "region"}
    membership_frequency = next(
        f for f in body["categorical_frequencies"] if f["column"] == "membership_type"
    )
    assert membership_frequency["truncated"] is False
    assert sum(c["count"] for c in membership_frequency["categories"]) == 222

    assert body["correlation"] is not None
    assert set(body["correlation"]["columns"]) == numeric_summary_columns
    diagonal_index = body["correlation"]["columns"].index("age")
    assert body["correlation"]["matrix"][diagonal_index][diagonal_index] == 1.0


def test_house_prices_profile_matches_known_fixture_facts(
    client: TestClient, fixtures_dir: Path
) -> None:
    dataset_id = _upload(client, fixtures_dir, "house_prices.csv")

    response = client.get(f"/api/datasets/{dataset_id}/profile")
    assert response.status_code == 200
    body = response.json()

    assert body["row_count"] == 222
    assert body["column_count"] == 8
    assert body["duplicate_row_count"] == 2

    missing_by_column = {c["name"]: c["missing_count"] for c in body["columns"]}
    assert missing_by_column["area_m2"] == 2
    assert missing_by_column["neighborhood"] == 2
    assert missing_by_column["has_parking"] == 2
    assert missing_by_column["price_usd"] == 0

    frequency_columns = {f["column"] for f in body["categorical_frequencies"]}
    assert "property_id" not in frequency_columns
    assert frequency_columns == {"neighborhood", "has_parking"}

    assert body["correlation"] is not None
    numeric_summary_columns = {s["column"] for s in body["numeric_summary"]}
    assert numeric_summary_columns == {
        "area_m2",
        "bedrooms",
        "age_years",
        "distance_to_center_km",
        "price_usd",
    }
    assert set(body["correlation"]["columns"]) == numeric_summary_columns


def test_profile_for_unknown_dataset_returns_404(client: TestClient) -> None:
    response = client.get("/api/datasets/does-not-exist/profile")
    assert response.status_code == 404


def test_eda_report_downloads_as_html(client: TestClient, fixtures_dir: Path) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")

    response = client.get(f"/api/datasets/{dataset_id}/profile/report")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith('.html"')

    html_content = response.text
    assert "<!doctype html>" in html_content.lower()
    assert "customer_segments.csv" in html_content
    assert "membership_type" in html_content
    # Self-contained: no external network dependencies.
    assert "http://" not in html_content
    assert "https://" not in html_content
    assert "<script" not in html_content.lower()


def test_eda_report_for_unknown_dataset_returns_404(client: TestClient) -> None:
    response = client.get("/api/datasets/does-not-exist/profile/report")
    assert response.status_code == 404
