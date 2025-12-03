"""Metadata cache manager."""

import logging
from typing import Any, Dict, Optional

from .models import CachedItem, ServerMetadata, Tool

logger = logging.getLogger(__name__)


class MetadataCache:
    """Cache manager for server metadata and tools."""

    def __init__(
        self,
        servers_ttl: int = 300,
        tools_ttl: int = 600,
        prompts_ttl: int = 0,  # 0 = never expire
    ):
        """
        Initialize cache manager.

        Args:
            servers_ttl: TTL for servers cache in seconds
            tools_ttl: TTL for tools cache in seconds
            prompts_ttl: TTL for prompts cache in seconds (0 = permanent)
        """
        self.servers_ttl = servers_ttl
        self.tools_ttl = tools_ttl
        self.prompts_ttl = prompts_ttl

        self._servers_cache: Dict[str, CachedItem] = {}
        self._tools_cache: Dict[str, CachedItem] = {}
        self._prompts_cache: Dict[str, CachedItem] = {}
        self._server_metadata_cache: Dict[str, CachedItem] = {}

    async def get_servers(self, catalog: str, fetch_func) -> list[ServerMetadata]:
        """
        Get cached servers or fetch if expired.

        Args:
            catalog: Catalog name
            fetch_func: Async function to fetch servers if cache expired

        Returns:
            List of server metadata
        """
        cache_key = f"catalog:{catalog}"
        cached = self._servers_cache.get(cache_key)

        if cached and not cached.is_expired():
            logger.debug(f"Cache hit for servers: {cache_key}")
            return cached.data

        logger.debug(f"Cache miss for servers: {cache_key}, fetching...")
        servers = await fetch_func()
        self._servers_cache[cache_key] = CachedItem(data=servers, ttl=self.servers_ttl)
        return servers

    async def get_server_metadata(self, server: str, fetch_func) -> Optional[ServerMetadata]:
        """
        Get cached server metadata or fetch if expired.

        Args:
            server: Server name
            fetch_func: Async function to fetch metadata if cache expired

        Returns:
            Server metadata or None
        """
        cached = self._server_metadata_cache.get(server)

        if cached and not cached.is_expired():
            logger.debug(f"Cache hit for server metadata: {server}")
            return cached.data

        logger.debug(f"Cache miss for server metadata: {server}, fetching...")
        metadata = await fetch_func()
        if metadata:
            self._server_metadata_cache[server] = CachedItem(
                data=metadata, ttl=self.servers_ttl
            )
        return metadata

    async def get_server_tools(self, server: str, fetch_func) -> list[Tool]:
        """
        Get cached server tools or fetch if expired.

        Args:
            server: Server name
            fetch_func: Async function to fetch tools if cache expired

        Returns:
            List of tools
        """
        cached = self._tools_cache.get(server)

        if cached and not cached.is_expired():
            logger.debug(f"Cache hit for server tools: {server}")
            return cached.data

        logger.debug(f"Cache miss for server tools: {server}, fetching...")
        tools = await fetch_func()
        self._tools_cache[server] = CachedItem(data=tools, ttl=self.tools_ttl)
        return tools

    async def get_server_prompt(self, server: str, fetch_func) -> Optional[str]:
        """
        Get cached server prompt or fetch if expired.

        Args:
            server: Server name
            fetch_func: Async function to fetch prompt if cache expired

        Returns:
            Prompt string or None
        """
        cached = self._prompts_cache.get(server)

        if cached and (self.prompts_ttl == 0 or not cached.is_expired()):
            logger.debug(f"Cache hit for server prompt: {server}")
            return cached.data

        logger.debug(f"Cache miss for server prompt: {server}, fetching...")
        prompt = await fetch_func()
        if prompt:
            self._prompts_cache[server] = CachedItem(data=prompt, ttl=self.prompts_ttl)
        return prompt

    def invalidate_servers(self, catalog: Optional[str] = None):
        """
        Invalidate servers cache.

        Args:
            catalog: Specific catalog to invalidate, or None for all
        """
        if catalog:
            cache_key = f"catalog:{catalog}"
            self._servers_cache.pop(cache_key, None)
        else:
            self._servers_cache.clear()

    def invalidate_server(self, server: str):
        """
        Invalidate cache for a specific server.

        Args:
            server: Server name
        """
        self._server_metadata_cache.pop(server, None)
        self._tools_cache.pop(server, None)
        self._prompts_cache.pop(server, None)

    def clear(self):
        """Clear all caches."""
        self._servers_cache.clear()
        self._tools_cache.clear()
        self._prompts_cache.clear()
        self._server_metadata_cache.clear()
