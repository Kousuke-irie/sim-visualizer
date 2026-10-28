import pytest
from fastapi.testclient import TestClient

from app.config import DATA_ROOTS_ENV
from app.main import app
from app.tests.sample_data import write_simulation_dir


@pytest.fixture(autouse=True)
def data_root(tmp_path, monkeypatch):
    """各テストの tmp_path だけを、アクセスを許可するデータルートにする。"""
    monkeypatch.setenv(DATA_ROOTS_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sim_dir(tmp_path):
    return write_simulation_dir(tmp_path / "sim")
