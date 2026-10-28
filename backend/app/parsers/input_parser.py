"""input.dat パーサ（mecnest.f90 の read 順序を再現するカーソル方式）。

mecnest.f90 の `open(10,file='input.dat')` 以降の `read` 文は、Fortran の
list-directed read の仕様（1回の read は必ず新しい行から読み始め、行内の
余分なトークンは破棄される）により、コメント（`#`以降）除去・空行除去後の
非コメント行を「1行 = 1回の read」として順に消費するだけで正確に再現できる
（実データ・実ソースで検証済み。単一グリッド `nest=1` 前提）。
"""

from dataclasses import dataclass


class InputParseError(ValueError):
    pass


@dataclass
class HistPointRaw:
    point: str
    i: int
    j: int
    n: int


@dataclass
class ParsedInput:
    ifit2: float
    endtime: float
    dt: float
    dx: float
    z_levels: list[float]
    nhist: int
    histout: float
    points: list[HistPointRaw]
    result_dirs: dict[str, str]  # {"hist": ..., "field1": ..., "field2": ...}


class _LineCursor:
    def __init__(self, lines: list[str]):
        self._lines = lines
        self._pos = 0

    def take(self) -> str:
        if self._pos >= len(self._lines):
            raise InputParseError("input.dat の行数が不足しています（読み出し順が想定と異なります）")
        line = self._lines[self._pos]
        self._pos += 1
        return line

    def take_tokens(self) -> list[str]:
        return self.take().split()


def _strip_comments_and_blanks(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def _first_float(tokens: list[str], label: str) -> float:
    """行の先頭トークンを float にする。失敗を素の ValueError/IndexError で漏らすと API が 500 になるため変換する。"""
    if not tokens:
        raise InputParseError(f"{label}のトークン数が不足しています")
    try:
        return float(tokens[0])
    except ValueError as e:
        raise InputParseError(f"{label}の数値変換に失敗しました: {tokens[0]!r}") from e


def parse_input_dat(text: str) -> ParsedInput:
    cur = _LineCursor(_strip_comments_and_blanks(text))

    cur.take_tokens()  # 1: isw(1..6)

    dims_tokens = cur.take_tokens()  # 2: in,jn,kn,nest
    if len(dims_tokens) < 4:
        raise InputParseError("2行目（in,jn,kn,nest）のトークン数が不足しています")
    try:
        nest = int(float(dims_tokens[3]))
    except ValueError as e:
        raise InputParseError("2行目（in,jn,kn,nest）の数値変換に失敗しました") from e
    if nest > 1:
        raise InputParseError("ネスト格子（nest>1）は本アプリでは未対応です")

    cur.take_tokens()  # 3: bear

    dt_tokens = cur.take_tokens()  # 4: dt(nast)
    dt = _first_float(dt_tokens, "4行目（dt）")

    e_tokens = cur.take_tokens()  # 5: endtime,ntime,irst
    endtime = _first_float(e_tokens, "5行目（endtime,ntime,irst）")

    cur.take_tokens()  # 6: dispout
    cur.take_tokens()  # 7: fifit1,fifit3,fifit4

    f_tokens = cur.take_tokens()  # 8: fifit2,fifit5,fifit6
    fifit2 = _first_float(f_tokens, "8行目（fifit2,fifit5,fifit6）")
    ifit2 = int(fifit2)
    if ifit2 < 0:
        raise InputParseError("負のfifit2（明示時刻リスト指定）は本アプリでは未対応です")

    dx_tokens = cur.take_tokens()  # 9: dx(1)
    dx = _first_float(dx_tokens, "9行目（dx）")

    z_tokens = cur.take_tokens()  # 10: z(k)
    try:
        z_levels = [float(v) for v in z_tokens]
    except ValueError as e:
        raise InputParseError("10行目（z(k)）の数値変換に失敗しました") from e

    cur.take_tokens()  # 11: am0,ac0,fkm0,fkc0,alat
    cur.take_tokens()  # 12: fkmmin,fkcmin
    cur.take_tokens()  # 13: fkm_in,fkc_in
    cur.take_tokens()  # 14: jsw(1,n)
    cur.take_tokens()  # 15: jsw(2,n)
    cur.take_tokens()  # 16: nopen
    cur.take_tokens()  # 17: nriv

    lb_tokens = cur.take_tokens()  # 18: milb,mjlb
    if len(lb_tokens) < 2:
        raise InputParseError("18行目（milb,mjlb）のトークン数が不足しています")
    try:
        milb = int(float(lb_tokens[0]))
        mjlb = int(float(lb_tokens[1]))
    except ValueError as e:
        raise InputParseError("18行目（milb,mjlb）の数値変換に失敗しました") from e
    if milb != 0:
        cur.take()  # milb 用の追加行
    if mjlb != 0:
        cur.take()  # mjlb 用の追加行

    cur.take_tokens()  # 19: i3d(n)
    cur.take_tokens()  # 20: cst,eps,nend

    nh_tokens = cur.take_tokens()  # 21: nhist,histout
    if len(nh_tokens) < 2:
        raise InputParseError("nhist,histout 行のトークン数が不足しています")
    try:
        nhist = int(float(nh_tokens[0]))
    except ValueError as e:
        raise InputParseError("nhist の数値変換に失敗しました") from e
    histout = _first_float(nh_tokens[1:], "nhist,histout 行の histout ")

    points: list[HistPointRaw] = []
    if nhist != 0:
        ij_tokens = cur.take_tokens()  # 22: ijhist0 (flat, 3*nhist)
        if len(ij_tokens) < nhist * 3:
            raise InputParseError(f"ijhist0 のトークン数が不足しています（期待={nhist * 3}、実際={len(ij_tokens)}）")
        try:
            values = [int(float(v)) for v in ij_tokens[: nhist * 3]]
        except ValueError as e:
            raise InputParseError("ijhist0 の数値変換に失敗しました") from e
        for idx in range(nhist):
            i_val, j_val, n_val = values[idx * 3 : idx * 3 + 3]
            points.append(HistPointRaw(point=f"{idx + 1:02d}", i=i_val, j=j_val, n=n_val))

    for _ in range(5):  # 23-27: fngrid, fngrid0, fnqin, fngin, fnwind
        cur.take()
    cur.take()  # 28: fnriv（river向けの1行、内容は問わない）
    cur.take()  # 29: fnclim
    cur.take()  # 30: fnopen（open boundary向けの1行、内容は問わない）

    hist_dir = cur.take().strip()  # 31: result3
    field1_dir = cur.take().strip()  # 32: result1
    field2_dir = cur.take().strip()  # 33: result2

    return ParsedInput(
        ifit2=float(ifit2),
        endtime=endtime,
        dt=dt,
        dx=dx,
        z_levels=z_levels,
        nhist=nhist,
        histout=histout,
        points=points,
        result_dirs={"hist": hist_dir, "field1": field1_dir, "field2": field2_dir},
    )
