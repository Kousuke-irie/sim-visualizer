from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ALLOW_ORIGINS
from app.error_handlers import register_app_error_handler
from app.routers import compare, directory, section, timeseries, upload

app = FastAPI(title="Sim Visualizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_app_error_handler(app)

app.include_router(upload.router)
app.include_router(section.router)
app.include_router(timeseries.router)
app.include_router(directory.router)
app.include_router(compare.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
