import pytest

from app.parsers.input_parser import InputParseError, parse_input_dat, source_reads_fkm_in
from app.tests.sample_data import make_input_dat_text, make_mecnest_source

BASE_LINES = [
    "1 5 0 1 1 0             #isw",
    "{dims}",
    "0.0                     #bear",
    "0.8                     #dt",
    "7200.  1  0             #endtime,ntime,irst",
    "3600.                   #dispout",
    "3600.  0.   999999999999.   #fifit1,3,4",
    "{fifit2}",
    "10.0                    #dx",
    "-2.0 -1.0 0.0 1.0 2.0   #z(k)",
    "0.1 0.1 0.001 0.001 0   #am0,ac0,fkm0,fkc0,alat",
    "1.0e-6 1.0e-6           #fkmmin,fkcmin",
    "1.0e-4 1.0e-4           #fkm_in,fkc_in",
    "1                       #jsw1",
    "1                       #jsw2",
    "2                       #nopen",
    "0                       #nriv",
    "{milb_mjlb}",
    "0                       #i3d",
    "1.0 1.e-6 30            #cst,eps,nend",
    "2  300.0                #nhist,histout",
    "5 5 1 3 3 1             #ijhist0",
    "data/depth.dat",
    "data/grit0.dat",
    "data/qini.dat",
    "data/ginit_0.dat",
    "wind/wind.dat",
    "river/",
    "clim/himeji.dat",
    "obc/north.dat obc/south.dat",
    "hist",
    "field1",
    "field2",
]


def build_input(
    dims="10 10 5 1 #in,jn,kn,nest",
    fifit2="3600.  0.   999999999999. #fifit2,5,6",
    milb_mjlb="0 0 #miflib",
):
    return "\n".join(BASE_LINES).format(dims=dims, fifit2=fifit2, milb_mjlb=milb_mjlb) + "\n"


def test_parse_input_dat_basic():
    parsed = parse_input_dat(build_input())
    assert parsed.ifit2 == 3600.0
    assert parsed.endtime == 7200.0
    assert parsed.dt == 0.8
    assert parsed.dx == 10.0
    assert parsed.z_levels == [-2.0, -1.0, 0.0, 1.0, 2.0]
    assert parsed.nhist == 2
    assert parsed.histout == 300.0
    assert [(p.point, p.i, p.j, p.n) for p in parsed.points] == [("01", 5, 5, 1), ("02", 3, 3, 1)]
    assert parsed.result_dirs == {"hist": "hist", "field1": "field1", "field2": "field2"}


def test_parse_input_dat_nest_unsupported():
    with pytest.raises(InputParseError):
        parse_input_dat(build_input(dims="10 10 5 2 #in,jn,kn,nest"))


def test_parse_input_dat_negative_ifit2_unsupported():
    with pytest.raises(InputParseError):
        parse_input_dat(build_input(fifit2="-10.  0.  999999999999. #fifit2,5,6"))


def test_parse_input_dat_milb_nonzero_skips_extra_line():
    lines = list(BASE_LINES)
    lines[17] = "{milb_mjlb}"
    text = "\n".join(lines).format(
        dims="10 10 5 1 #in,jn,kn,nest",
        fifit2="3600.  0.   999999999999. #fifit2,5,6",
        milb_mjlb="1 0 #miflib",
    )
    # milb=1 なので本来はこの直後に1行余分に読み出される。それをシミュレートするため挿入する。
    text = text.replace("1 0 #miflib\n0                       #i3d", "1 0 #miflib\n1 1 1\n0                       #i3d")
    parsed = parse_input_dat(text)
    assert parsed.result_dirs == {"hist": "hist", "field1": "field1", "field2": "field2"}


def test_parse_input_dat_truncated_file_raises():
    with pytest.raises(InputParseError):
        parse_input_dat("1 5 0 1 1 0\n10 10 5 1\n")


@pytest.mark.parametrize(
    ("original", "broken"),
    [
        ("0.8                     #dt", "abc #dt"),
        ("7200.  1  0             #endtime,ntime,irst", "end 1 0 #endtime"),
        ("3600.  0.   999999999999. #fifit2,5,6", "x 0. 1. #fifit2"),
        ("10.0                    #dx", "ten #dx"),
        ("2  300.0                #nhist,histout", "2 every5min #nhist,histout"),
    ],
)
def test_parse_input_dat_non_numeric_value_raises_parse_error(original, broken):
    # 数値変換の失敗が素の ValueError で漏れると API が 500 になるため、InputParseError に揃える
    text = build_input()
    assert original in text
    with pytest.raises(InputParseError, match="数値変換"):
        parse_input_dat(text.replace(original, broken))


# --- ソースの版による input.dat の行構成の違い（fkm_in,fkc_in 行の有無） ---


def test_old_layout_without_fkm_in_line_parses_when_told():
    text = make_input_dat_text(with_fkm_in=False)
    parsed = parse_input_dat(text, with_fkm_in=False)
    assert parsed.result_dirs == {"hist": "hist", "field1": "field1", "field2": "field2"}
    assert [(p.i, p.j) for p in parsed.points] == [(2, 3), (3, 4)]
    assert parsed.with_fkm_in is False


def test_reading_old_layout_as_new_layout_fails():
    # 1行ずれて読むと途中で辻褄が合わなくなる（以前は v2 がこれで開けなかった）
    with pytest.raises(InputParseError):
        parse_input_dat(make_input_dat_text(with_fkm_in=False), with_fkm_in=True)


def test_default_layout_is_the_current_one():
    assert parse_input_dat(make_input_dat_text()).with_fkm_in is True


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (make_mecnest_source(with_fkm_in=True), True),
        (make_mecnest_source(with_fkm_in=False), False),
        ("      READ (10, *) FKM_IN, FKC_IN\n", True),  # 大文字・空白の違い
        ("!     read(10,*) fkm_in,fkc_in\n", False),  # コメントアウトされた行は読まれない
        ("      read(11,*) fkm_in,fkc_in\n", False),  # input.dat（装置番号10）以外からの読み込み
    ],
)
def test_detect_layout_from_source(source, expected):
    assert source_reads_fkm_in(source) is expected


# --- 構造を決める行の位置（新しいランの作成で読み取り専用にする、DESIGN_research_features.md §4.2） ---


@pytest.mark.parametrize("with_fkm_in", [True, False])
def test_structural_lines_are_located_by_read_order(with_fkm_in):
    text = make_input_dat_text(with_fkm_in=with_fkm_in)
    parsed = parse_input_dat(text, with_fkm_in=with_fkm_in)
    stripped = [line.split("#", 1)[0].strip() for line in text.splitlines() if line.split("#", 1)[0].strip()]
    assert stripped[parsed.line_roles["dims"]].startswith("4 5 3 1")
    assert stripped[parsed.line_roles["nhist"]].split() == ["2", "300.0"]
    assert stripped[parsed.line_roles["ijhist"]].split() == ["2", "3", "1", "3", "4", "1"]


def test_structural_line_positions_follow_conditional_lines():
    # milb が 0 でないと追加の1行が読まれ、その分だけ地点の行が後ろにずれる
    text = make_input_dat_text(milb_mjlb="1 0 #miflib").replace("1 0 #miflib\n", "1 0 #miflib\n1 1 1\n")
    parsed = parse_input_dat(text)
    stripped = [line.split("#", 1)[0].strip() for line in text.splitlines() if line.split("#", 1)[0].strip()]
    assert stripped[parsed.line_roles["nhist"]].split() == ["2", "300.0"]
