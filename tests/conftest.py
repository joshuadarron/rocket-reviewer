"""Shared test fixtures for rocketride-reviewer tests."""

from __future__ import annotations

import pytest

from src.models import (
    AgentReview,
    CommentStatus,
    ReviewComment,
    ReviewConfig,
    Severity,
)


@pytest.fixture()
def mock_pr_diff() -> str:
    """A realistic multi-file diff string."""
    return (
        "diff --git a/src/utils.py b/src/utils.py\n"
        "index abc1234..def5678 100644\n"
        "--- a/src/utils.py\n"
        "+++ b/src/utils.py\n"
        "@@ -10,6 +10,8 @@ def helper():\n"
        "     existing_line = True\n"
        "+    new_line = False\n"
        "+    another_line = True\n"
        "     more_existing = 1\n"
        "diff --git a/src/main.py b/src/main.py\n"
        "index 1234567..89abcde 100644\n"
        "--- a/src/main.py\n"
        "+++ b/src/main.py\n"
        "@@ -1,3 +1,5 @@\n"
        " import os\n"
        "+import sys\n"
        "+import json\n"
        " \n"
    )


@pytest.fixture()
def mock_pr_comments() -> list[dict[str, str]]:
    """A list of existing PR comments with thread structure."""
    return [
        {
            "id": "1",
            "author": "developer",
            "body": "Should we refactor this?",
            "path": "src/utils.py",
            "line": "11",
        },
        {
            "id": "2",
            "author": "claude-reviewer[bot]",
            "body": "Consider extracting this into a helper function.",
            "path": "src/utils.py",
            "line": "11",
            "in_reply_to": "1",
        },
    ]


@pytest.fixture()
def mock_agent_response_clean() -> AgentReview:
    """A valid agent response with zero critical/high comments."""
    return AgentReview(
        reviewer="claude-reviewer",
        comments=[
            ReviewComment(
                file="src/utils.py",
                line=11,
                severity=Severity.LOW,
                status=CommentStatus.ADD,
                body="Consider using a more descriptive variable name.",
            ),
            ReviewComment(
                file="src/main.py",
                line=2,
                severity=Severity.NITPICK,
                status=CommentStatus.ADD,
                body="Unused import: sys.",
            ),
        ],
    )


@pytest.fixture()
def mock_agent_response_issues() -> AgentReview:
    """A valid agent response with mixed severity comments."""
    return AgentReview(
        reviewer="gpt-reviewer",
        comments=[
            ReviewComment(
                file="src/utils.py",
                line=11,
                severity=Severity.HIGH,
                status=CommentStatus.ADD,
                body="Potential null reference on this line.",
            ),
            ReviewComment(
                file="src/main.py",
                line=2,
                severity=Severity.MEDIUM,
                status=CommentStatus.ADD,
                body="Import json but never use it.",
            ),
        ],
    )


@pytest.fixture()
def mock_agent_response_malformed() -> dict[str, object]:
    """An invalid agent response (missing fields, wrong types)."""
    return {
        "reviewer": 12345,
        "comments": [
            {"file": "src/utils.py", "line": "not_a_number", "body": "oops"},
            {"severity": "invalid_severity"},
        ],
    }


@pytest.fixture()
def mock_config_default() -> ReviewConfig:
    """Default configuration object."""
    return ReviewConfig()


@pytest.fixture()
def mock_config_custom() -> ReviewConfig:
    """Configuration with custom ignore patterns and diff-only mode."""
    return ReviewConfig(
        review_context="diff",
        target_branch="develop",
        approval_threshold="critical",
        ignore_patterns_extra=["migrations/**", "*.sql"],
        max_chunk_lines=300,
    )


@pytest.fixture()
def mock_large_diff() -> str:
    """A diff exceeding 500 lines for chunking tests."""
    lines = ["diff --git a/big_file.py b/big_file.py\n"]
    lines.append("--- a/big_file.py\n")
    lines.append("+++ b/big_file.py\n")
    lines.append("@@ -1,600 +1,600 @@\n")
    for i in range(600):
        lines.append(f"+    line_{i} = {i}\n")
    return "".join(lines)


@pytest.fixture()
def mock_oversized_pr() -> dict[str, int]:
    """Metadata for a diff exceeding max files/lines thresholds."""
    return {"changed_files": 60, "total_lines": 6000}


# --- Phase 2 multi-agent fixtures ---


@pytest.fixture()
def mock_three_agent_reviews() -> list[AgentReview]:
    """Three agent reviews with some duplicate comments across agents."""
    return [
        AgentReview(
            reviewer="claude-reviewer",
            comments=[
                ReviewComment(
                    file="src/utils.py",
                    line=11,
                    severity=Severity.MEDIUM,
                    body="Consider using a more descriptive variable name here.",
                ),
                ReviewComment(
                    file="src/main.py",
                    line=3,
                    severity=Severity.LOW,
                    body="Unused import: json.",
                ),
            ],
        ),
        AgentReview(
            reviewer="gpt-reviewer",
            comments=[
                ReviewComment(
                    file="src/utils.py",
                    line=12,
                    severity=Severity.MEDIUM,
                    body="Consider using a more descriptive variable name.",
                ),
                ReviewComment(
                    file="src/config.py",
                    line=5,
                    severity=Severity.NITPICK,
                    body="Minor style issue with spacing.",
                ),
            ],
        ),
        AgentReview(
            reviewer="gemini-reviewer",
            comments=[
                ReviewComment(
                    file="src/utils.py",
                    line=11,
                    severity=Severity.MEDIUM,
                    body="Use a more descriptive variable name for clarity.",
                ),
                ReviewComment(
                    file="tests/test_main.py",
                    line=20,
                    severity=Severity.LOW,
                    body="Test could be more specific about expected output.",
                ),
            ],
        ),
    ]


@pytest.fixture()
def mock_all_clean_reviews() -> list[AgentReview]:
    """Three agent reviews with only low/nitpick severity (all should approve)."""
    return [
        AgentReview(
            reviewer="claude-reviewer",
            comments=[
                ReviewComment(
                    file="src/main.py",
                    line=5,
                    severity=Severity.LOW,
                    body="Consider renaming this variable.",
                ),
            ],
        ),
        AgentReview(
            reviewer="gpt-reviewer",
            comments=[
                ReviewComment(
                    file="src/main.py",
                    line=10,
                    severity=Severity.NITPICK,
                    body="Minor style suggestion.",
                ),
            ],
        ),
        AgentReview(
            reviewer="gemini-reviewer",
            comments=[],
        ),
    ]


@pytest.fixture()
def mock_mixed_severity_reviews() -> list[AgentReview]:
    """One agent has critical issue, others don't."""
    return [
        AgentReview(
            reviewer="claude-reviewer",
            comments=[
                ReviewComment(
                    file="src/auth.py",
                    line=15,
                    severity=Severity.CRITICAL,
                    body="SQL injection vulnerability — user input not sanitized.",
                ),
            ],
        ),
        AgentReview(
            reviewer="gpt-reviewer",
            comments=[
                ReviewComment(
                    file="src/main.py",
                    line=10,
                    severity=Severity.LOW,
                    body="Consider adding a docstring.",
                ),
            ],
        ),
        AgentReview(
            reviewer="gemini-reviewer",
            comments=[
                ReviewComment(
                    file="src/utils.py",
                    line=5,
                    severity=Severity.MEDIUM,
                    body="This function could be simplified.",
                ),
            ],
        ),
    ]
