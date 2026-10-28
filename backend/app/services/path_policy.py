"""サーバー上のパスを、許可したデータルート配下に制限する。

ブラウザから渡されるパスだけでなく、input.dat に書かれた出力ディレクトリ名
（../ や絶対パスもあり得る）も同じ判定を通す。シンボリックリンクと .. は realpath で
解決してから、パス要素単位（commonpath）で配下かどうかを判定する。
"""

import os

from app.config import data_roots


class PathNotAllowedError(PermissionError):
    pass


def _resolved_roots() -> list[str]:
    return [os.path.realpath(r) for r in data_roots()]


def resolve_within_data_roots(path: str) -> str:
    """path を実パスに解決し、データルート配下でなければ PathNotAllowedError を投げる。"""
    real = os.path.realpath(path)
    for root in _resolved_roots():
        # 文字列の前方一致では /data が /data2 を許してしまうため、パス要素単位で比べる
        if os.path.commonpath([root, real]) == root:
            return real
    raise PathNotAllowedError(path)


def is_data_root(path: str) -> bool:
    return os.path.realpath(path) in _resolved_roots()


def first_existing_data_root() -> str | None:
    return next((r for r in data_roots() if os.path.isdir(r)), None)
