"""The one reusable definition of "how raw selected columns become model
input": a scaler (or passthrough) for numeric columns, one-hot encoding for
categorical columns. Used by the configuration preview (this slice) and by
every model-training pipeline from Slice 4 onward, so preview and training
can never silently disagree about what the features look like.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler

from app.schemas.config import ScalerType
from app.services.dataset_summary import detect_column_type

NUMERIC_TRANSFORMER_NAME = "numeric"
CATEGORICAL_TRANSFORMER_NAME = "categorical"


def split_numeric_categorical(df: pd.DataFrame, columns: list[str]) -> tuple[list[str], list[str]]:
    numeric = [c for c in columns if detect_column_type(df[c]) == "numeric"]
    categorical = [c for c in columns if detect_column_type(df[c]) == "categorical"]
    return numeric, categorical


def _scaler_for(scaler: ScalerType) -> StandardScaler | MinMaxScaler | str:
    if scaler == ScalerType.standard:
        return StandardScaler()
    if scaler == ScalerType.minmax:
        return MinMaxScaler()
    return "passthrough"


def build_preprocessing_pipeline(
    numeric_features: list[str],
    categorical_features: list[str],
    scaler: ScalerType,
) -> ColumnTransformer:
    """Numeric columns are scaled (or passed through); categorical columns are
    one-hot encoded with unknown categories ignored at transform time, so a
    category unseen during fit (e.g. in a later prediction request) produces
    an all-zero row for that column instead of raising.
    """
    transformers: list[tuple[str, object, list[str]]] = []
    if numeric_features:
        transformers.append((NUMERIC_TRANSFORMER_NAME, _scaler_for(scaler), numeric_features))
    if categorical_features:
        transformers.append(
            (
                CATEGORICAL_TRANSFORMER_NAME,
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_features,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop")


def readable_feature_names(fitted_pipeline: ColumnTransformer) -> list[str]:
    """Strip the ColumnTransformer's "<transformer_name>__" prefix so preview
    output reads as plain column names (e.g. "membership_type_Gold" instead
    of "categorical__membership_type_Gold").
    """
    names = fitted_pipeline.get_feature_names_out().tolist()
    prefixes = (f"{NUMERIC_TRANSFORMER_NAME}__", f"{CATEGORICAL_TRANSFORMER_NAME}__")
    cleaned = []
    for name in names:
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix) :]
                break
        cleaned.append(name)
    return cleaned
