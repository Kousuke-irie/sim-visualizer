import os

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import MAX_UPLOAD_BYTES
from app.models.common import DatMeta, PltMeta
from app.parsers.dat_parser import DatParseError, parse_dat_bytes
from app.parsers.plt_parser import PltParseError, parse_plt_bytes
from app.services.store import store

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=PltMeta | DatMeta)
async def upload_file(file: UploadFile = File(...)) -> PltMeta | DatMeta:
    filename = file.filename or ""
    stem, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in (".plt", ".dat"):
        raise HTTPException(status_code=400, detail="対応していないファイル形式です（.plt / .dat のみ対応）")

    # 上限+1バイトだけ読めば超過を判定できる。全体を読んでから判定するとメモリを使い切りうる
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail=f"ファイルが大きすぎます（上限 {MAX_UPLOAD_BYTES // (1024 * 1024)} MB）"
        )

    if ext == ".plt":
        try:
            parsed = parse_plt_bytes(content)
        except PltParseError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return store.add_plt(parsed)

    try:
        parsed_dat = parse_dat_bytes(content)
    except DatParseError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    variable = stem or "value"
    return store.add_dat(variable, parsed_dat)


@router.get("/meta/{file_id}", response_model=PltMeta | DatMeta)
async def get_meta(file_id: str) -> PltMeta | DatMeta:
    try:
        return store.get_meta(file_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="指定されたfile_idが見つかりません") from None


@router.delete("/file/{file_id}")
async def delete_file(file_id: str) -> dict:
    store.delete(file_id)
    return {"status": "deleted"}
