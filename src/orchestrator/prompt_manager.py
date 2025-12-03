"""Prompt manager for MCP servers."""

import logging
from typing import Dict, List, Optional

from .cache import MetadataCache
from .docker_client import DockerMCPClient

logger = logging.getLogger(__name__)


class PromptManager:
    """Manager for server prompts."""

    def __init__(self, cache: MetadataCache, docker_client: DockerMCPClient):
        """
        Initialize prompt manager.

        Args:
            cache: MetadataCache instance
            docker_client: DockerMCPClient instance
        """
        self._cache = cache
        self._docker_client = docker_client

    async def get_server_prompt(self, server: str) -> Optional[str]:
        """
        Get prompt for a server.

        Args:
            server: Server name

        Returns:
            Prompt string or None if not available
        """
        async def fetch_prompt():
            metadata = await self._docker_client.get_server_info(server)
            if metadata and metadata.prompt:
                return metadata.prompt
            return None

        prompt = await self._cache.get_server_prompt(server, fetch_prompt)
        return prompt

    async def get_prompts_for_servers(self, servers: List[str]) -> Dict[str, str]:
        """
        Get prompts for multiple servers.

        Args:
            servers: List of server names

        Returns:
            Dictionary mapping server names to their prompts
        """
        prompts = {}
        for server in servers:
            prompt = await self.get_server_prompt(server)
            if prompt:
                prompts[server] = prompt
                logger.debug(f"Found prompt for server {server}")
            else:
                logger.debug(f"No prompt found for server {server}")

        return prompts
