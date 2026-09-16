"""Classification training: stratified 80/20 split with a fixed seed, tune
each registered model with a small bounded grid over stratified 3-fold
cross-validation on the training split only, evaluate once on the untouched
test split, and pick the highest-F1 successful model. See
app/ml/registry.py for the three registered models and their search spaces.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.metrics import confusion_matrix as sk_confusion_matrix
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline

from app.ml.registry import CLASSIFICATION_MODELS, RANDOM_SEED, ModelSpec
from app.schemas.config import ScalerType
from app.schemas.training import (
    ClassificationCharts,
    ConfusionMatrix,
    FeatureImportance,
    ModelResult,
    TrainingRequest,
    TrainingResponse,
)
from app.services.config_validation import (
    ConfigValidationError,
    classification_target_issues,
    clean_training_subset,
    validate_task_config,
)
from app.services.dataset_store import ActiveDataset
from app.services.preprocessing_pipeline import build_preprocessing_pipeline, readable_feature_names
from app.services.training_run import TrainingRun

TEST_SIZE = 0.2
CV_FOLDS = 3
PRIMARY_METRIC = "f1"
MIN_ROWS_FOR_TRAINING = 30

# "weighted" averaging works for both binary and multiclass targets without
# extra branching, and accounts for class imbalance (unlike "macro").
METRIC_AVERAGING = "weighted"


def compute_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(
            precision_score(y_true, y_pred, average=METRIC_AVERAGING, zero_division=0)
        ),
        "recall": float(recall_score(y_true, y_pred, average=METRIC_AVERAGING, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average=METRIC_AVERAGING, zero_division=0)),
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
    class_labels: list[Any],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[ModelResult, Pipeline | None]:
    started = time.perf_counter()
    try:
        preprocessing = build_preprocessing_pipeline(numeric_features, categorical_features, scaler)
        pipeline = Pipeline([("preprocessing", preprocessing), ("model", spec.estimator_factory())])

        cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)
        search = GridSearchCV(
            pipeline,
            param_grid=spec.param_grid,
            cv=cv,
            scoring=f"f1_{METRIC_AVERAGING}",
        )
        # Tuning only ever sees X_train/y_train; X_test/y_test are first used
        # below, strictly after the best configuration has already been chosen.
        search.fit(X_train, y_train)

        best_pipeline = search.best_estimator_
        predictions = best_pipeline.predict(X_test)
        metrics = compute_classification_metrics(y_test.to_numpy(), predictions)

        feature_importances = None
        if spec.supports_feature_importance:
            feature_names = readable_feature_names(best_pipeline.named_steps["preprocessing"])
            feature_importances = _extract_feature_importances(
                best_pipeline.named_steps["model"], feature_names
            )

        matrix = sk_confusion_matrix(y_test, predictions, labels=class_labels)

        result = ModelResult(
            key=spec.key,
            display_name=spec.display_name,
            status="success",
            duration_seconds=time.perf_counter() - started,
            best_params={k.replace("model__", ""): v for k, v in search.best_params_.items()},
            metrics=metrics,
            feature_importances=feature_importances,
            charts=ClassificationCharts(
                confusion_matrix=ConfusionMatrix(
                    labels=[str(c) for c in class_labels],
                    matrix=[[int(v) for v in row] for row in matrix],
                )
            ),
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
    """The highest-F1 model among the successful ones, or None if every
    model failed.
    """
    successful = [r for r in results if r.status == "success" and r.metrics is not None]
    if not successful:
        return None
    return max(successful, key=lambda r: r.metrics["f1"]).key  # type: ignore[index]


def run_classification_training(active: ActiveDataset, request: TrainingRequest) -> TrainingRun:
    df = active.dataframe
    numeric_features, categorical_features = validate_task_config(
        df, request.task, request.target, request.features
    )

    target = request.target
    assert target is not None  # guaranteed for classification by validate_task_config above

    clean = clean_training_subset(df, target, request.features, request.drop_duplicates)
    if len(clean) < MIN_ROWS_FOR_TRAINING:
        raise ConfigValidationError(
            f"Only {len(clean)} usable rows remain after preprocessing; at least "
            f"{MIN_ROWS_FOR_TRAINING} are required to train."
        )

    class_issues = classification_target_issues(clean[target])
    if class_issues:
        raise ConfigValidationError(" ".join(class_issues))

    X = clean[request.features]
    y = clean[target]
    class_labels = sorted(y.unique().tolist())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_SEED, stratify=y
    )

    pairs = [
        _train_one_model(
            spec,
            numeric_features,
            categorical_features,
            request.scaler,
            class_labels,
            X_train,
            y_train,
            X_test,
            y_test,
        )
        for spec in CLASSIFICATION_MODELS
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
