"""既存のランを元に新しいランを作る（runner, DESIGN_research_features.md §4.2・§4.4）。"""

import json

import pytest

from app.config import DATA_ROOTS_ENV
from app.errors import AccessDeniedError, ConflictError, InvalidInputError
from app.models.runs import EcoEdit, InputEdit, NewRunSpec
from app.parsers.input_parser import parse_input_dat
from app.runner.editors import parse_input_lines
from app.runner.runs import create_run, default_run_name, get_template, preview
from app.tests.sample_data import write_simulation_dir

ECO_H = "\t\tdata Alp1/1.04167d-05/\n\t\tdata Iopt/54.7/\n"
AMAMO = (
    "  OPEN(19, file='DIC_eco_check.dat', status='replace', action='write')\n"
    "  open(12, file='z_amamo.dat', status='old')\n"
)


@pytest.fixture
def base(data_root):
    """実際のランに近い元ラン（mecamamo_202606_v16 の構成を縮めたもの）。"""
    run = write_simulation_dir(data_root / "runs" / "mecamamo_202606_v16", with_source=True)
    (run / "amamo.f90").write_text(AMAMO)
    (run / "eco.f90").write_text("! eco\n")
    (run / "eco.h").write_text(ECO_H)
    (run / "param.h").write_text("! param\n")
    (run / "z_amamo.dat").write_text("1.0\n")  # 入力（status='old'）
    (run / "DIC_eco_check.dat").write_text("output\n")  # 出力（status='replace'）
    (run / "a.out").write_bytes(b"\x7fELF")
    (run / "a.out.bak_before_fix").write_bytes(b"\x7fELF")  # 実データ（v2）にあった実行ファイルの控え
    (run / "a.out.dSYM").mkdir()
    (run / "fort.13").write_text("x")
    (run / "結果.xlsx").write_bytes(b"PK")
    (run / ".DS_Store").write_bytes(b"x")
    (run / "data").mkdir()
    (run / "data" / "depth.dat").write_text("4.0\n")
    (run / "その他→").mkdir()  # 実データにある空の目印フォルダ
    (run / "outside_link").symlink_to(data_root.parent)
    return run


def spec(**overrides) -> NewRunSpec:
    values = {
        "name": "mecamamo_202606_v17",
        "compile_command": "gfortran -O2 -o a.out mecnest.f90 amamo.f90 eco.f90",
    }
    return NewRunSpec(**{**values, **overrides})


def line_no(base, tokens: list[str]) -> int:
    return next(line.line_no for line in parse_input_lines((base / "input.dat").read_text()) if line.tokens == tokens)


def test_template_lists_editable_values_and_the_copy_plan(base):
    t = get_template(str(base))
    assert t.default_name == "mecamamo_202606_v17"
    assert t.default_compile_command == "gfortran -O2 -o a.out mecnest.f90 amamo.f90 eco.f90"
    assert [c.name for c in t.eco_constants] == ["Alp1", "Iopt"]
    copied = {e.path for e in t.copy_entries}
    assert {"input.dat", "mecnest.f90", "eco.h", "param.h", "z_amamo.dat", "data/depth.dat", "その他→"} <= copied
    reasons = {e.path: e.reason for e in t.excluded}
    for path in (
        "field2",
        "hist",
        "field1",
        "a.out",
        "a.out.bak_before_fix",
        "a.out.dSYM",
        "fort.13",
        "結果.xlsx",
        "DIC_eco_check.dat",
    ):
        assert path in reasons, path
    assert reasons["outside_link"] == "シンボリックリンク"
    assert ".DS_Store" in reasons


def test_default_name_takes_the_next_free_version(base):
    (base.parent / "mecamamo_202606_v20").mkdir()
    assert default_run_name(base) == "mecamamo_202606_v21"
    other = base.parent / "plain_run"
    other.mkdir()
    assert default_run_name(other) == "plain_run_v2"


def test_create_run_copies_inputs_rewrites_values_and_records_history(base):
    dt_line = line_no(base, ["0.8"])
    created = create_run(
        str(base),
        spec(input_edits=[InputEdit(line_no=dt_line, tokens=["0.5"])], eco_edits=[EcoEdit(name="Iopt", value="60.0")]),
    )
    new = base.parent / "mecamamo_202606_v17"
    assert created.path == str(new)

    # 入力・ソースはコピー、出力は空のディレクトリ、生成物はコピーしない
    assert (new / "data" / "depth.dat").read_text() == "4.0\n"
    assert (new / "z_amamo.dat").exists() and (new / "その他→").is_dir()
    assert list((new / "field2").iterdir()) == [] and (new / "hist").is_dir() and (new / "field3").is_dir()
    for absent in ("a.out", "a.out.dSYM", "fort.13", "結果.xlsx", "DIC_eco_check.dat", ".DS_Store", "outside_link"):
        assert not (new / absent).exists(), absent

    # 値だけが書き換わり、その版の input.dat として読める
    assert parse_input_dat((new / "input.dat").read_text()).dt == 0.5
    assert "data Iopt/60.0/" in (new / "eco.h").read_text()
    assert (base / "eco.h").read_text() == ECO_H  # 元ランは触らない

    record = json.loads((new / "simviz_run.json").read_text())
    assert record["base_run"] == str(base)
    assert record["status"] == "created"
    assert {(c["file"], c["before"], c["after"]) for c in record["changes"]} == {
        ("input.dat", "0.8", "0.5"),
        ("eco.h", "54.7", "60.0"),
    }
    assert set(record["source_sha256"]) >= {"mecnest.f90", "eco.h"}


