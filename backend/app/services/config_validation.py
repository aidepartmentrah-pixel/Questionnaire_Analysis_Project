"""Validate a proposed (task, target, features, preprocessing) configuration
against the active dataset, and the shared row-cleaning step (drop missing,
optionally drop duplicates) used both by the preview (this module) and by
every task's real training service, so what the user previews and what
training actually sees can never silently drift apart.
"""

from __future__ import annotations

import pandas as pd

from app.schemas.config import PreprocessingPreview, PreprocessingRequest, TaskType
from app.services.dataset_store import ActiveDataset
from app.services.preprocessing_pipeline import (
    build_preprocessing_pipeline,
    readable_feature_names,
    split_numeric_categorical,
)

# Below this many rows, 3-fold cross-validation (used from Slice 4 onward)
# is not reliably stable, so the configuration is marked "not ready" rather
# than allowed to proceed to training.
MIN_ROWS_FOR_TRAINING = 30

# Above this fraction of rows removed, the user is warned even though the
# configuration may still be technically trainable.
HIGH_ROW_LOSS_WARNING_RATIO = 0.3

# A classification target should represent a small number of categories, not
# a near-continuous measurement (e.g. a raw distance or price column). Above
# this many distinct values, the column is almost certainly the wrong choice
# regardless of how many rows each value has - checked before the (much
# noisier) per-class row-count check below, so picking a continuous column
# produces one clear reason instead of a wall of tiny "classes".
MAX_CLASSES_FOR_CLASSIFICATION = 20

# Keeps at least 3 members of every class in the training fold after an
# 80/20 stratified split, so stratified 3-fold cross-validation is possible.
MIN_ROWS_PER_CLASS = 6

# How many class labels to name in a "too small" message before summarizing
# the rest, so a legitimate multi-class target with several rare classes
# still produces a readable message rather than a second wall of text.
MAX_CLASS_LABELS_IN_MESSAGE = 10


class ConfigValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _validate_columns_exist(
    df: pd.DataFrame, task: TaskType, target: str | None, features: list[str]
) -> None:
    unknown = sorted({c for c in [*features, target] if c is not None and c not in df.columns})
    if unknown:
        raise ConfigValidationError(f"Unknown column(s): {', '.join(unknown)}.")

    if not features:
        raise ConfigValidationError("Select at least one feature.")

    if task in (TaskType.regression, TaskType.classification) and target is None:
        raise ConfigValidationError(f"{task.value.capitalize()} requires a target column.")

    if task == TaskType.clustering and target is not None:
        raise ConfigValidationError("Clustering does not use a target column.")

    if target is not None and target in features:
        raise ConfigValidationError("The target column cannot also be selected as a feature.")


def validate_task_config(
    df: pd.DataFrame, task: TaskType, target: str | None, features: list[str]
) -> tuple[list[str], list[str]]:
    """Run every structural check and return (numeric_features, categorical_features)."""
    _validate_columns_exist(df, task, target, features)

    numeric_features, categorical_features = split_numeric_categorical(df, features)

    if task == TaskType.clustering and categorical_features:
        raise ConfigValidationError(
            "Clustering only supports numeric features in this version. Remove: "
            f"{', '.join(categorical_features)}."
        )

    return numeric_features, categorical_features


def classification_target_issues(y: pd.Series) -> list[str]:
    """Structural problems with a classification target, independent of how
    many rows are available overall. Shared by the live preview (surfaced as
    non-blocking warnings) and real training (raised as a hard error) so what
    the user is warned about and what training actually rejects can never
    drift apart - see MAX_CLASSES_FOR_CLASSIFICATION above for why this is
    checked as its own step rather than folded into the per-class-size check.
    """
    class_counts = y.value_counts()

    if len(class_counts) < 2:
        return ["The target column must contain at least two classes to train a classifier."]

    if len(class_counts) > MAX_CLASSES_FOR_CLASSIFICATION:
        return [
            f"The target column has {len(class_counts)} distinct values, which is too many for a "
            "classification target. Classification targets should represent a small number of "
            "categories (e.g. a label or class) - this looks like a continuous measurement "
            "instead. Consider Regression, or choose a different target column."
        ]

    too_small = class_counts[class_counts < MIN_ROWS_PER_CLASS]
    if not too_small.empty:
        shown = [str(c) for c in too_small.index[:MAX_CLASS_LABELS_IN_MESSAGE]]
        remaining = len(too_small) - len(shown)
        labels = ", ".join(shown) + (f", and {remaining} more" if remaining > 0 else "")
        return [
            f"Class(es) {labels} have fewer than {MIN_ROWS_PER_CLASS} rows after preprocessing, "
            "which is too few for reliable stratified cross-validation."
        ]

    return []


def clean_training_subset(
    df: pd.DataFrame, target: str | None, features: list[str], drop_duplicates: bool
) -> pd.DataFrame:
    """Rows with a missing value in any selected column are always dropped
    (Software Requirement.md 8.1: "shall be removed"); duplicate rows are
    dropped only if the caller asked for it.
    """
    subset_columns = [*features, target] if target else list(features)
    subset = df[subset_columns]
    non_missing = subset.dropna()
    return non_missing.drop_duplicates() if drop_duplicates else non_missing


def build_preprocessing_preview(
    active: ActiveDataset, request: PreprocessingRequest
) -> PreprocessingPreview:
    df = active.dataframe
    task, target, features = request.task, request.target, request.features

    numeric_features, categorical_features = validate_task_config(df, task, target, features)

    original_rows = len(df)
    subset_row_count = len(df[[*features, target] if target else features])
    non_missing_count = len(clean_training_subset(df, target, features, drop_duplicates=False))
    removed_missing_rows = subset_row_count - non_missing_count

    deduped = clean_training_subset(df, target, features, request.drop_duplicates)
    removed_duplicate_rows = non_missing_count - len(deduped)

    final_rows = len(deduped)

    warnings: list[str] = []
    removed_total = original_rows - final_rows
    if original_rows and removed_total / original_rows > HIGH_ROW_LOSS_WARNING_RATIO:
        pct = removed_total / original_rows
        warnings.append(
            f"{removed_total} of {original_rows} rows ({pct:.0%}) will be removed by preprocessing."
        )

    ready_to_train = final_rows >= MIN_ROWS_FOR_TRAINING
    if not ready_to_train:
        warnings.append(
            f"Only {final_rows} usable rows remain after preprocessing; at least "
            f"{MIN_ROWS_FOR_TRAINING} are required to train."
        )

    if task == TaskType.classification and target is not None and final_rows > 0:
        class_issues = classification_target_issues(deduped[target])
        if class_issues:
            warnings.extend(class_issues)
            ready_to_train = False

    final_feature_columns: list[str] = []
    if final_rows > 0:
        pipeline = build_preprocessing_pipeline(
            numeric_features, categorical_features, request.scaler
        )
        pipeline.fit(deduped[features])
        final_feature_columns = readable_feature_names(pipeline)

    return PreprocessingPreview(
        dataset_id=active.dataset_id,
        task=task,
        target=target,
        features=features,
        original_rows=original_rows,
        removed_missing_rows=removed_missing_rows,
        removed_duplicate_rows=removed_duplicate_rows,
        final_rows=final_rows,
        final_feature_columns=final_feature_columns,
        ready_to_train=ready_to_train,
        warnings=warnings,
    )
