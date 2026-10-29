"""/api/runs/*: バックエンドから runner への依頼（runner はテスト内で直接呼ぶ）。"""

import os
import time
import urllib.error

import pytest
from fastapi.testclient import TestClient

from app.config import CONTAINER_DATA_DIR_ENV, HOST_DATA_DIR_ENV
from app.runner import jobs
from app.runner.jobs import JobQueue
from app.runner.server import TOKEN_ENV
from app.runner.server import app as runner_app
from app.services import runner_client
from app.tests.sample_data import write_fake_toolchain, write_simulation_dir


@pytest.fixture
def runner_in_process(monkeypatch):
    """runner_client の送信先を、HTTP を介さず runner のアプリに直接つなぐ。"""
    monkeypatch.setenv(TOKEN_ENV, "tok")
    runner = TestClient(runner_app)

    def send(path, payload):
        res = runner.post(path, json=payload, headers={runner_client.TOKEN_HEADER: "tok"})
        return res.status_code, res.json()

    monkeypatch.setattr(runner_client, "_send", send)


@pytest.fixture
def opened(client, data_root):
    run = write_simulation_dir(data_root / "runs" / "case_v1", with_source=True)
    (run / "eco.h").write_text("      data Iopt/54.7/\n")
    res = client.post("/api/directory/open", json={"path": str(run)})
    assert res.status_code == 200, res.text
    return res.json()["dir_id"], run


def test_template_preview_and_create_through_the_backend(client, runner_in_process, opened):
    dir_id, base = opened
    t = client.post("/api/runs/template", json={"dir_id": dir_id})
    assert t.status_code == 200, t.text
    assert t.json()["default_name"] == "case_v2"

    body = {
        "dir_id": dir_id,
        "name": "case_v2",
        "compile_command": t.json()["default_compile_command"],
        "eco_edits": [{"name": "Iopt", "value": "60.0"}],
    }
    p = client.post("/api/runs/preview", json=body)
    assert p.status_code == 200, p.text
    assert p.json()["target_dir"] == str(base.parent / "case_v2")

    c = client.post("/api/runs", json=body)
    assert c.status_code == 200, c.text
    assert (base.parent / "case_v2" / "eco.h").read_text() == "      data Iopt/60.0/\n"
    assert client.post("/api/runs", json=body).status_code == 409


def test_runner_not_running_is_503_with_the_start_command(client, opened, monkeypatch):
    def refused(path, payload):
        raise runner_client.ServiceUnavailableError(runner_client.START_HINT)

    monkeypatch.setattr(runner_client, "_send", refused)
    res = client.post("/api/runs/template", json={"dir_id": opened[0]})
    assert res.status_code == 503
    assert "python -m app.runner" in res.json()["detail"]


def test_connection_refused_becomes_503(monkeypatch):
    monkeypatch.setattr(runner_client, "runner_url", lambda: "http://127.0.0.1:1")  # 誰も待ち受けていないポート

    def urlopen(*args, **kwargs):
        raise urllib.error.URLError("refused")

    monkeypatch.setattr(runner_client.urllib.request, "urlopen", urlopen)
    with pytest.raises(runner_client.ServiceUnavailableError):
        runner_client.call("/template", {})


def test_wrong_token_is_reported_as_configuration_problem(client, opened, monkeypatch):
    monkeypatch.setattr(runner_client, "_send", lambda path, payload: (401, {"detail": "token"}))
    res = client.post("/api/runs/template", json={"dir_id": opened[0]})
    assert res.status_code == 503
    assert "SIMVIZ_RUNNER_TOKEN" in res.json()["detail"]


def test_paths_are_translated_between_container_and_host(monkeypatch):
    monkeypatch.setenv(HOST_DATA_DIR_ENV, "/Users/me/Desktop")
    monkeypatch.setenv(CONTAINER_DATA_DIR_ENV, "/data")
    assert runner_client.to_host_path("/data/runs/v16") == "/Users/me/Desktop/runs/v16"
    assert runner_client.to_container_path("/Users/me/Desktop/runs/v17") == "/data/runs/v17"
    assert runner_client.to_host_path("/database/x") == "/database/x"  # 接頭辞が似ているだけの別パスは読み替えない
    monkeypatch.delenv(HOST_DATA_DIR_ENV)
    assert runner_client.to_host_path("/data/runs/v16") == "/data/runs/v16"


@pytest.fixture
def job_queue(tmp_path, data_root, monkeypatch):
    """runner の待ち行列を、テストごとの保存先と偽の gfortran で動かす。"""
    bin_dir = write_fake_toolchain(data_root / "bin")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_MODEL_FRAME_SECONDS", "0.05")
    queue = JobQueue(tmp_path / "state" / "jobs.json", poll_interval=0.05)
    queue.start()
    monkeypatch.setattr(jobs, "_queue", queue)
    yield queue
    queue.shutdown()


def test_create_then_run_through_the_backend(client, runner_in_process, job_queue, opened, monkeypatch):
    dir_id, base = opened
    template = client.post("/api/runs/template", json={"dir_id": dir_id}).json()
    created = client.post(
        "/api/runs",
        json={"dir_id": dir_id, "name": "case_v2", "compile_command": template["default_compile_command"]},
    ).json()

    res = client.post("/api/runs/jobs", json={"path": created["path"]})
    assert res.status_code == 200, res.text
    job = res.json()
    assert job["base_run"] == str(base)

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        listed = client.get("/api/runs/jobs").json()["jobs"]
        if listed[0]["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.05)
    assert listed[0]["status"] == "succeeded", listed[0]["message"]
    assert listed[0]["frames_done"] == listed[0]["frames_expected"] == 2

    log = client.get(f"/api/runs/jobs/{job['job_id']}/log", params={"lines": 1}).json()
    assert log["text"] == "fake model: done"
    # できたランは、そのまま可視化できる
    assert client.post("/api/directory/open", json={"path": created["path"]}).status_code == 200

    assert client.post("/api/runs/jobs", json={"path": created["path"]}).status_code == 409
    assert client.post(f"/api/runs/jobs/{job['job_id']}/cancel").status_code == 409
    assert client.get("/api/runs/jobs/nope/log").status_code == 404


def test_job_paths_are_shown_as_container_paths(client, job_queue, monkeypatch):
    monkeypatch.setenv(HOST_DATA_DIR_ENV, "/Users/me/Desktop")
    monkeypatch.setenv(CONTAINER_DATA_DIR_ENV, "/data")
    sent = {}

    def send(path, payload):
        sent[path] = payload
        job = {
            "job_id": "j1",
            "name": "v17",
            "run_dir": "/Users/me/Desktop/runs/v17",
            "base_run": "/Users/me/Desktop/runs/v16",
            "status": "queued",
            "message": "",
            "created_at": "2026-10-29T00:00:00+00:00",
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "frames_done": 0,
            "frames_expected": 3,
            "elapsed_sec": None,
            "eta_sec": None,
        }
        return 200, job if path == "/jobs" else {"jobs": [job]}

    monkeypatch.setattr(runner_client, "_send", send)
    body = client.post("/api/runs/jobs", json={"path": "/data/runs/v17"}).json()
    assert sent["/jobs"] == {"run_dir": "/Users/me/Desktop/runs/v17"}
    assert (body["run_dir"], body["base_run"]) == ("/data/runs/v17", "/data/runs/v16")
    assert client.get("/api/runs/jobs").json()["jobs"][0]["run_dir"] == "/data/runs/v17"
