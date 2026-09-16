"""Clustering training: unsupervised, so there is no train/test split and no
target - the complete preprocessed feature set is used directly (Software
Requirement.md 8.5).

There's also no GridSearchCV: without labels there's no scoring callable to
hand it, so each registered algorithm's small bounded grid is searched
manually. Every combination is fit on the same scaled numeric features and
scored with the silhouette score (higher is better) when the resulting
solution is valid - at least 2 and fewer than n_samples effective clusters,
and, for DBSCAN, not every point marked as noise. A combination that
produces an invalid solution is skipped when picking the best one; an
algorithm with no valid combination at all is reported as "failed" rather
than crashing. See app/ml/registry.py for the three registered algorithms
and their search spaces.
"""

from __future__ import annotations

import itertools
import time
from typing import Any

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.pipeline import Pipeline

from app.ml.registry import CLUSTERING_MODELS, RANDOM_SEED, ClusteringModelSpec
from app.schemas.training import (
    ClusteringCharts,
    ClusterSizePoint,
    ModelResult,
    PcaPoint,
    TrainingRequest,
    TrainingResponse,
)
from app.services.config_validation import (
    ConfigValidationError,
    clean_training_subset,
    validate_task_config,
)
from app.services.dataset_store import ActiveDataset
from app.services.preprocessing_pipeline import build_preprocessing_pipeline
from app.services.training_run import TrainingRun

PRIMARY_METRIC = "silhouette"
MIN_ROWS_FOR_TRAINING = 30
MAX_CHART_POINTS = 500


