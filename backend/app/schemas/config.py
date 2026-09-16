from enum import Enum

from pydantic import BaseModel


class TaskType(str, Enum):
    regression = "regression"
    classification = "classification"
    clustering = "clustering"


class ScalerType(str, Enum):
    none = "none"
    standard = "standard"
    minmax = "minmax"


class PreprocessingRequest(BaseModel):
    task: TaskType
    target: str | None = None
    features: list[str]
    drop_duplicates: bool = True
    scaler: ScalerType = ScalerType.standard


class PreprocessingPreview(BaseModel):
    dataset_id: str
    task: TaskType
    target: str | None
    features: list[str]
    original_rows: int
    removed_missing_rows: int
    removed_duplicate_rows: int
    final_rows: int
    final_feature_columns: list[str]
    ready_to_train: bool
    warnings: list[str]
