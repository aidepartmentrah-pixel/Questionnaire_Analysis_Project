import numpy as np
import pandas as pd
import pytest

from app.schemas.config import ScalerType
from app.services.preprocessing_pipeline import (
    build_preprocessing_pipeline,
    readable_feature_names,
    split_numeric_categorical,
)


@pytest.fixture()
def numeric_categorical_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "age": [20.0, 30.0, 40.0, 50.0, 60.0],
            "income": [10_000.0, 20_000.0, 30_000.0, 40_000.0, 50_000.0],
            "region": ["North", "South", "North", "East", "South"],
        }
    )


def test_split_numeric_categorical(numeric_categorical_df: pd.DataFrame) -> None:
    numeric, categorical = split_numeric_categorical(
        numeric_categorical_df, ["age", "income", "region"]
    )
    assert numeric == ["age", "income"]
    assert categorical == ["region"]


def test_standard_scaling_normalizes_mean_and_std(numeric_categorical_df: pd.DataFrame) -> None:
    pipeline = build_preprocessing_pipeline(["age", "income"], [], ScalerType.standard)
    transformed = pipeline.fit_transform(numeric_categorical_df[["age", "income"]])

    assert transformed.shape == (5, 2)
    np.testing.assert_allclose(transformed.mean(axis=0), [0.0, 0.0], atol=1e-8)
    np.testing.assert_allclose(transformed.std(axis=0), [1.0, 1.0], atol=1e-8)


def test_minmax_scaling_bounds_values_between_zero_and_one(
    numeric_categorical_df: pd.DataFrame,
) -> None:
    pipeline = build_preprocessing_pipeline(["age", "income"], [], ScalerType.minmax)
    transformed = pipeline.fit_transform(numeric_categorical_df[["age", "income"]])

    assert transformed.min() == pytest.approx(0.0)
    assert transformed.max() == pytest.approx(1.0)


def test_no_scaling_passes_values_through_unchanged(numeric_categorical_df: pd.DataFrame) -> None:
    pipeline = build_preprocessing_pipeline(["age", "income"], [], ScalerType.none)
    transformed = pipeline.fit_transform(numeric_categorical_df[["age", "income"]])

    np.testing.assert_allclose(transformed, numeric_categorical_df[["age", "income"]].to_numpy())


def test_one_hot_encoding_expands_categorical_column(numeric_categorical_df: pd.DataFrame) -> None:
    pipeline = build_preprocessing_pipeline([], ["region"], ScalerType.none)
    transformed = pipeline.fit_transform(numeric_categorical_df[["region"]])
    names = readable_feature_names(pipeline)

    assert sorted(names) == ["region_East", "region_North", "region_South"]
    assert transformed.shape == (5, 3)
    # Every row is a one-hot vector: exactly one column set to 1.
    assert (transformed.sum(axis=1) == 1).all()


def test_combined_numeric_and_categorical_feature_names(
    numeric_categorical_df: pd.DataFrame,
) -> None:
    pipeline = build_preprocessing_pipeline(["age", "income"], ["region"], ScalerType.standard)
    pipeline.fit(numeric_categorical_df[["age", "income", "region"]])
    names = readable_feature_names(pipeline)

    assert names[:2] == ["age", "income"]
    assert set(names[2:]) == {"region_East", "region_North", "region_South"}


def test_unknown_category_at_transform_time_does_not_raise(
    numeric_categorical_df: pd.DataFrame,
) -> None:
    pipeline = build_preprocessing_pipeline([], ["region"], ScalerType.none)
    pipeline.fit(numeric_categorical_df[["region"]])

    unseen = pd.DataFrame({"region": ["West"]})
    transformed = pipeline.transform(unseen)

    # handle_unknown="ignore": an unseen category becomes an all-zero row
    # instead of raising, so a later prediction request can't crash on it.
    assert transformed.shape == (1, 3)
    assert transformed.sum() == 0
