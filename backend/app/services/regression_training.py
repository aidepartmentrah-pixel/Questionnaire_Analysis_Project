"""Regression training: split 80/20 with a fixed seed, tune each registered
model with a small bounded grid over 3-fold cross-validation on the training
split only, evaluate once on the untouched test split, and pick the
lowest-RMSE successful model. See app/ml/registry.py for the three
registered models and their search spaces.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import GridSearchCV, KFold, train_test_split
from sklearn.pipeline import Pipeline

from app.ml.registry import RANDOM_SEED, REGRESSION_MODELS, ModelSpec
from app.schemas.config import ScalerType
from app.schemas.training import (
    ActualVsPredictedPoint,
    FeatureImportance,
    ModelResult,
    RegressionCharts,
    ResidualPoint,
    TrainingRequest,
    TrainingResponse,
)
from app.services.config_validation import (
    ConfigValidationError,
    clean_training_subset,
    regression_target_issues,
    validate_task_config,
)
from app.services.dataset_store import ActiveDataset
from app.services.preprocessing_pipeline import build_preprocessing_pipeline, readable_feature_names
from app.services.training_run import TrainingRun

TEST_SIZE = 0.2
CV_FOLDS = 3
PRIMARY_METRIC = "rmse"
MAX_CHART_POINTS = 500
MIN_ROWS_FOR_TRAINING = 30


def _build_charts(y_test: np.ndarray, predictions: np.ndarray) -> RegressionCharts:
    actual = y_test[:MAX_CHART_POINTS]
    predicted = predictions[:MAX_CHART_POINTS]
    return RegressionCharts(
        actual_vs_predicted=[
            ActualVsPredictedPoint(actual=float(a), predicted=float(p))
            for a, p in zip(actual, predicted, strict=True)
        ],
        residuals=[
            ResidualPoint(predicted=float(p), residual=float(a - p))
            for a, p in zip(actual, predicted, strict=True)
        ],
    )


def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def _extract_feature_importances(model: Any, feature_names: list[str]) -> list[FeatureImportance]:
    return [
        FeatureImportance(feature=name, importance=float(value))
        for name, value in zip(feature_names, model.feature_importances_, strict=True)
    ]


def _train_one_model(
    spec: ModelSpec,
    numeric_features: list[str],
    categorical_features: list[str],
    scaler: ScalerType,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[ModelResult, Pipeline | None]:
    started = time.perf_counter()
    try:
        preprocessing = build_preprocessing_pipeline(numeric_features, categorical_features, scaler)
        pipeline = Pipeline([("preprocessing", preprocessing), ("model", spec.estimator_factory())])

        cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)
        search = GridSearchCV(
            pipeline,
            param_grid=spec.param_grid,
            cv=cv,
            scoring="neg_root_mean_squared_error",
        )
        # Tuning only ever sees X_train/y_train; X_test/y_test are first used
        # below, strictly after the best configuration has already been chosen.
        search.fit(X_train, y_train)

        best_pipeline = search.best_estimator_
        predictions = best_pipeline.predict(X_test)
        metrics = compute_regression_metrics(y_test.to_numpy(), predictions)

        feature_importances = None
        if spec.supports_feature_importance:
            feature_names = readable_feature_names(best_pipeline.named_steps["preprocessing"])
            feature_importances = _extract_feature_importances(
                best_pipeline.named_steps["model"], feature_names
            )

        result = ModelResult(
            key=spec.key,
            display_name=spec.display_name,
            status="success",
            duration_seconds=time.perf_counter() - started,
            best_params={k.replace("model__", ""): v for k, v in search.best_params_.items()},
            metrics=metrics,
            feature_importances=feature_importances,
            charts=_build_charts(y_test.to_numpy(), predictions),
        )
        return result, best_pipeline
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
    """The lowest-RMSE model among the successful ones, or None if every
    model failed. Kept separate from the training loop so selection logic
    can be unit-tested against controlled, synthetic results.
    """
    successful = [r for r in results if r.status == "success" and r.metrics is not None]
    if not successful:
        return None
    return min(successful, key=lambda r: r.metrics["rmse"]).key  # type: ignore[index]


def run_regression_training(active: ActiveDataset, request: TrainingRequest) -> TrainingRun:
    df = active.dataframe
    numeric_features, categorical_features = validate_task_config(
        df, request.task, request.target, request.features
    )

    target = request.target
    assert target is not None  # guaranteed for regression by validate_task_config above

    target_issues = regression_target_issues(df, target)
    if target_issues:
        raise ConfigValidationError(" ".join(target_issues))

    clean = clean_training_subset(df, target, request.features, request.drop_duplicates)
    if len(clean) < MIN_ROWS_FOR_TRAINING:
        raise ConfigValidationError(
            f"Only {len(clean)} usable rows remain after preprocessing; at least "
            f"{MIN_ROWS_FOR_TRAINING} are required to train."
        )

    X = clean[request.features]
    y = clean[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_SEED
    )

    pairs = [
        _train_one_model(
            spec,
            numeric_features,
            categorical_features,
            request.scaler,
            X_train,
            y_train,
            X_test,
            y_test,
        )
        for spec in REGRESSION_MODELS
    ]
    results = [result for result, _ in pairs]
    fitted_pipelines = {result.key: p for result, p in pairs if p is not None}

    winner_key = select_winner(results)

    response = TrainingResponse(
        dataset_id=active.dataset_id,
        task=request.task,
        target=target,
        train_rows=len(X_train),
        test_rows=len(X_test),
        primary_metric=PRIMARY_METRIC,
        results=results,
        winner_key=winner_key,
    )
    return TrainingRun(response=response, fitted_pipelines=fitted_pipelines)
