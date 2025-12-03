"""List catalog servers tool."""

from typing import Any

from mcp.types import Tool

from ...cache import MetadataCache
from ...docker_client import DockerMCPClient


def get_tool() -> Tool:
    """Get list_catalog_servers tool definition."""
    return Tool(
        name="list_catalog_servers",
        description="Get list of all available servers in Docker MCP Catalog (for installation)",
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
    Handle list_catalog_servers tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client
        cache: Metadata cache

    Returns:
        List of all servers in catalog
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
                "catalog_source": server.catalog_source,
            }
        )

    return result
