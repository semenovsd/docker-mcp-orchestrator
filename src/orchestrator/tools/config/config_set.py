"""Config set tool."""

from typing import Any

from mcp.types import Tool

from ...docker_client import DockerMCPClient


def get_tool() -> Tool:
    """Get config_set tool definition."""
    return Tool(
        name="config_set",
        description="Set configuration for MCP servers (e.g., database URLs, API endpoints)",
        inputSchema={
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Server name (optional, for server-specific config)",
                },
                "config": {
                    "type": "object",
                    "description": "Configuration dictionary (key-value pairs)",
                },
            },
            "required": ["config"],
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
) -> dict[str, Any]:
    """
    Handle config_set tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client

    Returns:
        Result dictionary
    """
    config = arguments.get("config", {})
    server = arguments.get("server")

    if not config:
        return {"status": "error", "error": "Config is required"}

    # Note: Docker MCP config write may need server-specific handling
    # For now, we'll write to global config
    success = await docker_client.config_write(config)

    if success:
        return {
            "status": "success",
            "server": server,
            "config": config,
        }
    else:
        return {
            "status": "error",
            "error": "Failed to write configuration",
        }
