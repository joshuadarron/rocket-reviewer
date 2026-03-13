"""GitHub API wrapper for PR data, diffs, comments, and reviews.

Handles authentication via GitHub App installation tokens and provides
methods for fetching PR metadata, posting inline review comments, and
submitting review statuses.
"""

from __future__ import annotations


class GitHubClient:
    """Wrapper around PyGithub for PR review operations."""

    async def get_pr_diff(self) -> str:
        """Fetch the unified diff for a pull request."""
        raise NotImplementedError

    async def get_pr_metadata(self) -> dict[str, object]:
        """Fetch PR metadata (target branch, author, changed files)."""
        raise NotImplementedError

    async def get_file_content(self, path: str) -> str:
        """Fetch full content of a file at the PR's head ref."""
        raise NotImplementedError

    async def post_review_comment(
        self,
        body: str,
        path: str,
        line: int,
    ) -> None:
        """Post an inline review comment on a PR."""
        raise NotImplementedError

    async def submit_review(self, status: str, body: str) -> None:
        """Submit a review with the given status (approve/request_changes/comment)."""
        raise NotImplementedError
