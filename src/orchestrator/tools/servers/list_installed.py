"""List installed servers tool."""

from typing import Any

from mcp.types import Tool

from ...cache import MetadataCache
from ...docker_client import DockerMCPClient


def get_tool() -> Tool:
    """Get list_installed_servers tool definition."""
    return Tool(
        name="list_installed_servers",
        description="Get list of installed MCP servers from Docker MCP Catalog",
        inputSchema={
            "type": "object",
            "properties": {
                "catalog": {
                    "type": "string",
                    "description": "Catalog name (default: docker-mcp)",
                    "default": "docker-mcp",
                }
            },
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
    cache: MetadataCache,
) -> list[dict[str, Any]]:
    """
    Handle list_installed_servers tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client
        cache: Metadata cache

    Returns:
        List of installed servers with metadata
    """
    catalog = arguments.get("catalog", "docker-mcp")

    async def fetch_servers():
        return await docker_client.get_catalog_servers(catalog)

    servers = await cache.get_servers(catalog, fetch_servers)

    result = []
    for server in servers:
        result.append(
            {
                "name": server.name,
                "description": server.description,
                "version": server.version,
                "keywords": server.keywords,
                "tools_count": server.tools_count,
                "tools_preview": server.tools_preview[:10],  # Limit preview
            }
        )

    return result
