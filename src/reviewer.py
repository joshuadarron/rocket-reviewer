"""Review posting logic per GitHub App identity.

Takes deduplicated agent reviews and posts each agent's comments under
its own GitHub App identity. Handles review status submission based on
comment severities.
"""

from __future__ import annotations

from src.models import AgentReview


async def post_agent_review(review: AgentReview) -> None:
    """Post a single agent's review comments and submit review status.

    Args:
        review: The agent's deduplicated review to post.
    """
    raise NotImplementedError
