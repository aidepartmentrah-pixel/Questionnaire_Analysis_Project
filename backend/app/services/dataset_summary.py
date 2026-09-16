"""Build the JSON-safe dataset summary (columns, types, preview) returned by
the upload endpoint and reused wherever else the active dataset's shape needs
describing.
"""

from __future__ import annotations

import json

import pandas as pd

from app.schemas.dataset import ColumnInfo, DatasetSummary
from app.services.dataset_store import ActiveDataset

PREVIEW_ROW_LIMIT = 50


def detect_column_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "categorical"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "categorical"


def build_columns_info(df: pd.DataFrame) -> list[ColumnInfo]:
    return [
        ColumnInfo(
            name=str(column),
            dtype=detect_column_type(df[column]),
            pandas_dtype=str(df[column].dtype),
            unique_count=int(df[column].nunique(dropna=True)),
        )
        for column in df.columns
    ]


def build_preview_rows(df: pd.DataFrame, limit: int = PREVIEW_ROW_LIMIT) -> list[dict[str, object]]:
    """Pandas' own to_json handles NaN->null and numpy-scalar-> native-type
    conversion correctly, which a naive to_dict(orient="records") does not.
    """
    preview_json = df.head(limit).to_json(orient="records", date_format="iso")
    return json.loads(preview_json) if preview_json else []


def build_dataset_summary(active: ActiveDataset) -> DatasetSummary:
    df = active.dataframe
    return DatasetSummary(
        dataset_id=active.dataset_id,
        filename=active.filename,
        row_count=df.shape[0],
        column_count=df.shape[1],
        columns=build_columns_info(df),
        preview=build_preview_rows(df),
        preview_row_count=min(len(df), PREVIEW_ROW_LIMIT),
    )
