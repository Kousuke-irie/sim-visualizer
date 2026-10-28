"""ディレクトリ参照ダイアログ用に、データルート配下のサブディレクトリを列挙する。"""

import os

from app.errors import AccessDeniedError, NotFoundError
from app.models.directory import DirectoryBrowseEntry, DirectoryBrowseResponse
from app.parsers.dir_scanner import contains_input_dat
from app.services.path_policy import (
    PathNotAllowedError,
    first_existing_data_root,
    is_data_root,
    resolve_within_data_roots,
)

OUTSIDE_DATA_ROOT_DETAIL = "許可されたデータディレクトリの外にはアクセスできません"


def require_within_data_roots(path: str) -> None:
    try:
        resolve_within_data_roots(path)
    except PathNotAllowedError:
        raise AccessDeniedError(OUTSIDE_DATA_ROOT_DETAIL) from None


def browse(path: str | None) -> DirectoryBrowseResponse:
    # 起点はデータルート（docker compose では /data）。それより上や外はたどらせない
    target = path or first_existing_data_root()
    if target is None:
        raise NotFoundError("データディレクトリが見つかりません")
    target = os.path.abspath(target)
    require_within_data_roots(target)
    if not os.path.isdir(target):
        raise NotFoundError("指定されたパスが見つかりません")

    try:
        names = sorted(os.listdir(target), key=str.lower)
    except PermissionError:
        raise AccessDeniedError("このディレクトリへのアクセス権がありません") from None

    entries = []
    for name in names:
        if name.startswith("."):
            continue
        full = os.path.join(target, name)
        if not os.path.isdir(full):
            continue
        try:
            # データルート外を指すシンボリックリンクは一覧に出さない
            resolve_within_data_roots(full)
        except PathNotAllowedError:
            continue
        has_direct = os.path.isfile(os.path.join(full, "input.dat"))
        # input.dat を持たないディレクトリは、子孫にも無ければ一覧から除外する
        # （子孫のどこかに存在すればナビゲーション用に残す）。
        if has_direct or contains_input_dat(full):
            entries.append(DirectoryBrowseEntry(name=name, path=full, has_input_dat=has_direct))

    parent = None if is_data_root(target) else os.path.dirname(target)
    return DirectoryBrowseResponse(path=target, parent=parent, entries=entries)
