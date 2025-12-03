"""Call tool through proxy."""

from typing import Any

from mcp.types import Tool

from ...models import CallToolResult
from ...proxy import ToolProxy


def get_tool() -> Tool:
    """Get call_tool tool definition."""
    return Tool(
        name="call_tool",
        description="Call a tool from an active MCP server through Orchestrator proxy. This is the ONLY way to call tools from started servers.",
        inputSchema={
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "Name of the tool to call",
                },
                "arguments": {
                    "type": "object",
                    "description": "Tool arguments (key-value pairs)",
                },
            },
            "required": ["tool_name", "arguments"],
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    proxy: ToolProxy,
) -> dict[str, Any]:
    """
    Handle call_tool tool call.

    Args:
        arguments: Tool arguments
        proxy: Tool proxy

    Returns:
        CallToolResult as dictionary
    """
    tool_name = arguments.get("tool_name")
    tool_arguments = arguments.get("arguments", {})

    if not tool_name:
        return {
            "status": "error",
            "error": "tool_name is required",
            "result": None,
            "server": None,
        }

    # Get server for tool
    server = proxy.get_server_for_tool(tool_name)
    if not server:
        return {
            "status": "error",
            "error": f"Tool {tool_name} not found in any active server. Make sure the server is started.",
            "result": None,
            "server": None,
        }

    # Call tool through proxy
    result, error = await proxy.call_tool(tool_name, tool_arguments)

    if error:
        return {
            "status": "error",
            "error": error,
            "result": None,
            "server": server,
        }
    else:
        return {
            "status": "success",
            "result": result,
            "error": None,
            "server": server,
        }
