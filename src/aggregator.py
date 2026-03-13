"""Post-processing: parse agent output, deduplicate, and route to posting.

Receives combined output from all reviewer agents, runs the Claude
aggregator for deduplication, and produces per-agent review payloads.
"""

from __future__ import annotations

from src.models import AgentReview


async def deduplicate_reviews(
    agent_reviews: list[AgentReview],
) -> list[AgentReview]:
    """Deduplicate overlapping comments across agent reviews.

    Uses the Claude aggregator to identify and remove duplicate comments
    (same file + 3-line window + same semantic intent) across agents.

    Args:
        agent_reviews: List of reviews from all agents.

    Returns:
        Deduplicated list of agent reviews.
    """
    raise NotImplementedError
