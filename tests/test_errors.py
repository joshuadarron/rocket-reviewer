"""Tests for the exception hierarchy."""

from __future__ import annotations

from src.errors import (
    AgentError,
    AggregatorError,
    BaseReviewerError,
    ChunkingError,
    CommentPostingError,
    ConfigurationError,
    DiffRetrievalError,
    EngineError,
    FilterError,
    GitHubClientError,
    PipelineError,
    ReviewSubmissionError,
)


class TestExceptionHierarchy:
    """Verify all exceptions inherit correctly from BaseReviewerError."""

    def test_base_error_is_exception(self) -> None:
        assert issubclass(BaseReviewerError, Exception)

    def test_configuration_error(self) -> None:
        err = ConfigurationError("missing key")
        assert isinstance(err, BaseReviewerError)
        assert str(err) == "missing key"

    def test_engine_error(self) -> None:
        assert issubclass(EngineError, BaseReviewerError)

    def test_pipeline_error_hierarchy(self) -> None:
        assert issubclass(AgentError, PipelineError)
        assert issubclass(AggregatorError, PipelineError)
        assert issubclass(PipelineError, BaseReviewerError)

    def test_agent_error_has_agent_name(self) -> None:
        err = AgentError("timeout", agent_name="gpt-reviewer")
        assert err.agent_name == "gpt-reviewer"
        assert isinstance(err, PipelineError)

    def test_github_client_error_hierarchy(self) -> None:
        assert issubclass(DiffRetrievalError, GitHubClientError)
        assert issubclass(CommentPostingError, GitHubClientError)
        assert issubclass(ReviewSubmissionError, GitHubClientError)
        assert issubclass(GitHubClientError, BaseReviewerError)

    def test_filter_error(self) -> None:
        assert issubclass(FilterError, BaseReviewerError)

    def test_chunking_error(self) -> None:
        assert issubclass(ChunkingError, BaseReviewerError)
