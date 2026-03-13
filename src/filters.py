"""File filtering logic for excluding files from review.

Matches files against configurable ignore patterns (fnmatch/glob style).
Supports default patterns, user extensions, and full overrides.
"""

from __future__ import annotations


def should_ignore(file_path: str, patterns: list[str]) -> bool:
    """Check if a file path matches any of the ignore patterns.

    Args:
        file_path: Relative file path to check.
        patterns: List of glob/fnmatch patterns.

    Returns:
        True if the file should be ignored.
    """
    raise NotImplementedError


def get_effective_patterns(
    extra: list[str] | None = None,
    override: list[str] | None = None,
) -> list[str]:
    """Build the effective ignore pattern list.

    If override is provided, it replaces the defaults entirely.
    Otherwise, extra patterns are appended to the defaults.

    Args:
        extra: Additional patterns to append to defaults.
        override: If set, replaces all default patterns.

    Returns:
        The effective list of ignore patterns.
    """
    raise NotImplementedError
