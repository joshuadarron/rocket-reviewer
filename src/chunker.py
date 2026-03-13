"""Large PR diff chunking and line number remapping.

Splits diffs at file boundaries, then at function/class boundaries for
oversized files. Includes overlap context between segments and remaps
line numbers back to original diff coordinates after merge.
"""

from __future__ import annotations


def chunk_diff(
    diff: str,
    max_chunk_lines: int = 500,
    overlap_lines: int = 20,
) -> list[str]:
    """Split a diff into reviewable chunks.

    Args:
        diff: The full unified diff string.
        max_chunk_lines: Maximum lines per chunk.
        overlap_lines: Lines of overlap context between segments.

    Returns:
        List of diff chunk strings.
    """
    raise NotImplementedError


def remap_line_numbers(
    comments: list[dict[str, object]],
    chunk_offsets: list[int],
) -> list[dict[str, object]]:
    """Remap comment line numbers from chunk-local to original diff coordinates.

    Args:
        comments: Comments with chunk-local line numbers.
        chunk_offsets: Starting line offset for each chunk.

    Returns:
        Comments with remapped line numbers.
    """
    raise NotImplementedError
