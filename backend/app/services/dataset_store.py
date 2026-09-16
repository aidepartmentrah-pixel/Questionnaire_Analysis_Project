"""In-memory single-slot "active dataset" registry.

Only one dataset is active at a time (product scope explicitly excludes
multiple simultaneous datasets, user accounts and database-backed history):
uploading a new dataset replaces whatever was active before, including its
file on disk. State lives only for the lifetime of the process.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.core.config import get_settings


@dataclass
class ActiveDataset:
    dataset_id: str
    filename: str
    csv_path: Path
    dataframe: pd.DataFrame


class DatasetNotFoundError(Exception):
    def __init__(self, dataset_id: str) -> None:
        self.dataset_id = dataset_id
        super().__init__(f"Dataset '{dataset_id}' was not found or is no longer active.")


_active: ActiveDataset | None = None


def set_active_dataset(
    filename: str, dataframe: pd.DataFrame, raw_csv_bytes: bytes
) -> ActiveDataset:
    global _active

    settings = get_settings()
    settings.ensure_storage_dirs()

    if _active is not None:
        _active.csv_path.unlink(missing_ok=True)

    dataset_id = uuid.uuid4().hex
    csv_path = settings.uploads_dir / f"{dataset_id}.csv"
    csv_path.write_bytes(raw_csv_bytes)

    _active = ActiveDataset(
        dataset_id=dataset_id, filename=filename, csv_path=csv_path, dataframe=dataframe
    )
    return _active


def get_active_dataset() -> ActiveDataset | None:
    return _active


def get_dataset_or_raise(dataset_id: str) -> ActiveDataset:
    if _active is None or _active.dataset_id != dataset_id:
        raise DatasetNotFoundError(dataset_id)
    return _active


def clear_active_dataset() -> None:
    """Test-only helper: reset the store so tests don't leak state between runs."""
    global _active
    if _active is not None:
        _active.csv_path.unlink(missing_ok=True)
    _active = None
