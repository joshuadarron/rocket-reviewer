"""Tests for gating logic, orchestration, and multi-agent approval."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import (
    _build_agent_failure_message,
    _determine_cross_agent_statuses,
    _extract_changed_files,
    _initialize_agents,
    run,
    should_run,
)
from src.models import AgentReview, ReviewComment, ReviewConfig, Severity


@pytest.fixture()
def default_config() -> ReviewConfig:
    return ReviewConfig()


@pytest.fixture()
def pr_opened_event() -> dict[str, object]:
    return {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "base": {"ref": "main"},
            "head": {"sha": "abc123"},
            "user": {"login": "developer"},
        },
        "repository": {"full_name": "owner/repo"},
    }


@pytest.fixture()
def pr_sync_event() -> dict[str, object]:
    return {
        "action": "synchronize",
        "pull_request": {
            "number": 42,
            "base": {"ref": "main"},
            "head": {"sha": "def456"},
            "user": {"login": "developer"},
        },
        "repository": {"full_name": "owner/repo"},
    }


class TestShouldRun:
    """Tests for gating logic."""

    def test_pr_opened_on_main(
        self, pr_opened_event: dict[str, object], default_config: ReviewConfig
    ) -> None:
        assert should_run(pr_opened_event, "pull_request", default_config)

    def test_pr_synchronize_on_main(
        self, pr_sync_event: dict[str, object], default_config: ReviewConfig
    ) -> None:
        assert should_run(pr_sync_event, "pull_request", default_config)

    def test_wrong_event_type(
        self, pr_opened_event: dict[str, object], default_config: ReviewConfig
    ) -> None:
        assert not should_run(pr_opened_event, "issue_comment", default_config)

    def test_wrong_action(self, default_config: ReviewConfig) -> None:
        event = {
            "action": "closed",
            "pull_request": {"base": {"ref": "main"}},
        }
        assert not should_run(event, "pull_request", default_config)

    def test_wrong_branch(self, default_config: ReviewConfig) -> None:
        event = {
            "action": "opened",
            "pull_request": {"base": {"ref": "develop"}},
        }
        assert not should_run(event, "pull_request", default_config)

    def test_custom_target_branch(self, pr_opened_event: dict[str, object]) -> None:
        config = ReviewConfig(target_branch="develop")
        assert not should_run(pr_opened_event, "pull_request", config)

    def test_matches_custom_target_branch(self) -> None:
        event = {
            "action": "opened",
            "pull_request": {"base": {"ref": "develop"}},
        }
        config = ReviewConfig(target_branch="develop")
        assert should_run(event, "pull_request", config)

    def test_push_event_rejected(self, default_config: ReviewConfig) -> None:
        event = {"ref": "refs/heads/main"}
        assert not should_run(event, "push", default_config)

    def test_missing_pull_request_payload(self, default_config: ReviewConfig) -> None:
        event = {"action": "opened"}
        assert not should_run(event, "pull_request", default_config)


class TestExtractChangedFiles:
    """Tests for _extract_changed_files()."""

    def test_extract_from_diff(self, mock_pr_diff: str) -> None:
        files = _extract_changed_files(mock_pr_diff)
        assert "src/utils.py" in files
        assert "src/main.py" in files
        assert len(files) == 2

    def test_empty_diff(self) -> None:
        assert _extract_changed_files("") == []

    def test_no_plus_lines(self) -> None:
        diff = "--- a/file.py\nsome content\n"
        assert _extract_changed_files(diff) == []


class TestCrossAgentApproval:
    """Tests for _determine_cross_agent_statuses()."""

    def test_all_clean_all_approve(
        self, mock_all_clean_reviews: list[AgentReview]
    ) -> None:
        statuses = _determine_cross_agent_statuses(mock_all_clean_reviews)
        assert all(s == "APPROVE" for s in statuses.values())

    def test_one_critical_mixed_statuses(
        self, mock_mixed_severity_reviews: list[AgentReview]
    ) -> None:
        statuses = _determine_cross_agent_statuses(mock_mixed_severity_reviews)
        assert statuses["claude-reviewer"] == "REQUEST_CHANGES"
        assert statuses["gpt-reviewer"] == "COMMENT"
        assert statuses["gemini-reviewer"] == "COMMENT"

    def test_all_blocking_all_request_changes(self) -> None:
        reviews = [
            AgentReview(
                reviewer="claude-reviewer",
                comments=[
                    ReviewComment(
                        file="a.py", line=1, severity=Severity.CRITICAL, body="Bug"
                    )
                ],
            ),
            AgentReview(
                reviewer="gpt-reviewer",
                comments=[
                    ReviewComment(
                        file="b.py", line=2, severity=Severity.HIGH, body="Issue"
                    )
                ],
            ),
        ]
        statuses = _determine_cross_agent_statuses(reviews)
        assert statuses["claude-reviewer"] == "REQUEST_CHANGES"
        assert statuses["gpt-reviewer"] == "REQUEST_CHANGES"

    def test_critical_only_threshold(self) -> None:
        """With threshold='critical', high is not blocking."""
        reviews = [
            AgentReview(
                reviewer="claude-reviewer",
                comments=[
                    ReviewComment(
                        file="a.py", line=1, severity=Severity.HIGH, body="Issue"
                    )
                ],
            ),
            AgentReview(
                reviewer="gpt-reviewer",
                comments=[],
            ),
        ]
        statuses = _determine_cross_agent_statuses(reviews, "critical")
        assert statuses["claude-reviewer"] == "APPROVE"
        assert statuses["gpt-reviewer"] == "APPROVE"

    def test_empty_reviews_all_approve(self) -> None:
        reviews = [
            AgentReview(reviewer="claude-reviewer", comments=[]),
            AgentReview(reviewer="gpt-reviewer", comments=[]),
            AgentReview(reviewer="gemini-reviewer", comments=[]),
        ]
        statuses = _determine_cross_agent_statuses(reviews)
        assert all(s == "APPROVE" for s in statuses.values())


class TestBuildAgentFailureMessage:
    """Tests for _build_agent_failure_message()."""

    def test_single_failure(self) -> None:
        msg = _build_agent_failure_message(["gpt-reviewer"])
        assert "gpt-reviewer" in msg
        assert "unavailable" in msg

    def test_multiple_failures(self) -> None:
        msg = _build_agent_failure_message(["gpt-reviewer", "gemini-reviewer"])
        assert "gpt-reviewer" in msg
        assert "gemini-reviewer" in msg


class TestInitializeAgents:
    """Tests for _initialize_agents()."""

    def test_missing_credentials_adds_to_failures(self) -> None:
        env = {}
        with patch.dict(os.environ, env, clear=True):
            clients, failures = _initialize_agents("owner/repo", 42)

        assert len(clients) == 0
        assert len(failures) == 3

    def test_auth_failure_adds_to_failures(self) -> None:
        from src.errors import ConfigurationError

        env = {
            "INPUT_CLAUDE_APP_ID": "12345",
            "INPUT_CLAUDE_APP_PRIVATE_KEY": "fake-key",
            "INPUT_ANTHROPIC_API_KEY": "fake-api-key",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "src.main.GitHubClient",
                side_effect=ConfigurationError("Auth failed"),
            ),
        ):
            clients, failures = _initialize_agents("owner/repo", 42)

        assert len(clients) == 0
        assert "claude-reviewer" in failures
        # GPT and Gemini also failed (missing creds)
        assert len(failures) == 3

    def test_partial_success(self) -> None:
        env = {
            "INPUT_CLAUDE_APP_ID": "12345",
            "INPUT_CLAUDE_APP_PRIVATE_KEY": "fake-key",
            "INPUT_ANTHROPIC_API_KEY": "fake-api-key",
            "INPUT_GPT_APP_ID": "67890",
            "INPUT_GPT_APP_PRIVATE_KEY": "fake-key-2",
            "INPUT_OPENAI_API_KEY": "fake-openai-key",
        }
        mock_client = MagicMock()
        with (
            patch.dict(os.environ, env, clear=True),
            patch("src.main.GitHubClient", return_value=mock_client),
        ):
            clients, failures = _initialize_agents("owner/repo", 42)

        assert len(clients) == 2
        assert "claude-reviewer" in clients
        assert "gpt-reviewer" in clients
        assert len(failures) == 1
        assert "gemini-reviewer" in failures


class TestRunOrchestration:
    """Integration-style tests for the run() function."""

    @pytest.mark.asyncio()
    async def test_missing_event_path_exits_cleanly(self) -> None:
        env = {"GITHUB_EVENT_PATH": "", "GITHUB_EVENT_NAME": ""}
        with patch.dict(os.environ, env, clear=True):
            await run()  # Should not raise

    @pytest.mark.asyncio()
    async def test_wrong_event_type_exits_cleanly(self, tmp_path: Path) -> None:
        event_file = tmp_path / "event.json"
        event_file.write_text(json.dumps({"action": "created"}))

        env = {
            "GITHUB_EVENT_PATH": str(event_file),
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_WORKSPACE": str(tmp_path),
        }
        with patch.dict(os.environ, env, clear=True):
            await run()  # Should exit cleanly without error

    @pytest.mark.asyncio()
    async def test_all_files_filtered_posts_summary(
        self, tmp_path: Path, pr_opened_event: dict[str, object]
    ) -> None:
        event_file = tmp_path / "event.json"
        event_file.write_text(json.dumps(pr_opened_event))

        env = {
            "GITHUB_EVENT_PATH": str(event_file),
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_WORKSPACE": str(tmp_path),
            "INPUT_CLAUDE_APP_ID": "12345",
            "INPUT_CLAUDE_APP_PRIVATE_KEY": "fake-key",
            "INPUT_ANTHROPIC_API_KEY": "fake-api-key",
        }

        mock_client = AsyncMock()
        mock_client.get_pr_diff = AsyncMock(
            return_value=(
                "diff --git a/package-lock.json b/package-lock.json\n"
                "--- a/package-lock.json\n"
                "+++ b/package-lock.json\n"
                "@@ -1,1 +1,1 @@\n"
                "+updated\n"
            )
        )

        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "src.main._initialize_agents",
                return_value=({"claude-reviewer": mock_client}, []),
            ),
        ):
            await run()

        mock_client.post_issue_comment.assert_called_once()
        call_args = mock_client.post_issue_comment.call_args
        assert "ignore patterns" in call_args.args[0]

    @pytest.mark.asyncio()
    async def test_engine_failure_exits_cleanly(
        self, tmp_path: Path, pr_opened_event: dict[str, object]
    ) -> None:
        event_file = tmp_path / "event.json"
        event_file.write_text(json.dumps(pr_opened_event))

        env = {
            "GITHUB_EVENT_PATH": str(event_file),
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_WORKSPACE": str(tmp_path),
            "INPUT_CLAUDE_APP_ID": "12345",
            "INPUT_CLAUDE_APP_PRIVATE_KEY": "fake-key",
            "INPUT_ANTHROPIC_API_KEY": "fake-api-key",
        }

        mock_client = AsyncMock()
        mock_client.get_pr_diff = AsyncMock(
            return_value=(
                "diff --git a/src/app.py b/src/app.py\n"
                "--- a/src/app.py\n"
                "+++ b/src/app.py\n"
                "@@ -1,1 +1,2 @@\n"
                "+new code\n"
            )
        )
        mock_client.get_file_content = AsyncMock(return_value="file content")

        from src.errors import EngineError

        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "src.main._initialize_agents",
                return_value=({"claude-reviewer": mock_client}, []),
            ),
            patch(
                "src.main.EngineManager",
                side_effect=EngineError("Docker not available"),
            ),
        ):
            await run()  # Should not raise

        mock_client.post_issue_comment.assert_called()

    @pytest.mark.asyncio()
    async def test_oversized_pr_posts_summary(
        self, tmp_path: Path, pr_opened_event: dict[str, object]
    ) -> None:
        event_file = tmp_path / "event.json"
        event_file.write_text(json.dumps(pr_opened_event))

        lines = ["diff --git a/big.py b/big.py\n", "--- a/big.py\n", "+++ b/big.py\n"]
        lines.append("@@ -1,1 +1,6000 @@\n")
        for i in range(5500):
            lines.append(f"+line {i}\n")
        big_diff = "".join(lines)

        env = {
            "GITHUB_EVENT_PATH": str(event_file),
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_WORKSPACE": str(tmp_path),
            "INPUT_CLAUDE_APP_ID": "12345",
            "INPUT_CLAUDE_APP_PRIVATE_KEY": "fake-key",
            "INPUT_ANTHROPIC_API_KEY": "fake-api-key",
        }

        mock_client = AsyncMock()
        mock_client.get_pr_diff = AsyncMock(return_value=big_diff)

        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "src.main._initialize_agents",
                return_value=({"claude-reviewer": mock_client}, []),
            ),
        ):
            await run()

        mock_client.post_issue_comment.assert_called_once()
        call_args = mock_client.post_issue_comment.call_args
        assert "too large" in call_args.args[0]


class TestAgentFailureIsolation:
    """Tests for agent failure isolation during orchestration."""

    @pytest.mark.asyncio()
    async def test_one_auth_failure_others_proceed(
        self, tmp_path: Path, pr_opened_event: dict[str, object]
    ) -> None:
        """One agent auth failure doesn't prevent others from reviewing."""
        event_file = tmp_path / "event.json"
        event_file.write_text(json.dumps(pr_opened_event))

        diff = (
            "diff --git a/src/app.py b/src/app.py\n"
            "--- a/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@ -1,1 +1,2 @@\n"
            "+new code\n"
        )

        env = {
            "GITHUB_EVENT_PATH": str(event_file),
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_WORKSPACE": str(tmp_path),
        }

        mock_claude_client = AsyncMock()
        mock_claude_client.get_pr_diff = AsyncMock(return_value=diff)
        mock_claude_client.get_file_content = AsyncMock(return_value="content")

        mock_gpt_client = AsyncMock()

        # claude and gpt init OK, gemini failed
        agent_clients = {
            "claude-reviewer": mock_claude_client,
            "gpt-reviewer": mock_gpt_client,
        }
        agent_failures = ["gemini-reviewer"]

        reviews = [
            AgentReview(reviewer="claude-reviewer", comments=[]),
            AgentReview(reviewer="gpt-reviewer", comments=[]),
        ]

        mock_engine = AsyncMock()
        mock_engine.__aenter__ = AsyncMock(return_value=mock_engine)
        mock_engine.__aexit__ = AsyncMock(return_value=None)

        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "src.main._initialize_agents",
                return_value=(agent_clients, agent_failures),
            ),
            patch("src.main.EngineManager", return_value=mock_engine),
            patch("src.main.PipelineRunner") as mock_runner_cls,
            patch("src.main.deduplicate_reviews", return_value=reviews),
            patch("src.main.post_agent_review") as mock_post,
        ):
            mock_runner = AsyncMock()
            mock_runner.run_full_review = AsyncMock(return_value=(reviews, []))
            mock_runner_cls.return_value = mock_runner

            await run()

        # Two reviews posted (claude + gpt)
        assert mock_post.call_count == 2
        # Failure message posted about gemini
        mock_claude_client.post_issue_comment.assert_called()
        failure_call = mock_claude_client.post_issue_comment.call_args
        assert "gemini-reviewer" in failure_call.args[0]

    @pytest.mark.asyncio()
    async def test_posting_failure_continues(
        self, tmp_path: Path, pr_opened_event: dict[str, object]
    ) -> None:
        """If posting one agent's review fails, others still post."""
        event_file = tmp_path / "event.json"
        event_file.write_text(json.dumps(pr_opened_event))

        diff = (
            "diff --git a/src/app.py b/src/app.py\n"
            "--- a/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@ -1,1 +1,2 @@\n"
            "+new code\n"
        )

        env = {
            "GITHUB_EVENT_PATH": str(event_file),
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_WORKSPACE": str(tmp_path),
        }

        mock_claude_client = AsyncMock()
        mock_claude_client.get_pr_diff = AsyncMock(return_value=diff)
        mock_claude_client.get_file_content = AsyncMock(return_value="content")

        mock_gpt_client = AsyncMock()

        agent_clients = {
            "claude-reviewer": mock_claude_client,
            "gpt-reviewer": mock_gpt_client,
        }

        reviews = [
            AgentReview(reviewer="claude-reviewer", comments=[]),
            AgentReview(reviewer="gpt-reviewer", comments=[]),
        ]

        mock_engine = AsyncMock()
        mock_engine.__aenter__ = AsyncMock(return_value=mock_engine)
        mock_engine.__aexit__ = AsyncMock(return_value=None)

        call_count = 0

        async def mock_post_side_effect(**kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("GitHub API error")

        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "src.main._initialize_agents",
                return_value=(agent_clients, []),
            ),
            patch("src.main.EngineManager", return_value=mock_engine),
            patch("src.main.PipelineRunner") as mock_runner_cls,
            patch("src.main.deduplicate_reviews", return_value=reviews),
            patch(
                "src.main.post_agent_review",
                side_effect=mock_post_side_effect,
            ) as mock_post,
        ):
            mock_runner = AsyncMock()
            mock_runner.run_full_review = AsyncMock(return_value=(reviews, []))
            mock_runner_cls.return_value = mock_runner

            await run()  # Should not raise

        # Both were attempted
        assert mock_post.call_count == 2

    @pytest.mark.asyncio()
    async def test_no_agents_initialized_aborts(
        self, tmp_path: Path, pr_opened_event: dict[str, object]
    ) -> None:
        """If no agents could be initialized, abort without crashing."""
        event_file = tmp_path / "event.json"
        event_file.write_text(json.dumps(pr_opened_event))

        env = {
            "GITHUB_EVENT_PATH": str(event_file),
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_WORKSPACE": str(tmp_path),
        }

        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "src.main._initialize_agents",
                return_value=(
                    {},
                    ["claude-reviewer", "gpt-reviewer", "gemini-reviewer"],
                ),
            ),
        ):
            await run()  # Should not raise