def _param_combinations(param_grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not param_grid:
        return [{}]
    keys = list(param_grid.keys())
    return [
        dict(zip(keys, values, strict=True)) for values in itertools.product(*param_grid.values())
    ]


def is_valid_clustering_solution(labels: np.ndarray) -> bool:
    """At least 2 real clusters (excluding DBSCAN's -1 noise marker), and
    not every point in its own singleton cluster.
    """
    unique_labels = set(labels.tolist())
    unique_labels.discard(-1)
    return len(unique_labels) >= 2 and len(unique_labels) < len(labels)


def score_clustering_solution(X: np.ndarray, labels: np.ndarray) -> dict[str, float] | None:
    """Silhouette/Davies-Bouldin scores, or None if the solution is invalid.
    Noise points (-1) are excluded from scoring since they belong to no
    cluster by definition.
    """
    if not is_valid_clustering_solution(labels):
        return None

    mask = labels != -1
    if mask.sum() < 2:
        return None

    return {
        "silhouette": float(silhouette_score(X[mask], labels[mask])),
        "davies_bouldin": float(davies_bouldin_score(X[mask], labels[mask])),
    }


def _train_one_model(
    spec: ClusteringModelSpec,
    preprocessing: ColumnTransformer,
    X_transformed: np.ndarray,
    pca_coords: np.ndarray,
) -> tuple[ModelResult, Pipeline | None]:
    started = time.perf_counter()
    try:
        best: dict[str, Any] | None = None
        for params in _param_combinations(spec.param_grid):
            estimator = spec.estimator_factory(**params)
            labels = estimator.fit_predict(X_transformed)
            scores = score_clustering_solution(X_transformed, labels)
            if scores is None:
                continue
            if best is None or scores["silhouette"] > best["silhouette"]:
                best = {"params": params, "labels": labels, "estimator": estimator, **scores}

        if best is None:
            result = ModelResult(
                key=spec.key,
                display_name=spec.display_name,
                status="failed",
                duration_seconds=time.perf_counter() - started,
                warning=(
                    "No parameter combination produced a valid clustering solution "
                    "(at least 2 real clusters are required, and not every point can "
                    "be marked as noise)."
                ),
            )
            return result, None

        labels = best["labels"]
        unique_labels = sorted(set(labels.tolist()) - {-1})
        cluster_sizes = [
            ClusterSizePoint(cluster=str(label), size=int((labels == label).sum()))
            for label in unique_labels
        ]
        noise_count = int((labels == -1).sum())

        pca_points = [
            PcaPoint(x=float(pca_coords[i, 0]), y=float(pca_coords[i, 1]), cluster=str(labels[i]))
            for i in range(min(len(labels), MAX_CHART_POINTS))
        ]

        result = ModelResult(
            key=spec.key,
            display_name=spec.display_name,
            status="success",
            duration_seconds=time.perf_counter() - started,
            best_params=best["params"],
            metrics={
                "silhouette": best["silhouette"],
                "davies_bouldin": best["davies_bouldin"],
                "n_clusters": float(len(unique_labels)),
                "noise_points": float(noise_count),
            },
            charts=ClusteringCharts(pca_projection=pca_points, cluster_sizes=cluster_sizes),
        )
        # Combines the shared, already-fitted preprocessing with this
        # algorithm's winning already-fitted estimator into one exportable
        # Pipeline; sklearn doesn't require re-fitting a Pipeline whose
        # individual steps are already fitted.
        exportable_pipeline = Pipeline(
            [("preprocessing", preprocessing), ("model", best["estimator"])]
        )
        return result, exportable_pipeline
    except Exception as exc:  # noqa: BLE001 - one model's failure must not abort the others
        result = ModelResult(
            key=spec.key,
            display_name=spec.display_name,
            status="failed",
            duration_seconds=time.perf_counter() - started,
            warning=str(exc),
        )
        return result, None


def select_winner(results: list[ModelResult]) -> str | None:
    """The highest valid Silhouette score among the successful models, or
    None if every model failed to produce a valid solution.
    """
    successful = [r for r in results if r.status == "success" and r.metrics is not None]
    if not successful:
        return None
    return max(successful, key=lambda r: r.metrics["silhouette"]).key  # type: ignore[index]


def _build_pca_projection(X_transformed: np.ndarray) -> np.ndarray:
    n_components = min(2, X_transformed.shape[1])
    coords = PCA(n_components=n_components, random_state=RANDOM_SEED).fit_transform(X_transformed)
    if n_components == 1:
        coords = np.column_stack([coords, np.zeros(len(coords))])
    return coords


def run_clustering_training(active: ActiveDataset, request: TrainingRequest) -> TrainingRun:
    df = active.dataframe
    numeric_features, _categorical_features = validate_task_config(
        df, request.task, request.target, request.features
    )
    # validate_task_config already rejects any categorical feature for
    # clustering, so numeric_features == request.features here.

    clean = clean_training_subset(df, None, request.features, request.drop_duplicates)
    if len(clean) < MIN_ROWS_FOR_TRAINING:
        raise ConfigValidationError(
            f"Only {len(clean)} usable rows remain after preprocessing; at least "
            f"{MIN_ROWS_FOR_TRAINING} are required to train."
        )

    X = clean[request.features]

    # Shared across every model so their PCA projections are directly
    # comparable, and fit once rather than once per algorithm.
    preprocessing = build_preprocessing_pipeline(numeric_features, [], request.scaler)
    X_transformed = preprocessing.fit_transform(X)
    pca_coords = _build_pca_projection(X_transformed)

    pairs = [
        _train_one_model(spec, preprocessing, X_transformed, pca_coords)
        for spec in CLUSTERING_MODELS
    ]
    results = [result for result, _ in pairs]
    fitted_pipelines = {result.key: p for result, p in pairs if p is not None}

    winner_key = select_winner(results)

    response = TrainingResponse(
        dataset_id=active.dataset_id,
        task=request.task,
        target=None,
        train_rows=len(X),
        test_rows=0,
        primary_metric=PRIMARY_METRIC,
        results=results,
        winner_key=winner_key,
    )
    return TrainingRun(response=response, fitted_pipelines=fitted_pipelines)
