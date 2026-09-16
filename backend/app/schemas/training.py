from typing import Any

from pydantic import BaseModel

from app.schemas.config import ScalerType, TaskType


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class ActualVsPredictedPoint(BaseModel):
    actual: float
    predicted: float


class ResidualPoint(BaseModel):
    predicted: float
    residual: float


class RegressionCharts(BaseModel):
    actual_vs_predicted: list[ActualVsPredictedPoint]
    residuals: list[ResidualPoint]


class ConfusionMatrix(BaseModel):
    labels: list[str]
    matrix: list[list[int]]


class ClassificationCharts(BaseModel):
    confusion_matrix: ConfusionMatrix


class PcaPoint(BaseModel):
    x: float
    y: float
    cluster: str  # "-1" denotes a DBSCAN noise point


class ClusterSizePoint(BaseModel):
    cluster: str
    size: int


class ClusteringCharts(BaseModel):
    pca_projection: list[PcaPoint]
    cluster_sizes: list[ClusterSizePoint]


class ModelResult(BaseModel):
    key: str
    display_name: str
    status: str  # "success" | "failed"
    duration_seconds: float
    best_params: dict[str, Any] | None = None
    metrics: dict[str, float] | None = None
    warning: str | None = None
    feature_importances: list[FeatureImportance] | None = None
    charts: RegressionCharts | ClassificationCharts | ClusteringCharts | None = None


class TrainingRequest(BaseModel):
    task: TaskType
    target: str | None = None
    features: list[str]
    drop_duplicates: bool = True
    scaler: ScalerType = ScalerType.standard


class TrainingResponse(BaseModel):
    dataset_id: str
    task: TaskType
    target: str | None
    train_rows: int
    test_rows: int
    primary_metric: str
    results: list[ModelResult]
    winner_key: str | None
    # Set after persistence, only when at least one model trained successfully.
    experiment_id: str | None = None
