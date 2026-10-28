import os

from fastapi import APIRouter, HTTPException

from app.models.common import DatGrid
from app.models.directory import (
    DirectoryBrowseEntry,
    DirectoryBrowseResponse,
    DirectoryMeta,
    DirectoryOpenRequest,
    DirectorySectionDataRequest,
    DirectorySectionDataResponse,
    DirectoryTimeseriesRequest,
    DirectoryTimeseriesResponse,
)
from app.parsers.dat_parser import DatParseError, parse_dat_bytes
from app.parsers.dir_scanner import contains_input_dat, scan_hist_files, scan_plt_frames
from app.parsers.input_parser import InputParseError, parse_input_dat
from app.parsers.plt_parser import PltParseError, parse_plt_bytes
from app.services.directory_store import directory_store
from app.services.path_policy import (
    PathNotAllowedError,
    first_existing_data_root,
    is_data_root,
    resolve_within_data_roots,
)
from app.services.plt_cache import plt_cache
from app.services.section_data import SectionDataError, extract_section_data

router = APIRouter(prefix="/api/directory", tags=["directory"])

OUTSIDE_DATA_ROOT_DETAIL = "許可されたデータディレクトリの外にはアクセスできません"


@router.get("/browse", response_model=DirectoryBrowseResponse)
async def browse_directory(path: str | None = None) -> DirectoryBrowseResponse:
    # 起点はデータルート（docker compose では /data）。それより上や外はたどらせない
    target = path or first_existing_data_root()
    if target is None:
        raise HTTPException(status_code=404, detail="データディレクトリが見つかりません")
    target = os.path.abspath(target)
    try:
        resolve_within_data_roots(target)
    except PathNotAllowedError:
        raise HTTPException(status_code=403, detail=OUTSIDE_DATA_ROOT_DETAIL) from None
    if not os.path.isdir(target):
        raise HTTPException(status_code=404, detail="指定されたパスが見つかりません")

    try:
        names = sorted(os.listdir(target), key=str.lower)
    except PermissionError:
        raise HTTPException(status_code=403, detail="このディレクトリへのアクセス権がありません") from None

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


def _result_dir(root: str, name: str, label: str) -> str:
    # input.dat の出力先は ../ や絶対パスもあり得る。データルート配下に収まる限りは許可する
    path = os.path.join(root, name)
    try:
        resolve_within_data_roots(path)
    except PathNotAllowedError:
        raise HTTPException(
            status_code=400, detail=f"{label}ディレクトリ（{name}）が許可されたデータディレクトリの外を指しています"
        ) from None
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"{label}ディレクトリが見つかりません: {path}")
    return path


@router.post("/open", response_model=DirectoryMeta)
async def open_directory(req: DirectoryOpenRequest) -> DirectoryMeta:
    root = req.path
    try:
        resolve_within_data_roots(root)
    except PathNotAllowedError:
        raise HTTPException(status_code=403, detail=OUTSIDE_DATA_ROOT_DETAIL) from None
    if not os.path.isdir(root):
        raise HTTPException(status_code=404, detail="指定されたパスが見つかりません")

    input_path = os.path.join(root, "input.dat")
    if not os.path.isfile(input_path):
        raise HTTPException(status_code=400, detail="input.dat が見つかりません")

    try:
        with open(input_path, encoding="utf-8", errors="replace") as f:
            parsed_input = parse_input_dat(f.read())
    except InputParseError as e:
        raise HTTPException(status_code=400, detail=f"input.dat の解析に失敗しました: {e}") from e

    field2_dir = _result_dir(root, parsed_input.result_dirs["field2"], "field2")
    hist_dir = _result_dir(root, parsed_input.result_dirs["hist"], "hist")

    frames = scan_plt_frames(field2_dir, parsed_input.ifit2)
    if not frames:
        raise HTTPException(status_code=400, detail="field2 に tec-*.plt が見つかりません")
    ts_index = scan_hist_files(hist_dir)

    first_frame_path = os.path.join(field2_dir, frames[0].file)
    try:
        with open(first_frame_path, "rb") as f:
            first_frame = parse_plt_bytes(f.read())
    except PltParseError as e:
        raise HTTPException(status_code=400, detail=f"最初のpltファイルの解析に失敗しました: {e}") from e

    return directory_store.add(root, field2_dir, hist_dir, parsed_input, frames, ts_index, first_frame)


@router.get("/{dir_id}/meta", response_model=DirectoryMeta)
async def get_directory_meta(dir_id: str) -> DirectoryMeta:
    try:
        return directory_store.get_meta(dir_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="指定されたdir_idが見つかりません") from None


@router.post("/section/data", response_model=DirectorySectionDataResponse)
async def get_directory_section_data(req: DirectorySectionDataRequest) -> DirectorySectionDataResponse:
    try:
        entry = directory_store.get(req.dir_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="指定されたdir_idが見つかりません") from None

    frame_meta = next((f for f in entry.plt_frames if f.index == req.frame_index), None)
    if frame_meta is None:
        raise HTTPException(
            status_code=400, detail=f"指定されたframe_indexのフレームが見つかりません: {req.frame_index}"
        )

    frame_path = os.path.join(entry.field2_dir, frame_meta.file)
    try:
        parsed_frame = plt_cache.get_or_parse(req.dir_id, req.frame_index, frame_path)
    except PltParseError as e:
        raise HTTPException(status_code=400, detail=f"pltファイルの解析に失敗しました: {e}") from e

    try:
        section_data = extract_section_data(parsed_frame, req)
    except SectionDataError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return DirectorySectionDataResponse(
        **section_data.model_dump(),
        frame_index=req.frame_index,
        time_sec=frame_meta.time_sec,
    )


@router.post("/timeseries/data", response_model=DirectoryTimeseriesResponse)
async def get_directory_timeseries_data(req: DirectoryTimeseriesRequest) -> DirectoryTimeseriesResponse:
    try:
        entry = directory_store.get(req.dir_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="指定されたdir_idが見つかりません") from None

    points = entry.ts_index.by_param.get(req.param)
    if points is None or req.point not in points:
        raise HTTPException(
            status_code=404, detail=f"指定されたparam/pointのhistファイルが見つかりません: {req.param}-{req.point}"
        )

    file_path = os.path.join(entry.hist_dir, f"{req.param}-{req.point}.dat")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"histファイルが見つかりません: {file_path}")

    try:
        with open(file_path, "rb") as f:
            parsed_dat = parse_dat_bytes(f.read())
    except DatParseError as e:
        raise HTTPException(status_code=400, detail=f"histファイルの解析に失敗しました: {e}") from e

    return DirectoryTimeseriesResponse(
        variable=req.param,
        point=req.point,
        grid=DatGrid(**parsed_dat.grid),
        depths=parsed_dat.depths,
        depth_values=parsed_dat.depth_values,
        times=parsed_dat.times.tolist(),
        values=parsed_dat.values.tolist(),
    )
