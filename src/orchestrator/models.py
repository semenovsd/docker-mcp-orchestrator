"""Data models for Orchestrator."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServerStatus(str, Enum):
    """Server status enumeration."""

    INSTALLED = "installed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class Tool(BaseModel):
    """MCP Tool model."""

    name: str = Field(..., description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    inputSchema: Optional[Dict[str, Any]] = Field(None, description="Tool input schema")


class ServerPrompt(BaseModel):
    """Server prompt model."""

    content: str = Field(..., description="Prompt content")
    server: str = Field(..., description="Server name")


class ServerConfig(BaseModel):
    """Server configuration model."""

    server: str = Field(..., description="Server name")
    config: Dict[str, Any] = Field(default_factory=dict, description="Configuration dictionary")


class ServerMetadata(BaseModel):
    """Server metadata model."""

    name: str = Field(..., description="Server name")
    description: Optional[str] = Field(None, description="Server description")
    version: Optional[str] = Field(None, description="Server version")
    keywords: List[str] = Field(default_factory=list, description="Server keywords")
    tools_count: int = Field(0, description="Number of tools")
    tools_preview: List[str] = Field(default_factory=list, description="Preview of tool names")
    catalog_source: Optional[str] = Field(None, description="Catalog source")
    prompt: Optional[str] = Field(None, description="Server prompt")
    config_requirements: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration requirements"
    )


class Server(BaseModel):
    """Server model."""

    name: str = Field(..., description="Server name")
    status: ServerStatus = Field(ServerStatus.INSTALLED, description="Server status")
    metadata: Optional[ServerMetadata] = Field(None, description="Server metadata")
    tools: List[Tool] = Field(default_factory=list, description="Server tools")
    active_since: Optional[datetime] = Field(None, description="When server was activated")
    error: Optional[str] = Field(None, description="Error message if status is ERROR")


class CachedItem(BaseModel):
    """Cached item model."""

    data: Any = Field(..., description="Cached data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Cache timestamp")
    ttl: int = Field(300, description="Time to live in seconds")

    def is_expired(self) -> bool:
        """Check if cache item is expired."""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl


class StartServersResult(BaseModel):
    """Result of starting servers."""

    status: str = Field(..., description="Status: success or error")
    servers: List[str] = Field(default_factory=list, description="List of server names")
    tools: List[Tool] = Field(default_factory=list, description="List of available tools")
    prompts: Dict[str, str] = Field(
        default_factory=dict, description="Server prompts by server name"
    )
    errors: Dict[str, str] = Field(
        default_factory=dict, description="Errors by server name if any"
    )


class CallToolResult(BaseModel):
    """Result of calling a tool."""

    status: str = Field(..., description="Status: success or error")
    result: Optional[Any] = Field(None, description="Tool result if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    server: Optional[str] = Field(None, description="Server that executed the tool")
