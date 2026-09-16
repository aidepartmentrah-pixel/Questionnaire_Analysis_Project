"""Central model registry.

Every supported estimator is registered here, alongside its bounded
hyperparameter search space, so training services look models up through
this module instead of constructing estimators ad hoc. There is exactly one
place that defines "the three models for task X" and their tuning grids.

Populated for regression in Slice 4, classification in Slice 5, clustering
in Slice 6.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sklearn.base import BaseEstimator
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from xgboost import XGBClassifier, XGBRegressor

# Used everywhere a model, split or cross-validation fold needs a fixed seed,
# so a given dataset + configuration always trains and compares identically.
RANDOM_SEED = 42

# XGBoost's default n_jobs auto-detects the reported CPU count and spawns
# that many OpenMP threads per fit. On a high-core-count host running under
# Docker Desktop's WSL2 backend, that thread count can be wildly mismatched
# to what's actually available, and fitting on these small fixture-sized
# datasets was observed to go from ~0.1s to never completing (a real hang,
# not just "slower") purely from thread-pool contention - reproduced
# directly (bypassing this project's own code) with a bare
# XGBRegressor().fit() on a 200x10 array. A small fixed thread count avoids
# the pathological case entirely while still being fast both natively and
# in Docker.
XGBOOST_N_JOBS = 4


@dataclass(frozen=True)
class ModelSpec:
    key: str
    display_name: str
    estimator_factory: Callable[[], BaseEstimator]
    # Keys are already pipeline-step-prefixed (e.g. "model__n_estimators")
    # so they can be passed straight to GridSearchCV on a Pipeline.
    param_grid: dict[str, list[Any]]
    supports_feature_importance: bool


REGRESSION_MODELS: list[ModelSpec] = [
    ModelSpec(
        key="linear_regression",
        display_name="Linear Regression",
        estimator_factory=LinearRegression,
        param_grid={"model__fit_intercept": [True, False]},
        supports_feature_importance=False,
    ),
    ModelSpec(
        key="random_forest_regressor",
        display_name="Random Forest Regressor",
        estimator_factory=lambda: RandomForestRegressor(random_state=RANDOM_SEED),
        param_grid={
            "model__n_estimators": [50, 100],
            "model__max_depth": [None, 5],
        },
        supports_feature_importance=True,
    ),
    ModelSpec(
        key="xgboost_regressor",
        display_name="XGBoost Regressor",
        estimator_factory=lambda: XGBRegressor(
            random_state=RANDOM_SEED, verbosity=0, n_jobs=XGBOOST_N_JOBS
        ),
        param_grid={
            "model__n_estimators": [50, 100],
            "model__max_depth": [3, 5],
        },
        supports_feature_importance=True,
    ),
]

CLASSIFICATION_MODELS: list[ModelSpec] = [
    ModelSpec(
        key="logistic_regression",
        display_name="Logistic Regression",
        estimator_factory=lambda: LogisticRegression(max_iter=1000, random_state=RANDOM_SEED),
        param_grid={"model__C": [0.1, 1.0, 10.0]},
        supports_feature_importance=False,
    ),
    ModelSpec(
        key="random_forest_classifier",
        display_name="Random Forest Classifier",
        estimator_factory=lambda: RandomForestClassifier(random_state=RANDOM_SEED),
        param_grid={
            "model__n_estimators": [50, 100],
            "model__max_depth": [None, 5],
        },
        supports_feature_importance=True,
    ),
    ModelSpec(
        key="xgboost_classifier",
        display_name="XGBoost Classifier",
        estimator_factory=lambda: XGBClassifier(
            random_state=RANDOM_SEED, verbosity=0, n_jobs=XGBOOST_N_JOBS
        ),
        param_grid={
            "model__n_estimators": [50, 100],
            "model__max_depth": [3, 5],
        },
        supports_feature_importance=True,
    ),
]


@dataclass(frozen=True)
class ClusteringModelSpec:
    """Clustering has no labels, so there's no GridSearchCV scoring callable
    to reuse - the param grid is a plain (unprefixed) constructor kwarg grid,
    manually searched by the clustering training service instead.
    """

    key: str
    display_name: str
    estimator_factory: Callable[..., BaseEstimator]
    param_grid: dict[str, list[Any]]


CLUSTERING_MODELS: list[ClusteringModelSpec] = [
    ClusteringModelSpec(
        key="kmeans",
        display_name="K-Means",
        estimator_factory=lambda **params: KMeans(random_state=RANDOM_SEED, n_init=10, **params),
        param_grid={"n_clusters": [2, 3, 4, 5]},
    ),
    ClusteringModelSpec(
        key="agglomerative_clustering",
        display_name="Agglomerative Clustering",
        estimator_factory=lambda **params: AgglomerativeClustering(**params),
        param_grid={"n_clusters": [2, 3, 4, 5], "linkage": ["ward", "average"]},
    ),
    ClusteringModelSpec(
        key="dbscan",
        display_name="DBSCAN",
        estimator_factory=lambda **params: DBSCAN(**params),
        param_grid={"eps": [0.5, 0.75, 1.0, 1.5, 2.0], "min_samples": [3, 5, 10]},
    ),
]
