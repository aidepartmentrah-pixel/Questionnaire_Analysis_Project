"""Persist successful training experiments (fitted pipelines, metrics,
metadata, per-model charts, EDA report) to disk under a generated
experiment id, so they can be downloaded later.

Filesystem-only, in-process-lifetime storage under Settings.artifacts_dir -
consistent with the rest of the app's scope (no database, no permanent
history beyond the current process), the same way uploaded datasets are
stored under Settings.uploads_dir.

Every path this module builds starts from an experiment_id / model_key that
has first passed a strict whitelist check (see _validate_*), so a caller can
never walk a "../" or absolute path out of the artifacts directory.
"""

from __future__ import annotations

import io
import json
import re
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import joblib
from sklearn.pipeline import Pipeline

from app.core.config import get_settings
from app.schemas.training import TrainingResponse

_EXPERIMENT_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")  # uuid4().hex
_MODEL_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")  # matches every registry key

CLUSTERING_PREDICTION_NOTE = (
    "K-Means supports predicting new, unseen rows via .predict(). Agglomerative "
    "Clustering and DBSCAN do not support predicting new rows by design (scikit-learn "
    "only assigns labels to the data given at fit time) - this exported pipeline "
    "reproduces the fitted preprocessing and the cluster labels assigned to the "
    "original training rows, but calling .predict() on new data with these two "
    "algorithms will raise an error."
)
SUPERVISED_PREDICTION_NOTE = (
    "This pipeline bundles both preprocessing and the trained model: call "
    ".predict(raw_dataframe[features]) directly on new rows using the same raw "
    "(unencoded, unscaled) feature columns used during training - no manual "
    "preprocessing is needed."
)


class ExperimentNotFoundError(Exception):
    def __init__(self, experiment_id: str) -> None:
        self.experiment_id = experiment_id
        super().__init__(f"Experiment '{experiment_id}' was not found or has expired.")


class ExperimentModelNotFoundError(Exception):
    def __init__(self, experiment_id: str, model_key: str) -> None:
        self.experiment_id = experiment_id
        self.model_key = model_key
        super().__init__(
            f"Model '{model_key}' was not found (or did not train successfully) "
            f"in experiment '{experiment_id}'."
        )


@dataclass(frozen=True)
class ExperimentPaths:
    root: Path
    models_dir: Path
    charts_dir: Path
    metadata_path: Path
    eda_report_path: Path


def _experiment_paths(experiment_id: str) -> ExperimentPaths:
    if not _EXPERIMENT_ID_PATTERN.match(experiment_id):
        raise ExperimentNotFoundError(experiment_id)

    root = get_settings().artifacts_dir / experiment_id
    return ExperimentPaths(
        root=root,
        models_dir=root / "models",
        charts_dir=root / "charts",
        metadata_path=root / "metadata.json",
        eda_report_path=root / "eda_report.html",
    )


def persist_experiment(
    dataset_filename: str,
    response: TrainingResponse,
    fitted_pipelines: dict[str, Pipeline],
    eda_report_html: str,
) -> str:
    """Writes every successful model's fitted pipeline, its chart data,
    metadata.json, and the EDA report to a fresh experiment directory.
    Returns the generated experiment id.
    """
    experiment_id = uuid.uuid4().hex
    paths = _experiment_paths(experiment_id)
    paths.models_dir.mkdir(parents=True, exist_ok=True)
    paths.charts_dir.mkdir(parents=True, exist_ok=True)

    for result in response.results:
        if result.status != "success":
            continue
        pipeline = fitted_pipelines.get(result.key)
        if pipeline is None:
            continue
        joblib.dump(pipeline, paths.models_dir / f"{result.key}.joblib")
        if result.charts is not None:
            (paths.charts_dir / f"{result.key}.json").write_text(
                result.charts.model_dump_json(indent=2), encoding="utf-8"
            )

    prediction_notes = (
        CLUSTERING_PREDICTION_NOTE
        if response.task.value == "clustering"
        else SUPERVISED_PREDICTION_NOTE
    )

    metadata = {
        "experiment_id": experiment_id,
        "dataset_filename": dataset_filename,
        "task": response.task.value,
        "target": response.target,
        "train_rows": response.train_rows,
        "test_rows": response.test_rows,
        "primary_metric": response.primary_metric,
        "winner_key": response.winner_key,
        "created_at": datetime.now(UTC).isoformat(),
        "prediction_notes": prediction_notes,
        "models": [
            {
                "key": r.key,
                "display_name": r.display_name,
                "status": r.status,
                "duration_seconds": r.duration_seconds,
                "best_params": r.best_params,
                "metrics": r.metrics,
                "warning": r.warning,
            }
            for r in response.results
        ],
    }
    paths.metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    paths.eda_report_path.write_text(eda_report_html, encoding="utf-8")

    return experiment_id


def get_model_artifact_path(experiment_id: str, model_key: str) -> Path:
    if not _MODEL_KEY_PATTERN.match(model_key):
        raise ExperimentModelNotFoundError(experiment_id, model_key)

    paths = _experiment_paths(experiment_id)  # validates experiment_id
    if not paths.root.is_dir():
        raise ExperimentNotFoundError(experiment_id)

    model_path = paths.models_dir / f"{model_key}.joblib"
    if not model_path.is_file():
        raise ExperimentModelNotFoundError(experiment_id, model_key)
    return model_path


def build_experiment_zip(experiment_id: str) -> bytes:
    paths = _experiment_paths(experiment_id)  # validates experiment_id
    if not paths.root.is_dir():
        raise ExperimentNotFoundError(experiment_id)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths.root.rglob("*")):
            if path.is_file():
                # arcname is always relative to the experiment root (never
                # absolute, never containing "..") because it's derived from
                # a real file discovered under that root, not from input.
                archive.write(path, path.relative_to(paths.root))

    return buffer.getvalue()
