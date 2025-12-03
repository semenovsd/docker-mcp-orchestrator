"""Secret set tool."""

from typing import Any

from mcp.types import Tool

from ...docker_client import DockerMCPClient


def get_tool() -> Tool:
    """Get secret_set tool definition."""
    return Tool(
        name="secret_set",
        description="Set a secret (e.g., API keys, passwords) for MCP servers",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Secret key name",
                },
                "value": {
                    "type": "string",
                    "description": "Secret value",
                },
            },
            "required": ["key", "value"],
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
) -> dict[str, Any]:
    """
    Handle secret_set tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client

    Returns:
        Result dictionary
    """
    key = arguments.get("key")
    value = arguments.get("value")

    if not key or not value:
        return {"status": "error", "error": "Key and value are required"}

    success = await docker_client.secret_set(key, value)

    if success:
        return {
            "status": "success",
            "key": key,
        }
    else:
        return {
            "status": "error",
            "error": "Failed to set secret",
        }
