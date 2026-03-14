"""Entry point: event detection, gating, and orchestration.

Reads the GitHub event payload, checks trigger conditions (target branch,
event type, comment author), and orchestrates the multi-agent review
pipeline. The top-level handler catches all exceptions, logs errors, posts
a summary comment if possible, and always exits with code 0.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from src.aggregator import deduplicate_reviews
from src.config import AGENT_CREDENTIALS, load_config
from src.engine import EngineManager
from src.errors import ConfigurationError
from src.filters import get_effective_patterns, should_ignore
from src.github_client import GitHubClient
from src.models import AgentReview, ReviewConfig, Severity
from src.pipeline import PipelineRunner
from src.reviewer import post_agent_review

logger = logging.getLogger(__name__)


def should_run(event: dict[str, object], event_name: str, config: ReviewConfig) -> bool:
    """Check whether the review should proceed based on the event.

    Args:
        event: Parsed GitHub event payload.
        event_name: GitHub event name (e.g., ``pull_request``).
        config: Loaded review configuration.

    Returns:
        True if the review should run.
    """
    if event_name != "pull_request":
        logger.info("Skipping: event type is '%s', not 'pull_request'", event_name)
        return False

    action = event.get("action")
    if action not in ("opened", "synchronize"):
        logger.info("Skipping: PR action is '%s'", action)
        return False

    pr = event.get("pull_request", {})
    if not isinstance(pr, dict):
        logger.info("Skipping: missing pull_request payload")
        return False

    base = pr.get("base", {})
    if not isinstance(base, dict):
        logger.info("Skipping: missing base branch info")
        return False

    target_branch = base.get("ref", "")
    if target_branch != config.target_branch:
        logger.info(
            "Skipping: target branch '%s' != configured '%s'",
            target_branch,
            config.target_branch,
        )
        return False

    return True


def _extract_changed_files(diff: str) -> list[str]:
    """Parse changed file paths from a unified diff.

    Args:
        diff: Raw unified diff string.

    Returns:
        List of file paths that were changed.
    """
    files: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:])
    return files


def _initialize_agents(
    repo_name: str,
    pr_number: int,
) -> tuple[dict[str, GitHubClient], list[str]]:
    """Initialize GitHub clients for all configured agents.

    For each agent in ``AGENT_CREDENTIALS``, reads environment variables
    for app ID, private key, and API key. On auth failure, logs a warning
    and adds the agent to the failures list.

    Args:
        repo_name: Full repository name (e.g., ``owner/repo``).
        pr_number: Pull request number.

    Returns:
        A tuple of (mapping of agent name to GitHubClient, list of
        agent names that failed to initialize).
    """
    clients: dict[str, GitHubClient] = {}
    failures: list[str] = []

    for cred in AGENT_CREDENTIALS:
        name = cred["name"]
        app_id_str = os.environ.get(cred["app_id_env"], "")
        private_key = os.environ.get(cred["key_env"], "")
        api_key = os.environ.get(cred["api_key_env"], "")

        if not app_id_str or not private_key:
            logger.warning("Credentials not configured for %s — skipping agent", name)
            failures.append(name)
            continue

        if not api_key:
            logger.warning("API key not configured for %s — skipping agent", name)
            failures.append(name)
            continue

        try:
            app_id = int(app_id_str)
            client = GitHubClient(
                app_id=app_id,
                private_key=private_key,
                repo_name=repo_name,
                pr_number=pr_number,
            )
        except (ConfigurationError, ValueError) as e:
            logger.warning("Failed to initialize %s: %s", name, e)
            failures.append(name)
            continue

        # Set the LLM API key in the environment for the pipeline
        os.environ.setdefault(cred["api_key_target"], api_key)
        clients[name] = client

    return clients, failures


def _determine_cross_agent_statuses(
    reviews: list[AgentReview],
    approval_threshold: str = "high",
) -> dict[str, str]:
    """Compute review statuses based on findings across all agents.

    If no agent found critical/high issues, all agents approve. If any
    agent found blocking issues, that agent requests changes while
    others post as comment.

    Args:
        reviews: List of all agent reviews.
        approval_threshold: Severity at or above which approval is
            blocked (``"critical"`` or ``"high"``).

    Returns:
        Mapping of reviewer name to review status string.
    """
    blocking_severities: set[Severity] = {Severity.CRITICAL}
    if approval_threshold == "high":
        blocking_severities.add(Severity.HIGH)

    # Determine which agents found blocking issues
    flagging_agents: set[str] = set()
    for review in reviews:
        for comment in review.comments:
            if comment.severity in blocking_severities:
                flagging_agents.add(review.reviewer)
                break

    statuses: dict[str, str] = {}
    if not flagging_agents:
        # No blocking issues anywhere — all approve
        for review in reviews:
            statuses[review.reviewer] = "APPROVE"
    else:
        # Some agents found issues
        for review in reviews:
            if review.reviewer in flagging_agents:
                statuses[review.reviewer] = "REQUEST_CHANGES"
            else:
                statuses[review.reviewer] = "COMMENT"

    return statuses


def _build_agent_failure_message(failed_agents: list[str]) -> str:
    """Build a human-readable message about agents that failed.

    Args:
        failed_agents: List of agent names that were unavailable.

    Returns:
        Formatted markdown string for posting as a PR comment.
    """
    agent_list = ", ".join(failed_agents)
    return (
        f"The following reviewer(s) were unavailable for this review: "
        f"{agent_list}. See workflow logs for details."
    )


async def _post_summary_comment(client: GitHubClient, message: str) -> None:
    """Post a summary comment on the PR. Best-effort."""
    try:
        await client.post_issue_comment(message)
    except Exception:
        logger.exception("Failed to post summary comment")


async def run() -> None:
    """Execute the multi-agent review pipeline.

    This is the top-level entry point. It catches all exceptions, logs
    errors, posts a summary comment on the PR if possible, and always
    exits with code 0 so that a failed review never blocks CI.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    primary_client: GitHubClient | None = None

    try:
        # Load event payload
        event_path = os.environ.get("GITHUB_EVENT_PATH", "")
        event_name = os.environ.get("GITHUB_EVENT_NAME", "")

        if not event_path or not Path(event_path).is_file():
            logger.error("GITHUB_EVENT_PATH not set or file missing")
            return

        event = json.loads(Path(event_path).read_text(encoding="utf-8"))

        # Load config
        repo_root = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd()))
        config = load_config(repo_root)

        # Gating
        if not should_run(event, event_name, config):
            return

        # Extract PR info from event
        pr_data = event.get("pull_request", {})
        repo_name = event.get("repository", {}).get("full_name", "")
        pr_number = pr_data.get("number", 0)

        if not repo_name or not pr_number:
            logger.error("Could not determine repo name or PR number from event")
            return

        # Initialize all agents
        agent_clients, agent_failures = _initialize_agents(repo_name, pr_number)

        if not agent_clients:
            logger.error("No agents could be initialized — aborting review")
            return

        # Use first available client as primary for diff fetching
        primary_client = next(iter(agent_clients.values()))

        # Fetch diff
        diff = await primary_client.get_pr_diff()

        # Filter files
        changed_files = _extract_changed_files(diff)
        patterns = get_effective_patterns(
            extra=config.ignore_patterns_extra,
            override=config.ignore_patterns_override,
        )
        reviewed_files = [f for f in changed_files if not should_ignore(f, patterns)]

        if not reviewed_files:
            logger.info("All changed files are filtered out — skipping review")
            await _post_summary_comment(
                primary_client,
                "All changed files match ignore patterns. No review performed.",
            )
            return

        # Check oversized PR
        total_lines = diff.count("\n")
        too_many_files = len(reviewed_files) > config.max_files
        too_many_lines = total_lines > config.max_total_lines
        if too_many_files or too_many_lines:
            msg = (
                f"PR is too large for automated review "
                f"({len(reviewed_files)} files, ~{total_lines} lines). "
                f"Limits: {config.max_files} files, {config.max_total_lines} lines."
            )
            logger.info(msg)
            await _post_summary_comment(primary_client, msg)
            return

        # Fetch file context if in full mode
        file_context: dict[str, str] | None = None
        if config.review_context == "full":
            file_context = {}
            for file_path in reviewed_files:
                try:
                    content = await primary_client.get_file_content(file_path)
                    file_context[file_path] = content
                except Exception:
                    logger.warning("Could not fetch content for %s", file_path)

        # Start engine and run pipeline
        async with EngineManager() as _engine:
            runner = PipelineRunner()
            reviews, pipeline_failures = await runner.run_full_review(
                diff=diff,
                file_context=file_context,
                review_mode=config.review_context,
            )

        # Merge pipeline failures into agent failures
        agent_failures.extend(pipeline_failures)

        # Deduplicate
        reviews = deduplicate_reviews(reviews)

        # Compute cross-agent review statuses
        statuses = _determine_cross_agent_statuses(reviews, config.approval_threshold)

        # Post each review under its own app identity
        for review in reviews:
            client = agent_clients.get(review.reviewer)
            if client is None:
                logger.warning(
                    "No client for %s — skipping review posting", review.reviewer
                )
                continue

            try:
                await post_agent_review(
                    review=review,
                    github_client=client,
                    approval_threshold=config.approval_threshold,
                    review_status=statuses.get(review.reviewer),
                )
            except Exception:
                logger.exception("Failed to post review for %s", review.reviewer)

        # Report agent failures
        if agent_failures:
            failure_msg = _build_agent_failure_message(agent_failures)
            await _post_summary_comment(primary_client, failure_msg)

        logger.info("Review complete")

    except Exception:
        logger.exception("Review failed with unexpected error")
        if primary_client is not None:
            await _post_summary_comment(
                primary_client,
                "\u26a0\ufe0f RocketRide Reviewer encountered an unexpected error. "
                "See workflow logs for details.",
            )


if __name__ == "__main__":
    asyncio.run(run())
