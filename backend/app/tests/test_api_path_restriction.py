"""データルート外へのアクセス制限（browse / open / input.dat 内の出力先）とアップロード上限。"""

from app.config import DATA_ROOTS_ENV
from app.routers import upload as upload_module
from app.tests.sample_data import write_simulation_dir


def test_browse_outside_data_root_is_403(client, data_root):
    res = client.get("/api/directory/browse", params={"path": str(data_root.parent)})
    assert res.status_code == 403


def test_browse_without_path_starts_at_data_root(client, data_root):
    res = client.get("/api/directory/browse")
    assert res.status_code == 200
    assert res.json()["path"] == str(data_root)


def test_browse_at_data_root_has_no_parent_but_subdir_does(client, data_root):
    (data_root / "group" / "sim").mkdir(parents=True)
    (data_root / "group" / "sim" / "input.dat").write_text("dummy")

    assert client.get("/api/directory/browse", params={"path": str(data_root)}).json()["parent"] is None
    sub = client.get("/api/directory/browse", params={"path": str(data_root / "group")}).json()
    assert sub["parent"] == str(data_root)


def test_browse_hides_symlinks_pointing_outside(client, tmp_path, monkeypatch):
    root = tmp_path / "root"
    outside = write_simulation_dir(tmp_path / "outside")
    root.mkdir()
    (root / "link").symlink_to(outside)
    monkeypatch.setenv(DATA_ROOTS_ENV, str(root))

    names = [e["name"] for e in client.get("/api/directory/browse", params={"path": str(root)}).json()["entries"]]
    assert "link" not in names


def test_open_outside_data_root_is_403(client, tmp_path, monkeypatch):
    sim = write_simulation_dir(tmp_path / "sim")
    monkeypatch.setenv(DATA_ROOTS_ENV, str(tmp_path / "elsewhere"))
    res = client.post("/api/directory/open", json={"path": str(sim)})
    assert res.status_code == 403


def test_result_dir_with_dotdot_inside_data_root_is_allowed(client, data_root):
    # 実データで ../ を使うかは不明なため、データルート配下に収まる限りは許可する
    sim = write_simulation_dir(data_root / "sim")
    write_simulation_dir(data_root / "shared")
    text = (sim / "input.dat").read_text().replace("\nfield2\n", "\n../shared/field2\n")
    (sim / "input.dat").write_text(text)

    res = client.post("/api/directory/open", json={"path": str(sim)})
    assert res.status_code == 200


def test_result_dir_escaping_data_root_is_400(client, tmp_path, monkeypatch):
    root = tmp_path / "root"
    sim = write_simulation_dir(root / "sim")
    write_simulation_dir(tmp_path / "outside")
    text = (sim / "input.dat").read_text().replace("\nfield2\n", "\n../../outside/field2\n")
    (sim / "input.dat").write_text(text)
    monkeypatch.setenv(DATA_ROOTS_ENV, str(root))

    res = client.post("/api/directory/open", json={"path": str(sim)})
    assert res.status_code == 400
    assert "field2" in res.json()["detail"]


def test_result_dir_absolute_path_outside_is_400(client, data_root, tmp_path_factory):
    sim = write_simulation_dir(data_root / "sim")
    outside = write_simulation_dir(tmp_path_factory.mktemp("other"))
    text = (sim / "input.dat").read_text().replace("\nhist\n", f"\n{outside / 'hist'}\n")
    (sim / "input.dat").write_text(text)

    res = client.post("/api/directory/open", json={"path": str(sim)})
    assert res.status_code == 400
    assert "hist" in res.json()["detail"]


def test_upload_larger_than_limit_is_413(client, monkeypatch):
    monkeypatch.setattr(upload_module, "MAX_UPLOAD_BYTES", 16)
    res = client.post("/api/upload", files={"file": ("big.plt", b"x" * 17, "application/octet-stream")})
    assert res.status_code == 413
