"""Configuration loading and project-wide constants.

Loads configuration from environment variables (action inputs) and an
optional .rocketride-review.yml file from the repository root. All model
names, bot usernames, and agent routing are defined here as constants.
"""

from __future__ import annotations

# Model identifiers (not user-configurable in v1)
MODELS: dict[str, str] = {
    "claude-reviewer": "claude-sonnet-4-20250514",
    "gpt-reviewer": "gpt-4o",
    "gemini-reviewer": "gemini-2.0-flash",
    "aggregator": "claude-sonnet-4-20250514",
}

# Maps GitHub App bot username to RocketRide pipeline node ID
AGENT_ROUTING: dict[str, str] = {
    "claude-reviewer[bot]": "claude-reviewer",
    "gpt-reviewer[bot]": "gpt-reviewer",
    "gemini-reviewer[bot]": "gemini-reviewer",
}

# All bot usernames (for loop prevention)
BOT_USERNAMES: set[str] = set(AGENT_ROUTING.keys())

# Default file ignore patterns
DEFAULT_IGNORE_PATTERNS: list[str] = [
    "*.lock",
    "*.min.js",
    "*.min.css",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "*.generated.*",
    "*.g.dart",
    "*.pb.go",
    "dist/**",
    "build/**",
    "vendor/**",
    "node_modules/**",
    "*.svg",
    "*.png",
    "*.jpg",
    "*.gif",
    "*.ico",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.eot",
]

# Engine health check settings
ENGINE_HEALTH_CHECK_INTERVAL: float = 2.0
ENGINE_HEALTH_CHECK_TIMEOUT: float = 30.0
ENGINE_PORT: int = 5565

# Retry settings
MAX_RETRIES: int = 3
RETRY_BACKOFF_BASE: float = 1.0
