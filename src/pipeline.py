"""Pipeline execution for full review and conversation modes.

Loads pipeline JSON, starts pipelines via the RocketRide SDK, sends
diff data, and receives structured agent responses.
"""

from __future__ import annotations


class PipelineRunner:
    """Executes RocketRide pipelines and collects agent responses."""

    async def run_full_review(self, diff: str) -> list[dict[str, object]]:
        """Run the full 3-agent parallel review pipeline."""
        raise NotImplementedError

    async def run_conversation_reply(
        self,
        agent_node_id: str,
        thread_context: str,
    ) -> dict[str, object]:
        """Run the single-agent conversation reply pipeline."""
        raise NotImplementedError
