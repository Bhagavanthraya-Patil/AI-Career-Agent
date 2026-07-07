from fastapi import FastAPI
from app.core.settings import settings

app = FastAPI(
    title=settings.app.project_name,
    version=settings.app.version,
    description="AI Career Agent Backend API",
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.app.version}
