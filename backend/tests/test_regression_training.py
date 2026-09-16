from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.model_selection import GridSearchCV

import app.services.regression_training as regression_training_module
from app.ml.registry import REGRESSION_MODELS, ModelSpec
from app.schemas.config import ScalerType, TaskType
from app.schemas.training import ModelResult, TrainingRequest
from app.services.dataset_store import ActiveDataset
from app.services.regression_training import (
    compute_regression_metrics,
    run_regression_training,
    select_winner,
)


def _upload(client: TestClient, fixtures_dir: Path, filename: str) -> str:
    content = (fixtures_dir / filename).read_bytes()
    response = client.post("/api/datasets/upload", files={"file": (filename, content, "text/csv")})
    assert response.status_code == 200
    return str(response.json()["dataset_id"])


def _train(client: TestClient, dataset_id: str, payload: dict) -> object:
    return client.post(f"/api/datasets/{dataset_id}/train", json=payload)


# --- Unit tests: metric calculations and winner selection -----------------


def test_compute_regression_metrics_matches_known_values() -> None:
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([12.0, 18.0, 33.0])

    metrics = compute_regression_metrics(y_true, y_pred)

    assert metrics["mae"] == pytest.approx((2 + 2 + 3) / 3)
    assert metrics["rmse"] == pytest.approx(np.sqrt((4 + 4 + 9) / 3))
    assert metrics["r2"] == pytest.approx(1 - (4 + 4 + 9) / np.sum((y_true - y_true.mean()) ** 2))


def test_compute_regression_metrics_perfect_prediction_is_zero_error() -> None:
    y = np.array([1.0, 2.0, 3.0, 4.0])
    metrics = compute_regression_metrics(y, y.copy())

    assert metrics["mae"] == pytest.approx(0.0)
    assert metrics["rmse"] == pytest.approx(0.0)
    assert metrics["r2"] == pytest.approx(1.0)


def _result(key: str, status: str, rmse: float | None = None) -> ModelResult:
    return ModelResult(
        key=key,
        display_name=key,
        status=status,
        duration_seconds=0.1,
        metrics={"mae": 1.0, "rmse": rmse, "r2": 0.5} if rmse is not None else None,
    )


def test_select_winner_picks_lowest_rmse_among_successful() -> None:
    results = [
        _result("a", "success", rmse=50.0),
        _result("b", "success", rmse=20.0),
        _result("c", "failed"),
    ]

    assert select_winner(results) == "b"


def test_select_winner_ignores_failed_models_even_if_listed_first() -> None:
    results = [_result("a", "failed"), _result("b", "success", rmse=10.0)]

    assert select_winner(results) == "b"


def test_select_winner_returns_none_when_every_model_fails() -> None:
    results = [_result("a", "failed"), _result("b", "failed")]

    assert select_winner(results) is None


# --- Proves tuning never sees the held-out test split ----------------------


def test_tuning_only_receives_the_training_split(monkeypatch: pytest.MonkeyPatch) -> None:
    rng = np.random.default_rng(0)
    n = 40
    df = pd.DataFrame(
        {
            "x1": rng.normal(size=n),
            "x2": rng.normal(size=n),
            "y": rng.normal(size=n),
        }
    )

    active = ActiveDataset(dataset_id="t", filename="t.csv", csv_path=Path("t.csv"), dataframe=df)
    request = TrainingRequest(
        task=TaskType.regression,
        target="y",
        features=["x1", "x2"],
        drop_duplicates=False,
        scaler=ScalerType.standard,
    )

    seen_fit_sizes: list[int] = []
    original_fit = GridSearchCV.fit

    def spying_fit(
        self: GridSearchCV, X: pd.DataFrame, y: pd.Series, **kwargs: object
    ) -> GridSearchCV:
        seen_fit_sizes.append(len(X))
        return original_fit(self, X, y, **kwargs)

    monkeypatch.setattr(GridSearchCV, "fit", spying_fit)

    response = run_regression_training(active, request).response

    expected_train_rows = response.train_rows
    assert response.test_rows == n - expected_train_rows
    # Every model's GridSearchCV.fit() must only ever have seen the 32
    # training rows (80% of 40), never the 8 held-out test rows.
    assert seen_fit_sizes
    assert all(size == expected_train_rows for size in seen_fit_sizes)


# --- Graceful partial failure ----------------------------------------------


class _AlwaysFailsEstimator(BaseEstimator, RegressorMixin):
    def fit(self, X: object, y: object = None) -> "_AlwaysFailsEstimator":
        raise RuntimeError("synthetic training failure")

    def predict(self, X: object) -> object:
        raise RuntimeError("synthetic training failure")


