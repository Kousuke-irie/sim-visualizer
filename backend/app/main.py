from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ALLOW_ORIGINS
from app.errors import AccessDeniedError, AppError, InvalidInputError, NotFoundError, PayloadTooLargeError
from app.routers import compare, directory, section, timeseries, upload

app = FastAPI(title="Sim Visualizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATUS_BY_ERROR: dict[type[AppError], int] = {
    NotFoundError: 404,
    AccessDeniedError: 403,
    InvalidInputError: 400,
    PayloadTooLargeError: 413,
}


@app.exception_handler(AppError)
async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    status = next((code for cls, code in STATUS_BY_ERROR.items() if isinstance(exc, cls)), 500)
    # FastAPI の HTTPException と同じ {"detail": ...} 形式にそろえ、フロントの扱いを変えない
    return JSONResponse(status_code=status, content={"detail": exc.detail})


app.include_router(upload.router)
app.include_router(section.router)
app.include_router(timeseries.router)
app.include_router(directory.router)
app.include_router(compare.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
