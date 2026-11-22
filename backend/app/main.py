from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.mcp.http import McpApiKeyMiddleware, mcp_http_app
from app.mcp.server import mcp
from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router
from app.modules.customers.router import router as customers_router
from app.modules.products.router import router as products_router
from app.modules.reports.router import router as reports_router
from app.modules.sales.router import returns_router, router as sales_router
from app.modules.shifts.router import router as shifts_router
from app.modules.stock.router import purchases_router, stock_router
from app.modules.suppliers.router import router as suppliers_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Required when MCP Streamable HTTP is mounted (session task group).
    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(McpApiKeyMiddleware)
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
app.include_router(chat_router)
app.mount("/mcp", mcp_http_app)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "message": "Dokan Assistant API",
        "docs": "/docs",
        "health": "/health",
        "mcp": "/mcp/",
    }
