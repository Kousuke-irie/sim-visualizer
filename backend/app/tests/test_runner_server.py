import pytest
from fastapi.testclient import TestClient

from app.runner.server import TOKEN_ENV, TOKEN_HEADER, app
from app.tests.sample_data import write_simulation_dir

TOKEN = "test-token-123"


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.setenv(TOKEN_ENV, TOKEN)
    return TestClient(app)


@pytest.fixture
def base(data_root):
    run = write_simulation_dir(data_root / "runs" / "case_v1", with_source=True)
    (run / "eco.h").write_text("      data Iopt/54.7/\n")
    return run


def auth(token=TOKEN):
    return {TOKEN_HEADER: token}


@pytest.mark.parametrize("headers", [{}, {TOKEN_HEADER: "wrong"}, {TOKEN_HEADER: ""}])
def test_requests_without_the_right_token_are_rejected(runner, base, headers):
    assert runner.get("/health", headers=headers).status_code == 401
    assert runner.post("/template", json={"base_dir": str(base)}, headers=headers).status_code == 401


def test_runner_refuses_everything_when_no_token_is_configured(monkeypatch, base):
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    client = TestClient(app)
    assert client.get("/health", headers={TOKEN_HEADER: ""}).status_code == 401


def test_template_preview_and_create(runner, base):
    t = runner.post("/template", json={"base_dir": str(base)}, headers=auth())
    assert t.status_code == 200, t.text
    body = t.json()
    spec = {
        "base_dir": str(base),
        "name": body["default_name"],
        "compile_command": "gfortran -O2 -o a.out mecnest.f90",
        "eco_edits": [{"name": "Iopt", "value": "60.0"}],
    }
    p = runner.post("/preview", json=spec, headers=auth())
    assert p.status_code == 200, p.text
    assert p.json()["changes"][0]["after"] == "60.0"

    c = runner.post("/runs", json=spec, headers=auth())
    assert c.status_code == 200, c.text
    assert c.json()["path"].endswith("case_v2")
    assert runner.post("/runs", json=spec, headers=auth()).status_code == 409


def test_domain_errors_keep_their_status(runner, base):
    res = runner.post(
        "/runs",
        json={"base_dir": str(base), "name": "x", "compile_command": "rm -rf /"},
        headers=auth(),
    )
    assert res.status_code == 400
    assert "gfortran" in res.json()["detail"]
