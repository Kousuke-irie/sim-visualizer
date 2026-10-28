import pytest

from app.parsers.plt_parser import PltParseError, parse_plt_text

SAMPLE = """\
Title=No.00001 data
VARIABLES=X,Y,Z,U,V,W,TEMP
ZONE I= 2, J= 2, K= 1, F=POINT
0.0 0.0 -4.0 0.0 0.0 0.0 -999.0
10.0 0.0 -4.0 0.0 0.0 0.0 27.0
0.0 10.0 -4.0 0.0 0.0 0.0 26.0
10.0 10.0 -4.0 0.0 0.0 0.0 25.0
"""


def test_parse_plt_text_basic():
    parsed = parse_plt_text(SAMPLE)
    assert parsed.variables == ["X", "Y", "Z", "U", "V", "W", "TEMP"]
    assert parsed.dims == {"I": 2, "J": 2, "K": 1}
    assert parsed.grid.shape == (1, 2, 2, 7)
    assert parsed.grid[0, 0, 1, 0] == 10.0  # X at I=1


def test_parse_plt_text_missing_variables_line():
    text = "ZONE I=2, J=2, K=1, F=POINT\n0 0 0\n"
    with pytest.raises(PltParseError):
        parse_plt_text(text)


def test_parse_plt_text_missing_coord_var():
    text = "VARIABLES=U,V\nZONE I=1, J=1, K=1, F=POINT\n0 0\n"
    with pytest.raises(PltParseError):
        parse_plt_text(text)


def test_parse_plt_text_dimension_mismatch():
    text = "VARIABLES=X,Y,Z\nZONE I=2, J=2, K=1, F=POINT\n0 0 0\n1 1 1\n"
    with pytest.raises(PltParseError):
        parse_plt_text(text)
