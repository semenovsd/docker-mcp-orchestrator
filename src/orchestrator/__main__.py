"""Entry point for Orchestrator."""

import asyncio
import logging
import sys
from pathlib import Path

from .server import OrchestratorServer


def setup_logging(config: dict):
    """Setup logging from config."""
    log_config = config.get("orchestrator", {}).get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO").upper())
    format_str = log_config.get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logging.basicConfig(level=level, format=format_str)


async def main():
    """Main entry point."""
    # Determine config path
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"

    # Create server (will load config)
    server = OrchestratorServer(str(config_path))

    # Setup logging
    setup_logging(server.config)

    # Run server
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
