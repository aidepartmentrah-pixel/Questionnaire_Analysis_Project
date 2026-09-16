from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import dataset_store

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_dataset_store():
    dataset_store.clear_active_dataset()
    yield
    dataset_store.clear_active_dataset()


@pytest.fixture()
def fixtures_dir() -> Path:
    return FIXTURES_DIR
