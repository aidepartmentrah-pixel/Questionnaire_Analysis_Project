from pathlib import Path

from fastapi.testclient import TestClient

CUSTOMER_SEGMENTS_COLUMNS = {
    "customer_id",
    "age",
    "annual_income",
    "spending_score",
    "visits_per_month",
    "membership_type",
    "region",
    "churned",
}

HOUSE_PRICES_COLUMNS = {
    "property_id",
    "area_m2",
    "bedrooms",
    "age_years",
    "distance_to_center_km",
    "neighborhood",
    "has_parking",
    "price_usd",
}


def _upload(client: TestClient, filename: str, content: bytes, content_type: str = "text/csv"):
    return client.post(
        "/api/datasets/upload",
        files={"file": (filename, content, content_type)},
    )


def test_upload_customer_segments_fixture(client: TestClient, fixtures_dir: Path) -> None:
    content = (fixtures_dir / "customer_segments.csv").read_bytes()

    response = _upload(client, "customer_segments.csv", content)

    assert response.status_code == 200
    body = response.json()

    assert body["filename"] == "customer_segments.csv"
    assert body["row_count"] == 222
    assert body["column_count"] == 8
    assert {c["name"] for c in body["columns"]} == CUSTOMER_SEGMENTS_COLUMNS
    assert body["dataset_id"]
    assert 0 < len(body["preview"]) <= 50
    assert body["preview_row_count"] == len(body["preview"])

    column_types = {c["name"]: c["dtype"] for c in body["columns"]}
    assert column_types["age"] == "numeric"
    assert column_types["annual_income"] == "numeric"
    assert column_types["membership_type"] == "categorical"

    unique_counts = {c["name"]: c["unique_count"] for c in body["columns"]}
    assert unique_counts["customer_id"] == 220
    assert unique_counts["membership_type"] == 3
    assert unique_counts["churned"] == 2
    assert column_types["region"] == "categorical"


def test_upload_house_prices_fixture(client: TestClient, fixtures_dir: Path) -> None:
    content = (fixtures_dir / "house_prices.csv").read_bytes()

    response = _upload(client, "house_prices.csv", content)

    assert response.status_code == 200
    body = response.json()

    assert body["filename"] == "house_prices.csv"
    assert body["row_count"] == 222
    assert body["column_count"] == 8
    assert {c["name"] for c in body["columns"]} == HOUSE_PRICES_COLUMNS

    column_types = {c["name"]: c["dtype"] for c in body["columns"]}
    assert column_types["area_m2"] == "numeric"
    assert column_types["price_usd"] == "numeric"
    assert column_types["neighborhood"] == "categorical"
    assert column_types["has_parking"] == "categorical"


def test_uploading_new_dataset_replaces_active_one(client: TestClient, fixtures_dir: Path) -> None:
    first = _upload(
        client, "customer_segments.csv", (fixtures_dir / "customer_segments.csv").read_bytes()
    )
    second = _upload(client, "house_prices.csv", (fixtures_dir / "house_prices.csv").read_bytes())

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["dataset_id"] != second.json()["dataset_id"]
    assert second.json()["filename"] == "house_prices.csv"


def test_missing_values_become_json_null_in_preview(client: TestClient) -> None:
    csv_content = b"a,b\n1,\n2,3\n"

    response = _upload(client, "small.csv", csv_content)

    assert response.status_code == 200
    preview = response.json()["preview"]
    assert preview[0]["b"] is None
    assert preview[1]["b"] == 3


def test_empty_csv_is_rejected(client: TestClient) -> None:
    response = _upload(client, "empty.csv", b"")

    assert response.status_code == 422
    assert "empty" in response.json()["detail"].lower()


def test_header_only_csv_is_rejected(client: TestClient) -> None:
    response = _upload(client, "header_only.csv", b"col_a,col_b,col_c\n")

    assert response.status_code == 422
    assert "no data rows" in response.json()["detail"].lower()


def test_malformed_csv_is_rejected(client: TestClient) -> None:
    # Header declares 3 fields; the second data row supplies 5 -> unparsable.
    csv_content = b"a,b,c\n1,2,3\n1,2,3,4,5\n"

    response = _upload(client, "malformed.csv", csv_content)

    assert response.status_code == 422
    assert "could not be parsed" in response.json()["detail"].lower()


def test_duplicate_header_csv_is_rejected(client: TestClient) -> None:
    csv_content = b"a,b,a\n1,2,3\n"

    response = _upload(client, "duplicate_headers.csv", csv_content)

    assert response.status_code == 422
    assert "duplicate column names" in response.json()["detail"].lower()


def test_unsupported_extension_is_rejected(client: TestClient) -> None:
    response = _upload(client, "data.txt", b"a,b\n1,2\n", content_type="text/plain")

    assert response.status_code == 422
    assert "only .csv files" in response.json()["detail"].lower()
