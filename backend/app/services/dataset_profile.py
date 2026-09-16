"""Dataset profiling (EDA): dimensions, types, descriptive statistics,
missing/duplicate counts, numeric histograms, categorical frequencies and a
numeric correlation matrix for the active dataset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.schemas.profile import (
    CategoricalFrequency,
    CategoryCount,
    ColumnProfile,
    CorrelationMatrix,
    DatasetProfileResponse,
    HistogramBin,
    NumericDistribution,
    NumericSummary,
)
from app.services.dataset_store import ActiveDataset
from app.services.dataset_summary import detect_column_type

NUMERIC_HISTOGRAM_BINS = 10

# Numeric columns with only a handful of distinct values (e.g. a 0/1 flag or
# a bedroom count) get one bar per exact value instead of being forced into
# NUMERIC_HISTOGRAM_BINS equal-width buckets, which would otherwise produce a
# mostly-empty, misleading chart.
DISCRETE_NUMERIC_MAX_UNIQUE = 12

# Categorical columns are only charted up to this many distinct categories
# (the rest are folded into an "Other" bucket) ...
CATEGORICAL_TOP_N = 20

# ... and are skipped entirely once more than half their values are unique,
# since that signals an identifier/free-text column rather than a genuine
# category (e.g. customer_id), where a frequency chart wouldn't be meaningful
# and would balloon the response for no benefit.
CATEGORICAL_SKIP_UNIQUE_RATIO = 0.5


def _safe_float(value: object) -> float | None:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.columns if detect_column_type(df[c]) == "numeric"]


def _categorical_columns(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.columns if detect_column_type(df[c]) == "categorical"]


def build_column_profiles(df: pd.DataFrame) -> list[ColumnProfile]:
    row_count = len(df)
    profiles = []
    for column in df.columns:
        series = df[column]
        missing = int(series.isna().sum())
        profiles.append(
            ColumnProfile(
                name=str(column),
                dtype=detect_column_type(series),
                pandas_dtype=str(series.dtype),
                missing_count=missing,
                missing_percentage=round(missing / row_count * 100, 2) if row_count else 0.0,
                unique_count=int(series.nunique(dropna=True)),
            )
        )
    return profiles


def build_numeric_summary(df: pd.DataFrame) -> list[NumericSummary]:
    summaries = []
    for column in _numeric_columns(df):
        series = df[column].dropna()
        if series.empty:
            continue
        summaries.append(
            NumericSummary(
                column=column,
                count=int(series.count()),
                mean=float(series.mean()),
                std=_safe_float(series.std()),
                min=float(series.min()),
                q25=float(series.quantile(0.25)),
                median=float(series.quantile(0.5)),
                q75=float(series.quantile(0.75)),
                max=float(series.max()),
            )
        )
    return summaries


def _discrete_value_bins(values: np.ndarray) -> list[HistogramBin]:
    unique_values, counts = np.unique(values, return_counts=True)
    return [
        HistogramBin(bin_start=float(value), bin_end=float(value), count=int(count))
        for value, count in zip(unique_values, counts, strict=True)
    ]


def _histogram_bins(values: np.ndarray) -> list[HistogramBin]:
    counts, edges = np.histogram(values, bins=NUMERIC_HISTOGRAM_BINS)
    return [
        HistogramBin(bin_start=float(edges[i]), bin_end=float(edges[i + 1]), count=int(counts[i]))
        for i in range(len(counts))
    ]


def build_numeric_distributions(df: pd.DataFrame) -> list[NumericDistribution]:
    distributions = []
    for column in _numeric_columns(df):
        values = df[column].dropna().to_numpy(dtype=float)
        if values.size < 2 or np.allclose(values, values[0]):
            continue

        unique_count = np.unique(values).size
        bins = (
            _discrete_value_bins(values)
            if unique_count <= DISCRETE_NUMERIC_MAX_UNIQUE
            else _histogram_bins(values)
        )
        distributions.append(NumericDistribution(column=column, bins=bins))
    return distributions


def build_categorical_frequencies(df: pd.DataFrame) -> list[CategoricalFrequency]:
    row_count = len(df)
    frequencies = []
    for column in _categorical_columns(df):
        series = df[column].dropna()
        if series.empty:
            continue

        unique_count = series.nunique()
        if row_count and unique_count / row_count > CATEGORICAL_SKIP_UNIQUE_RATIO:
            continue

        value_counts = series.value_counts()
        truncated = len(value_counts) > CATEGORICAL_TOP_N
        top = value_counts.iloc[:CATEGORICAL_TOP_N]
        categories = [CategoryCount(value=str(idx), count=int(count)) for idx, count in top.items()]
        if truncated:
            other_count = int(value_counts.iloc[CATEGORICAL_TOP_N:].sum())
            categories.append(CategoryCount(value="Other", count=other_count))

        frequencies.append(
            CategoricalFrequency(column=column, categories=categories, truncated=truncated)
        )
    return frequencies


def build_correlation(df: pd.DataFrame) -> CorrelationMatrix | None:
    numeric_cols = _numeric_columns(df)
    if len(numeric_cols) < 2:
        return None

    corr = df[numeric_cols].corr(numeric_only=True)
    matrix = [[_safe_float(corr.at[row, col]) for col in corr.columns] for row in corr.index]
    return CorrelationMatrix(columns=[str(c) for c in corr.columns], matrix=matrix)


def build_dataset_profile(active: ActiveDataset) -> DatasetProfileResponse:
    df = active.dataframe
    return DatasetProfileResponse(
        dataset_id=active.dataset_id,
        filename=active.filename,
        row_count=len(df),
        column_count=df.shape[1],
        duplicate_row_count=int(df.duplicated().sum()),
        columns=build_column_profiles(df),
        numeric_summary=build_numeric_summary(df),
        numeric_distributions=build_numeric_distributions(df),
        categorical_frequencies=build_categorical_frequencies(df),
        correlation=build_correlation(df),
    )
