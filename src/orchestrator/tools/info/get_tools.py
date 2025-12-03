"""Get server tools tool."""

from typing import Any

from mcp.types import Tool

from ...cache import MetadataCache
from ...docker_client import DockerMCPClient


def get_tool() -> Tool:
    """Get get_server_tools tool definition."""
    return Tool(
        name="get_server_tools",
        description="Get list of tools provided by a specific MCP server (metadata only, server doesn't need to be running)",
        inputSchema={
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Server name",
                }
            },
            "required": ["server"],
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
    cache: MetadataCache,
) -> dict[str, Any]:
    """
    Handle get_server_tools tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client
        cache: Metadata cache

    Returns:
        Dictionary with server tools
    """
    server = arguments.get("server")
    if not server:
        return {"error": "Server name is required"}

    async def fetch_tools():
        return await docker_client.get_server_tools(server)

    tools = await cache.get_server_tools(server, fetch_tools)

    return {
        "server": server,
        "tools_count": len(tools),
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            }
            for tool in tools
        ],
    }
