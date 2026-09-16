import io
import json
import zipfile
from pathlib import Path

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient


def _upload(client: TestClient, fixtures_dir: Path, filename: str) -> str:
    content = (fixtures_dir / filename).read_bytes()
    response = client.post("/api/datasets/upload", files={"file": (filename, content, "text/csv")})
    assert response.status_code == 200
    return str(response.json()["dataset_id"])


def _train(client: TestClient, dataset_id: str, payload: dict) -> dict:
    response = client.post(f"/api/datasets/{dataset_id}/train", json=payload)
    assert response.status_code == 200
    return dict(response.json())


REGRESSION_FEATURES = [
    "area_m2",
    "bedrooms",
    "age_years",
    "distance_to_center_km",
    "neighborhood",
    "has_parking",
]


@pytest.fixture()
def regression_experiment(client: TestClient, fixtures_dir: Path) -> dict:
    dataset_id = _upload(client, fixtures_dir, "house_prices.csv")
    return _train(
        client,
        dataset_id,
        {"task": "regression", "target": "price_usd", "features": REGRESSION_FEATURES},
    )


# --- Training persists an experiment when at least one model succeeds ------


def test_successful_training_returns_an_experiment_id(regression_experiment: dict) -> None:
    assert regression_experiment["experiment_id"] is not None
    assert len(regression_experiment["experiment_id"]) == 32  # uuid4().hex


