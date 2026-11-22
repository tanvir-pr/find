"""MCP server: 3 tools + 1 resource + 1 prompt (reuses chat tool executors)."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from mcp.server.mcpserver import MCPServer
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.mcp.db import mcp_session
from app.models.product import Product, ProductVariant
from app.models.sales import Sale, SaleItem
from app.modules.chat import tool_executors
from app.modules.stock.helpers import get_variant_stock

mcp = MCPServer(
    name="dokan-assistant",
    title="Dokan Assistant MCP",
    description="Read-only store tools for remote owners (stock, sales, low stock).",
    instructions=(
        "You help the shop owner inspect Dokan Assistant data. "
        "Use check_stock, sales_summary, and low_stock_list. "
        "Read dokan://catalog for the product catalog. "
        "Use the daily_sales_report prompt for an end-of-day style briefing. "
        "Never invent numbers — always call tools."
    ),
    version="0.1.0",
)


@mcp.tool(
    name="check_stock",
    description=(
        "Look up current stock and prices by product name, variant, or barcode. "
        "Example: School Bag, SEED-PEN-ORIG."
    ),
)
async def check_stock(query: str) -> str:
    async with mcp_session() as (session, user):
        return await tool_executors.check_stock(session, user, {"query": query})


@mcp.tool(
    name="sales_summary",
    description=(
        "Sales summary for today, week, or month: totals, bill count, payment mix, "
        "estimated profit. period must be today|week|month."
    ),
)
async def sales_summary(period: str = "today", staff_name: str | None = None) -> str:
    args: dict[str, Any] = {"period": period}
    if staff_name:
        args["staff_name"] = staff_name
    async with mcp_session() as (session, user):
        return await tool_executors.sales_summary(session, user, args)


@mcp.tool(
    name="low_stock_list",
    description="List products at or below their low-stock threshold. Optional category filter.",
)
async def low_stock_list(category: str | None = None) -> str:
    args: dict[str, Any] = {}
    if category:
        args["category"] = category
    async with mcp_session() as (session, user):
        return await tool_executors.low_stock_list(session, user, args)


@mcp.resource(
    "dokan://catalog",
    name="product_catalog",
    title="Product catalog with stock",
    description="Active products, variants, prices, and current stock.",
    mime_type="application/json",
)
async def product_catalog() -> str:
    async with mcp_session() as (session, _user):
        products = (
            await session.scalars(
                select(Product)
                .where(Product.is_active.is_(True))
                .options(selectinload(Product.variants))
                .order_by(Product.name)
                .limit(200)
            )
        ).unique().all()
        items = []
        for p in products:
            variants = []
            for v in p.variants:
                if not v.is_active:
                    continue
                stock = await get_variant_stock(session, v.id)
                variants.append(
                    {
                        "variant": v.name,
                        "barcode": v.barcode,
                        "retail_price": str(v.retail_price),
                        "dealer_price": str(v.dealer_price),
                        "current_stock": str(stock),
                        "low_stock_threshold": str(v.low_stock_threshold),
                    }
                )
            items.append(
                {
                    "product": p.name,
                    "category": p.category,
                    "tracks_expiry": p.tracks_expiry,
                    "variants": variants,
                }
            )
        return json.dumps(
            {"as_of": date.today().isoformat(), "products": items, "count": len(items)},
            ensure_ascii=False,
            indent=2,
        )


@mcp.prompt(
    name="daily_sales_report",
    title="দৈনিক বিক্রির রিপোর্ট / Daily sales report",
    description=(
        "End-of-day style briefing (like a daily SMS summary): today's sales, profit, "
        "top products, low stock, and cash/payment mix hints."
    ),
)
async def daily_sales_report() -> list[dict[str, str]]:
    today = date.today().isoformat()
    # Top-sold hint from DB for richer prompt context
    top_line = "unknown"
    try:
        async with mcp_session() as (session, _user):
            row = (
                await session.execute(
                    select(
                        Product.name,
                        ProductVariant.name,
                        func.coalesce(func.sum(SaleItem.qty), 0),
                    )
                    .join(ProductVariant, SaleItem.variant_id == ProductVariant.id)
                    .join(Product, ProductVariant.product_id == Product.id)
                    .join(Sale, SaleItem.sale_id == Sale.id)
                    .where(func.date(Sale.created_at) == date.today())
                    .group_by(Product.name, ProductVariant.name)
                    .order_by(func.coalesce(func.sum(SaleItem.qty), 0).desc())
                    .limit(1)
                )
            ).first()
            if row:
                top_line = f"{row[0]} / {row[1]} (qty {row[2]})"
    except Exception:  # noqa: BLE001
        top_line = "unavailable"

    text = f"""\
Prepare a daily store briefing for the owner (Bangla or English matching the user).

Date: {today}
Hint — today's top mover (if any): {top_line}

Required steps (call tools; do not invent numbers):
1) Call sales_summary with period="today" — total sales, bill count, cash/bkash/nagad/credit, estimated profit.
2) Call low_stock_list — list items that need reorder attention.
3) Optionally read resource dokan://catalog if useful for context.

Then write a short SMS-style summary covering:
- Today's total sales and estimated profit
- Best-selling product (use tool data; mention the hint only if tools confirm)
- Low-stock alerts
- Payment mix / cash situation note

Keep it concise (8–12 lines). If a tool returns empty, say so clearly.
"""
    return [{"role": "user", "content": text}]
