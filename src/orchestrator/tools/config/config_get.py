"""Config get tool."""

from typing import Any

from mcp.types import Tool

from ...docker_client import DockerMCPClient


def get_tool() -> Tool:
    """Get config_get tool definition."""
    return Tool(
        name="config_get",
        description="Get current MCP configuration",
        inputSchema={
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Server name (optional, for server-specific config)",
                },
            },
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
) -> dict[str, Any]:
    """
    Handle config_get tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client

    Returns:
        Configuration dictionary
    """
    server = arguments.get("server")

    config = await docker_client.config_read()

    if server:
        # Filter config for specific server if needed
        server_config = config.get(server, {})
        return {
            "server": server,
            "config": server_config,
        }
    else:
        return {"config": config}
