"""Post-processing: deduplicate overlapping comments across agent reviews.

Uses heuristic matching (same file, nearby line, text similarity) to remove
duplicate comments when multiple agents flag the same issue. Keeps the
longer/more specific version of each duplicate pair.
"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from itertools import combinations

from src.models import AgentReview, ReviewComment

logger = logging.getLogger(__name__)

# Deduplication thresholds
LINE_WINDOW: int = 3
SIMILARITY_THRESHOLD: float = 0.6


def _is_duplicate(a: ReviewComment, b: ReviewComment) -> bool:
    """Check whether two comments are duplicates.

    Two comments are considered duplicates when they target the same file,
    their line numbers are within ``LINE_WINDOW``, and the body text
    similarity meets or exceeds ``SIMILARITY_THRESHOLD``.

    Args:
        a: First comment.
        b: Second comment.

    Returns:
        True if the comments are duplicates.
    """
    if a.file != b.file:
        return False

    if abs(a.line - b.line) > LINE_WINDOW:
        return False

    ratio = SequenceMatcher(None, a.body, b.body).ratio()
    return ratio >= SIMILARITY_THRESHOLD


def deduplicate_reviews(
    agent_reviews: list[AgentReview],
) -> list[AgentReview]:
    """Deduplicate overlapping comments across agent reviews.

    Compares comments across every pair of agents. When duplicates are
    found, the shorter comment is marked for removal (the longer/more
    specific one is kept). If both are the same length, the one from the
    later agent in the list is removed.

    Args:
        agent_reviews: List of reviews from all agents.

    Returns:
        New list of AgentReview objects with duplicate comments removed.
    """
    if len(agent_reviews) <= 1:
        return agent_reviews

    # Build removal set: (agent_index, comment_index)
    removals: set[tuple[int, int]] = set()

    for (i, review_a), (j, review_b) in combinations(enumerate(agent_reviews), 2):
        for ci, comment_a in enumerate(review_a.comments):
            if (i, ci) in removals:
                continue
            for cj, comment_b in enumerate(review_b.comments):
                if (j, cj) in removals:
                    continue
                if _is_duplicate(comment_a, comment_b):
                    # Keep the longer body; on tie, keep the earlier agent's
                    if len(comment_b.body) > len(comment_a.body):
                        removals.add((i, ci))
                        logger.debug(
                            "Removing duplicate from %s (keeping %s): %s:%d",
                            review_a.reviewer,
                            review_b.reviewer,
                            comment_a.file,
                            comment_a.line,
                        )
                    else:
                        removals.add((j, cj))
                        logger.debug(
                            "Removing duplicate from %s (keeping %s): %s:%d",
                            review_b.reviewer,
                            review_a.reviewer,
                            comment_b.file,
                            comment_b.line,
                        )

    # Reconstruct clean reviews
    result: list[AgentReview] = []
    for agent_idx, review in enumerate(agent_reviews):
        kept_comments = [
            c
            for comment_idx, c in enumerate(review.comments)
            if (agent_idx, comment_idx) not in removals
        ]
        result.append(AgentReview(reviewer=review.reviewer, comments=kept_comments))

    total_removed = len(removals)
    if total_removed > 0:
        logger.info("Deduplication removed %d duplicate comment(s)", total_removed)

    return result
