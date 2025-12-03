"""Docker MCP Toolkit client."""

import json
import logging
from typing import Any, Dict, List, Optional

from .models import Server, ServerMetadata, Tool
from .utils import parse_json_output, run_command

logger = logging.getLogger(__name__)


class DockerMCPClient:
    """Client for interacting with Docker MCP Toolkit."""

    def __init__(self, catalog: str = "docker-mcp", command_timeout: int = 30):
        """
        Initialize Docker MCP Client.

        Args:
            catalog: Default catalog name
            command_timeout: Command timeout in seconds
        """
        self.catalog = catalog
        self.command_timeout = command_timeout

    async def get_catalog_servers(self, catalog: Optional[str] = None) -> List[ServerMetadata]:
        """
        Get list of servers from catalog.

        Args:
            catalog: Catalog name (uses default if None)

        Returns:
            List of server metadata
        """
        catalog_name = catalog or self.catalog
        cmd = ["docker", "mcp", "catalog", "show", catalog_name, "--format=json"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            logger.error(f"Failed to get catalog servers: {stdout}")
            return []

        data = parse_json_output(stdout)
        if not data:
            return []

        servers = []
        # Parse catalog structure (structure may vary)
        if isinstance(data, dict):
            if "servers" in data:
                for server_name, server_data in data["servers"].items():
                    servers.append(self._parse_server_metadata(server_name, server_data))
            else:
                # Try to parse as flat structure
                for key, value in data.items():
                    if isinstance(value, dict):
                        servers.append(self._parse_server_metadata(key, value))

        return servers

    async def get_installed_servers(self) -> List[str]:
        """
        Get list of installed server names.

        Returns:
            List of installed server names
        """
        # Get servers from catalog (installed servers are in catalog)
        servers = await self.get_catalog_servers()
        return [s.name for s in servers]

    async def get_active_servers(self) -> List[str]:
        """
        Get list of active (enabled) servers.

        Returns:
            List of active server names
        """
        cmd = ["docker", "mcp", "server", "ls", "--json"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            logger.error(f"Failed to get active servers: {stdout}")
            return []

        data = parse_json_output(stdout)
        if not data:
            return []

        # Parse server list structure
        if isinstance(data, list):
            return [s.get("name", s) if isinstance(s, dict) else s for s in data]
        elif isinstance(data, dict):
            if "servers" in data:
                return [s.get("name", s) if isinstance(s, dict) else s for s in data["servers"]]
            elif "enabled" in data:
                return data["enabled"]

        return []

    async def enable_servers(self, servers: List[str]) -> bool:
        """
        Enable (start) servers.

        Args:
            servers: List of server names to enable

        Returns:
            True if successful, False otherwise
        """
        if not servers:
            return True

        cmd = ["docker", "mcp", "server", "enable"] + servers
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            logger.error(f"Failed to enable servers: {stdout}")
            return False

        return True

    async def disable_servers(self, servers: List[str]) -> bool:
        """
        Disable (stop) servers.

        Args:
            servers: List of server names to disable

        Returns:
            True if successful, False otherwise
        """
        if not servers:
            return True

        cmd = ["docker", "mcp", "server", "disable"] + servers
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            logger.error(f"Failed to disable servers: {stdout}")
            return False

        return True

    async def get_server_tools(self, server: str) -> List[Tool]:
        """
        Get tools from a specific server.

        Args:
            server: Server name

        Returns:
            List of tools
        """
        cmd = ["docker", "mcp", "tools", "ls", "--format=json"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            logger.error(f"Failed to get server tools: {stdout}")
            return []

        data = parse_json_output(stdout)
        if not data:
            return []

        tools = []
        # Filter tools by server
        if isinstance(data, list):
            for tool_data in data:
                if isinstance(tool_data, dict):
                    tool_server = tool_data.get("server")
                    if tool_server == server:
                        tools.append(self._parse_tool(tool_data))
        elif isinstance(data, dict):
            if "tools" in data:
                for tool_data in data["tools"]:
                    if isinstance(tool_data, dict):
                        tool_server = tool_data.get("server")
                        if tool_server == server:
                            tools.append(self._parse_tool(tool_data))

        return tools

    async def get_server_info(self, server: str) -> Optional[ServerMetadata]:
        """
        Get detailed information about a server.

        Args:
            server: Server name

        Returns:
            Server metadata or None if not found
        """
        # Try inspect command first
        cmd = ["docker", "mcp", "server", "inspect", server]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code == 0:
            data = parse_json_output(stdout)
            if data:
                return self._parse_server_metadata(server, data)

        # Fallback to catalog
        servers = await self.get_catalog_servers()
        for s in servers:
            if s.name == server:
                return s

        return None

    async def config_read(self) -> Dict[str, Any]:
        """
        Read MCP configuration.

        Returns:
            Configuration dictionary
        """
        cmd = ["docker", "mcp", "config", "read"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            logger.error(f"Failed to read config: {stdout}")
            return {}

        data = parse_json_output(stdout)
        return data if data else {}

    async def config_write(self, config: Dict[str, Any]) -> bool:
        """
        Write MCP configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if successful, False otherwise
        """
        import asyncio

        # Docker MCP config write expects input from stdin
        config_json = json.dumps(config)
        cmd = ["docker", "mcp", "config", "write"]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=config_json.encode()), timeout=self.command_timeout
            )

            if process.returncode == 0:
                return True
            else:
                logger.error(f"Failed to write config: {stderr.decode()}")
                return False
        except Exception as e:
            logger.error(f"Error writing config: {e}")
            return False

    async def secret_set(self, key: str, value: str) -> bool:
        """
        Set a secret.

        Args:
            key: Secret key
            value: Secret value

        Returns:
            True if successful, False otherwise
        """
        cmd = ["docker", "mcp", "secret", "set", f"{key}={value}"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            logger.error(f"Failed to set secret: {stdout}")
            return False

        return True

    async def secret_list(self) -> List[str]:
        """
        List all secrets.

        Returns:
            List of secret keys
        """
        cmd = ["docker", "mcp", "secret", "ls", "--json"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            logger.error(f"Failed to list secrets: {stdout}")
            return []

        data = parse_json_output(stdout)
        if not data:
            return []

        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "secrets" in data:
            return data["secrets"]

        return []

    async def secret_remove(self, key: str) -> bool:
        """
        Remove a secret.

        Args:
            key: Secret key to remove

        Returns:
            True if successful, False otherwise
        """
        cmd = ["docker", "mcp", "secret", "rm", key]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            logger.error(f"Failed to remove secret: {stdout}")
            return False

        return True

    def _parse_server_metadata(self, name: str, data: Dict[str, Any]) -> ServerMetadata:
        """Parse server metadata from catalog data."""
        return ServerMetadata(
            name=name,
            description=data.get("description"),
            version=data.get("version"),
            keywords=data.get("keywords", []),
            tools_count=data.get("tools_count", 0),
            tools_preview=data.get("tools_preview", []),
            catalog_source=data.get("catalog_source"),
            prompt=data.get("prompt"),
            config_requirements=data.get("config_requirements", {}),
        )

    def _parse_tool(self, data: Dict[str, Any]) -> Tool:
        """Parse tool from data."""
        return Tool(
            name=data.get("name", ""),
            description=data.get("description"),
            inputSchema=data.get("inputSchema"),
        )


