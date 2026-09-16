"""Wraps a TrainingResponse together with the successful models' fitted
sklearn pipelines. The fitted pipelines can't live in the pydantic response
schema (they aren't JSON-serializable) but the route layer needs them to
persist a downloadable experiment (Slice 7).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sklearn.pipeline import Pipeline

from app.schemas.training import TrainingResponse


@dataclass
class TrainingRun:
    response: TrainingResponse
    fitted_pipelines: dict[str, Pipeline] = field(default_factory=dict)
