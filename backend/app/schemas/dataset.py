from typing import Any

from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    dtype: str  # "numeric" | "categorical"
    pandas_dtype: str
    unique_count: int


class DatasetSummary(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    preview: list[dict[str, Any]]
    preview_row_count: int
