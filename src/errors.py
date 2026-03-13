"""Exception hierarchy for rocketride-reviewer.

All project exceptions inherit from BaseReviewerError. Use specific
exceptions — never catch bare Exception outside of main.py's top-level handler.
"""

from __future__ import annotations


class BaseReviewerError(Exception):
    """Base exception for all rocketride-reviewer errors."""


class ConfigurationError(BaseReviewerError):
    """Invalid configuration or missing secrets."""


class EngineError(BaseReviewerError):
    """RocketRide engine startup or connection failure."""


class PipelineError(BaseReviewerError):
    """Pipeline execution failure."""


class AgentError(PipelineError):
    """Individual agent failure during pipeline execution.

    Attributes:
        agent_name: Name of the agent that failed.
    """

    def __init__(self, message: str, agent_name: str) -> None:
        super().__init__(message)
        self.agent_name = agent_name


class AggregatorError(PipelineError):
    """Aggregator failure during deduplication."""


class GitHubClientError(BaseReviewerError):
    """GitHub API interaction failure."""


class DiffRetrievalError(GitHubClientError):
    """Failed to fetch PR diff."""


class CommentPostingError(GitHubClientError):
    """Failed to post a comment on a PR."""


class ReviewSubmissionError(GitHubClientError):
    """Failed to submit a review status."""


class FilterError(BaseReviewerError):
    """File filtering configuration error."""


class ChunkingError(BaseReviewerError):
    """Diff chunking failure (split, overlap, or remap)."""
