"""アップロードされた .plt / .dat を判定・パースしてストアに登録する。"""

import os

from app.config import MAX_UPLOAD_BYTES
from app.errors import InvalidInputError, PayloadTooLargeError
from app.models.common import DatMeta, PltMeta
from app.parsers.dat_parser import DatParseError, parse_dat_bytes
from app.parsers.plt_parser import PltParseError, parse_plt_bytes
from app.services.store import store


def check_upload_size(content: bytes) -> None:
    if len(content) > MAX_UPLOAD_BYTES:
        raise PayloadTooLargeError(f"ファイルが大きすぎます（上限 {MAX_UPLOAD_BYTES // (1024 * 1024)} MB）")


def register_upload(filename: str, content: bytes) -> PltMeta | DatMeta:
    stem, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in (".plt", ".dat"):
        raise InvalidInputError("対応していないファイル形式です（.plt / .dat のみ対応）")

    if ext == ".plt":
        try:
            return store.add_plt(parse_plt_bytes(content))
        except PltParseError as e:
            raise InvalidInputError(str(e)) from e

    try:
        parsed_dat = parse_dat_bytes(content)
    except DatParseError as e:
        raise InvalidInputError(str(e)) from e
    # .dat はファイル名（例: DIC-01）を変数名として使う
    return store.add_dat(stem or "value", parsed_dat)
