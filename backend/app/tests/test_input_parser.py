import pytest

from app.parsers.input_parser import InputParseError, parse_input_dat

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


def build_input(dims="10 10 5 1 #in,jn,kn,nest", fifit2="3600.  0.   999999999999. #fifit2,5,6", milb_mjlb="0 0 #miflib"):
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
