from fastapi import FastAPI

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.products.router import router as products_router
from app.modules.stock.router import purchases_router, stock_router
from app.modules.suppliers.router import router as suppliers_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(suppliers_router)
app.include_router(purchases_router)
app.include_router(stock_router)


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
