# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-03

### Added
- Initial release
- Core orchestration tools:
  - `list_available_servers()` - Server catalog with descriptions
  - `activate_server(name, reason)` - Enable MCP server on-demand
  - `deactivate_server(name)` - Disable MCP server
  - `activate_for_task(description)` - Auto-detect servers for task
  - `get_active_servers()` - List active servers with tools
  - `deactivate_all()` - Disable all servers
  - `server_info(name)` - Detailed server information
  - `sync_state()` - Sync with Docker MCP Toolkit
- Support for 8 Docker MCP Toolkit servers:
  - context7 (documentation)
  - playwright (browser automation)
  - github (GitHub integration)
  - fetch (HTTP client)
  - desktop-commander (file system)
  - postgres (PostgreSQL)
  - redis (Redis)
  - sequential-thinking (reasoning)
- English and Russian documentation
- Cursor and Claude Desktop configuration examples
- Unit tests with pytest
- CC BY-NC 4.0 license

### Performance
- Reduces token usage by 90%+ compared to loading all MCP tools
- Typical context: 500-2,000 tokens vs 15,000-20,000 tokens

## [Unreleased]

### Planned
- Support for additional MCP servers
- Configuration file for custom server registry
- GUI for server management
- Integration with more MCP clients
