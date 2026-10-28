"""ディレクトリモードの業務処理（計算結果ディレクトリを開く・断面と時系列を取り出す）。"""

import os

from app.errors import InvalidInputError, NotFoundError
from app.models.common import DatGrid
from app.models.directory import (
    DirectoryMeta,
    DirectorySectionDataRequest,
    DirectorySectionDataResponse,
    DirectoryTimeseriesRequest,
    DirectoryTimeseriesResponse,
)
from app.parsers.dat_parser import DatParseError, parse_dat_bytes
from app.parsers.dir_scanner import scan_hist_files, scan_plt_frames
from app.parsers.input_parser import InputParseError, parse_input_dat
from app.parsers.plt_parser import PltParseError, parse_plt_bytes
from app.services.directory_browse import require_within_data_roots
from app.services.directory_store import directory_store
from app.services.path_policy import PathNotAllowedError, resolve_within_data_roots
from app.services.plt_cache import plt_cache
from app.services.section_data import extract_section_data


def _result_dir(root: str, name: str, label: str) -> str:
    # input.dat の出力先は ../ や絶対パスもあり得る。データルート配下に収まる限りは許可する
    path = os.path.join(root, name)
    try:
        resolve_within_data_roots(path)
    except PathNotAllowedError:
        raise InvalidInputError(
            f"{label}ディレクトリ（{name}）が許可されたデータディレクトリの外を指しています"
        ) from None
    if not os.path.isdir(path):
        raise InvalidInputError(f"{label}ディレクトリが見つかりません: {path}")
    return path


def open_directory(root: str) -> DirectoryMeta:
    require_within_data_roots(root)
    if not os.path.isdir(root):
        raise NotFoundError("指定されたパスが見つかりません")

    input_path = os.path.join(root, "input.dat")
    if not os.path.isfile(input_path):
        raise InvalidInputError("input.dat が見つかりません")

    try:
        with open(input_path, encoding="utf-8", errors="replace") as f:
            parsed_input = parse_input_dat(f.read())
    except InputParseError as e:
        raise InvalidInputError(f"input.dat の解析に失敗しました: {e}") from e

    field2_dir = _result_dir(root, parsed_input.result_dirs["field2"], "field2")
    hist_dir = _result_dir(root, parsed_input.result_dirs["hist"], "hist")

    frames = scan_plt_frames(field2_dir, parsed_input.ifit2)
    if not frames:
        raise InvalidInputError("field2 に tec-*.plt が見つかりません")
    ts_index = scan_hist_files(hist_dir)

    first_frame_path = os.path.join(field2_dir, frames[0].file)
    try:
        with open(first_frame_path, "rb") as f:
            first_frame = parse_plt_bytes(f.read())
    except PltParseError as e:
        raise InvalidInputError(f"最初のpltファイルの解析に失敗しました: {e}") from e

    return directory_store.add(root, field2_dir, hist_dir, parsed_input, frames, ts_index, first_frame)


def get_section_data(req: DirectorySectionDataRequest) -> DirectorySectionDataResponse:
    entry = directory_store.get(req.dir_id)

    frame_meta = next((f for f in entry.plt_frames if f.index == req.frame_index), None)
    if frame_meta is None:
        raise InvalidInputError(f"指定されたframe_indexのフレームが見つかりません: {req.frame_index}")

    frame_path = os.path.join(entry.field2_dir, frame_meta.file)
    try:
        parsed_frame = plt_cache.get_or_parse(req.dir_id, req.frame_index, frame_path)
    except PltParseError as e:
        raise InvalidInputError(f"pltファイルの解析に失敗しました: {e}") from e

    section_data = extract_section_data(parsed_frame, req)
    return DirectorySectionDataResponse(
        **section_data.model_dump(),
        frame_index=req.frame_index,
        time_sec=frame_meta.time_sec,
    )


def get_timeseries_data(req: DirectoryTimeseriesRequest) -> DirectoryTimeseriesResponse:
    entry = directory_store.get(req.dir_id)

    # パスを組み立てる前に、走査済みの索引にある組み合わせかを確かめる（任意のファイル名を作らせない）
    points = entry.ts_index.by_param.get(req.param)
    if points is None or req.point not in points:
        raise NotFoundError(f"指定されたparam/pointのhistファイルが見つかりません: {req.param}-{req.point}")

    file_path = os.path.join(entry.hist_dir, f"{req.param}-{req.point}.dat")
    if not os.path.isfile(file_path):
        raise NotFoundError(f"histファイルが見つかりません: {file_path}")

    try:
        with open(file_path, "rb") as f:
            parsed_dat = parse_dat_bytes(f.read())
    except DatParseError as e:
        raise InvalidInputError(f"histファイルの解析に失敗しました: {e}") from e

    return DirectoryTimeseriesResponse(
        variable=req.param,
        point=req.point,
        grid=DatGrid(**parsed_dat.grid),
        depths=parsed_dat.depths,
        depth_values=parsed_dat.depth_values,
        times=parsed_dat.times.tolist(),
        values=parsed_dat.values.tolist(),
    )
