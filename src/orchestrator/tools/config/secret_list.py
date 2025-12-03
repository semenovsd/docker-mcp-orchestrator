"""Secret list tool."""

from typing import Any

from mcp.types import Tool

from ...docker_client import DockerMCPClient


def get_tool() -> Tool:
    """Get secret_list tool definition."""
    return Tool(
        name="secret_list",
        description="List all configured secrets (keys only, not values)",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
) -> dict[str, Any]:
    """
    Handle secret_list tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client

    Returns:
        Dictionary with list of secret keys
    """
    secrets = await docker_client.secret_list()

    return {
        "secrets": secrets,
        "count": len(secrets),
    }
