"""アップロード方式（断面ビュー・時系列ビュー）の API テスト。"""

from app.tests.sample_data import make_dat_text, make_plt_text


def upload(client, name: str, content: str):
    return client.post("/api/upload", files={"file": (name, content.encode(), "application/octet-stream")})


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_upload_plt_then_fetch_section(client):
    res = upload(client, "tec-00000.plt", make_plt_text())
    assert res.status_code == 200
    meta = res.json()
    assert meta["kind"] == "plt"
    assert "TEMP" in meta["variables"]

    res = client.post(
        "/api/section/data",
        json={"file_id": meta["file_id"], "plane": "XZ", "slice_index": 1, "variable": "TEMP"},
    )
    assert res.status_code == 200
    body = res.json()
    assert (body["h_label"], body["v_label"]) == ("X", "Z")
    assert body["values"][0][0] is None  # 陸地は null として JSON 化される

    assert client.get(f"/api/meta/{meta['file_id']}").json()["file_id"] == meta["file_id"]


def test_upload_dat_then_fetch_timeseries(client):
    meta = upload(client, "DIC-01.dat", make_dat_text(n_times=4)).json()
    assert meta["kind"] == "dat"
    assert meta["variable"] == "DIC-01"
    assert meta["n_times"] == 4

    body = client.get(f"/api/timeseries/data/{meta['file_id']}").json()
    assert len(body["times"]) == 4
    assert len(body["values"][0]) == len(meta["depths"])


def test_upload_rejects_unknown_extension(client):
    res = upload(client, "notes.txt", "hello")
    assert res.status_code == 400


def test_upload_reports_parse_error_as_400(client):
    res = upload(client, "broken.plt", "VARIABLES=X,Y,Z\nZONE I=2, J=2, K=1\n0 0 0\n")
    assert res.status_code == 400
    assert "データ点数" in res.json()["detail"]


def test_section_bad_slice_is_400(client):
    file_id = upload(client, "a.plt", make_plt_text()).json()["file_id"]
    res = client.post(
        "/api/section/data",
        json={"file_id": file_id, "plane": "XY", "slice_index": 99, "variable": "TEMP"},
    )
    assert res.status_code == 400


def test_section_invalid_plane_is_422(client):
    file_id = upload(client, "a.plt", make_plt_text()).json()["file_id"]
    res = client.post(
        "/api/section/data",
        json={"file_id": file_id, "plane": "AB", "slice_index": 0, "variable": "TEMP"},
    )
    assert res.status_code == 422


def test_unknown_or_deleted_file_id_is_404(client):
    file_id = upload(client, "a.plt", make_plt_text()).json()["file_id"]
    assert client.delete(f"/api/file/{file_id}").status_code == 200

    assert client.get(f"/api/meta/{file_id}").status_code == 404
    res = client.post(
        "/api/section/data",
        json={"file_id": file_id, "plane": "XY", "slice_index": 0, "variable": "TEMP"},
    )
    assert res.status_code == 404
    assert client.get(f"/api/timeseries/data/{file_id}").status_code == 404
