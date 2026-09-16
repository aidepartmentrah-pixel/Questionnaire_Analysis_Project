from pathlib import Path

from fastapi.testclient import TestClient


def _upload(client: TestClient, fixtures_dir: Path, filename: str) -> str:
    content = (fixtures_dir / filename).read_bytes()
    response = client.post("/api/datasets/upload", files={"file": (filename, content, "text/csv")})
    assert response.status_code == 200
    return str(response.json()["dataset_id"])


def _preview(client: TestClient, dataset_id: str, payload: dict) -> object:
    return client.post(f"/api/datasets/{dataset_id}/preprocessing-preview", json=payload)


def test_regression_preview_matches_known_fixture_facts(
    client: TestClient, fixtures_dir: Path
) -> None:
    dataset_id = _upload(client, fixtures_dir, "house_prices.csv")
    features = [
        "area_m2",
        "bedrooms",
        "age_years",
        "distance_to_center_km",
        "neighborhood",
        "has_parking",
    ]

    response = _preview(
        client,
        dataset_id,
        {"task": "regression", "target": "price_usd", "features": features},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["task"] == "regression"
    assert body["target"] == "price_usd"
    assert body["features"] == features
    assert body["original_rows"] == 222
    assert body["removed_missing_rows"] == 6
    assert body["removed_duplicate_rows"] == 2
    assert body["final_rows"] == 214
    assert body["ready_to_train"] is True

    # One-hot encoding must have expanded the categorical columns.
    assert "area_m2" in body["final_feature_columns"]
    assert any(name.startswith("neighborhood_") for name in body["final_feature_columns"])
    assert any(name.startswith("has_parking_") for name in body["final_feature_columns"])


def test_classification_preview_matches_known_fixture_facts(
    client: TestClient, fixtures_dir: Path
) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")
    features = [
        "age",
        "annual_income",
        "spending_score",
        "visits_per_month",
        "membership_type",
        "region",
    ]

    response = _preview(
        client,
        dataset_id,
        {"task": "classification", "target": "churned", "features": features},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["original_rows"] == 222
    assert body["removed_missing_rows"] == 6
    assert body["removed_duplicate_rows"] == 2
    assert body["final_rows"] == 214
    assert body["ready_to_train"] is True
    assert any(name.startswith("membership_type_") for name in body["final_feature_columns"])


def test_clustering_preview_matches_known_fixture_facts(
    client: TestClient, fixtures_dir: Path
) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")
    features = ["age", "annual_income", "spending_score", "visits_per_month"]

    response = _preview(
        client, dataset_id, {"task": "clustering", "target": None, "features": features}
    )

    assert response.status_code == 200
    body = response.json()

    assert body["target"] is None
    assert body["original_rows"] == 222
    assert body["removed_missing_rows"] == 4
    assert body["removed_duplicate_rows"] == 2
    assert body["final_rows"] == 216
    assert body["ready_to_train"] is True
    # No one-hot columns: clustering v1 only uses numeric features directly.
    assert set(body["final_feature_columns"]) == set(features)


def test_target_selected_as_feature_is_rejected(client: TestClient, fixtures_dir: Path) -> None:
    dataset_id = _upload(client, fixtures_dir, "house_prices.csv")

    response = _preview(
        client,
        dataset_id,
        {"task": "regression", "target": "price_usd", "features": ["area_m2", "price_usd"]},
    )

    assert response.status_code == 422
    assert "cannot also be selected" in response.json()["detail"].lower()


def test_regression_without_target_is_rejected(client: TestClient, fixtures_dir: Path) -> None:
    dataset_id = _upload(client, fixtures_dir, "house_prices.csv")

    response = _preview(
        client, dataset_id, {"task": "regression", "target": None, "features": ["area_m2"]}
    )

    assert response.status_code == 422
    assert "requires a target" in response.json()["detail"].lower()


def test_classification_without_target_is_rejected(client: TestClient, fixtures_dir: Path) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")

    response = _preview(
        client, dataset_id, {"task": "classification", "target": None, "features": ["age"]}
    )

    assert response.status_code == 422
    assert "requires a target" in response.json()["detail"].lower()


def test_clustering_with_target_is_rejected(client: TestClient, fixtures_dir: Path) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")

    response = _preview(
        client,
        dataset_id,
        {"task": "clustering", "target": "churned", "features": ["age", "annual_income"]},
    )

    assert response.status_code == 422
    assert "does not use a target" in response.json()["detail"].lower()


def test_clustering_rejects_categorical_features(client: TestClient, fixtures_dir: Path) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")

    response = _preview(
        client,
        dataset_id,
        {"task": "clustering", "target": None, "features": ["age", "membership_type"]},
    )

    assert response.status_code == 422
    assert "only supports numeric features" in response.json()["detail"].lower()


def test_unknown_column_is_rejected(client: TestClient, fixtures_dir: Path) -> None:
    dataset_id = _upload(client, fixtures_dir, "house_prices.csv")

    response = _preview(
        client,
        dataset_id,
        {"task": "regression", "target": "price_usd", "features": ["does_not_exist"]},
    )

    assert response.status_code == 422
    assert "unknown column" in response.json()["detail"].lower()


def test_empty_feature_list_is_rejected(client: TestClient, fixtures_dir: Path) -> None:
    dataset_id = _upload(client, fixtures_dir, "house_prices.csv")

    response = _preview(
        client, dataset_id, {"task": "regression", "target": "price_usd", "features": []}
    )

    assert response.status_code == 422
    assert "select at least one feature" in response.json()["detail"].lower()


def test_too_few_rows_marks_configuration_not_ready(client: TestClient) -> None:
    csv_content = (
        b"a,b,target\n" + b"\n".join(f"{i},{i * 2},{i % 2}".encode() for i in range(10)) + b"\n"
    )
    upload = client.post(
        "/api/datasets/upload", files={"file": ("tiny.csv", csv_content, "text/csv")}
    )
    assert upload.status_code == 200
    dataset_id = upload.json()["dataset_id"]

    response = _preview(
        client,
        dataset_id,
        {"task": "classification", "target": "target", "features": ["a", "b"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["final_rows"] == 10
    assert body["ready_to_train"] is False
    assert any("at least" in w.lower() for w in body["warnings"])


def test_regression_preview_flags_a_categorical_target_as_not_ready(client: TestClient) -> None:
    """The live Configure-step preview must catch a categorical regression
    target (e.g. a neighborhood name) before the user ever reaches Train,
    where it would otherwise fail deep inside sklearn with a raw traceback.
    """
    rows = [f"{i},{'red' if i % 2 else 'blue'}" for i in range(40)]
    csv_content = ("a,y\n" + "\n".join(rows) + "\n").encode()
    upload = client.post(
        "/api/datasets/upload", files={"file": ("categorical_target.csv", csv_content, "text/csv")}
    )
    dataset_id = upload.json()["dataset_id"]

    response = _preview(
        client, dataset_id, {"task": "regression", "target": "y", "features": ["a"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ready_to_train"] is False
    assert any("numeric" in w.lower() and "categorical" in w.lower() for w in body["warnings"])


def test_classification_preview_flags_a_continuous_looking_target_as_not_ready(
    client: TestClient,
) -> None:
    """The live Configure-step preview must catch the same "this target looks
    continuous, not categorical" problem that training rejects, so the user
    sees a clear reason before ever reaching Train - not just at train time.
    """
    rows = [f"{i},{i * 1.37}" for i in range(60)]
    csv_content = ("a,y\n" + "\n".join(rows) + "\n").encode()
    upload = client.post(
        "/api/datasets/upload", files={"file": ("continuous.csv", csv_content, "text/csv")}
    )
    dataset_id = upload.json()["dataset_id"]

    response = _preview(
        client, dataset_id, {"task": "classification", "target": "y", "features": ["a"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ready_to_train"] is False
    assert any("too many" in w.lower() and "continuous" in w.lower() for w in body["warnings"])


def test_preview_for_unknown_dataset_returns_404(client: TestClient) -> None:
    response = _preview(
        client, "does-not-exist", {"task": "regression", "target": "y", "features": ["x"]}
    )
    assert response.status_code == 404
