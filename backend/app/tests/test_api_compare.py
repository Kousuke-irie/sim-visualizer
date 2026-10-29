"""2ケース比較 API（DESIGN_research_features.md §3）。"""

import pytest

from app.tests.sample_data import temp_value, write_simulation_dir


def open_run(client, path) -> str:
    res = client.post("/api/directory/open", json={"path": str(path)})
    assert res.status_code == 200, res.text
    return res.json()["dir_id"]


@pytest.fixture
def runs(client, data_root):
    # B は TEMP だけ +1.5 ずらしたラン。差分 B−A は海域で一様に 1.5 になる
    a = open_run(client, write_simulation_dir(data_root / "a"))
    b = open_run(client, write_simulation_dir(data_root / "b", temp_offset=1.5))
    return a, b


def section(client, a, b, **overrides):
    body = {"dir_a": a, "dir_b": b, "time_sec": 3600.0, "plane": "XY", "slice_index": 0, "variable": "TEMP"}
    return client.post("/api/compare/section", json={**body, **overrides})


def test_check_lists_what_both_runs_share(client, runs):
    res = client.post("/api/compare/check", json={"dir_a": runs[0], "dir_b": runs[1]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["common_times"] == [0.0, 3600.0, 7200.0]
    assert "TEMP" in body["common_variables"] and "X" not in body["common_variables"]
    assert body["common_params"] == ["DOX", "TEMP"]
    assert [(p["point_a"], p["point_b"], p["i"], p["j"]) for p in body["common_points"]] == [
        ("01", "01", 2, 3),
        ("02", "02", 3, 4),
    ]


def test_section_returns_a_b_and_b_minus_a(client, runs):
    res = section(client, *runs)
    assert res.status_code == 200, res.text
    body = res.json()
    # 海域（i>=1）は A=解析解、B=A+1.5、差分=1.5。陸地（i=0）は差分も null
    assert body["a"]["values"][3][2] == pytest.approx(temp_value(2, 3, 0, t=1))
    assert body["b"]["values"][3][2] == pytest.approx(temp_value(2, 3, 0, t=1) + 1.5)
    assert all(row[0] is None for row in body["diff"])
    assert all(v == pytest.approx(1.5) for row in body["diff"] for v in row[1:])
    assert body["diff_range"] == pytest.approx([1.5, 1.5])
    assert body["a"]["time_sec"] == body["b"]["time_sec"] == 3600.0


def test_identical_runs_have_zero_diff(client, data_root):
    a = open_run(client, write_simulation_dir(data_root / "a"))
    b = open_run(client, write_simulation_dir(data_root / "b"))
    body = section(client, a, b).json()
    assert body["diff_range"] == [0.0, 0.0]


def test_frames_are_matched_by_time_not_by_index(client, data_root):
    # A は1時間ごと、B は2時間ごとに出力。B のフレーム1（7200秒）は A のフレーム2と比べる
    a = open_run(client, write_simulation_dir(data_root / "a", n_frames=4, ifit2=3600.0))
    b = open_run(client, write_simulation_dir(data_root / "b", n_frames=2, ifit2=7200.0))
    check = client.post("/api/compare/check", json={"dir_a": a, "dir_b": b}).json()
    assert check["common_times"] == [0.0, 7200.0]

    body = section(client, a, b, time_sec=7200.0).json()
    assert (body["a"]["frame_index"], body["b"]["frame_index"]) == (2, 1)
    # 合成データの値はフレーム番号 t に依存するので、A(t=2) と B(t=1) の差は -1
    assert body["diff"][3][2] == pytest.approx(-1.0)


def test_time_not_in_both_runs_is_400(client, runs):
    res = section(client, *runs, time_sec=1800.0)
    assert res.status_code == 400
    assert "1800" in res.json()["detail"]


def test_different_grid_is_not_comparable(client, data_root):
    a = open_run(client, write_simulation_dir(data_root / "a", ni=4))
    b = open_run(client, write_simulation_dir(data_root / "b", ni=3))
    res = client.post("/api/compare/check", json={"dir_a": a, "dir_b": b})
    assert res.status_code == 400
    assert "格子" in res.json()["detail"] and "4x5x3" in res.json()["detail"]
    assert section(client, a, b).status_code == 400


def test_same_dims_but_different_coordinates_is_not_comparable(client, data_root):
    a = open_run(client, write_simulation_dir(data_root / "a"))
    b_dir = write_simulation_dir(data_root / "b")
    for plt in (b_dir / "field2").iterdir():
        lines = plt.read_text().splitlines()
        # 最初のデータ行の X を書き換える（格子寸法は同じで座標だけ違う）
        cols = lines[3].split()
        cols[0] = "999.0"
        lines[3] = " ".join(cols)
        plt.write_text("\n".join(lines) + "\n")
    b = open_run(client, b_dir)
    res = client.post("/api/compare/check", json={"dir_a": a, "dir_b": b})
    assert res.status_code == 400
    assert "座標" in res.json()["detail"]


def test_unknown_dir_is_404(client, runs):
    res = client.post("/api/compare/check", json={"dir_a": runs[0], "dir_b": "nope"})
    assert res.status_code == 404
