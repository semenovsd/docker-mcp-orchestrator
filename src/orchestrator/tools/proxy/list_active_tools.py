"""List active tools tool."""

from typing import Any

from mcp.types import Tool

from ...proxy import ToolProxy


def get_tool() -> Tool:
    """Get list_active_tools tool definition."""
    return Tool(
        name="list_active_tools",
        description="Get list of all available tools from all active MCP servers",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    proxy: ToolProxy,
) -> dict[str, Any]:
    """
    Handle list_active_tools tool call.

    Args:
        arguments: Tool arguments
        proxy: Tool proxy

    Returns:
        Dictionary with active tools grouped by server
    """
    all_tools = proxy.list_active_tools()
    servers = proxy.list_servers()

    # Group tools by server
    tools_by_server = {}
    for server in servers:
        server_tools = proxy.get_server_tools(server)
        tools_by_server[server] = [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            }
            for tool in server_tools
        ]

    return {
        "total_tools": len(all_tools),
        "servers": servers,
        "tools_by_server": tools_by_server,
        "all_tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "server": proxy.get_server_for_tool(tool.name),
            }
            for tool in all_tools
        ],
    }
