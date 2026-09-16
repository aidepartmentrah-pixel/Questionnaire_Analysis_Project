from pathlib import Path

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from sklearn.cluster import DBSCAN

from app.ml.registry import ClusteringModelSpec
from app.schemas.config import ScalerType
from app.schemas.training import ModelResult
from app.services.clustering_training import (
    _train_one_model,
    is_valid_clustering_solution,
    score_clustering_solution,
    select_winner,
)
from app.services.preprocessing_pipeline import build_preprocessing_pipeline


def _upload(client: TestClient, fixtures_dir: Path, filename: str) -> str:
    content = (fixtures_dir / filename).read_bytes()
    response = client.post("/api/datasets/upload", files={"file": (filename, content, "text/csv")})
    assert response.status_code == 200
    return str(response.json()["dataset_id"])


def _train(client: TestClient, dataset_id: str, payload: dict) -> object:
    return client.post(f"/api/datasets/{dataset_id}/train", json=payload)


# --- Unit tests: solution validity and metric calculations ------------------


def test_two_real_clusters_is_valid() -> None:
    labels = np.array([0, 0, 0, 1, 1, 1])
    assert is_valid_clustering_solution(labels) is True


def test_a_single_cluster_is_invalid() -> None:
    labels = np.array([0, 0, 0, 0, 0])
    assert is_valid_clustering_solution(labels) is False


def test_every_point_as_its_own_singleton_cluster_is_invalid() -> None:
    labels = np.array([0, 1, 2, 3, 4])
    assert is_valid_clustering_solution(labels) is False


def test_all_points_marked_as_dbscan_noise_is_invalid() -> None:
    labels = np.array([-1, -1, -1, -1, -1])
    assert is_valid_clustering_solution(labels) is False


def test_two_clusters_plus_some_noise_is_valid() -> None:
    labels = np.array([0, 0, 0, 1, 1, 1, -1, -1])
    assert is_valid_clustering_solution(labels) is True


def test_score_clustering_solution_returns_none_for_invalid_labels() -> None:
    rng = np.random.default_rng(0)
    X = rng.normal(size=(10, 2))
    labels = np.zeros(10, dtype=int)

    assert score_clustering_solution(X, labels) is None


def test_score_clustering_solution_returns_finite_scores_for_valid_labels() -> None:
    rng = np.random.default_rng(0)
    cluster_a = rng.normal(loc=-5, scale=0.3, size=(15, 2))
    cluster_b = rng.normal(loc=5, scale=0.3, size=(15, 2))
    X = np.vstack([cluster_a, cluster_b])
    labels = np.array([0] * 15 + [1] * 15)

    scores = score_clustering_solution(X, labels)

    assert scores is not None
    assert scores["silhouette"] > 0.5  # well-separated synthetic clusters
    assert scores["davies_bouldin"] >= 0.0


def test_noise_points_are_excluded_from_scoring_but_counted() -> None:
    rng = np.random.default_rng(1)
    cluster_a = rng.normal(loc=-5, scale=0.3, size=(15, 2))
    cluster_b = rng.normal(loc=5, scale=0.3, size=(15, 2))
    noise = rng.normal(loc=0, scale=0.3, size=(5, 2))
    X = np.vstack([cluster_a, cluster_b, noise])
    labels = np.array([0] * 15 + [1] * 15 + [-1] * 5)

    scores = score_clustering_solution(X, labels)

    assert scores is not None  # 2 real clusters remain once noise is excluded


# --- select_winner ------------------------------------------------------


def _result(key: str, status: str, silhouette: float | None = None) -> ModelResult:
    return ModelResult(
        key=key,
        display_name=key,
        status=status,
        duration_seconds=0.1,
        metrics={"silhouette": silhouette, "davies_bouldin": 1.0}
        if silhouette is not None
        else None,
    )


def test_select_winner_picks_highest_silhouette_among_successful() -> None:
    results = [
        _result("a", "success", silhouette=0.2),
        _result("b", "success", silhouette=0.8),
        _result("c", "failed"),
    ]

    assert select_winner(results) == "b"


def test_select_winner_returns_none_when_every_model_fails() -> None:
    assert select_winner([_result("a", "failed"), _result("b", "failed")]) is None


# --- A model with no valid parameter combination fails gracefully ----------


def test_model_with_no_valid_combination_is_reported_as_failed() -> None:
    rng = np.random.default_rng(2)
    X = rng.normal(size=(30, 2))
    pca_coords = X[:, :2]

    # A single-cluster-only DBSCAN configuration (eps far larger than the
    # data's spread) never produces >= 2 real clusters, so every combination
    # in this tiny grid is invalid.
    always_one_cluster_spec = ClusteringModelSpec(
        key="degenerate",
        display_name="Degenerate",
        estimator_factory=lambda **params: DBSCAN(**params),
        param_grid={"eps": [1000.0], "min_samples": [3]},
    )

    preprocessing = build_preprocessing_pipeline(["x1", "x2"], [], ScalerType.none)
    preprocessing.fit(pd.DataFrame(X, columns=["x1", "x2"]))

    result, pipeline = _train_one_model(always_one_cluster_spec, preprocessing, X, pca_coords)

    assert result.status == "failed"
    assert result.warning
    assert pipeline is None
    assert result.metrics is None


# --- Real, bounded end-to-end clustering via the API ------------------------


def test_clustering_training_real_bounded_integration(
    client: TestClient, fixtures_dir: Path
) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")
    features = ["age", "annual_income", "spending_score", "visits_per_month"]

    response = _train(
        client,
        dataset_id,
        {"task": "clustering", "target": None, "features": features},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["target"] is None
    assert body["test_rows"] == 0
    assert body["train_rows"] == 216
    assert body["primary_metric"] == "silhouette"
    assert len(body["results"]) == 3

    keys = {r["key"] for r in body["results"]}
    assert keys == {"kmeans", "agglomerative_clustering", "dbscan"}

    successful = [r for r in body["results"] if r["status"] == "success"]
    assert len(successful) >= 1
    for result in successful:
        assert result["best_params"]
        assert result["metrics"]["silhouette"] > 0
        assert result["metrics"]["n_clusters"] >= 2
        assert result["charts"]["pca_projection"]
        assert result["charts"]["cluster_sizes"]

    winner = body["winner_key"]
    assert winner is not None
    winner_silhouette = next(r["metrics"]["silhouette"] for r in successful if r["key"] == winner)
    assert winner_silhouette == max(r["metrics"]["silhouette"] for r in successful)


def test_clustering_dbscan_reports_noise_point_count(
    client: TestClient, fixtures_dir: Path
) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")
    features = ["age", "annual_income", "spending_score", "visits_per_month"]

    response = _train(
        client, dataset_id, {"task": "clustering", "target": None, "features": features}
    )

    assert response.status_code == 200
    body = response.json()
    dbscan = next(r for r in body["results"] if r["key"] == "dbscan")

    if dbscan["status"] == "success":
        assert dbscan["metrics"]["noise_points"] >= 0
        labels_in_pca = {p["cluster"] for p in dbscan["charts"]["pca_projection"]}
        if dbscan["metrics"]["noise_points"] > 0:
            assert "-1" in labels_in_pca


def test_clustering_with_categorical_feature_is_rejected(
    client: TestClient, fixtures_dir: Path
) -> None:
    dataset_id = _upload(client, fixtures_dir, "customer_segments.csv")

    response = _train(
        client,
        dataset_id,
        {"task": "clustering", "target": None, "features": ["age", "membership_type"]},
    )

    assert response.status_code == 422
    assert "only supports numeric features" in response.json()["detail"].lower()
