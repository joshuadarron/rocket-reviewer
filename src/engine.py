"""RocketRide engine lifecycle management.

Handles starting the Docker container, health check polling, SDK
connection, and teardown. Exposed as an async context manager.
"""

from __future__ import annotations


class EngineManager:
    """Manages the RocketRide engine Docker container lifecycle."""

    async def start(self) -> None:
        """Start the RocketRide engine Docker container."""
        raise NotImplementedError

    async def wait_for_healthy(self) -> None:
        """Poll the engine health endpoint until ready or timeout."""
        raise NotImplementedError

    async def stop(self) -> None:
        """Stop and remove the Docker container."""
        raise NotImplementedError
