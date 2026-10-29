"""ソースの版による input.dat の行構成の違いを、ディレクトリを開くときに判定する（DESIGN_research_features.md §2）。"""

import pytest

from app.tests.sample_data import write_simulation_dir


def open_dir(client, path):
    return client.post("/api/directory/open", json={"path": str(path)})


@pytest.mark.parametrize("with_fkm_in", [True, False])
def test_layout_is_taken_from_mecnest_source(client, data_root, with_fkm_in):
    sim = write_simulation_dir(data_root / "sim", with_fkm_in=with_fkm_in, with_source=True)
    res = open_dir(client, sim)
    assert res.status_code == 200, res.text
    assert [(p["i"], p["j"]) for p in res.json()["points"]] == [(2, 3), (3, 4)]


@pytest.mark.parametrize("with_fkm_in", [True, False])
def test_without_source_the_layout_whose_output_dirs_exist_is_used(client, data_root, with_fkm_in):
    sim = write_simulation_dir(data_root / "sim", with_fkm_in=with_fkm_in, with_source=False)
    res = open_dir(client, sim)
    assert res.status_code == 200, res.text
    assert res.json()["input"]["result_dirs"]["field2"] == "field2"


def test_source_and_input_dat_disagree_reports_the_layout(client, data_root):
    # ソースは新しい版なのに input.dat が古い版（ファイルを混ぜてコピーした等）
    sim = write_simulation_dir(data_root / "sim", with_fkm_in=False, with_source=True)
    (sim / "mecnest.f90").write_text((sim / "mecnest.f90").read_text() + "      read(10,*) fkm_in,fkc_in\n")
    res = open_dir(client, sim)
    assert res.status_code == 400
    assert "fkm_in" in res.json()["detail"]


def test_old_layout_without_output_dirs_reports_the_missing_dir_not_a_shifted_line(client, data_root):
    # 以前は 1行ずれて読んだ結果「nhist,histout 行のトークン数が不足」という原因の分からないエラーになった
    sim = write_simulation_dir(data_root / "sim", with_fkm_in=False, with_source=False)
    for f in (sim / "field2").iterdir():
        f.unlink()
    (sim / "field2").rmdir()
    res = open_dir(client, sim)
    assert res.status_code == 400
    assert "field2ディレクトリが見つかりません" in res.json()["detail"]


def test_unparseable_input_dat_keeps_the_original_message(client, data_root):
    sim = write_simulation_dir(data_root / "sim", with_source=False)
    text = (sim / "input.dat").read_text().replace("4 5 3 1 #in", "4 5 3 2 #in")
    (sim / "input.dat").write_text(text)
    res = open_dir(client, sim)
    assert res.status_code == 400
    assert res.json()["detail"] == "input.dat の解析に失敗しました: ネスト格子（nest>1）は本アプリでは未対応です"
