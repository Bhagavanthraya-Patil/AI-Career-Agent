from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from app.api.routers import jobs_router
from app.core.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from app.db.session import configure, create_tables

    try:
        configure()
        await create_tables()
    except Exception:
        pass
    yield


app = FastAPI(
    title=settings.app.project_name,
    version=settings.app.version,
    description="AI Career Agent Backend API",
    lifespan=lifespan,
)

app.include_router(jobs_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.app.version}
