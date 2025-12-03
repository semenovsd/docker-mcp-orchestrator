"""Get server info tool."""

from typing import Any

from mcp.types import Tool

from ...cache import MetadataCache
from ...docker_client import DockerMCPClient


def get_tool() -> Tool:
    """Get get_server_info tool definition."""
    return Tool(
        name="get_server_info",
        description="Get detailed information about a specific MCP server including description, requirements, and configuration",
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
    Handle get_server_info tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client
        cache: Metadata cache

    Returns:
        Dictionary with server information
    """
    server = arguments.get("server")
    if not server:
        return {"error": "Server name is required"}

    async def fetch_info():
        return await docker_client.get_server_info(server)

    metadata = await cache.get_server_metadata(server, fetch_info)

    if not metadata:
        return {"error": f"Server {server} not found"}

    return {
        "name": metadata.name,
        "description": metadata.description,
        "version": metadata.version,
        "keywords": metadata.keywords,
        "tools_count": metadata.tools_count,
        "tools_preview": metadata.tools_preview,
        "catalog_source": metadata.catalog_source,
        "has_prompt": metadata.prompt is not None,
        "config_requirements": metadata.config_requirements,
    }
