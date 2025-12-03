"""Get active servers tool."""

from typing import Any

from mcp.types import Tool

from ...docker_client import DockerMCPClient
from ...proxy import ToolProxy


def get_tool() -> Tool:
    """Get get_active_servers tool definition."""
    return Tool(
        name="get_active_servers",
        description="Get list of currently active (running) MCP servers",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
    proxy: ToolProxy,
) -> dict[str, Any]:
    """
    Handle get_active_servers tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client
        proxy: Tool proxy

    Returns:
        Dictionary with active servers and their tools
    """
    # Get active servers from Docker MCP Toolkit
    active_servers = await docker_client.get_active_servers()

    # Also get servers registered in proxy
    proxy_servers = proxy.list_servers()

    # Combine and deduplicate
    all_active = list(set(active_servers + proxy_servers))

    # Get tools for each server
    result = {
        "servers": all_active,
        "servers_detail": [],
    }

    for server in all_active:
        tools = proxy.get_server_tools(server)
        result["servers_detail"].append(
            {
                "name": server,
                "tools_count": len(tools),
                "tools": [tool.name for tool in tools],
            }
        )

    return result