def test_no_experiment_is_persisted_when_every_model_fails(
    client: TestClient, fixtures_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sklearn.base import BaseEstimator, RegressorMixin

    import app.services.regression_training as regression_training_module
    from app.ml.registry import ModelSpec

    class _AlwaysFails(BaseEstimator, RegressorMixin):
        def fit(self, X: object, y: object = None) -> "_AlwaysFails":
            raise RuntimeError("synthetic failure")

        def predict(self, X: object) -> object:
            raise RuntimeError("synthetic failure")

    broken = [
        ModelSpec(
            key=f"broken_{i}",
            display_name=f"Broken {i}",
            estimator_factory=_AlwaysFails,
            param_grid={},
            supports_feature_importance=False,
        )
        for i in range(3)
    ]
    monkeypatch.setattr(regression_training_module, "REGRESSION_MODELS", broken)

    dataset_id = _upload(client, fixtures_dir, "house_prices.csv")
    body = _train(
        client,
        dataset_id,
        {"task": "regression", "target": "price_usd", "features": REGRESSION_FEATURES},
    )

    assert body["winner_key"] is None
    assert body["experiment_id"] is None


# --- Downloading and reloading a supervised pipeline ------------------------


def test_downloaded_model_reloads_and_predicts_on_raw_rows_without_manual_preprocessing(
    client: TestClient, fixtures_dir: Path, regression_experiment: dict
) -> None:
    experiment_id = regression_experiment["experiment_id"]
    winner_key = regression_experiment["winner_key"]
    assert winner_key is not None

    response = client.get(f"/api/experiments/{experiment_id}/models/{winner_key}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"

    pipeline = joblib.load(io.BytesIO(response.content))
    assert list(pipeline.named_steps.keys()) == ["preprocessing", "model"]

    raw_df = pd.read_csv(fixtures_dir / "house_prices.csv").dropna().head(5)
    predictions = pipeline.predict(raw_df[REGRESSION_FEATURES])

    assert len(predictions) == 5
    assert all(p > 0 for p in predictions)  # plausible house prices, not NaN/garbage


def test_downloading_a_failed_models_artifact_returns_404(
    client: TestClient, fixtures_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sklearn.base import BaseEstimator, RegressorMixin

    import app.services.regression_training as regression_training_module
    from app.ml.registry import REGRESSION_MODELS, ModelSpec

    class _AlwaysFails(BaseEstimator, RegressorMixin):
        def fit(self, X: object, y: object = None) -> "_AlwaysFails":
            raise RuntimeError("synthetic failure")

        def predict(self, X: object) -> object:
            raise RuntimeError("synthetic failure")

    broken_spec = ModelSpec(
        key="broken_model",
        display_name="Broken",
        estimator_factory=_AlwaysFails,
        param_grid={},
        supports_feature_importance=False,
    )
    monkeypatch.setattr(
        regression_training_module, "REGRESSION_MODELS", [REGRESSION_MODELS[0], broken_spec]
    )

    dataset_id = _upload(client, fixtures_dir, "house_prices.csv")
    body = _train(
        client,
        dataset_id,
        {"task": "regression", "target": "price_usd", "features": REGRESSION_FEATURES},
    )
    experiment_id = body["experiment_id"]
    assert experiment_id is not None

    response = client.get(f"/api/experiments/{experiment_id}/models/broken_model/download")
    assert response.status_code == 404


# --- Metadata and complete-experiment ZIP -----------------------------------


def test_experiment_zip_contains_metadata_charts_models_and_eda_report(
    client: TestClient, regression_experiment: dict
) -> None:
    experiment_id = regression_experiment["experiment_id"]

    response = client.get(f"/api/experiments/{experiment_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())

    assert "metadata.json" in names
    assert "eda_report.html" in names
    for result in regression_experiment["results"]:
        if result["status"] != "success":
            continue
        assert f"models/{result['key']}.joblib" in names
        assert f"charts/{result['key']}.json" in names

    # No unsafe paths: every member must be relative and stay inside the archive.
    for name in names:
        assert not name.startswith("/")
        assert ".." not in Path(name).parts

    metadata = json.loads(archive.read("metadata.json"))
    assert metadata["task"] == "regression"
    assert metadata["target"] == "price_usd"
    assert metadata["dataset_filename"] == "house_prices.csv"
    assert metadata["winner_key"] == regression_experiment["winner_key"]
    assert metadata["created_at"]  # a timestamp is present
    assert metadata["prediction_notes"]
    model_keys = {m["key"] for m in metadata["models"]}
    assert model_keys == {"linear_regression", "random_forest_regressor", "xgboost_regressor"}
    for model in metadata["models"]:
        if model["status"] == "success":
            assert model["best_params"]
            assert model["metrics"]


def test_clustering_experiment_metadata_documents_prediction_limitations(
    client: TestClient, fixtures_dir: Path
) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")
    body = _train(
        client,
        dataset_id,
        {
            "task": "clustering",
            "target": None,
            "features": ["age", "annual_income", "spending_score", "visits_per_month"],
        },
    )
    experiment_id = body["experiment_id"]
    assert experiment_id is not None

    response = client.get(f"/api/experiments/{experiment_id}/download")
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    metadata = json.loads(archive.read("metadata.json"))

    assert "predict" in metadata["prediction_notes"].lower()
    assert "dbscan" in metadata["prediction_notes"].lower()


# --- Export security: unknown ids and path traversal ------------------------


def test_unknown_experiment_download_returns_404_not_a_crash(client: TestClient) -> None:
    response = client.get("/api/experiments/does-not-exist-1234567890abcdef12/download")
    assert response.status_code == 404
    assert "traceback" not in response.text.lower()


def test_unknown_model_key_returns_404(client: TestClient, regression_experiment: dict) -> None:
    experiment_id = regression_experiment["experiment_id"]
    response = client.get(f"/api/experiments/{experiment_id}/models/does_not_exist/download")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "malicious_experiment_id",
    [
        "..%2F..%2F..%2Fetc",
        "..",
        "a" * 32 + "/../../etc",
    ],
)
def test_path_traversal_in_experiment_id_is_rejected(
    client: TestClient, malicious_experiment_id: str
) -> None:
    response = client.get(f"/api/experiments/{malicious_experiment_id}/download")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "malicious_model_key",
    [
        "..%2F..%2F..%2Fetc%2Fpasswd",
        "../../secrets",
        # A bare ".." segment is normalized away by the HTTP client before
        # the request is even sent (RFC 3986 path normalization), so it
        # never reaches our handler as a literal value - percent-encoding
        # the dots is what actually exercises the model-key whitelist check.
        "%2E%2E",
    ],
)
def test_path_traversal_in_model_key_is_rejected(
    client: TestClient, regression_experiment: dict, malicious_model_key: str
) -> None:
    experiment_id = regression_experiment["experiment_id"]
    response = client.get(f"/api/experiments/{experiment_id}/models/{malicious_model_key}/download")
    assert response.status_code == 404
