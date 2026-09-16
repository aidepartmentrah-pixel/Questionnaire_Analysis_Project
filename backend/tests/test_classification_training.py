from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import GridSearchCV

import app.services.classification_training as classification_training_module
from app.ml.registry import CLASSIFICATION_MODELS, ModelSpec
from app.schemas.config import ScalerType, TaskType
from app.schemas.training import ModelResult, TrainingRequest
from app.services.classification_training import (
    compute_classification_metrics,
    run_classification_training,
    select_winner,
)
from app.services.dataset_store import ActiveDataset


def _upload(client: TestClient, fixtures_dir: Path, filename: str) -> str:
    content = (fixtures_dir / filename).read_bytes()
    response = client.post("/api/datasets/upload", files={"file": (filename, content, "text/csv")})
    assert response.status_code == 200
    return str(response.json()["dataset_id"])


def _train(client: TestClient, dataset_id: str, payload: dict) -> object:
    return client.post(f"/api/datasets/{dataset_id}/train", json=payload)


# --- Unit tests: metric calculations and winner selection -----------------


def test_compute_classification_metrics_perfect_prediction_is_all_ones() -> None:
    y = np.array([0, 1, 0, 1, 1])
    metrics = compute_classification_metrics(y, y.copy())

    assert metrics["accuracy"] == pytest.approx(1.0)
    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall"] == pytest.approx(1.0)
    assert metrics["f1"] == pytest.approx(1.0)


def test_compute_classification_metrics_known_accuracy() -> None:
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 1, 1, 1])

    metrics = compute_classification_metrics(y_true, y_pred)

    assert metrics["accuracy"] == pytest.approx(0.75)
    for value in metrics.values():
        assert 0.0 <= value <= 1.0


def _result(key: str, status: str, f1: float | None = None) -> ModelResult:
    return ModelResult(
        key=key,
        display_name=key,
        status=status,
        duration_seconds=0.1,
        metrics={"accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": f1}
        if f1 is not None
        else None,
    )


def test_select_winner_picks_highest_f1_among_successful() -> None:
    results = [
        _result("a", "success", f1=0.5),
        _result("b", "success", f1=0.9),
        _result("c", "failed"),
    ]

    assert select_winner(results) == "b"


def test_select_winner_ignores_failed_models() -> None:
    results = [_result("a", "failed"), _result("b", "success", f1=0.1)]

    assert select_winner(results) == "b"


def test_select_winner_returns_none_when_every_model_fails() -> None:
    assert select_winner([_result("a", "failed"), _result("b", "failed")]) is None


# --- Proves tuning never sees the held-out test split ----------------------


