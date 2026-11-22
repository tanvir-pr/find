"""Step 10 smoke: MCP tools/resource/prompt + HTTP API-key gate."""

from __future__ import annotations

import asyncio
import json

from app.core.config import settings
from app.main import app
from app.mcp.server import mcp


async def test_mcp_surface() -> None:
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names >= {"check_stock", "sales_summary", "low_stock_list"}, names
    print("ok tools", sorted(names))

    stock = await mcp.call_tool("check_stock", {"query": "School Bag"})
    assert stock.is_error is False, stock
    text = stock.content[0].text  # type: ignore[index]
    payload = json.loads(text)
    assert payload["count"] >= 1, payload
    print("ok check_stock", payload["count"])

    sales = await mcp.call_tool("sales_summary", {"period": "month"})
    assert sales.is_error is False, sales
    sales_body = json.loads(sales.content[0].text)  # type: ignore[index]
    assert "bill_count" in sales_body, sales_body
    print("ok sales_summary bills", sales_body["bill_count"])

    low = await mcp.call_tool("low_stock_list", {})
    assert low.is_error is False, low
    print("ok low_stock_list")

    resources = await mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "dokan://catalog" in uris, uris
    catalog = await mcp.read_resource("dokan://catalog")
    cat_text = catalog[0].content
    cat = json.loads(cat_text if isinstance(cat_text, str) else cat_text.decode())
    assert cat["count"] >= 1, cat
    print("ok resource catalog", cat["count"])

    prompts = await mcp.list_prompts()
    pnames = {p.name for p in prompts}
    assert "daily_sales_report" in pnames, pnames
    prompt = await mcp.get_prompt("daily_sales_report")
    assert prompt.messages, prompt
    print("ok prompt daily_sales_report")


def test_http_auth() -> None:
    # TestClient runs FastAPI lifespan (MCP session_manager).
    from starlette.testclient import TestClient

    with TestClient(app) as client:
        denied = client.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
        assert denied.status_code == 401, denied.text
        print("ok http 401 without key")

        headers = {"Authorization": f"Bearer {settings.MCP_API_KEY}"}
        init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "step10-test", "version": "0.1"},
            },
        }
        ok = client.post("/mcp/", headers=headers, json=init)
        assert ok.status_code in (200, 202), (ok.status_code, ok.text[:500])
        print("ok http initialize", ok.status_code)

        root = client.get("/")
        assert root.json().get("mcp") == "/mcp/"
        print("ok root lists /mcp")


async def main() -> None:
    await test_mcp_surface()
    test_http_auth()
    print("step10 smoke OK")


if __name__ == "__main__":
    asyncio.run(main())
