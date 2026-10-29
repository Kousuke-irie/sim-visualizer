import pytest

from app.errors import InvalidInputError
from app.runner.compile_command import parse_compile_command
from app.runner.editors import (
    apply_eco_edits,
    apply_input_edits,
    is_fortran_number,
    parse_eco_constants,
    parse_input_lines,
)
from app.tests.sample_data import make_input_dat_text

ECO_H = """\
\t\tdouble precision,dimension(Np) :: PHY
!\t\tdata Old/1.0/
\t\tdata Alp1/1.04167d-05/
\t\tdata Iopt/54.7/          ! light
\t\tdata Scphy/.7d-1/
\t\tdata Pair/1.0, 2.0/
"""


@pytest.mark.parametrize("token", ["1", "-2.5", "0.8", "3600.", ".7d-1", "1.0e-6", "1.04167D-05", "+4"])
def test_fortran_numbers(token):
    assert is_fortran_number(token)


@pytest.mark.parametrize("token", ["abc", "1.0.0", "data/depth.dat", "../field2", "1e", ""])
def test_not_fortran_numbers(token):
    assert not is_fortran_number(token)


def test_input_lines_mark_only_numeric_lines_editable():
    lines = {line.comment: line for line in parse_input_lines(make_input_dat_text())}
    assert lines["dt"].editable and lines["dt"].tokens == ["0.8"]
    # 出力先（hist / field2）やファイル名の行は編集できない
    non_editable = [line.tokens[0] for line in parse_input_lines(make_input_dat_text()) if not line.editable]
    assert "hist" in non_editable and "field2" in non_editable and "data/depth.dat" in non_editable


def test_apply_input_edits_keeps_spacing_and_comments():
    text = "0.8                     #dt\n3600.  0.   999999999999.       #fifit2,5,6\n"
    out = apply_input_edits(text, {2: ["1800.", "0.", "999999999999."]})
    assert out == "0.8                     #dt\n1800.  0.   999999999999.       #fifit2,5,6\n"


def test_apply_input_edits_rejects_unsafe_or_malformed_values():
    text = make_input_dat_text()
    by_tokens = {tuple(line.tokens): line.line_no for line in parse_input_lines(text)}
    field2_line = by_tokens[("field2",)]
    dt_line = by_tokens[("0.8",)]
    with pytest.raises(InvalidInputError, match="変更できません"):
        apply_input_edits(text, {field2_line: ["0"]})
    with pytest.raises(InvalidInputError, match="値の数"):
        apply_input_edits(text, {dt_line: ["0.8", "1.0"]})
    with pytest.raises(InvalidInputError, match="数値でない"):
        apply_input_edits(text, {dt_line: ["fast"]})


def test_eco_constants_skip_comments_and_arrays():
    names = [c.name for c in parse_eco_constants(ECO_H)]
    assert names == ["Alp1", "Iopt", "Scphy"]


def test_apply_eco_edits_replaces_only_the_value():
    out = apply_eco_edits(ECO_H, {"iopt": "60.0", "Alp1": "2.0d-05"})
    assert "\t\tdata Iopt/60.0/          ! light\n" in out
    assert "\t\tdata Alp1/2.0d-05/\n" in out
    assert out.count("\n") == ECO_H.count("\n")
    assert "\t\tdata Scphy/.7d-1/\n" in out  # 触っていない行はそのまま


def test_apply_eco_edits_rejects_unknown_or_invalid():
    with pytest.raises(InvalidInputError, match="Nope"):
        apply_eco_edits(ECO_H, {"Nope": "1.0"})
    with pytest.raises(InvalidInputError, match="Fortran の数値"):
        apply_eco_edits(ECO_H, {"Iopt": "1.0/; call system('rm')"})


# ---- コンパイルコマンド ----


@pytest.fixture
def src_dir(tmp_path):
    for name in ("mecnest.f90", "amamo.f90"):
        (tmp_path / name).write_text("! source\n")
    return tmp_path


def test_compile_command_accepts_the_usual_form(src_dir):
    argv = parse_compile_command("gfortran -O2 -g -o a.out mecnest.f90 amamo.f90", src_dir)
    assert argv == ["gfortran", "-O2", "-g", "-o", "a.out", "mecnest.f90", "amamo.f90"]


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("rm -rf /", "gfortran で始め"),
        ("gfortran -O2 -o a.out mecnest.f90; rm -rf ~", "指定できない引数"),
        ("gfortran -O2 -o ../a.out mecnest.f90", "ディレクトリを含まない"),
        ("gfortran -O2 -o a.out /etc/passwd.f90", "指定できない引数"),
        ("gfortran -O2 -o a.out missing.f90", "見つかりません"),
        ("gfortran -O2 -o a.out @args mecnest.f90", "指定できない引数"),
        ("gfortran -O2 -I/etc -o a.out mecnest.f90", "使えないオプション"),
        ("gfortran -O2 mecnest.f90", "-o で"),
        ("gfortran -O2 -o a.out", "ソース"),
    ],
)
def test_compile_command_rejects_anything_else(src_dir, command, message):
    with pytest.raises(InvalidInputError, match=message):
        parse_compile_command(command, src_dir)
