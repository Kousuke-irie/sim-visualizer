import os
from typing import Optional

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
from app.services.plt_cache import plt_cache
from app.services.section_data import SectionDataError, extract_section_data
from app.services.store import PltEntry

router = APIRouter(prefix="/api/directory", tags=["directory"])

# UIの「参照」機能のデフォルト起点。docker-compose では /data にマウントする想定（design 2節）。
# 存在しなければホームディレクトリにフォールバックする（非Docker実行時にも参照UIが機能するように）。
DEFAULT_BROWSE_ROOTS = ["/data", os.path.expanduser("~")]


@router.get("/browse", response_model=DirectoryBrowseResponse)
async def browse_directory(path: Optional[str] = None) -> DirectoryBrowseResponse:
    target = path or next((r for r in DEFAULT_BROWSE_ROOTS if os.path.isdir(r)), "/")
    if not os.path.isdir(target):
        raise HTTPException(status_code=404, detail="指定されたパスが見つかりません")
    target = os.path.abspath(target)

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
        has_direct = os.path.isfile(os.path.join(full, "input.dat"))
        # input.dat を持たないディレクトリは、子孫にも無ければ一覧から除外する
        # （子孫のどこかに存在すればナビゲーション用に残す）。
        if has_direct or contains_input_dat(full):
            entries.append(DirectoryBrowseEntry(name=name, path=full, has_input_dat=has_direct))

    parent = os.path.dirname(target) if os.path.dirname(target) != target else None

    return DirectoryBrowseResponse(path=target, parent=parent, entries=entries)


@router.post("/open", response_model=DirectoryMeta)
async def open_directory(req: DirectoryOpenRequest) -> DirectoryMeta:
    root = req.path
    if not os.path.isdir(root):
        raise HTTPException(status_code=404, detail="指定されたパスが見つかりません")

    input_path = os.path.join(root, "input.dat")
    if not os.path.isfile(input_path):
        raise HTTPException(status_code=400, detail="input.dat が見つかりません")

    try:
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            parsed_input = parse_input_dat(f.read())
    except InputParseError as e:
        raise HTTPException(status_code=400, detail=f"input.dat の解析に失敗しました: {e}") from e

    field2_dir = os.path.join(root, parsed_input.result_dirs["field2"])
    hist_dir = os.path.join(root, parsed_input.result_dirs["hist"])
    if not os.path.isdir(field2_dir):
        raise HTTPException(status_code=400, detail=f"field2ディレクトリが見つかりません: {field2_dir}")
    if not os.path.isdir(hist_dir):
        raise HTTPException(status_code=400, detail=f"histディレクトリが見つかりません: {hist_dir}")

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

    plt_entry = PltEntry(variables=parsed_frame.variables, dims=parsed_frame.dims, grid=parsed_frame.grid)
    try:
        section_data = extract_section_data(plt_entry, req)
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
