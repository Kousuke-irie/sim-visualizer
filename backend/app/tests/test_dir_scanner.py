from app.parsers.dir_scanner import scan_hist_files, scan_plt_frames


def test_scan_plt_frames_sorts_and_computes_time(tmp_path):
    field2 = tmp_path / "field2"
    field2.mkdir()
    for name in ["tec-00002.plt", "tec-00000.plt", "tec-00005.plt", "avrg-00001.plt", "notes.txt"]:
        (field2 / name).write_text("dummy")

    frames = scan_plt_frames(str(field2), ifit2=3600.0)

    assert [f.file for f in frames] == ["tec-00000.plt", "tec-00002.plt", "tec-00005.plt"]
    assert [f.index for f in frames] == [0, 2, 5]
    assert [f.time_sec for f in frames] == [0.0, 7200.0, 18000.0]


def test_scan_plt_frames_empty_dir(tmp_path):
    field2 = tmp_path / "field2"
    field2.mkdir()
    assert scan_plt_frames(str(field2), ifit2=3600.0) == []


def test_scan_hist_files_groups_by_param_and_normalizes_point(tmp_path):
    hist = tmp_path / "hist"
    hist.mkdir()
    for name in ["DIC-01.dat", "DIC-02.dat", "TAlk-01.dat", "adh.dat", "din-01.dat"]:
        (hist / name).write_text("dummy")

    result = scan_hist_files(str(hist))

    assert result.params == ["DIC", "TAlk", "din"]
    assert result.by_param["DIC"] == ["01", "02"]
    assert result.by_param["TAlk"] == ["01"]
    assert result.by_param["din"] == ["01"]
    assert "adh" not in result.by_param
