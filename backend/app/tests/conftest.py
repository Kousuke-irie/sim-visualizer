import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tests.sample_data import write_simulation_dir


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sim_dir(tmp_path):
    return write_simulation_dir(tmp_path / "sim")
