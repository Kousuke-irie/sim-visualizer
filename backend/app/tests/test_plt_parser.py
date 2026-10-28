import numpy as np
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


# --- 高速化（NumPy での一括変換）前に、現在の挙動を固定しておくテスト ---

HEADER = 'TITLE = "x"\nVARIABLES = "X","Y","Z","TEMP"\nZONE I=2, J=1, K=1, F=POINT\n'


def test_quoted_variable_names_and_lowercase_zone():
    parsed = parse_plt_text('VARIABLES = "X","Y","Z","TEMP"\nzone i=2, j=1, k=1, f=point\n0 0 0 1\n1 0 0 2\n')
    assert parsed.variables == ["X", "Y", "Z", "TEMP"]
    assert parsed.dims == {"I": 2, "J": 1, "K": 1}


def test_crlf_blank_lines_tabs_and_exponents_are_accepted():
    text = HEADER.replace("\n", "\r\n") + "0.0\t0 0  1.5E+01  \r\n\r\n1.0e1 0 0 -2.5e-1\r\n"
    parsed = parse_plt_text(text)
    assert parsed.grid[0, 0, :, 3].tolist() == [15.0, -0.25]
    assert parsed.grid[0, 0, 1, 0] == 10.0


def test_values_are_laid_out_k_j_i():
    text = "VARIABLES=X,Y,Z,V\nZONE I=2, J=2, K=2, F=POINT\n" + "".join(f"0 0 0 {n}\n" for n in range(8))
    grid = parse_plt_text(text).grid
    # I が最速で変わる: 行 n = (k*J + j)*I + i
    assert grid[1, 0, 1, 3] == (1 * 2 + 0) * 2 + 1
    assert grid[0, 1, 0, 3] == 2


def test_non_numeric_value_is_a_parse_error():
    with pytest.raises(PltParseError, match="数値変換"):
        parse_plt_text(HEADER + "0 0 0 1\n1 0 0 abc\n")


def test_column_count_mismatch_reports_counts():
    with pytest.raises(PltParseError, match="列数が変数数と一致しません: 変数数=4 列数=3"):
        parse_plt_text(HEADER + "0 0 0\n1 0 0\n")


def test_ragged_rows_are_a_parse_error():
    with pytest.raises(PltParseError):
        parse_plt_text(HEADER + "0 0 0 1\n1 0 0\n")


def test_point_count_mismatch_reports_counts():
    with pytest.raises(PltParseError, match="期待=2 実際=3"):
        parse_plt_text(HEADER + "0 0 0 1\n1 0 0 2\n2 0 0 3\n")


def test_missing_data_rows():
    with pytest.raises(PltParseError, match="データ行が見つかりません"):
        parse_plt_text(HEADER)


def test_rows_starting_with_nan_are_data_not_header():
    # 計算が発散すると Fortran は NaN を書き出す。英字で始まってもヘッダ扱いしないこと
    parsed = parse_plt_text(HEADER + "NaN 0 0 1\n1 0 0 Infinity\n")
    assert np.isnan(parsed.grid[0, 0, 0, 0])
    assert np.isinf(parsed.grid[0, 0, 1, 3])