def test_partial_model_failure_does_not_abort_the_others(monkeypatch: pytest.MonkeyPatch) -> None:
    rng = np.random.default_rng(1)
    n = 40
    df = pd.DataFrame({"x1": rng.normal(size=n), "y": rng.normal(size=n)})

    broken_spec = ModelSpec(
        key="broken_model",
        display_name="Broken Model",
        estimator_factory=_AlwaysFailsEstimator,
        param_grid={},
        supports_feature_importance=False,
    )
    monkeypatch.setattr(
        regression_training_module,
        "REGRESSION_MODELS",
        [REGRESSION_MODELS[0], broken_spec, REGRESSION_MODELS[2]],
    )

    active = ActiveDataset(dataset_id="t", filename="t.csv", csv_path=Path("t.csv"), dataframe=df)
    request = TrainingRequest(
        task=TaskType.regression,
        target="y",
        features=["x1"],
        drop_duplicates=False,
        scaler=ScalerType.none,
    )

    run = regression_training_module.run_regression_training(active, request)
    response = run.response

    assert len(response.results) == 3
    by_key = {r.key: r for r in response.results}
    assert by_key["broken_model"].status == "failed"
    assert by_key["broken_model"].warning
    assert by_key["broken_model"].metrics is None
    assert by_key[REGRESSION_MODELS[0].key].status == "success"
    assert by_key[REGRESSION_MODELS[2].key].status == "success"
    assert response.winner_key in {REGRESSION_MODELS[0].key, REGRESSION_MODELS[2].key}
    assert set(run.fitted_pipelines.keys()) == {REGRESSION_MODELS[0].key, REGRESSION_MODELS[2].key}


# --- Real, bounded end-to-end training via the API -------------------------


def test_regression_training_real_bounded_integration(
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

    response = _train(
        client,
        dataset_id,
        {"task": "regression", "target": "price_usd", "features": features},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["train_rows"] + body["test_rows"] == 214
    assert body["primary_metric"] == "rmse"
    assert len(body["results"]) == 3

    keys = {r["key"] for r in body["results"]}
    assert keys == {"linear_regression", "random_forest_regressor", "xgboost_regressor"}

    successful = [r for r in body["results"] if r["status"] == "success"]
    assert len(successful) == 3
    for result in successful:
        assert result["best_params"]
        assert all(np.isfinite(v) for v in result["metrics"].values())
        assert result["charts"]["actual_vs_predicted"]
        assert result["charts"]["residuals"]

    rf_and_xgb = [r for r in successful if r["key"] != "linear_regression"]
    assert all(r["feature_importances"] for r in rf_and_xgb)
    # Feature names must be the readable column names, not the
    # ColumnTransformer's internal "numeric__"/"categorical__"-prefixed ones.
    for result in rf_and_xgb:
        names = {fi["feature"] for fi in result["feature_importances"]}
        assert "area_m2" in names
        assert any(name.startswith("neighborhood_") for name in names)
        assert not any(name.startswith(("numeric__", "categorical__")) for name in names)
    linear = next(r for r in successful if r["key"] == "linear_regression")
    assert linear["feature_importances"] is None

    winner = body["winner_key"]
    assert winner is not None
    winner_rmse = next(r["metrics"]["rmse"] for r in successful if r["key"] == winner)
    assert winner_rmse == min(r["metrics"]["rmse"] for r in successful)


def test_training_with_too_few_rows_is_rejected(client: TestClient) -> None:
    csv_content = b"a,y\n" + b"\n".join(f"{i},{i * 2}".encode() for i in range(10)) + b"\n"
    upload = client.post(
        "/api/datasets/upload", files={"file": ("tiny.csv", csv_content, "text/csv")}
    )
    dataset_id = upload.json()["dataset_id"]

    response = _train(client, dataset_id, {"task": "regression", "target": "y", "features": ["a"]})

    assert response.status_code == 422
    assert "usable rows" in response.json()["detail"].lower()


def test_categorical_target_is_rejected_with_a_clean_message(client: TestClient) -> None:
    """Regression test for a real bug: picking a categorical column (e.g. a
    neighborhood name) as a regression target used to reach GridSearchCV and
    fail deep inside sklearn with a raw Python traceback ("could not convert
    string to float") shown to the user instead of a clean, early message.
    """
    rows = [f"{i},{'red' if i % 2 else 'blue'}" for i in range(40)]
    csv_content = ("a,y\n" + "\n".join(rows) + "\n").encode()
    upload = client.post(
        "/api/datasets/upload", files={"file": ("categorical_target.csv", csv_content, "text/csv")}
    )
    dataset_id = upload.json()["dataset_id"]

    response = _train(client, dataset_id, {"task": "regression", "target": "y", "features": ["a"]})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "numeric" in detail.lower()
    assert "categorical" in detail.lower()
    assert "traceback" not in detail.lower()


def test_train_for_unknown_dataset_returns_404(client: TestClient) -> None:
    response = _train(
        client, "does-not-exist", {"task": "regression", "target": "y", "features": ["x"]}
    )
    assert response.status_code == 404