def test_tuning_only_receives_the_training_split(monkeypatch: pytest.MonkeyPatch) -> None:
    rng = np.random.default_rng(0)
    n = 60
    labels = np.array([0] * (n // 2) + [1] * (n // 2))
    df = pd.DataFrame({"x1": rng.normal(size=n) + labels, "y": labels})

    active = ActiveDataset(dataset_id="t", filename="t.csv", csv_path=Path("t.csv"), dataframe=df)
    request = TrainingRequest(
        task=TaskType.classification,
        target="y",
        features=["x1"],
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

    response = run_classification_training(active, request).response

    assert response.test_rows == n - response.train_rows
    assert seen_fit_sizes
    assert all(size == response.train_rows for size in seen_fit_sizes)


# --- Graceful partial failure ----------------------------------------------


class _AlwaysFailsEstimator(BaseEstimator, ClassifierMixin):
    def fit(self, X: object, y: object = None) -> "_AlwaysFailsEstimator":
        raise RuntimeError("synthetic training failure")

    def predict(self, X: object) -> object:
        raise RuntimeError("synthetic training failure")


def test_partial_model_failure_does_not_abort_the_others(monkeypatch: pytest.MonkeyPatch) -> None:
    rng = np.random.default_rng(1)
    n = 60
    labels = np.array([0] * (n // 2) + [1] * (n // 2))
    df = pd.DataFrame({"x1": rng.normal(size=n) + labels, "y": labels})

    broken_spec = ModelSpec(
        key="broken_model",
        display_name="Broken Model",
        estimator_factory=_AlwaysFailsEstimator,
        param_grid={},
        supports_feature_importance=False,
    )
    monkeypatch.setattr(
        classification_training_module,
        "CLASSIFICATION_MODELS",
        [CLASSIFICATION_MODELS[0], broken_spec, CLASSIFICATION_MODELS[2]],
    )

    active = ActiveDataset(dataset_id="t", filename="t.csv", csv_path=Path("t.csv"), dataframe=df)
    request = TrainingRequest(
        task=TaskType.classification,
        target="y",
        features=["x1"],
        drop_duplicates=False,
        scaler=ScalerType.none,
    )

    response = classification_training_module.run_classification_training(active, request).response

    assert len(response.results) == 3
    by_key = {r.key: r for r in response.results}
    assert by_key["broken_model"].status == "failed"
    assert by_key["broken_model"].warning
    assert by_key[CLASSIFICATION_MODELS[0].key].status == "success"
    assert by_key[CLASSIFICATION_MODELS[2].key].status == "success"
    assert response.winner_key in {CLASSIFICATION_MODELS[0].key, CLASSIFICATION_MODELS[2].key}


# --- Multiclass support -----------------------------------------------------


def test_classification_handles_a_programmatically_created_multiclass_target() -> None:
    rng = np.random.default_rng(2)
    per_class = 30
    labels = np.repeat([0, 1, 2], per_class)
    centers = {0: -3.0, 1: 0.0, 2: 3.0}
    x = np.array([centers[label] for label in labels]) + rng.normal(scale=0.4, size=len(labels))
    df = pd.DataFrame({"x": x, "y": labels})

    active = ActiveDataset(dataset_id="t", filename="t.csv", csv_path=Path("t.csv"), dataframe=df)
    request = TrainingRequest(
        task=TaskType.classification,
        target="y",
        features=["x"],
        drop_duplicates=False,
        scaler=ScalerType.standard,
    )

    response = run_classification_training(active, request).response

    assert len(response.results) == 3
    successful = [r for r in response.results if r.status == "success"]
    assert len(successful) == 3
    for result in successful:
        assert result.metrics is not None
        assert 0.0 <= result.metrics["f1"] <= 1.0
        confusion = result.charts.confusion_matrix  # type: ignore[union-attr]
        assert confusion.labels == ["0", "1", "2"]
        assert len(confusion.matrix) == 3
        assert all(len(row) == 3 for row in confusion.matrix)


# --- Real, bounded end-to-end training via the API -------------------------


def test_classification_training_real_bounded_integration(
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

    response = _train(
        client,
        dataset_id,
        {"task": "classification", "target": "churned", "features": features},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["train_rows"] + body["test_rows"] == 214
    assert body["primary_metric"] == "f1"
    assert len(body["results"]) == 3

    keys = {r["key"] for r in body["results"]}
    assert keys == {"logistic_regression", "random_forest_classifier", "xgboost_classifier"}

    successful = [r for r in body["results"] if r["status"] == "success"]
    assert len(successful) == 3
    for result in successful:
        assert result["best_params"]
        assert all(0.0 <= v <= 1.0 for v in result["metrics"].values())
        assert result["charts"]["confusion_matrix"]["labels"] == ["0", "1"]
        assert len(result["charts"]["confusion_matrix"]["matrix"]) == 2

    winner = body["winner_key"]
    assert winner is not None
    winner_f1 = next(r["metrics"]["f1"] for r in successful if r["key"] == winner)
    assert winner_f1 == max(r["metrics"]["f1"] for r in successful)

    tree_models = [r for r in successful if r["key"] != "logistic_regression"]
    assert all(r["feature_importances"] for r in tree_models)
    for result in tree_models:
        names = {fi["feature"] for fi in result["feature_importances"]}
        assert "age" in names
        assert any(name.startswith("membership_type_") for name in names)
        assert not any(name.startswith(("numeric__", "categorical__")) for name in names)
    logistic = next(r for r in successful if r["key"] == "logistic_regression")
    assert logistic["feature_importances"] is None


def test_one_class_target_is_rejected(client: TestClient) -> None:
    csv_content = b"a,y\n" + b"\n".join(f"{i},1".encode() for i in range(40)) + b"\n"
    upload = client.post(
        "/api/datasets/upload", files={"file": ("tiny.csv", csv_content, "text/csv")}
    )
    dataset_id = upload.json()["dataset_id"]

    response = _train(
        client, dataset_id, {"task": "classification", "target": "y", "features": ["a"]}
    )

    assert response.status_code == 422
    assert "at least two classes" in response.json()["detail"].lower()


def test_too_small_class_is_rejected(client: TestClient) -> None:
    rows = [f"{i},0" for i in range(35)] + [f"{i},1" for i in range(35, 38)]
    csv_content = ("a,y\n" + "\n".join(rows) + "\n").encode()
    upload = client.post(
        "/api/datasets/upload", files={"file": ("small_class.csv", csv_content, "text/csv")}
    )
    dataset_id = upload.json()["dataset_id"]

    response = _train(
        client, dataset_id, {"task": "classification", "target": "y", "features": ["a"]}
    )

    assert response.status_code == 422
    assert "too few" in response.json()["detail"].lower()


def test_continuous_looking_target_is_rejected_with_a_clean_bounded_message(
    client: TestClient,
) -> None:
    """Regression test for a real bug: picking a near-continuous numeric
    column (e.g. a distance/price measurement) as a classification target
    used to reach the per-class-size check, where almost every "class" is a
    single row - dumping every distinct value into one unreadable sentence.
    It must now be rejected earlier, with one clear, short message.
    """
    rows = [f"{i},{i * 1.37}" for i in range(60)]
    csv_content = ("a,y\n" + "\n".join(rows) + "\n").encode()
    upload = client.post(
        "/api/datasets/upload", files={"file": ("continuous.csv", csv_content, "text/csv")}
    )
    dataset_id = upload.json()["dataset_id"]

    response = _train(
        client, dataset_id, {"task": "classification", "target": "y", "features": ["a"]}
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "too many" in detail.lower()
    assert "continuous" in detail.lower()
    # The old bug produced a message hundreds of characters long, one raw
    # value at a time - this must stay a single short sentence regardless of
    # how many distinct values the bad target actually has.
    assert len(detail) < 400
