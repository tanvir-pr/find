"""Run Dokan Assistant MCP over stdio (Claude Desktop / local clients).

Claude Desktop example (claude_desktop_config.json):
{
  "mcpServers": {
    "dokan-assistant": {
      "command": "uv",
      "args": ["run", "python", "scripts/run_mcp_stdio.py"],
      "cwd": "D:/phitron project 1/backend"
    }
  }
}
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.mcp.server import mcp


def main() -> None:
    asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
