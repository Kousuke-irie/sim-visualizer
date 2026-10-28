import pytest

from app.parsers.dat_parser import DatParseError, parse_dat_text

SAMPLE = """\
i=  5 j=  10 n=  3 h= 5.70
time[sec]  -1.75m   -0.75m   3.95m
300.0   0.2000006E+04   1.9000000E+03   1.8000000E+03
900.0   0.2100000E+04   2.0000000E+03   1.9000000E+03
"""


def test_parse_dat_text_basic():
    parsed = parse_dat_text(SAMPLE)
    assert parsed.grid == {"i": 5.0, "j": 10.0, "n": 3.0, "h": 5.70}
    assert parsed.depths == ["-1.75m", "-0.75m", "3.95m"]
    assert parsed.depth_values == [-1.75, -0.75, 3.95]
    assert parsed.times.tolist() == [300.0, 900.0]
    assert parsed.values.shape == (2, 3)
    assert parsed.values[0, 0] == pytest.approx(2000.006)


def test_parse_dat_text_missing_grid_line():
    text = "time[sec]  -1.75m\n300.0 1.0\n"
    with pytest.raises(DatParseError):
        parse_dat_text(text)


def test_parse_dat_text_invalid_depth_label():
    text = "i=1 j=1 n=1 h=1.0\ntime[sec]  notadepth\n300.0 1.0\n"
    with pytest.raises(DatParseError):
        parse_dat_text(text)


def test_parse_dat_text_column_mismatch():
    text = "i=1 j=1 n=1 h=1.0\ntime[sec]  -1.75m   -0.75m\n300.0 1.0\n"
    with pytest.raises(DatParseError):
        parse_dat_text(text)


def test_parse_dat_text_not_enough_lines():
    text = "i=1 j=1 n=1 h=1.0\n"
    with pytest.raises(DatParseError):
        parse_dat_text(text)
