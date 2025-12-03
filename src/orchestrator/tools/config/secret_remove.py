"""Secret remove tool."""

from typing import Any

from mcp.types import Tool

from ...docker_client import DockerMCPClient


def get_tool() -> Tool:
    """Get secret_remove tool definition."""
    return Tool(
        name="secret_remove",
        description="Remove a secret",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Secret key name to remove",
                },
            },
            "required": ["key"],
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
) -> dict[str, Any]:
    """
    Handle secret_remove tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client

    Returns:
        Result dictionary
    """
    key = arguments.get("key")

    if not key:
        return {"status": "error", "error": "Key is required"}

    success = await docker_client.secret_remove(key)

    if success:
        return {
            "status": "success",
            "key": key,
        }
    else:
        return {
            "status": "error",
            "error": "Failed to remove secret",
        }
