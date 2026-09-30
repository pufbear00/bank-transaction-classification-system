"""Isolated local demo: creates an empty schema, never downloads data."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import Base, engine
from app import models
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="银行流水 · 本地空数据版", lifespan=lifespan,
              docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list,
                   allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "offline-empty-demo", "external_sync": False}
