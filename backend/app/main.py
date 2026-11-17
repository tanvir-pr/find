from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "message": "Dokan Assistant API",
        "docs": "/docs",
        "health": "/health",
    }
