"""Minimal MCP server exposing the novomcp-lite tools.

Requires the optional `mcp` dependency:  pip install "novomcp-lite[mcp]"

Run it over stdio (the default local MCP transport):

    novomcp-lite            # console script
    python -m novomcp_tools.server

Point any MCP client (Claude Desktop, an agent, etc.) at that command and the
eight tools appear. The tool logic is identical to the library API.
"""
from __future__ import annotations

import json

from .registry import call_tool, list_tools


def build_server():
    """Construct the MCP Server wired to the lite tool registry."""
    try:
        from mcp.server import Server
        import mcp.types as types
    except ImportError as e:  # pragma: no cover
        raise SystemExit(
            "The MCP server needs the optional 'mcp' dependency:\n"
            '    pip install "novomcp-lite[mcp]"'
        ) from e

    server = Server("novomcp-lite")

    @server.list_tools()
    async def _list():  # type: ignore[no-untyped-def]
        return [
            types.Tool(name=t["name"], description=t["description"], inputSchema=t["input_schema"])
            for t in list_tools()
        ]

    @server.call_tool()
    async def _call(name: str, arguments: dict):  # type: ignore[no-untyped-def]
        result = await call_tool(name, arguments or {})
        payload = result.data if result.success else {"error": result.error}
        return [types.TextContent(type="text", text=json.dumps(payload, default=str))]

    return server


def main() -> None:
    """Run the MCP server over stdio."""
    import anyio
    from mcp.server.stdio import stdio_server

    server = build_server()

    async def _run() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    anyio.run(_run)


if __name__ == "__main__":
    main()