def test_preview_does_not_write_anything(base):
    before = sorted(p.name for p in base.parent.iterdir())
    p = preview(str(base), spec(eco_edits=[EcoEdit(name="Iopt", value="60.0")]))
    assert p.target_dir.endswith("mecamamo_202606_v17")
    assert [(c.where, c.before, c.after) for c in p.changes] == [("Iopt", "54.7", "60.0")]
    assert sorted(p.name for p in base.parent.iterdir()) == before


def test_unchanged_values_are_not_reported_as_changes(base):
    p = preview(str(base), spec(input_edits=[InputEdit(line_no=line_no(base, ["0.8"]), tokens=["0.8"])]))
    assert p.changes == []


def test_existing_name_is_a_conflict(base):
    (base.parent / "mecamamo_202606_v17").mkdir()
    with pytest.raises(ConflictError):
        create_run(str(base), spec())


@pytest.mark.parametrize("name", ["../escape", "a/b", ".hidden", "..", ""])
def test_unsafe_names_are_rejected(base, name):
    with pytest.raises(InvalidInputError):
        create_run(str(base), spec(name=name))


def test_cannot_create_outside_data_roots(base, monkeypatch):
    # 元ランそのものをデータルートにすると、隣（親ディレクトリ）はルートの外になる
    monkeypatch.setenv(DATA_ROOTS_ENV, str(base))
    with pytest.raises(AccessDeniedError):
        create_run(str(base), spec())


def test_base_outside_data_roots_is_denied(base, tmp_path_factory):
    other = write_simulation_dir(tmp_path_factory.mktemp("elsewhere") / "run")
    with pytest.raises(AccessDeniedError):
        get_template(str(other))


def test_output_directory_lines_cannot_be_edited(base):
    with pytest.raises(InvalidInputError, match="変更できません"):
        create_run(str(base), spec(input_edits=[InputEdit(line_no=line_no(base, ["field2"]), tokens=["0"])]))


def test_invalid_compile_command_creates_nothing(base):
    with pytest.raises(InvalidInputError):
        create_run(str(base), spec(compile_command="bash -c 'rm -rf ~'"))
    assert not (base.parent / "mecamamo_202606_v17").exists()


def test_failure_midway_leaves_no_partial_run(base, monkeypatch):
    import app.runner.runs as runs_module

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(runs_module.shutil, "copy2", boom)
    with pytest.raises(OSError):
        create_run(str(base), spec())
    assert not (base.parent / "mecamamo_202606_v17").exists()
    assert not any(p.name.startswith(".mecamamo_202606_v17") for p in base.parent.iterdir())


# --- 格子寸法と地点の値は変更できない（変えると計算の実行まで失敗に気づけないため） ---


def test_grid_and_point_values_are_locked_in_the_template(base):
    lines = {tuple(line.tokens): line for line in get_template(str(base)).input_lines}
    assert lines[("4", "5", "3", "1")].locked == [True, True, True, True]  # in,jn,kn,nest
    assert lines[("2", "300.0")].locked == [True, False]  # nhist は固定、histout は変更できる
    assert all(lines[("2", "3", "1", "3", "4", "1")].locked)  # ijhist0
    assert lines[("0.8",)].locked == [False]


@pytest.mark.parametrize(
    ("tokens", "edited", "message"),
    [
        (["4", "5", "3", "1"], ["8", "5", "3", "1"], "格子寸法"),
        (["2", "300.0"], ["3", "300.0"], "地点"),
        (["2", "3", "1", "3", "4", "1"], ["2", "3", "1", "3", "9", "1"], "地点"),
    ],
)
def test_editing_locked_values_is_rejected(base, tokens, edited, message):
    with pytest.raises(InvalidInputError, match=message):
        preview(str(base), spec(input_edits=[InputEdit(line_no=line_no(base, tokens), tokens=edited)]))


def test_unlocked_value_on_a_locked_line_can_change(base):
    p = preview(str(base), spec(input_edits=[InputEdit(line_no=line_no(base, ["2", "300.0"]), tokens=["2", "600.0"])]))
    assert [(c.before, c.after) for c in p.changes] == [("2 300.0", "2 600.0")]
