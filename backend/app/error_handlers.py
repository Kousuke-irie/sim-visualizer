"""業務エラー（app/errors.py）を HTTP の応答に変換する。バックエンドと runner の両方で使う。"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import (
    AccessDeniedError,
    AppError,
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PayloadTooLargeError,
    ServiceUnavailableError,
)

STATUS_BY_ERROR: dict[type[AppError], int] = {
    NotFoundError: 404,
    AccessDeniedError: 403,
    InvalidInputError: 400,
    PayloadTooLargeError: 413,
    ConflictError: 409,
    ServiceUnavailableError: 503,
}


def status_for(exc: AppError) -> int:
    return next((code for cls, code in STATUS_BY_ERROR.items() if isinstance(exc, cls)), 500)


def register_app_error_handler(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        # FastAPI の HTTPException と同じ {"detail": ...} 形式にそろえ、フロントの扱いを変えない
        return JSONResponse(status_code=status_for(exc), content={"detail": exc.detail})
