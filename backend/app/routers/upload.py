import os
from typing import Union

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.common import DatMeta, PltMeta
from app.parsers.dat_parser import DatParseError, parse_dat_bytes
from app.parsers.plt_parser import PltParseError, parse_plt_bytes
from app.services.store import store

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=Union[PltMeta, DatMeta])
async def upload_file(file: UploadFile = File(...)) -> Union[PltMeta, DatMeta]:
    filename = file.filename or ""
    stem, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in (".plt", ".dat"):
        raise HTTPException(status_code=400, detail="対応していないファイル形式です（.plt / .dat のみ対応）")

    content = await file.read()

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


@router.get("/meta/{file_id}", response_model=Union[PltMeta, DatMeta])
async def get_meta(file_id: str) -> Union[PltMeta, DatMeta]:
    try:
        return store.get_meta(file_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="指定されたfile_idが見つかりません") from None


@router.delete("/file/{file_id}")
async def delete_file(file_id: str) -> dict:
    store.delete(file_id)
    return {"status": "deleted"}
