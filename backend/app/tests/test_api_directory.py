"""ディレクトリモードの API テスト（open → section / timeseries の一連の流れ）。"""

import pytest

from app.tests.sample_data import temp_value


@pytest.fixture
def opened(client, sim_dir):
    res = client.post("/api/directory/open", json={"path": str(sim_dir)})
    assert res.status_code == 200, res.text
    return res.json()


def test_open_builds_meta_from_input_and_scanned_files(opened, sim_dir):
    assert opened["root"] == str(sim_dir)
    assert opened["input"]["ifit2"] == 3600.0
    assert [f["time_sec"] for f in opened["plt_frames"]] == [0.0, 3600.0, 7200.0]
    assert opened["timeseries"]["params"] == ["DOX", "TEMP"]
    assert opened["timeseries"]["by_param"]["TEMP"] == ["01", "02"]
    assert [(p["point"], p["i"], p["j"]) for p in opened["points"]] == [("01", 2, 3), ("02", 3, 4)]
    assert opened["plt_dims"] == {"I": 4, "J": 5, "K": 3}


def test_meta_can_be_refetched(client, opened):
    res = client.get(f"/api/directory/{opened['dir_id']}/meta")
    assert res.json() == opened


def test_section_data_differs_per_frame(client, opened):
    def fetch(frame_index):
        res = client.post(
            "/api/directory/section/data",
            json={
                "dir_id": opened["dir_id"],
                "frame_index": frame_index,
                "plane": "XY",
                "slice_index": 0,
                "variable": "TEMP",
            },
        )
        assert res.status_code == 200
        return res.json()

    f0, f2 = fetch(0), fetch(2)
    assert f2["time_sec"] == 7200.0
    assert f0["values"][3][2] == pytest.approx(temp_value(2, 3, 0, t=0))
    assert f2["values"][3][2] == pytest.approx(temp_value(2, 3, 0, t=2))


def test_section_unknown_frame_is_400(client, opened):
    res = client.post(
        "/api/directory/section/data",
        json={"dir_id": opened["dir_id"], "frame_index": 42, "plane": "XY", "slice_index": 0, "variable": "TEMP"},
    )
    assert res.status_code == 400


def test_timeseries_data(client, opened):
    res = client.post(
        "/api/directory/timeseries/data",
        json={"dir_id": opened["dir_id"], "param": "DOX", "point": "02"},
    )
    assert res.status_code == 200
    body = res.json()
    assert (body["variable"], body["point"]) == ("DOX", "02")
    assert len(body["times"]) == len(body["values"])


def test_timeseries_unknown_point_is_404(client, opened):
    res = client.post(
        "/api/directory/timeseries/data",
        json={"dir_id": opened["dir_id"], "param": "DOX", "point": "09"},
    )
    assert res.status_code == 404


def test_unknown_dir_id_is_404(client):
    assert client.get("/api/directory/nope/meta").status_code == 404
    res = client.post(
        "/api/directory/section/data",
        json={"dir_id": "nope", "frame_index": 0, "plane": "XY", "slice_index": 0, "variable": "TEMP"},
    )
    assert res.status_code == 404


def test_open_without_input_dat_is_400(client, tmp_path):
    res = client.post("/api/directory/open", json={"path": str(tmp_path)})
    assert res.status_code == 400
    assert "input.dat" in res.json()["detail"]


def test_open_without_plt_frames_is_400(client, sim_dir):
    for plt in (sim_dir / "field2").iterdir():
        plt.unlink()
    res = client.post("/api/directory/open", json={"path": str(sim_dir)})
    assert res.status_code == 400


def test_open_with_unsupported_nest_is_400(client, sim_dir):
    text = (sim_dir / "input.dat").read_text().replace("4 5 3 1 #in", "4 5 3 2 #in")
    (sim_dir / "input.dat").write_text(text)
    res = client.post("/api/directory/open", json={"path": str(sim_dir)})
    assert res.status_code == 400
    assert "nest" in res.json()["detail"]


def test_open_nonexistent_path_is_404(client):
    res = client.post("/api/directory/open", json={"path": "/no/such/dir"})
    assert res.status_code == 404


def test_open_with_non_numeric_input_value_is_400_not_500(client, sim_dir):
    text = (sim_dir / "input.dat").read_text().replace("0.8                     #dt", "abc #dt")
    (sim_dir / "input.dat").write_text(text)
    res = client.post("/api/directory/open", json={"path": str(sim_dir)})
    assert res.status_code == 400
    assert "dt" in res.json()["detail"]
