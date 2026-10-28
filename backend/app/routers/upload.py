from fastapi import APIRouter, File, UploadFile

from app.models.common import DatMeta, PltMeta, UploadedMeta
from app.services import uploads
from app.services.store import store

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadedMeta)
async def upload_file(file: UploadFile = File(...)) -> PltMeta | DatMeta:
    # 上限+1バイトだけ読めば超過を判定できる。全体を読んでから判定するとメモリを使い切りうる
    content = await file.read(uploads.MAX_UPLOAD_BYTES + 1)
    uploads.check_upload_size(content)
    return uploads.register_upload(file.filename or "", content)


@router.get("/meta/{file_id}", response_model=UploadedMeta)
async def get_meta(file_id: str) -> PltMeta | DatMeta:
    return store.get_meta(file_id)


@router.delete("/file/{file_id}")
async def delete_file(file_id: str) -> dict:
    store.delete(file_id)
    return {"status": "deleted"}
