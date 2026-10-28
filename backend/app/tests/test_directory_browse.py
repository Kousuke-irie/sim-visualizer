from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_browse_lists_subdirectories_and_flags_input_dat(tmp_path):
    (tmp_path / "sim_a").mkdir()
    (tmp_path / "sim_a" / "input.dat").write_text("dummy")
    (tmp_path / "sim_b_nested" / "deeper").mkdir(parents=True)
    (tmp_path / "sim_b_nested" / "deeper" / "input.dat").write_text("dummy")
    (tmp_path / "no_sim_here").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "not_a_dir.txt").write_text("dummy")

    res = client.get("/api/directory/browse", params={"path": str(tmp_path)})
    assert res.status_code == 200
    body = res.json()

    assert body["path"] == str(tmp_path)
    assert body["parent"] == str(tmp_path.parent)
    names = {e["name"]: e["has_input_dat"] for e in body["entries"]}
    # 直接 input.dat を持つものは has_input_dat=True、子孫に持つだけのものは False で残す。
    # input.dat をどこにも持たないディレクトリは一覧から除外する。
    assert names == {"sim_a": True, "sim_b_nested": False}
    assert "no_sim_here" not in names


def test_browse_respects_max_depth(tmp_path):
    deep = tmp_path / "too_deep"
    nested = deep
    for i in range(6):
        nested = nested / f"level{i}"
    nested.mkdir(parents=True)
    (nested / "input.dat").write_text("dummy")

    res = client.get("/api/directory/browse", params={"path": str(tmp_path)})
    assert res.status_code == 200
    names = {e["name"] for e in res.json()["entries"]}
    assert "too_deep" not in names


def test_browse_root_has_no_parent():
    res = client.get("/api/directory/browse", params={"path": "/"})
    assert res.status_code == 200
    assert res.json()["parent"] is None


def test_browse_nonexistent_path_returns_404():
    res = client.get("/api/directory/browse", params={"path": "/no/such/path/at/all"})
    assert res.status_code == 404
