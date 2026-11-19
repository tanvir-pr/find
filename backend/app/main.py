from fastapi import FastAPI

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.customers.router import router as customers_router
from app.modules.products.router import router as products_router
from app.modules.reports.router import router as reports_router
from app.modules.sales.router import returns_router, router as sales_router
from app.modules.shifts.router import router as shifts_router
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
app.include_router(customers_router)
app.include_router(sales_router)
app.include_router(returns_router)
app.include_router(shifts_router)
app.include_router(reports_router)


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
